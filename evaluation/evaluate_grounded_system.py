# evaluate_grounded_system.py — Nyaya Legal OS Phase 6.9 Grounded 3-Tier System Evaluator
#
# Objective:
# Evaluate the full 3-Tier Grounded Nyaya System:
# 1. Authoritative RAG Retriever (Authoritative Corpus + Cross-Mappings)
# 2. Conditioned LLM (Behavioral Adapter / Fast CPU Model + Evidence Pack)
# 3. Legal Verification Firewall (Claim Extractor & Enforcement)

import os
import sys
import gc
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

try:
    from peft import PeftModel
    HAS_PEFT = True
except ImportError:
    HAS_PEFT = False

BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall
from training.evaluate_clean_checkpoints import PREDICATE_EVALUATORS, STRICT_TEST_QUESTIONS

MODEL_NAME_GPU = "unsloth/Meta-Llama-3.1-8B-Instruct"
MODEL_NAME_CPU = "Qwen/Qwen2.5-0.5B-Instruct"
HF_TOKEN = os.getenv("HF_TOKEN", None)
CHECKPOINT_PATH = Path("./nyaya_checkpoint_sweep_68c/checkpoint-60")

def load_grounded_llm():
    gc.collect()
    
    if torch.cuda.is_available():
        print(f"[+] CUDA GPU Detected: {torch.cuda.get_device_name(0)}. Loading 4-Bit NF4 Quantized Llama 3.1 8B...")
        torch.cuda.empty_cache()
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16,
        )
        base_model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME_GPU,
            quantization_config=bnb_config,
            device_map={"": 0},
            dtype=torch.float16,
            low_cpu_mem_usage=True,
            token=HF_TOKEN,
            trust_remote_code=True,
        )
        model_name_used = MODEL_NAME_GPU
    else:
        print(f"[+] Local CPU Mode: Loading lightweight '{MODEL_NAME_CPU}' for instant zero-delay local execution...")
        base_model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME_CPU,
            device_map="cpu",
            low_cpu_mem_usage=True,
            token=HF_TOKEN,
            trust_remote_code=True,
        )
        model_name_used = MODEL_NAME_CPU

    if HAS_PEFT and CHECKPOINT_PATH.exists() and torch.cuda.is_available():
        print(f"[+] Loading Checkpoint-60 behavioral adapter from: {CHECKPOINT_PATH.name}")
        model = PeftModel.from_pretrained(base_model, str(CHECKPOINT_PATH), is_trainable=False)
    else:
        print(f"[+] Running 3-Tier System with {model_name_used} + Authoritative RAG + Claim Firewall.")
        model = base_model

    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(model_name_used, token=HF_TOKEN, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return model, tokenizer

def run_phase_6_9_grounded_evaluation():
    print("=========================================================================")
    print("=== NYAYA LEGAL OS — PHASE 6.9 GROUNDED 3-TIER SYSTEM EVALUATION       ===")
    print("=========================================================================")

    retriever = AuthoritativeLegalRetriever()
    firewall = LegalVerificationFirewall()
    model, tokenizer = load_grounded_llm()

    results = []
    strict_score = 0
    firewall_interventions = 0

    for q_spec in STRICT_TEST_QUESTIONS:
        q_id = q_spec["id"]
        q_text = q_spec["question"]

        # Step 1: Retrieve Authoritative RAG Evidence Pack
        evidence_pack = retriever.retrieve_evidence_pack(q_text)
        evidence_ctx = retriever.format_evidence_context(evidence_pack)

        # Step 2: Construct RAG-Conditioned Legal Prompt
        prompt = (
            f"You are Nyaya Darshana, an expert Indian Legal AI Assistant fine-tuned to reason, structure, cite, and respond strictly according to current Indian Statutory Law (BNS 2023, BNSS 2023, BSA 2023).\n"
            f"Use the following authoritative statutory evidence to answer the user's question accurately.\n\n"
            f"{evidence_ctx}\n\n"
            f"User Question: {q_text}\n"
            f"Answer:"
        )

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=100, do_sample=False, pad_token_id=tokenizer.eos_token_id)
        raw_llm_ans = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

        # Step 3: Run Legal Verification Firewall
        passed_fw, final_enforced_ans, claims = firewall.verify_and_enforce(raw_llm_ans, evidence_pack)
        ans_lower = final_enforced_ans.lower()

        # Step 4: Strict Predicate Legal Evaluation
        eval_fn = PREDICATE_EVALUATORS[q_id]
        is_correct = eval_fn(ans_lower)

        if is_correct:
            strict_score += 1

        if not passed_fw:
            firewall_interventions += 1

        results.append({
            "id": q_id,
            "question": q_text,
            "raw_llm": raw_llm_ans,
            "final_answer": final_enforced_ans,
            "firewall_passed": passed_fw,
            "is_correct": is_correct
        })

        print(f"\n[{q_id}]: {q_text}")
        print(f"  - Authoritative Evidence Facts : {len(evidence_pack['authoritative_facts'])}")
        print(f"  - Raw LLM Output               : {raw_llm_ans[:100]}...")
        print(f"  - Final Enforced Answer        : {final_enforced_ans[:120]}...")
        print(f"  - Grounding Status             : {'PASS ✅' if is_correct else 'FAIL ❌'} (Firewall Clean: {passed_fw})")

    print("\n=========================================================================")
    print("=== PHASE 6.9 GROUNDED 3-TIER EVALUATION MATRIX                        ===")
    print("=========================================================================")
    print(f"  - Total Questions Evaluated         : {len(STRICT_TEST_QUESTIONS)}")
    print(f"  - Strict Predicate Score            : {strict_score}/{len(STRICT_TEST_QUESTIONS)} ({strict_score*10}%)")
    print(f"  - Verification Firewall Interventions: {firewall_interventions}")
    print(f"  - Production Readiness Status       : {'READY FOR PHASE 6.9J HELD-OUT BENCHMARK ✅' if strict_score >= 8 else 'NEEDS FINE-TUNING / RAG REFINEMENT ⚠️'}")
    print("=========================================================================")

if __name__ == "__main__":
    run_phase_6_9_grounded_evaluation()
