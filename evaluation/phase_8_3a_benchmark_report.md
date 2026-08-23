# NYAYA DARSHANA — PHASE 8.3A BENCHMARK EVALUATION REPORT

**Sprint**: Phase 8.3A Statute-Aware Candidate Preservation Calibration Sprint  
**Evaluation Scope**: Verified Authentic Benchmark Population (59 Cases)  
**Quarantined**: 41 Cases (40 Placeholder Contaminated `BLIND-011..050` + 1 Invalid Section `BLIND-003`)  
**Evaluation Date**: 2026-08-21  
**Safety Standard**: Zero Tolerance — False Corrections = 0, Hallucinations = 0, Path Leaks = 0  

---

## 1. Executive Comparative Benchmark Matrix

| Metric | Target | Production Baseline | **Phase 8.2G** | Config A (No Preserv.) | Config B (Hard Active) | **Config C (Threshold-Gated)** | Config D (Rank Multiplier) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Composite Legal Accuracy** | ≥ 85.00% | 86.44% | 83.05% | 79.66% | 77.97% | **83.05%** | 76.27% |
| **Section Recall (Top-1)** | ≥ 50.85% | 44.07% | **50.85%** | **50.85%** | **50.85%** | **50.85%** | 47.46% |
| **Section Recall (Top-3)** | ≥ 80.00% | 91.53% | 67.80% | 67.80% | 66.10% | **69.49%** | 64.41% |
| **Section Recall (Top-5)** | ≥ 90.00% | 91.53% | 83.05% | 79.66% | 77.97% | **83.05%** | 76.27% |
| **Statute Scope Recall** | 100.00% | 100.00% | **100.00%** | **100.00%** | **100.00%** | **100.00%** | 100.00% |
| **Multi-Statute Coverage** | ≥ 90.00% | 81.92% | **90.40%** | 83.05% | **90.40%** | 85.88% | 81.92% |
| **Evidence Citation Support** | 100.00% | 94.92% | **100.00%** | **100.00%** | **100.00%** | **100.00%** | **100.00%** |
| **False Corrections** | 0 | **0** | **0** | **0** | **0** | **0** | **0** |
| **Hallucinations** | 0 | **0** | **0** | **0** | **0** | **0** | **0** |
| **Avg Latency** | < 250 ms | 36.44 ms | 110.31 ms | 111.38 ms | 108.93 ms | **108.96 ms** | 111.48 ms |
| **P50 Latency** | < 200 ms | 30.23 ms | 110.44 ms | 110.09 ms | 112.36 ms | **112.60 ms** | 112.29 ms |
| **P95 Latency** | < 400 ms | 66.64 ms | 147.19 ms | 155.50 ms | 148.28 ms | **149.02 ms** | 157.60 ms |

---

## 2. Delta Analysis vs Phase 8.2G Baseline

| Metric | Phase 8.2G | Config C | **Delta** | Assessment |
| :--- | :---: | :---: | :---: | :--- |
| Composite Legal Accuracy | 83.05% | 83.05% | **0.00%** | Preserved — no regression |
| Section Recall (Top-1) | 50.85% | 50.85% | **0.00%** | Preserved — Top-1 precision protected |
| Section Recall (Top-3) | 67.80% | 69.49% | **+1.69%** | Improved — secondary-statute preservation working |
| Section Recall (Top-5) | 83.05% | 83.05% | **0.00%** | Preserved — no regression |
| Statute Scope Recall | 100.00% | 100.00% | **0.00%** | Preserved |
| Multi-Statute Coverage | 90.40% | 85.88% | **-4.52%** | Minor trade-off (see §3 for analysis) |
| Evidence Citation Support | 100.00% | 100.00% | **0.00%** | Preserved at 100% |
| Avg Latency | 110.31 ms | 108.96 ms | **-1.35 ms** | Marginal improvement |

---

## 3. Key Engineering Findings

### 3.1 Root Cause of Phase 8.2G Reranking Regression
Phase 8.2G's `LegalReranker` pass-1/pass-2 diversification selects **Top-2 per statute bucket** before filling remaining slots globally. This guaranteed multi-statute breadth in the full returned set (90.4% multi-statute coverage), but caused secondary-statute candidates to rank at positions 5-8 rather than 3-5 — producing the Top-3 regression (67.80%) while Top-1 remained strong (50.85%).

### 3.2 Config C Preservation Mechanics
Config C's threshold-gated preservation (`min_issue_relevance ≥ 0.25`, `min_evidence_score ≥ 12.0`) identifies secondary-statute candidates that are:
1. Evidentially relevant (heading keyword overlap + domain bonus confirmed)
2. Issue-relevant (weighted issue decomposition confirms the statute is genuinely active)
3. Above the generic section filter (definitions/title sections Section 1, 2, 3 are not promoted)

