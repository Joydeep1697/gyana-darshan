# NYAYA DARSHAN — KNOWN LIMITATIONS & OPERATIONAL CONSTRAINTS

**Version**: 2.0.0 (Production Release)  
**Date**: 2026-08-21  

---

## 1. Statutory Retrieval Limitations

1. **Complex Narrative Fact-Pattern Coverage on Secondary Offences (BLIND-007 type cases)**:
   - Narratives involving criminal interference with essential utility supplies (such as landlord water/electricity cutoffs) require explicit keyword cues or future concept expansion bridging to BNS Section 324 (Mischief). Without explicit cues, retrieval may prioritize tenancy civil remedies over penal mischief provisions.
2. **Obscure Sub-Provision Retrieval Depth**:
   - For queries requiring secondary statute retrieval beyond `top_k=5` within a single statute branch, retrieval accuracy is bounded by `per_statute_k=5`. High-cardinality multi-statute queries with 3+ overlapping codes may experience slight secondary recall suppression below Top-5.
3. **Quarantined Synthetic Test Data**:
   - Benchmark cases `BLIND-011` through `BLIND-050` (placeholder-contaminated) and `BLIND-003` (invalid section reference) remain quarantined from statutory performance accounting. The verified operational population consists of 59 forensically verified authentic cases.

---

## 2. Infrastructure & Deployment Constraints

1. **In-Memory Rate Limiter Scope**:
   - The rate limiter is currently in-memory per worker process. On multi-worker setups (e.g. `--workers 2`), the effective rate limit is `300 * num_workers` RPM across the cluster. For high-scale distributed deployments, an external Redis backend is recommended in a future milestone.
2. **Synchronous Audit Log Writes**:
   - API audit logs are appended to `logs/nyaya_api_audit.jsonl` synchronously on request completion. At current throughput (< 1,000 RPM) this introduces negligible latency (~0.1ms), but for ultra-high concurrency it should be offloaded to an asynchronous background task worker.
3. **Local Embedding Model Loading Time**:
   - The initial loading of the sentence transformer embedding model (`all-mpnet-base-v2`) requires ~5-8 seconds during container cold start. Cold startup probes should allow a 15-second initial delay before health checking.
