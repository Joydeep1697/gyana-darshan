"""Regression tests for conservative answer-level legal grounding states."""

from app.intelligence.grounding_verdict import (
    AuthorityStatus,
    ClaimStatus,
    ConflictStatus,
    assess_grounding,
)


EVIDENCE = "AUTHORITATIVE STATUTORY EXCERPTS:\n- BNSS section 173: Information in cognizable cases may be given by electronic communication."


def test_model_citation_without_retrieved_record_is_not_proposition_proof():
    verdict = assess_grounding(
        "Can an FIR be filed electronically?",
        "An electronic FIR is always conclusive proof of guilt (BNSS section 173).",
        EVIDENCE,
        firewall_passed=True,
        deterministic_answer=None,
    )
    assert verdict.status == "INSUFFICIENT_EVIDENCE"
    assert verdict.claims[0].status == ClaimStatus.UNSUPPORTED
    assert verdict.citation_coverage == 0.0


def test_uncited_material_claim_is_insufficient_evidence():
    verdict = assess_grounding(
        "Can an FIR be filed electronically?",
        "An electronic FIR always proves guilt.",
        EVIDENCE,
        firewall_passed=True,
        deterministic_answer=None,
    )
    assert verdict.status == "INSUFFICIENT_EVIDENCE"
    assert verdict.claims[0].status == ClaimStatus.UNSUPPORTED


def test_material_legal_claim_categories_and_critical_claims_are_detected():
    answer = (
        "The accused is guilty. The court has jurisdiction. The landlord must provide notice. "
        "The contract is unenforceable. The accused may be arrested."
    )
    verdict = assess_grounding("Assess these consequences.", answer, EVIDENCE, True, None)
    assert len(verdict.claims) == 5
    assert all(item.status == ClaimStatus.UNSUPPORTED for item in verdict.claims)
    assert sum(item.criticality.value == "CRITICAL" for item in verdict.claims) == 3


def test_multi_claim_answer_is_not_fully_grounded_when_one_material_claim_has_no_citation():
    answer = (
        "Electronic information may be given under BNSS section 173. "
        "It always proves guilt."
    )
    verdict = assess_grounding(
        "Can an FIR be filed electronically?", answer, EVIDENCE, True, answer,
        [{"short_name": "BNSS", "section": "173", "text": "Electronic information may be given."}],
    )
    assert verdict.status == "INSUFFICIENT_EVIDENCE"
    assert verdict.citation_completeness == 0.0
    assert verdict.citation_coverage == 0.5
    assert any(item.status == ClaimStatus.UNSUPPORTED for item in verdict.claims)


def test_deterministic_answer_with_retrieved_citation_still_requires_independent_proof():
    answer = "Electronic information may be given under BNSS section 173."
    verdict = assess_grounding(
        "Can an FIR be filed electronically?", answer, EVIDENCE, True, answer,
        [{"short_name": "BNSS", "section": "173", "country": "India",
          "text": "Information may be given by electronic communication.",
          "source": "India Code / Official Gazette", "curation": "full statutory text"}],
    )
    assert verdict.status == "INSUFFICIENT_EVIDENCE"
    assert verdict.claims[0].status == ClaimStatus.INSUFFICIENT_EVIDENCE
    assert verdict.evidence_verifications[0].proposition_status == verdict.claims[0].status
    assert verdict.citation_coverage == 1.0
    assert verdict.citation_completeness == 0.0


def test_claim_evidence_records_distinguish_identity_jurisdiction_and_quote_mismatch():
    answer = 'Electronic information is "always conclusive proof" (BNSS section 173).'
    verdict = assess_grounding(
        "Can an FIR be filed electronically?", answer, EVIDENCE, True, None,
        [{"id": "bnss-173", "short_name": "BNSS", "section": "173", "country": "India",
          "text": "Information may be given by electronic communication."}],
    )
    verification = verdict.evidence_verifications[0]
    assert verification.identity_status.value == "VERIFIED"
    assert verification.jurisdiction_status.value == "VALID"
    assert verification.quote_status.value == "MISMATCH"
    assert verification.proposition_status == ClaimStatus.INSUFFICIENT_EVIDENCE


def test_foreign_source_is_not_a_valid_indian_supporting_authority():
    verdict = assess_grounding(
        "What Indian law applies?", "The rule applies (BNSS section 173).", EVIDENCE, True, None,
        [{"short_name": "BNSS", "section": "173", "country": "United States", "text": "Rule text."}],
    )
    assert verdict.evidence_verifications[0].jurisdiction_status.value == "INVALID"