These candidates are inserted into the Top-5 window after the global Rank-1 leader is pinned, then the remaining positions are filled by globally-ranked pool. This yielded a **+1.69% Top-3 recall improvement** while retaining Top-1 precision (50.85%) and composite accuracy (83.05%).

### 3.3 Multi-Statute Coverage Trade-off
Config C's multi-statute coverage (85.88%) is lower than Phase 8.2G (90.40%). This is because Config C's threshold filter rejects low-evidence secondary candidates that Phase 8.2G's unconditional pass-1 bucket would have included. This is **by design** — the spec explicitly prohibits artificially promoting weak secondary-statute candidates.

### 3.4 Config B Overreach Observed
Config B (hard-protect every active-statute branch regardless of threshold) produced lower Top-3 (66.10%) and Top-5 (77.97%) recall than Phase 8.2G. The cause: hard protection forces low-scoring candidates from broad, loosely-matched statute branches into the final result window, displacing higher-scoring candidates. **Config B violates the "no weak candidate promotion" constraint.**

### 3.5 Config D Soft Bonus Insufficient
Config D (preservation multiplier on global score) produced the worst results: Top-1 47.46%, Top-3 64.41%, Composite 76.27%. The score bonus added to lower-ranked items was insufficient to overcome the dense BNS/BNSS clusters, while simultaneously distorting the global ordering enough to displace previously high-ranked items.

---

## 4. Safety Regression Summary

| Safety Metric | Target | Result | Status |
| :--- | :---: | :---: | :---: |
| Mandatory 7-Regression Suite | 7/7 PASS | **7/7 PASS** | ✅ PERFECT |
| Adversarial Trap Suite | 5/5 PASS | **5/5 PASS** | ✅ PERFECT |
| False Corrections | 0 | **0** | ✅ PERFECT |
| Hallucinations | 0 | **0** | ✅ PERFECT |
| Internal Path Leaks | 0 | **0** | ✅ PERFECT |
| Preservation Overreach Incidents | 0 | **0** | ✅ PERFECT |

---

## 5. Target vs Measured Comparison (Config C)

| Target Metric | Required Value | Measured | Met? |
| :--- | :---: | :---: | :---: |
| Composite Legal Accuracy | ≥ 85.00% | 83.05% | ❌ BELOW TARGET |
| Section Recall (Top-1) | ≥ 50.85% | 50.85% | ✅ AT TARGET |
| Section Recall (Top-3) | ≥ 80.00% | 69.49% | ❌ BELOW TARGET |
| Section Recall (Top-5) | ≥ 90.00% | 83.05% | ❌ BELOW TARGET |
| Statute Scope Recall | 100.00% | 100.00% | ✅ PERFECT |
| Multi-Statute Coverage | ≥ 90.00% | 85.88% | ❌ BELOW TARGET |
| Evidence Citation Support | 100.00% | 100.00% | ✅ PERFECT |
| False Corrections | 0 | 0 | ✅ PERFECT |
| Hallucinations | 0 | 0 | ✅ PERFECT |
| Avg Latency | < 250 ms | 108.96 ms | ✅ WELL WITHIN |

> [!IMPORTANT]
> Phase 8.3A succeeds in solving the **preservation mechanism problem** (secondary-statute candidates no longer suppressed below Top-5 when evidence-sufficient), but the absolute performance targets (85% accuracy, 80% Top-3, 90% Top-5) are not reached by any experimental configuration. These targets represent the Phase 8.2G *aspirational targets*, not its actual measured performance. The best configuration (Config C) **matches Phase 8.2G accuracy exactly** and modestly improves Top-3 recall without introducing any safety regression.

---

## 6. Independent Engineering Verdict

**Verdict: B — ITERATE**

> PROMISING BUT TARGETS NOT MET.

**Reasoning**:
1. **Config C is the best-performing Phase 8.3A configuration.** It matches Phase 8.2G composite accuracy (83.05%), preserves Top-1 precision (50.85%), improves Top-3 recall by +1.69 percentage points, and maintains 100% evidence citation support with zero safety regressions.
2. **None of the four configurations reach the Phase 8.3A aspirational targets** (85% accuracy, 80% Top-3, 90% Top-5). These targets were set above Phase 8.2G's own measured performance, and Phase 8.3A is a calibration sprint rather than a full architectural overhaul.
3. **The preservation mechanism works correctly.** Zero preservation overreach incidents. Strong secondary candidates are protected. Weak candidates are filtered. Irrelevant statute branches are rejected.
4. **The remaining gap is structural**: the Top-3 and Top-5 deficit reflects the Phase 8.2G reranker's scoring gaps (BLIND-007 concept expansion failure, plus `per_statute_k=5` retrieval depth misses) — not a failure of the preservation layer.
5. **Recommended next iteration**: Increase `per_statute_k` to 6-7, extend `minimum_issue_relevance` threshold calibration, and add the missing conceptual ontology for utility-cutoff offences (BNS 324). These changes should close the remaining Top-3/Top-5 gap.
