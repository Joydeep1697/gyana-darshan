# parallel_statute_retriever.py — Multi-Branch Parallel Statutory Retriever (Phase 8.2G Hardened)
#
# Objective:
# Execute isolated, parallel retrieval branches across active statutes (BNS, BNSS, BSA, POCSO)
# based on decomposed legal issues, preventing global score domination and preserving multi-statute recall.

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))
CORPUS_DIR = BASE_DIR / "corpus_integrity"

from retrieval.experimental.issue_decomposer import LegalIssueDecomposer
from retrieval.experimental.legal_concept_expander import LegalConceptExpander
from retrieval.deterministic_legal_indexer import DeterministicLegalIndexer
from retrieval.procedural_rules_registry import ProceduralRulesRegistry
from retrieval.query_analyzer import LegalQueryAnalyzer
from retrieval.transition_router import TransitionLawRouter

class ParallelStatuteRetriever:
    """Executes parallel statute-specific retrieval to ensure high multi-statute coverage."""

    def __init__(self):
        self.corpus_by_statute = {"BNS": [], "BNSS": [], "BSA": [], "POCSO": []}
        self.corpus_by_statute_sec = {}
        self.cross_mappings = {}
        self.decomposer = LegalIssueDecomposer()
        self.expander = LegalConceptExpander()
        self.deterministic_indexer = DeterministicLegalIndexer()
        self.procedural_registry = ProceduralRulesRegistry()
        self.query_analyzer = LegalQueryAnalyzer()
        self.transition_router = TransitionLawRouter()
        self._load_corpus()

    def _load_corpus(self):
        file_map = {
            "BNS": "bns_2023_corpus.jsonl",
            "BNSS": "bnss_2023_corpus.jsonl",
            "BSA": "bsa_2023_corpus.jsonl",
            "POCSO": "pocso_2012_corpus.jsonl"
        }
        for st, filename in file_map.items():
            p = CORPUS_DIR / filename
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            rec = json.loads(line)
                            rec["short_name"] = st
                            rec["statute_short"] = st
                            self.corpus_by_statute[st].append(rec)
                            sec_clean = re.sub(r'[^\w]', '', str(rec.get("section", ""))).upper()
                            self.corpus_by_statute_sec[(st, sec_clean)] = rec

        map_file = CORPUS_DIR / "statutory_cross_mappings.json"
        if map_file.exists():
            with open(map_file, "r", encoding="utf-8") as f:
                self.cross_mappings = json.load(f)

    def _score_statute_record(self, rec: Dict[str, Any], query_words: Set[str], candidate_sections: Set[str]) -> float:
        score = 0.0
        sec_str = str(rec.get("section", "")).strip()
        sec_base = sec_str.split('(')[0]
        st_short = rec.get("short_name", "").upper()

        # Exact target section match from ontology, deterministic indexer, or query hints
        if sec_str in candidate_sections or sec_base in candidate_sections or any(re.sub(r'\(.*?\)', '', s) == sec_base for s in candidate_sections):
            score += 80.0

        # Check section number in query words (with boundary)
        if sec_str in query_words and sec_str not in ["1", "2", "3"]:
            score += 40.0

        heading_lower = rec.get("heading", "").lower()
        text_snippet = rec.get("text", "")[:400].lower()

        # Demote generic definition / commencement sections unless specifically requested
        if sec_str in ["1", "2", "2(1)(d)", "42"] and not any(w in query_words for w in ["definition", "title", "commencement", "application", "scope"]):
            score -= 35.0

        # Heading and Element-Aware Keyword Matches
        for w in query_words:
            if len(w) > 3 and w not in ["with", "from", "that", "this", "have", "under", "which", "shall", "about", "their", "where"]:
                if w in heading_lower:
                    score += 18.0
                elif w in text_snippet:
                    score += 4.0

        # Specific Key Compound Matches in Heading (Strict Phrase Match)
        q_clean = " " + " ".join(query_words) + " "
        for key_phrase in [
            "electronic record", "admissibility", "attachment of property", "proceeds of crime",
            "police custody", "remand", "bail", "undertrial", "sexual harassment", "sexual assault",
            "mandatory reporting", "forgery", "criminal breach of trust", "cheating", "private defence",
            "rash driving", "death by negligence", "snatching", "extortion", "robbery", "dacoity",
            "dishonest misappropriation", "counterfeiting", "stalking", "voyeurism", "notice of appearance",
            "unlawful assembly", "mob lynching", "mischief", "trespass", "housebreaking",
            "aggravated penetrative", "penetrative sexual assault"
        ]:
            if key_phrase in heading_lower and (key_phrase in q_clean or any(w in query_words for w in key_phrase.split())):
                score += 45.0

        return score

    def retrieve_parallel_branches(self, query: str, per_statute_k: int = 4) -> Dict[str, Any]:
        """Decompose query and execute parallel statute-specific retrieval branches."""
        # 1. Decompose query into issues
        decomp = self.decomposer.decompose_query(query)
        expansion = self.expander.expand_query(query)

        # 2. Extract deterministic mappings and analyzer candidate sections
        analysis = self.query_analyzer.analyze_query(query)
        candidate_sections = set(analysis.get("candidate_sections", []))
        candidate_statutes = set(analysis.get("candidate_statutes", []))
        statute_to_candidate_sections = analysis.get("statute_to_candidate_sections", {})

        # Merge decomposed statutes
        candidate_statutes.update(decomp["statute_candidates"])
        candidate_statutes.update(expansion["statute_hints"])

        # Extract explicit section numbers from text
        explicit_sec_matches = re.findall(r'(?:section|sec\.?|§|u/s|under\s+section)\s+(\d+[A-Za-z]*(?:\(\w+\))?)', query, re.IGNORECASE)
        for s in explicit_sec_matches:
            clean_s = s.strip()
            candidate_sections.add(clean_s)
            for st in candidate_statutes:
                if st not in statute_to_candidate_sections:
                    statute_to_candidate_sections[st] = []
                statute_to_candidate_sections[st].append(clean_s)

        # Deterministic payload lookups
        det_payload = self.deterministic_indexer.route_query_and_extract(query)
        deterministic_injected_sections = []
        if det_payload:
            payload_type = det_payload.get("type")
            data = det_payload.get("data", {})
            if payload_type == "SECTION_CONVERSION":
                ref_sec = str(data.get("reformed_section", ""))
                ref_st = "BNSS" if "BNSS" in data.get("reformed_statute","") else ("BNS" if "BNS" in data.get("reformed_statute","") else ("BSA" if "BSA" in data.get("reformed_statute","") else ""))
                if ref_sec and ref_st:
                    candidate_sections.add(ref_sec)
                    candidate_statutes.add(ref_st)
                    deterministic_injected_sections.append((ref_st, ref_sec))
            elif payload_type == "PROCEDURAL_TIMELINE":
                ref_sec = str(data.get("section", ""))
                if ref_sec:
                    candidate_sections.add(ref_sec)
                    candidate_statutes.add("BNSS")
                    deterministic_injected_sections.append(("BNSS", ref_sec))
            elif payload_type == "FACT_PATTERN_MATCH":
                for item in data.get("mapped_sections", []):
                    ref_st = item.get("statute")
                    ref_sec = str(item.get("section"))
                    candidate_sections.add(ref_sec)
                    candidate_statutes.add(ref_st)
                    deterministic_injected_sections.append((ref_st, ref_sec))

        # Transition law check
        if self.transition_router.is_transition_query(query):
            trans_ev = self.transition_router.route_transition_evidence(query)
            for item in trans_ev.get("candidate_sections", []):
                st = item.get("statute", "").upper()
                sec = str(item.get("section", "")).strip()
                if st and sec:
                    candidate_statutes.add(st)
                    candidate_sections.add(sec)
                    deterministic_injected_sections.append((st, sec))

        # Ensure active statutes set
        active_statutes = candidate_statutes if candidate_statutes else {"BNS"}

        # Tokenize query words
        query_words = set(re.findall(r'\b\w+\b', query.lower()))
        for eq in expansion.get("expanded_retrieval_queries", []):
            query_words.update(re.findall(r'\b\w+\b', eq.lower()))

        branch_results = {}
        all_candidates = []
        seen_pairs = set()

        # 3. Inject deterministic sections first per branch
        for st, sec in deterministic_injected_sections:
            clean_sec = re.sub(r'[^\w]', '', sec).upper()
            key = (st.upper(), clean_sec)
            if key in self.corpus_by_statute_sec and key not in seen_pairs:
                rec = self.corpus_by_statute_sec[key]
                cand_item = {
                    "statute": st.upper(),
                    "section": rec.get("section"),
                    "heading": rec.get("heading"),
                    "text": rec.get("text"),
                    "branch_score": 120.0,
                    "is_deterministic": True
                }
                if st.upper() not in branch_results:
                    branch_results[st.upper()] = []
                branch_results[st.upper()].append(cand_item)
                all_candidates.append(cand_item)
                seen_pairs.add(key)

        # 4. Run retrieval across each active statute branch
        for statute in ["BNS", "BNSS", "BSA", "POCSO"]:
            if statute not in active_statutes and len(active_statutes) > 0:
                continue

            statute_corpus = self.corpus_by_statute.get(statute, [])
            stat_cands = set(statute_to_candidate_sections.get(statute, []))
            stat_cands.update(candidate_sections)

            scored = []
            for rec in statute_corpus:
                sec_raw = str(rec.get("section", "")).strip().upper()
                sec_clean = re.sub(r'[^\w]', '', sec_raw)
                if (statute, sec_clean) in seen_pairs:
                    continue

                sc = self._score_statute_record(rec, query_words, stat_cands)
                if sc > 0:
                    scored.append((sc, rec))

            scored.sort(key=lambda x: x[0], reverse=True)
            top_for_statute = scored[:per_statute_k]

            if statute not in branch_results:
                branch_results[statute] = []

            for sc, r in top_for_statute:
                sec_clean = re.sub(r'[^\w]', '', str(r.get("section", ""))).upper()
                seen_pairs.add((statute, sec_clean))
                cand_item = {
                    "statute": statute,
                    "section": r.get("section"),
                    "heading": r.get("heading"),
                    "text": r.get("text"),
                    "branch_score": round(sc, 2),
                    "is_deterministic": False
                }
                branch_results[statute].append(cand_item)
                all_candidates.append(cand_item)

        return {
            "query": query,
            "decomposition": decomp,
            "active_statutes": list(active_statutes),
            "branch_results": branch_results,
            "candidate_count": len(all_candidates),
            "candidates": all_candidates
        }
