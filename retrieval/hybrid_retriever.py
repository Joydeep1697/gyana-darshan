# hybrid_retriever.py — Nyaya Legal OS Authoritative Statutory RAG Engine (Phase 8.2F Generalized Architecture)
#
# Objective:
# Provide 100% authoritative statutory evidence packs for legal queries using:
# 1. Structured Statutory Corpus (BNS, BNSS, BSA, POCSO JSONL records)
# 2. Multi-Issue Query Decomposition & Generalized Legal Ontology Expansion
# 3. Statutory Cross-Mapping Registry & Deterministic Section Injection
# 4. Statute-Diversified Parallel Branch Retrieval & Fusion
# 5. Procedural Rules Registry & Transition Router Integration

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
CORPUS_DIR = BASE_DIR / "corpus_integrity"

from retrieval.deterministic_legal_indexer import DeterministicLegalIndexer
from retrieval.procedural_rules_registry import ProceduralRulesRegistry
from retrieval.statute_scope_classifier import StatuteScopeClassifier
from retrieval.query_analyzer import LegalQueryAnalyzer
from retrieval.transition_router import TransitionLawRouter
from retrieval.legal_issue_classifier import LegalIssueClassifier
from retrieval.legal_reranker import LegalReranker
from retrieval.issue_planner import LegalIssuePlanner
from retrieval.legal_concept_expander import LegalConceptExpander
from retrieval.evidence_budget_engine import EvidenceBudgetEngine
from retrieval.legal_reasoning import build_reasoning_plan, format_compact_evidence, prioritize_evidence

