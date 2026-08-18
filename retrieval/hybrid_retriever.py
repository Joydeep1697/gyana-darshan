# hybrid_retriever.py — Nyaya Legal OS Authoritative Statutory RAG Engine (Phase 6.15 Hardened)
#
# Objective:
# Provide 100% authoritative statutory evidence packs for legal queries using:
# 1. Structured Statutory Corpus (BNS, BNSS, BSA JSONL records)
# 2. Statutory Cross-Mapping Registry (IPC -> BNS, CrPC -> BNSS, IEA -> BSA, POCSO status)
# 3. Deterministic Legal Indexer & Provenance Tracking
# 4. Procedural Rules Registry (Timelines, Remand, Bail, FIR)
# 5. Statute Scope Classifier (Substantive, Procedural, Evidentiary Scope)

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any

BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))
CORPUS_DIR = BASE_DIR / "corpus_integrity"

from retrieval.deterministic_legal_indexer import DeterministicLegalIndexer
from retrieval.procedural_rules_registry import ProceduralRulesRegistry
from retrieval.statute_scope_classifier import StatuteScopeClassifier

class AuthoritativeLegalRetriever:
    def __init__(self):
        self.corpus = []
        self.cross_mappings = {}
        self.deterministic_indexer = DeterministicLegalIndexer()
        self.procedural_registry = ProceduralRulesRegistry()
        self.statute_classifier = StatuteScopeClassifier()
        self._load_corpus()

    def _load_corpus(self):
        for corpus_file in ["bns_2023_corpus.jsonl", "bnss_2023_corpus.jsonl", "bsa_2023_corpus.jsonl"]:
            fp = CORPUS_DIR / corpus_file
            if fp.exists():
                with open(fp, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            self.corpus.append(json.loads(line))

        map_file = CORPUS_DIR / "statutory_cross_mappings.json"
        if map_file.exists():
            with open(map_file, "r", encoding="utf-8") as f:
                self.cross_mappings = json.load(f)

    def retrieve_evidence_pack(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        query_lower = query.lower()
        matched_records = []
        authoritative_facts = []

        # 1. Statute Scope Classification
        scope = self.statute_classifier.classify_statute_scope(query)
        if scope:
            authoritative_facts.append({
                "type": "STATUTE_SCOPE",
                "scope_data": scope
            })

        # 2. Procedural Rule Lookup
        proc_rule = self.procedural_registry.lookup_procedural_rule(query)
        if proc_rule:
            authoritative_facts.append({
                "type": "PROCEDURAL_RULE",
                "proc_data": proc_rule
            })

        # 3. Deterministic Payload Integration
        deterministic_payload = self.deterministic_indexer.route_query_and_extract(query)
        if deterministic_payload:
            payload_type = deterministic_payload["type"]
            data = deterministic_payload["data"]

            if payload_type == "SECTION_CONVERSION":
                authoritative_facts.append({
                    "type": "SECTION_CONVERSION",
                    "legacy_section": data["legacy_section"],
                    "legacy_statute": data["legacy_statute"],
                    "reformed_section": data["reformed_section"],
                    "reformed_statute": data["reformed_statute"],
                    "subject": data["subject"],
                    "reform_note": data["reform_note"]
                })
            elif payload_type == "CASE_LAW_PRECEDENT":
                authoritative_facts.append({
                    "type": "CASE_LAW_PRECEDENT",
                    "case_title": data["case_title"],
                    "citation": data["citation"],
                    "ratio_decidendi": data["ratio_decidendi"],
                    "codified_statute": data["codified_statute"],
                    "codified_section": data["codified_section"],
                    "statutory_standard": data["statutory_standard"]
                })
            elif payload_type == "OFFENCE_METADATA":
                authoritative_facts.append({
                    "type": "OFFENCE_METADATA",
                    "offence_name": data["offence_name"],
                    "statute": data["statute"],
                    "section": data["section"],
                    "chapter": data["chapter"],
                    "penalty": data["penalty"],
                    "legislative_context": data["legislative_context"]
                })
            elif payload_type == "FACT_PATTERN_REASONING":
                authoritative_facts.append({
                    "type": "FACT_PATTERN_REASONING",
                    "statutory_authority": data["statutory_authority"],
                    "legal_analysis": data["legal_analysis"],
                    "qualification": data["qualification"]
                })

        # 4. Check Statutory Replacements & Relationships
        if any(w in query_lower for w in ["ipc", "indian penal code", "penal code"]):
            authoritative_facts.append({
                "predecessor": "Indian Penal Code, 1860 (IPC)",
                "successor": "Bharatiya Nyaya Sanhita, 2023 (BNS)",
                "effective_date": "July 1, 2024",
                "act_number": "Act 45 of 2023",
                "status": "REPLACED_AND_REPEALED"
            })
        if any(w in query_lower for w in ["crpc", "criminal procedure", "criminal-procedure", "code of criminal procedure"]):
            authoritative_facts.append({
                "predecessor": "Code of Criminal Procedure, 1973 (CrPC)",
                "successor": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
                "effective_date": "July 1, 2024",
                "act_number": "Act 46 of 2023",
                "status": "REPLACED_AND_REPEALED"
            })
        if any(w in query_lower for w in ["iea", "evidence act", "indian evidence act"]):
            authoritative_facts.append({
                "predecessor": "Indian Evidence Act, 1872 (IEA)",
                "successor": "Bharatiya Sakshya Adhiniyam, 2023 (BSA)",
                "effective_date": "July 1, 2024",
                "act_number": "Act 47 of 2023",
                "status": "REPLACED_AND_REPEALED"
            })
        if any(w in query_lower for w in ["pocso", "protection of children"]):
            authoritative_facts.append({
                "statute": "Protection of Children from Sexual Offences Act, 2012 (POCSO)",
                "status": "ACTIVE_INDEPENDENT_LAW",
                "relationship": "UNREPEALED_SPECIAL_STATUTE",
                "note": "POCSO remains an unrepealed independent special statute. It is NOT repealed or subsumed into BNS."
            })

        # 5. Match Specific Corpus Sections
        query_words = set(re.findall(r'\w+', query_lower))
        for rec in self.corpus:
            score = 0
            text_lower = (rec["statute"] + " " + rec["heading"] + " " + rec["text"][:300]).lower()
            for w in query_words:
                if len(w) > 3 and w in text_lower:
                    score += 1
            if score > 0:
                matched_records.append((score, rec))

        matched_records.sort(key=lambda x: x[0], reverse=True)
        top_sections = [r[1] for r in matched_records[:top_k]]

        return {
            "query": query,
            "deterministic_payload": deterministic_payload,
            "statute_scope": scope,
            "procedural_rule": proc_rule,
            "authoritative_facts": authoritative_facts,
            "retrieved_sections": top_sections
        }

    def format_evidence_context(self, evidence_pack: Dict[str, Any]) -> str:
        ctx = "=== AUTHORITATIVE STATUTORY EVIDENCE PACK (OFFICIAL GAZETTE) ===\n"
        for fact in evidence_pack["authoritative_facts"]:
            f_type = fact.get("type", "")
            if f_type == "STATUTE_SCOPE":
                s = fact["scope_data"]
                ctx += f"• STATUTE SCOPE & APPLICABILITY: {s['standard_statement']}\n"
            elif f_type == "PROCEDURAL_RULE":
                p = fact["proc_data"]
                ctx += f"• PROCEDURAL LAW RULE & TIMELINE ({p['section']} {p['statute']}): {p['rule_summary']}\n  Exact Timeline: {p['exact_timeline']}\n"
            elif f_type == "SECTION_CONVERSION":
                ctx += f"• STATUTORY SECTION MAPPING: {fact['legacy_statute']} Section {fact['legacy_section']} ({fact['subject']}) corresponds to Section {fact['reformed_section']} of the {fact['reformed_statute']}.\n  Reform Note: {fact['reform_note']}\n"
            elif f_type == "CASE_LAW_PRECEDENT":
                ctx += f"• CASE LAW PRECEDENT CODIFICATION: Precedent Analysis for {fact['case_title']}:\n  - Core Ratio Decidendi: {fact['ratio_decidendi']}\n  - Codified Provision: {fact['codified_statute']} {fact['codified_section']}\n  - Statutory Standard: {fact['statutory_standard']}\n"
            elif f_type == "OFFENCE_METADATA":
                ctx += f"• STATUTORY PROVISION & PENALTY: Under Section {fact['section']} of the {fact['statute']}, the offence of '{fact['offence_name']}' is governed as follows:\n  1. Chapter Classification: {fact['chapter']}\n  2. Statutory Penalty / Scope: {fact['penalty']}\n  3. Legislative Context: {fact['legislative_context']}\n"
            elif f_type == "FACT_PATTERN_REASONING":
                ctx += f"• STATUTORY REASONING & ANALYSIS:\n  1. Applicable Statutory Authority: {fact['statutory_authority']}\n  2. Legal Analysis: {fact['legal_analysis']}\n  3. Statutory Qualification: {fact['qualification']}\n"
            elif "successor" in fact:
                ctx += f"• STATUTORY REPLACEMENT: {fact['predecessor']} was REPLACED and REPEALED by {fact['successor']} ({fact['act_number']}, effective {fact['effective_date']}).\n"
            elif "relationship" in fact:
                ctx += f"• SPECIAL STATUTE STATUS: {fact['statute']} is an {fact['status']} ({fact['note']}).\n"

        for sec in evidence_pack["retrieved_sections"]:
            ctx += f"\n• [{sec['short_name']} Section {sec['section']}]: {sec['heading']}\n  Chapter: {sec['chapter']}\n  Text Snippet: {sec['text'][:300]}...\n"

        ctx += "=================================================================\n"
        return ctx
