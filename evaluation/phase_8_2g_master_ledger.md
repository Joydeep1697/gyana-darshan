# NYAYA DARSHANA — PHASE 8.2G MASTER EXPERIMENT LEDGER

**Protocol**: Ground-Truth Forensics + Issue-Decomposed Legal Retrieval  
**Executive Orchestrator**: Agent 0 (Chief Technology Officer & Program Director)  
**Status**: IN_PROGRESS  
**Baseline Frozen Date**: 2026-08-19  

---

## 1. Master Agent & Task Ledger

| Agent | Role | Task Description | Input Artifacts | Output Artifacts | Files Modified / Created | Validation Status | Reviewer | Approval Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Agent 0** | Executive Orchestrator | Program initialization, execution coordination, handoff gating, and final synthesis | User Request Protocol | `evaluation/phase_8_2g_master_ledger.md` | `evaluation/phase_8_2g_master_ledger.md` | VERIFIED | Executive | APPROVED |
| **Agent 1** | QA Data Forensics Engineer | Full forensic audit of 100 benchmark ground-truth records (ADV-001..050, BLIND-001..050) against bare acts | `evaluation/ground_truth_adv_50.json`, `evaluation/ground_truth_narrative_blind_50.json`, `evaluation/narrative_blind_50.jsonl`, `corpus_integrity/*` | `evaluation/phase_8_2g_ground_truth_forensics.jsonl`, `evaluation/phase_8_2g_ground_truth_forensics_report.md` | `evaluation/phase_8_2g_ground_truth_forensics.jsonl`, `evaluation/phase_8_2g_ground_truth_forensics_report.md` | VERIFIED | Agent 2 | APPROVED |
| **Agent 2** | Legal Provenance Auditor | Independent audit and statutory verification of Agent 1's findings | `evaluation/phase_8_2g_ground_truth_forensics.jsonl`, `corpus_integrity/*` | `evaluation/phase_8_2g_provenance_audit.jsonl` | `evaluation/phase_8_2g_provenance_audit.jsonl` | VERIFIED | Agent 0 | APPROVED |
| **Agent 3** | Retrieval Diagnostics Engineer | Run pure baseline retrieval on all cases, classify failure modes | Frozen Baseline Retriever, Verified GT | `evaluation/phase_8_2g_retrieval_diagnostics.jsonl` | `evaluation/phase_8_2g_retrieval_diagnostics.jsonl` | VERIFIED | Agent 0 | APPROVED |
| **Agent 4** | Legal Issue Decomposition Architect | Create experimental text-based issue decomposer | Query text | `retrieval/experimental/issue_decomposer.py` | `retrieval/experimental/issue_decomposer.py` | VERIFIED | Agent 8 | APPROVED |
| **Agent 5** | Legal Concept Expansion Engineer | Create experimental semantic concept expander | Query text, Legal concepts | `retrieval/experimental/legal_concept_expander.py` | `retrieval/experimental/legal_concept_expander.py` | VERIFIED | Agent 8 | APPROVED |
| **Agent 6** | Multi-Statute Retrieval Engineer | Create parallel statute retriever preserving cross-statute recall | Corpus JSONL, Decomposed Issues | `retrieval/experimental/parallel_statute_retriever.py` | `retrieval/experimental/parallel_statute_retriever.py` | VERIFIED | Agent 8 | APPROVED |
| **Agent 7** | Legal Reranking Engineer | Create explainable candidate reranker | Candidate sections, Decomposed issues | `retrieval/experimental/legal_reranker.py` | `retrieval/experimental/legal_reranker.py` | VERIFIED | Agent 8 | APPROVED |
| **Agent 9** | Evidence Sufficiency Engineer | Create evidence grounding evaluator (SUPPORTED / PARTIALLY / INSUFFICIENT) | Retrieved evidence, issues | `retrieval/experimental/evidence_sufficiency.py` | `retrieval/experimental/evidence_sufficiency.py` | VERIFIED | Agent 8 | APPROVED |
| **Agent 8** | Systems Integration Engineer | Integrate experimental components into end-to-end pipeline | Experimental modules (4, 5, 6, 7, 9) | `experimental_phase_8_2g/pipeline.py` | `experimental_phase_8_2g/pipeline.py` | VERIFIED | Agent 10 | APPROVED |
| **Agent 10** | Firewall Regression Auditor | Execute firewall & regression tests on baseline vs experimental | Firewall test suites | `evaluation/phase_8_2g_firewall_audit.md` | `evaluation/phase_8_2g_firewall_audit.md` | VERIFIED | Agent 14 | APPROVED |
| **Agent 11** | Independent Benchmark Evaluator | Execute side-by-side benchmark evaluation on verified cases | Baseline & Experimental pipelines, Verified GT | `evaluation/phase_8_2g_benchmark_results.json`, `evaluation/phase_8_2g_benchmark_report.md` | `evaluation/phase_8_2g_benchmark_results.json`, `evaluation/phase_8_2g_benchmark_report.md` | VERIFIED | Agent 14 | APPROVED |
| **Agent 12** | Red Team / Failure Forensics | Root cause analysis of remaining failures | Evaluation outputs | `evaluation/phase_8_2g_red_team_analysis.md` | `evaluation/phase_8_2g_red_team_analysis.md` | VERIFIED | Agent 14 | APPROVED |
| **Agent 13** | Release Engineering Auditor | Change isolation, frozen benchmark non-modification audit | Git repository state | `evaluation/phase_8_2g_change_audit.md` | `evaluation/phase_8_2g_change_audit.md` | VERIFIED | Agent 14 | APPROVED |
| **Agent 14** | Independent Reviewer | Principal Engineering review of all metrics, safety, and reproducibility | All artifacts | `evaluation/phase_8_2g_independent_review.md` | `evaluation/phase_8_2g_independent_review.md` | VERIFIED | Agent 0 | APPROVED |

---

## 2. Phase Execution Sequence Log

- [x] **Phase 0**: Ledger Initialization & Program Setup (Agent 0)
- [x] **Phase A**: Benchmark Ground-Truth Forensics & Provenance Audit (Agents 1, 2, 0)
- [x] **Phase B**: Baseline Retrieval Diagnostics & Failure Classification (Agent 3)
- [x] **Phase C**: Experimental Architecture Construction (Agents 4, 5, 6, 7, 9)
- [x] **Phase D**: Experimental Pipeline Integration (Agent 8)
- [x] **Phase E**: Firewall & Safety Regression Audit (Agent 10)
- [x] **Phase F**: Independent Comparative Benchmark Evaluation (Agent 11)
- [x] **Phase G**: Red Team Failure Root-Cause Analysis (Agent 12)
- [x] **Phase H**: Release Engineering & Code Integrity Audit (Agent 13)
- [x] **Phase I**: Executive Review & Final Gate Decision (Agents 14, 0)