def test_post_2024_statute_cannot_be_fully_grounded_for_a_pre_commencement_offence():
    answer = "BNS section 303 governs the theft."
    verdict = assess_grounding(
        "A theft occurred on 29 June 2024.", answer, EVIDENCE, True, answer,
        [{"short_name": "BNS", "section": "303", "country": "India", "text": "Theft provision."}],
    )
    assert verdict.status != "GROUNDED_AND_VERIFIED"
    assert verdict.evidence_verifications[0].temporal_status.value == "NOT_YET_EFFECTIVE"


def test_foreign_authority_is_irrelevant_and_cannot_promote_a_deterministic_answer():
    answer = "BNSS section 173 governs electronic information."
    verdict = assess_grounding(
        "What Indian law applies?", answer, EVIDENCE, True, answer,
        [{"short_name": "BNSS", "section": "173", "country": "United States",
          "authority_type": "statute", "text": "Rule text."}],
    )
    verification = verdict.evidence_verifications[0]
    assert verdict.status != "GROUNDED_AND_VERIFIED"
    assert verification.authority_status == AuthorityStatus.IRRELEVANT


def test_known_indian_primary_law_is_classified_as_binding():
    answer = "Electronic information may be given under BNSS section 173."
    verdict = assess_grounding(
        "Can an FIR be filed electronically?", answer, EVIDENCE, True, answer,
        [{"short_name": "BNSS", "section": "173", "country": "India",
          "text": "Information may be given by electronic communication.",
          "source": "India Code / Official Gazette", "curation": "full statutory text"}],
    )
    assert verdict.status == "INSUFFICIENT_EVIDENCE"
    assert verdict.evidence_verifications[0].authority_status == AuthorityStatus.BINDING


def test_whitespace_only_quote_layout_noise_is_verified_without_repairing_text():
    answer = 'BNSS section 173 says "may be given by electronic communication".'
    verdict = assess_grounding(
        "Can an FIR be filed electronically?", answer, EVIDENCE, True, None,
        [{"short_name": "BNSS", "section": "173", "country": "India",
          "text": "Information may be given\n by electronic communication."}],
    )
    assert verdict.evidence_verifications[0].quote_status.value == "VERIFIED"


def test_wrong_subsection_pincite_is_detected_even_when_the_section_exists():
    answer = "BNSS section 173(3) governs electronic information."
    verdict = assess_grounding(
        "Can an FIR be filed electronically?", answer, EVIDENCE, True, answer,
        [{"short_name": "BNSS", "section": "173", "country": "India",
          "text": "Section 173(1). Information may be given by electronic communication.",
          "source": "India Code / Official Gazette", "curation": "full statutory text"}],
    )
    assert verdict.status != "GROUNDED_AND_VERIFIED"
    assert verdict.evidence_verifications[0].pinpoint_status.value == "MISMATCH"


def test_ocr_derived_source_cannot_promote_an_answer_to_fully_verified():
    answer = "Electronic information may be given under BNSS section 173."
    verdict = assess_grounding(
        "Can an FIR be filed electronically?", answer, EVIDENCE, True, answer,
        [{"short_name": "BNSS", "section": "173", "country": "India",
          "text": "Information may be given by electronic communication.",
          "extraction_method": "ocr", "ocr_confidence": 0.99}],
    )
    assert verdict.status != "GROUNDED_AND_VERIFIED"
    assert verdict.evidence_verifications[0].source_integrity_status.value == "SUSPECT"


def test_explicit_conflicting_sources_force_an_evidence_conflict_verdict():
    answer = "The notice rule is established (BNSS section 173 and BNSS section 174)."
    verdict = assess_grounding(
        "Does the notice rule apply?", answer, EVIDENCE, True, answer,
        [
            {"short_name": "BNSS", "section": "173", "country": "India",
             "text": "First rule.", "conflict_group": "notice-rule", "position": "supports"},
            {"short_name": "BNSS", "section": "174", "country": "India",
             "text": "Second rule.", "conflict_group": "notice-rule", "position": "refutes"},
        ],
    )
    assert verdict.status == "EVIDENCE_CONFLICT"
    assert all(item.conflict_status == ConflictStatus.UNRESOLVED for item in verdict.evidence_verifications)
