from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from training.model_quality import (
    LEGAL_PROBES,
    audit_dataset,
    audit_splits,
    evaluate_answers,
    record_fingerprint,
    score_answer,
)
from training.finetune_kaggle_safe import CompletionOnlyCollator


def record(index: int, *, category: str = "statutory_mapping", output: str | None = None) -> dict:
    return {
        "id": f"record-{index}",
        "category": category,
        "instruction": f"Explain statutory rule {index}",
        "input": "",
        "output": output or f"The relevant statutory rule number {index} remains applicable.",
    }


class DatasetAuditTests(unittest.TestCase):
    def test_fingerprint_ignores_case_and_whitespace(self) -> None:
        left = record(1)
        right = dict(left, instruction="  EXPLAIN   statutory rule 1  ")
        self.assertEqual(record_fingerprint(left), record_fingerprint(right))

    def test_audit_rejects_fabricated_law(self) -> None:
        report = audit_dataset(
            [record(1, output="The B.P. Singh Penal Code replaced the IPC.")],
            split_name="train",
        )
        self.assertFalse(report["passed"])
        self.assertIn("fabricated", report["errors"][0])

    def test_audit_rejects_wrong_bnss_year(self) -> None:
        report = audit_dataset(
            [record(1, output="The Bharatiya Nagarik Suraksha Sanhita (BNSS), 2020 applies.")],
            split_name="train",
        )
        self.assertFalse(report["passed"])
        self.assertTrue(any("false legal claim" in error for error in report["errors"]))

    def test_audit_rejects_split_leakage(self) -> None:
        train = [record(index) for index in range(60)]
        validation = [record(index) for index in range(55, 70)]
        report = audit_splits(train, validation)
        self.assertFalse(report["passed"])
        self.assertEqual(report["overlap"]["train__validation"], 5)

    def test_audit_accepts_clean_splits(self) -> None:
        report = audit_splits(
            [record(index) for index in range(60)],
            [record(index) for index in range(100, 115)],
        )
        self.assertTrue(report["passed"])

    def test_audit_warns_about_imbalanced_categories(self) -> None:
        records = [record(index, category="dominant") for index in range(75)]
        records.extend(record(index, category="other") for index in range(75, 100))
        report = audit_dataset(records, split_name="validation")
        self.assertTrue(report["passed"])
        self.assertTrue(any("imbalanced" in warning for warning in report["warnings"]))


class LegalQualityGateTests(unittest.TestCase):
    def test_correct_ipc_successor_passes(self) -> None:
        probe = next(item for item in LEGAL_PROBES if item.name == "ipc_successor")
        result = score_answer(probe, "The Bharatiya Nyaya Sanhita, 2023 replaced the IPC.")
        self.assertTrue(result["passed"])

    def test_previous_kaggle_hallucination_fails(self) -> None:
        probe = next(item for item in LEGAL_PROBES if item.name == "ipc_successor")
        result = score_answer(probe, "The B.P. Singh Penal Code replaced the IPC under Mission 250.")
        self.assertFalse(result["passed"])
        self.assertTrue(result["fabricated_patterns"])

    def test_false_pocso_repeal_fails(self) -> None:
        probe = next(item for item in LEGAL_PROBES if item.name == "pocso_independent")
        result = score_answer(probe, "No, BNS replaced POCSO in 2023.")
        self.assertFalse(result["passed"])
        self.assertTrue(result["forbidden_patterns"])

    def test_release_requires_every_critical_probe(self) -> None:
        answers = {
            "ipc_successor": "Bharatiya Nyaya Sanhita, 2023",
            "crpc_successor": "Bharatiya Nagarik Suraksha Sanhita, 2023",
            "evidence_successor": "Bharatiya Sakshya Adhiniyam, 2023",
            "pocso_independent": "No, POCSO remains a separate statute.",
            "bns_not_procedure": "No. BNSS governs criminal procedure.",
            "retrospective_substantive_law": "The IPC applies because substantive law is not retrospective; BNS section 358 preserves prior liability.",
            "procedural_savings": "BNS section 358 and BNSS section 531 contain savings provisions.",
            "zero_fir": "Under BNSS section 173, a Zero FIR may be registered irrespective of territorial jurisdiction.",
            "pocso_age": "No. A child under 18 remains protected.",
            "electronic_evidence": "Bharatiya Sakshya Adhiniyam governs electronic evidence under sections 61 to 63.",
        }
        report = evaluate_answers(answers)
        self.assertTrue(report["release_ready"])
        self.assertEqual(report["accuracy"], 1.0)

        answers["pocso_independent"] = "Yes, BNS replaced POCSO."
        report = evaluate_answers(answers, minimum_accuracy=0.8)
        self.assertFalse(report["release_ready"])
        self.assertIn("pocso_independent", report["critical_failures"])

    def test_actual_kaggle_r2_errors_are_all_rejected(self) -> None:
        answers = {
            "ipc_successor": "The Indian Penal Code, 1860 has been replaced by the Bharatiya Nyaya Sanhita (BNS).",
            "crpc_successor": "The Code of Criminal Procedure, 1973 has been replaced by the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2020.",
            "evidence_successor": "The Indian Evidence Act, 1872 has been replaced by the Bharatiya Sakshya Adhiniyam, 2023 (BSA).",
            "pocso_independent": "The POCSO Act, 2012 remains an independent special statute.",
            "bns_not_procedure": "The CrPC has been replaced by the Bharatiya Nagarik Suraksha Sanhita (BNSS).",
            "retrospective_substantive_law": "The offence occurred on 29 June 2024, so BNS applies to this case.",
            "procedural_savings": "Section 6 of the Code of Criminal Procedure (Amendment) Act, 2020 applies from 1 September 2023.",
            "zero_fir": "Under Section 157(1) of the BNSS, information may be recorded irrespective of jurisdiction.",
            "pocso_age": "A person below 18 is a child under POCSO.",
            "electronic_evidence": "The Information Technology Act governs electronic evidence; section 65B of the BSA does not apply.",
        }
        report = evaluate_answers(answers)
        self.assertFalse(report["release_ready"])
        self.assertLessEqual(report["accuracy"], 0.5)
        for name in (
            "crpc_successor",
            "retrospective_substantive_law",
            "procedural_savings",
            "zero_fir",
            "electronic_evidence",
        ):
            self.assertIn(name, report["critical_failures"])


class CompletionOnlyCollatorTests(unittest.TestCase):
    def test_reconstructs_attention_mask_when_trainer_removes_it(self) -> None:
        fake_torch = SimpleNamespace(long="long", tensor=lambda value, dtype: value)
        collator = CompletionOnlyCollator(tokenizer=SimpleNamespace(pad_token_id=0))
        features = [
            {"input_ids": [1, 2, 3], "labels": [-100, 2, 3]},
            {"input_ids": [4, 5], "labels": [-100, 5]},
        ]
        with patch.dict("sys.modules", {"torch": fake_torch}):
            result = collator(features)

        self.assertEqual(result["attention_mask"], [[1, 1, 1], [1, 1, 0]])
        self.assertEqual(result["input_ids"], [[1, 2, 3], [4, 5, 0]])
        self.assertEqual(result["labels"], [[-100, 2, 3], [-100, 5, -100]])


if __name__ == "__main__":
    unittest.main()
