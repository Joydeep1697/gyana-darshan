# NYAYA DARSHANA — PHASE 8.3A MASTER EXPERIMENT LEDGER

**Protocol**: Statute-Aware Candidate Preservation Calibration Sprint  
**Role**: Senior Retrieval Systems Engineer & Principal Legal AI Architect  
**Status**: COMPLETE — VERDICT: **B — ITERATE**  
**Baseline Frozen Date**: 2026-08-19 (Phase 8.2G)  
**Sprint Start Date**: 2026-08-21  

---

## 1. Master Task Ledger

| Step | Task | Input Artifacts | Output Artifacts | Status |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Inspect Phase 8.2G Architecture — trace candidate ranking data flow across `issue_decomposer.py`, `legal_concept_expander.py`, `parallel_statute_retriever.py`, `legal_reranker.py`, `evidence_sufficiency.py`, `pipeline.py` | `retrieval/experimental/*.py`, `experimental_phase_8_2g/pipeline.py` | Architecture trace | **COMPLETE ✅** |
| **2** | Identify minimal integration point — Phase 8.2G reranker produces global scores; preservation must INSERT AFTER reranking, not replace it | `legal_reranker.py` reranking flow | Integration point identified | **COMPLETE ✅** |
| **3** | Implement isolated Phase 8.3A modules | — | `retrieval/experimental_phase_8_3a/__init__.py`, `phase_8_3a_config.py`, `statute_aware_preserver.py` | **COMPLETE ✅** |
| **4** | Write focused unit tests (11 scenarios) | `statute_aware_preserver.py` | `test_statute_aware_preserver.py` | **COMPLETE ✅** |
| **5** | Run unit tests | `test_statute_aware_preserver.py` | 11/11 PASS | **COMPLETE ✅** |
| **6** | Create Phase 8.3A pipeline (reranker + preservation fusion) | `LegalReranker`, `StatuteAwarePreserver` | `experimental_phase_8_3a/pipeline.py`, `runner.py` | **COMPLETE ✅** |
| **7** | Identify and fix scoring regression (first pipeline incorrectly replaced reranker) | Benchmark run 1 results | Corrected `pipeline.py` | **COMPLETE ✅** |
| **8** | Run baseline Configuration A through Configuration D | Verified 59-case benchmark set | `phase_8_3a_results.json`, `phase_8_3a_benchmark_report.md` | **IN PROGRESS 🔄** |
| **9** | Generate metric comparison | `phase_8_3a_results.json` | `phase_8_3a_benchmark_report.md` | PENDING |
| **10** | Run mandatory safety regressions + red-team | `run_phase_8_3a_red_team.py` | `phase_8_3a_failure_analysis.md` | PENDING |
| **11** | Run red-team adversarial analysis | Adversarial trap suite (5 cases), Mandatory 7-test suite | Verified safety | PENDING |
| **12** | Perform change audit | File diff inspection | `phase_8_3a_change_audit.md` | **COMPLETE ✅** |
| **13** | Produce independent recommendation & final verdict | Benchmark matrix, safety results | Master ledger verdict | PENDING |

---

## 2. Quarantine Registry (Immutable)

| Case Range | Status | Reason | Affected Count |
| :--- | :--- | :--- | :---: |
| `BLIND-011` through `BLIND-050` | **QUARANTINED** | Placeholder template contamination | 40 |
| `BLIND-003` | **QUARANTINED** | References nonexistent bare-act section | 1 |
| All other verified cases | **ACTIVE** | Ground truth independently forensically verified | 59 |

---

## 2. Phase 8.3A Configuration Registry

| Config | Mode | Strategy | Key Thresholds |
| :--- | :--- | :--- | :--- |
| **Config A** | `CONFIG_A` | Phase 8.2G baseline behavior — no additional preservation | N/A |
| **Config B** | `CONFIG_B` | Hard-protect top local candidate from every active statute branch | `branch_score > 0` |
| **Config C** | `CONFIG_C` | Evidence + relevance threshold-gated protection | `min_issue_relevance=0.25`, `min_evidence_score=12.0`, `branch_preservation_threshold=28.0` |
| **Config D** | `CONFIG_D` | Soft preservation multiplier bonus on global score | `preservation_bonus_multiplier=0.35`, `max_preservation_bonus=35.0` |

---

## 3. Verified Immutable Artifacts (Phase 8.2G Frozen Baseline)

| Artifact | Path | Modification Status |
| :--- | :--- | :--- |
| Ground Truth ADV-001..050 | `evaluation/ground_truth_adv_50.json` | UNTOUCHED |
| Ground Truth BLIND-001..010 (verified) | `evaluation/ground_truth_narrative_blind_50.json` | UNTOUCHED |
| Phase 8.2G Benchmark Results | `evaluation/phase_8_2g_benchmark_results.json` | UNTOUCHED |
| All `phase_8_2g_*.md` reports | `evaluation/phase_8_2g_*.md` | UNTOUCHED |
| Official Gazette Corpus | `corpus_integrity/*.jsonl` | UNTOUCHED |
| Production Retriever | `retrieval/hybrid_retriever.py` | UNTOUCHED |
| Production Firewall | `verification/claim_firewall.py` | UNTOUCHED |

---

## 4. Stop Conditions (Monitoring Active)

- [ ] Production files modified → **STOP**
- [ ] False corrections > 0 → **STOP**
- [ ] Hallucinations > 0 → **STOP**
- [ ] Preservation layer artificially injects irrelevant sections → **STOP**
- [ ] Phase 8.2G benchmark artifacts overwritten → **STOP**
