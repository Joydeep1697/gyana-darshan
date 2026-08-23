# Phase 6 — SFT / QLoRA Pipeline for Nyaya Darshan
**Project**: Nyaya Legal OS  
**Objective**: Build a high-precision Supervised Fine-Tuning (SFT) & QLoRA pipeline to train **Nyaya Darshan** on legal reasoning, statutory qualification, structure, citation standards, challenging false premises, handling historical vs. current 2023 laws, and resisting hallucination.

---

## 1. Phase 6 Execution Status Roadmap

| Phase | Milestone | Status | Details |
|---|---|---|---|
| **6.1** | Training Infrastructure | **DONE** | Pipeline scripts created in `training/` |
| **6.2** | Hardware Preflight Audit | **DONE** | Local 4 GB VRAM vs Cloud 16 GB VRAM requirement logged |
| **6.3** | QLoRA Configuration | **DONE** | Recorded in `config.yaml` (`Meta-Llama-3.1-8B-Instruct`, 4-bit NF4, r=16, alpha=32, LR=1e-4) |
| **6.4** | Inference Pipeline | **DONE** | `inference.py` engine with RAG context support |
| **6.5** | Evaluation Framework | **DONE** | `evaluate_model.py` reporting strictly `NOT TRAINED / N/A` for QLoRA |
| **6.6** | Training Corpus Expansion | **DONE** | Expanded to **2,100 examples** across 11 legal categories |
| **6.7** | Quality Audit & Group-Aware Split | **DONE** | 0% benchmark leakage, 1,611 train / 206 val / 163 test split |
| **6.7.5** | Source-Grounding Audit | **DONE** | 100% CLEAN PASS (`source_audit.json` & `source_audit.md`) |
| **6.8A** | Stage A Infrastructure & Reload | **PASSED** | **100/100 steps**, 41.9M params reloaded, 258MB adapter verified |
| **6.8A** | Stage A Legal Quality Audit | **FLAGGED** | Caught hallucination ("BNS replaces CrPC & POCSO"). Pre-Stage B fixes active |
| **6.8** | **Pre-Stage B Enhancements** | **COMPLETED** | **1.** Completion-Only Loss (`DataCollatorForCompletionOnlyLM`) <br>**2.** Statutory Fact Audit (`audit_dataset_facts.py` -> 100% pass) <br>**3.** Deterministic Benchmark (`legal_sanity_benchmark.jsonl`) |
| **6.8B** | Full QLoRA Training | **GATED** | 3-epoch full training gated by Pre-Stage B enhancements |
| **6.9** | Real Post-Training Evaluation | **NOT STARTED** | Held-out 163 training test + 800 benchmark + 22 adversarial cases |
| **6.10** | Select / Reject Adapter | **NOT STARTED** | Decision gate based on post-training metrics vs Model B (Base+RAG) |

---

## 2. Pre-Stage B Legal Quality Enhancements

1. **Completion-Only Loss (`DataCollatorForCompletionOnlyLM`)**:
   System and User prompt tokens are masked (`-100`). 100% of loss gradient is focused strictly on the assistant's legal answers, citations, and structural reasoning.
2. **Statutory Fact Audit (`audit_dataset_facts.py`)**:
   Programmatic fact verification confirming 1,611 training records maintain strict 1:1 IPC->BNS, CrPC->BNSS, IEA->BSA mapping, with POCSO Act 2012 cited as an un-repealed special law (Passed 100% clean).
3. **Deterministic Legal Benchmark (`legal_sanity_benchmark.jsonl`)**:
   10-item ground-truth test suite to evaluate pre vs post Stage B legal precision.

---

## 3. Post-Training Evaluation Protocol (Phase 6.9)

After full training, compare 3 models against the held-out benchmark:
- **Model A**: Base LLM (`Meta-Llama-3.1-8B-Instruct`)
- **Model B**: Base LLM + RAG Retrieval + Statutory Validator
- **Model C**: QLoRA LLM + RAG Retrieval + Statutory Validator

### Decision Gate:
* If Model C (QLoRA + RAG) scores **worse** than Model B (Base + RAG) on legal accuracy, citation, or hallucination resistance, **the adapter will be rejected**.