class AuthoritativeLegalRetriever:
    def __init__(self):
        self.corpus = []
        self.corpus_by_id = {}
        self.corpus_by_statute_sec = {}
        self.cross_mappings = {}
        self.deterministic_indexer = DeterministicLegalIndexer()
        self.procedural_registry = ProceduralRulesRegistry()
        self.statute_classifier = StatuteScopeClassifier()
        self.query_analyzer = LegalQueryAnalyzer()
        self.transition_router = TransitionLawRouter()
        self.issue_classifier = LegalIssueClassifier()
        self.legal_reranker = LegalReranker()
        self.issue_planner = LegalIssuePlanner()
        self.concept_expander = LegalConceptExpander()
        self.evidence_budget_engine = EvidenceBudgetEngine()
        self._load_corpus()

    def _load_corpus(self):
        corpus_files = [
            "bns_2023_corpus.jsonl",
            "bnss_2023_corpus.jsonl",
            "bsa_2023_corpus.jsonl",
            "pocso_2012_corpus.jsonl"
        ]
        for corpus_file in corpus_files:
            fp = CORPUS_DIR / corpus_file
            if fp.exists():
                with open(fp, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            rec = json.loads(line)
                            self.corpus.append(rec)
                            self.corpus_by_id[rec.get("id")] = rec
                            st_short = rec.get("short_name") or ("BNS" if "Nyaya" in rec.get("statute","") else ("BNSS" if "Nagarik" in rec.get("statute","") else ("BSA" if "Sakshya" in rec.get("statute","") else ("POCSO" if "POCSO" in rec.get("statute","") else ""))))
                            sec_clean = str(rec.get("section", "")).strip().upper()
                            self.corpus_by_statute_sec[(st_short.upper(), sec_clean)] = rec

        map_file = CORPUS_DIR / "statutory_cross_mappings.json"
        if map_file.exists():
            with open(map_file, "r", encoding="utf-8") as f:
                self.cross_mappings = json.load(f)

    def _score_section(self, rec: Dict[str, Any], query_words: Set[str], candidate_sections: Set[str], target_statute: str = None) -> float:
        score = 0.0
        sec_str = str(rec.get("section", "")).strip()
        sec_base = sec_str.split('(')[0]
        st_short = rec.get("short_name", "").upper()

        if target_statute and target_statute.upper() != st_short:
            return -100.0

        # Exact target section match from ontology or query
        if sec_str in candidate_sections or sec_base in candidate_sections or any(re.sub(r'\(.*?\)', '', s) == sec_base for s in candidate_sections):
            score += 60.0

        # Check section number in query words (with boundary)
        if sec_str in query_words and sec_str not in ["1", "2", "3"]:
            score += 30.0

        heading_lower = rec.get("heading", "").lower()
        text_snippet = rec.get("text", "")[:400].lower()

        # Demote generic definition / commencement sections unless specifically requested
        if sec_str in ["1", "2"] and not any(w in query_words for w in ["definition", "title", "commencement", "application", "scope"]):
            score -= 25.0

        # Heading and Element-Aware Keyword Matches
        for w in query_words:
            if len(w) > 3 and w not in ["with", "from", "that", "this", "have", "under", "which", "shall", "about", "their", "where"]:
                if w in heading_lower:
                    score += 15.0
                elif w in text_snippet:
                    score += 4.0

        # Specific Key Compound Matches in Heading (Strict Phrase Match)
        q_clean = " " + " ".join(query_words) + " "
        for key_phrase in ["electronic record", "admissibility", "attachment of property", "proceeds of crime", "police custody", "remand", "bail", "undertrial", "sexual harassment", "sexual assault", "mandatory reporting", "forgery", "criminal breach of trust", "cheating", "private defence", "rash driving", "death by negligence", "snatching", "extortion", "robbery", "dacoity", "dishonest misappropriation", "counterfeiting"]:
            if key_phrase in heading_lower and (key_phrase in q_clean or all(w in query_words for w in key_phrase.split())):
                score += 35.0

        return score

    def retrieve_evidence_pack(self, query: str, top_k: int = 4) -> Dict[str, Any]:
        query_lower = query.lower()
        authoritative_facts = []

        # 1. Query Analysis & Generalized Legal Concept Expansion
        analysis = self.query_analyzer.analyze_query(query)
        candidate_sections = set(analysis["candidate_sections"])
        candidate_statutes = analysis["candidate_statutes"]
        statute_to_candidate_sections = analysis.get("statute_to_candidate_sections", {})

        # Extract explicit section numbers from text (e.g. "Section 303", "Sec 187")
        explicit_sec_matches = re.findall(r'(?:section|sec\.?|§|u/s|under\s+section)\s+(\d+[A-Za-z]*(?:\(\w+\))?)', query, re.IGNORECASE)
        for s in explicit_sec_matches:
            clean_s = s.strip()
            candidate_sections.add(clean_s)
            for st in candidate_statutes:
                if st not in statute_to_candidate_sections:
                    statute_to_candidate_sections[st] = []
                statute_to_candidate_sections[st].append(clean_s)

        # 2. Statute Scope Classification
        scope = self.statute_classifier.classify_statute_scope(query)
        if scope:
            authoritative_facts.append({
                "type": "STATUTE_SCOPE",
                "scope_data": scope
            })

        # 3. Procedural Rule Lookup
        proc_rule = self.procedural_registry.lookup_procedural_rule(query)
        if proc_rule:
            authoritative_facts.append({
                "type": "PROCEDURAL_RULE",
                "proc_data": proc_rule
            })

        # 4. Deterministic Payload Integration & Section Resolution
        deterministic_payload = self.deterministic_indexer.route_query_and_extract(query)
        deterministic_injected_sections = []

        if deterministic_payload:
            payload_type = deterministic_payload["type"]
            data = deterministic_payload["data"]

            if payload_type == "SECTION_CONVERSION":
                ref_st = "BNS" if "BNS" in data["reformed_statute"] or "Nyaya" in data["reformed_statute"] else ("BNSS" if "BNSS" in data["reformed_statute"] or "Nagarik" in data["reformed_statute"] else ("BSA" if "BSA" in data["reformed_statute"] or "Sakshya" in data["reformed_statute"] else ""))
                ref_sec = str(data["reformed_section"]).split("/")[0].split("(")[0].strip().upper()
                if (ref_st, ref_sec) in self.corpus_by_statute_sec:
                    deterministic_injected_sections.append(self.corpus_by_statute_sec[(ref_st, ref_sec)])

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
                cod_st = "BNS" if "BNS" in data["codified_statute"] else ("BNSS" if "BNSS" in data["codified_statute"] else ("BSA" if "BSA" in data["codified_statute"] else ""))
                cod_sec = str(data["codified_section"]).split("(")[0].strip().upper()
                if (cod_st, cod_sec) in self.corpus_by_statute_sec:
                    deterministic_injected_sections.append(self.corpus_by_statute_sec[(cod_st, cod_sec)])

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
                off_st = "BNS" if "BNS" in data["statute"] else ("BNSS" if "BNSS" in data["statute"] else ("BSA" if "BSA" in data["statute"] else ""))
                off_sec = str(data["section"]).split("(")[0].strip().upper()
                if (off_st, off_sec) in self.corpus_by_statute_sec:
                    deterministic_injected_sections.append(self.corpus_by_statute_sec[(off_st, off_sec)])

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

        # 5. Statutory Replacements & Relationships
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
        if any(w in query_lower for w in ["pocso", "protection of children", "child victim", "15-year-old child", "child subjected", "sexual assault on child"]):
            authoritative_facts.append({
                "statute": "Protection of Children from Sexual Offences Act, 2012 (POCSO)",
                "status": "ACTIVE_INDEPENDENT_LAW",
                "relationship": "UNREPEALED_SPECIAL_STATUTE",
                "note": "POCSO Act 2012 remains an unrepealed independent special statute operating alongside Bharatiya Nyaya Sanhita, 2023 (BNS). It is NOT repealed or subsumed into BNS."
            })

        # 6. Structured Legal Issue Plan, Concept Expansion & Issue-Aware Candidate Allocation (Phase 8.2K)
        concept_res = self.concept_expander.extract_concepts_and_expand(query)
        expanded_statute_sections = concept_res.get("statute_to_expanded_sections", {})
        concept_prohibited = set((d[0].upper(), str(d[1]).upper()) for d in concept_res.get("negation_analysis", {}).get("prohibited_sections", []))

        issue_analysis = self.issue_classifier.classify_issues(query)
        issue_plan = self.issue_planner.create_issue_plan(issue_analysis, top_k=top_k)
        targeted_sections = issue_analysis.get("targeted_sections", {})
        negative_distractors = set((d[0].upper(), str(d[1]).upper()) for d in issue_analysis.get("negative_distractors", []))
        negative_distractors.update(concept_prohibited)

        query_words = set(re.findall(r'\w+', query_lower))
        for tok in analysis.get("enriched_tokens", []):
            query_words.add(tok)

        # Step 6a: Gather all targeted and expanded sections per statute
        target_map: Dict[str, List[str]] = {}
        for st_source in [targeted_sections, expanded_statute_sections, statute_to_candidate_sections]:
            for st, s_list in st_source.items():
                if st not in target_map:
                    target_map[st] = []
                for s in s_list:
                    if s not in target_map[st]:
                        target_map[st].append(s)

        # Step 6b: Ensure all active statutes with targets have an issue plan entry
        active_statutes = set(analysis.get("candidate_statutes", []))
        for st in target_map.keys():
            active_statutes.add(st)
        if not active_statutes:
            active_statutes.add("BNS")

        # Step 6c: Per-Statute / Issue Priority Queues (Verified Targets + Scored Corpus Candidates)
        issue_queues = {}
        for st in sorted(active_statutes):
            iss_candidates = []
            seen_iss_ids = set()

            # Priority 1: Verified target & concept-expanded sections for this statute
            for s in target_map.get(st, []):
                s_clean = re.match(r'(\d+[A-Za-z]*)', str(s).strip())
                s_norm = s_clean.group(1).upper() if s_clean else str(s).strip().upper()
                sec_key = (st.upper(), s_norm)
                if sec_key in negative_distractors:
                    continue
                rec = self.corpus_by_statute_sec.get(sec_key)
                if rec and rec["id"] not in seen_iss_ids:
                    seen_iss_ids.add(rec["id"])
                    iss_candidates.append((100.0, rec))

            # Priority 2: Scored corpus candidates for this statute
            for rec in self.corpus:
                st_short = rec.get("short_name") or ("BNS" if "Nyaya" in rec.get("statute","") else ("BNSS" if "Nagarik" in rec.get("statute","") else ("BSA" if "Sakshya" in rec.get("statute","") else ("POCSO" if "POCSO" in rec.get("statute","") else ""))))
                if st and st.upper() != st_short.upper():
                    continue
                if rec["id"] in seen_iss_ids:
                    continue

                sc = self.legal_reranker.score_candidate(rec, query, query_words, issue_analysis)
                sec_clean = str(rec.get("section", "")).strip().upper()
                sec_key = (st_short.upper(), sec_clean)
                if sc > 0 and sec_key not in negative_distractors:
                    iss_candidates.append((sc, rec))

            iss_candidates.sort(key=lambda x: x[0], reverse=True)
            issue_queues[st] = [c[1] for c in iss_candidates[:25]]

        # Step 6d: Dynamic Issue Budget Allocation & Fair Diversified Top-K Selection
        active_issue_objs = [{"issue_id": st, "statute": st, "priority": "PRIMARY" if st in ["BNS", "POCSO"] else "SECONDARY"} for st in issue_queues.keys()]
        issue_budgets = self.evidence_budget_engine.allocate_issue_budgets(active_issue_objs, top_k=top_k)

        top_sections = self.evidence_budget_engine.select_diversified_evidence(
            issue_queues,
            issue_budgets,
            top_k=top_k,
            negative_distractors=negative_distractors
        )

        # Prepend deterministic cross-mappings if any
        if deterministic_injected_sections:
            det_to_add = []
            curr_sec_keys = set((s.get("short_name","").upper(), str(s.get("section","")).strip().upper()) for s in top_sections)
            for d in deterministic_injected_sections:
                d_key = (d.get("short_name","").upper(), str(d.get("section","")).strip().upper())
                if d_key not in curr_sec_keys and d_key not in negative_distractors:
                    det_to_add.append(d)
            top_sections = det_to_add + top_sections
            top_sections = top_sections[:top_k]

        # Step 6c: Transition Law Guarantees
        if analysis.get("is_transition"):
            curr_top_ids = set(s["id"] for s in top_sections)
            for rec in self.corpus:
                st_short = rec.get("short_name") or ("BNS" if "Nyaya" in rec.get("statute","") else ("BNSS" if "Nagarik" in rec.get("statute","") else ""))
                sec_str = str(rec.get("section", "")).strip()
                if (st_short == "BNS" and sec_str == "358") or (st_short == "BNSS" and sec_str == "531"):
                    if rec["id"] not in curr_top_ids:
                        curr_top_ids.add(rec["id"])
                        top_sections.append(rec)

        reasoning_plan = build_reasoning_plan(query)
        if reasoning_plan.issues:
            top_sections = prioritize_evidence(
                reasoning_plan, top_sections, self.corpus_by_statute_sec,
                limit=max(top_k, min(8, len(reasoning_plan.required_citations))),
            )

        return {
            "query": query,
            "deterministic_payload": deterministic_payload,
            "statute_scope": scope,
            "procedural_rule": proc_rule,
            "authoritative_facts": authoritative_facts,
            "retrieved_sections": top_sections,
            "top_documents": top_sections,
            "query_analysis": analysis,
            "issue_categories": [issue.category for issue in reasoning_plan.issues],
            "legal_safeguards": reasoning_plan.safeguards,
        }

    def format_evidence_context(self, evidence_pack: Dict[str, Any]) -> str:
        reasoning_plan = build_reasoning_plan(evidence_pack.get("query", ""))
        if reasoning_plan.issues:
            return format_compact_evidence(
                reasoning_plan, evidence_pack.get("retrieved_sections", [])
            )
        analysis = evidence_pack.get("query_analysis", {})
        ctx = "=== AUTHORITATIVE STATUTORY EVIDENCE PACK (OFFICIAL GAZETTE) ===\n"

        # Multi-Statute Jurisdictional Architecture Header
        if analysis.get("is_multi_statute"):
            ctx += "• MULTI-STATUTE JURISDICTIONAL ARCHITECTURE:\n"
            if "BNS" in analysis.get("candidate_statutes", []):
                ctx += "  - Substantive Criminal Offences: Governed by the Bharatiya Nyaya Sanhita, 2023 (BNS).\n"
            if "BNSS" in analysis.get("candidate_statutes", []):
                ctx += "  - Criminal Procedure, Arrest & Remand: Governed by the Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS).\n"
            if "BSA" in analysis.get("candidate_statutes", []):
                ctx += "  - Law of Evidence, Electronic Records & Admissibility: Governed by the Bharatiya Sakshya Adhiniyam, 2023 (BSA).\n"
            if "POCSO" in analysis.get("candidate_statutes", []):
                ctx += "  - Special Child Protection Law: Governed by the Protection of Children from Sexual Offences Act, 2012 (POCSO Act, 2012 — Unrepealed Special Statute).\n"

        for fact in evidence_pack.get("authoritative_facts", []):
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

        for sec in evidence_pack.get("retrieved_sections", []):
            st_name = sec.get("short_name") or ("BNS" if "Nyaya" in sec.get("statute","") else ("BNSS" if "Nagarik" in sec.get("statute","") else ("BSA" if "Sakshya" in sec.get("statute","") else "POCSO")))
            ctx += f"\n• [{st_name} Section {sec.get('section')}]: {sec.get('heading', '')}\n  Chapter: {sec.get('chapter', '')}\n  Text Snippet: {sec.get('text', '')[:350]}...\n"

        ctx += "=================================================================\n"
        return ctx
