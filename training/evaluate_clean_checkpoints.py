# evaluate_clean_checkpoints.py — Nyaya Legal OS Phase 6.8D Refined Predicate Checkpoint Evaluator
# 
# Technical Features:
# 1. Fresh Base Model per Checkpoint (Zero adapter stacking).
# 2. Refined Semantic Predicates for Q4, Q9, and Q10 (Exact proposition verification).
# 3. Dynamic Selection Gate:
#    - Gate 1: Zero Substantive Hallucinations (hallucinations == 0)
#    - Gate 2: Highest Strict Predicate Legal Score
#    - Gate 3: Tie-breaker using Lowest Validation Loss
# 4. HF Deprecation Fix: Uses `dtype=torch.float16`.
#
# Target Checkpoints: 40, 50, 60, 70, 80, 90, 100, 110

import os
import sys
import gc
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List

if "CUDA_VISIBLE_DEVICES" not in os.environ:
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

try:
    from peft import PeftModel
except ImportError:
    PeftModel = None

MODEL_NAME = "unsloth/Meta-Llama-3.1-8B-Instruct"
HF_TOKEN = os.getenv("HF_TOKEN", None)
SWEEP_DIR = Path("./nyaya_checkpoint_sweep_68c")

# --- Refined Predicate Evaluators ---

def evaluate_predicate_q1(ans: str) -> bool:
    has_bns = ("bns" in ans or "bharatiya nyaya" in ans)
    has_wrong = any(w in ans for w in ["bnss", "bsa", "bncp", "bncr", "crpc"])
    return has_bns and not has_wrong

def evaluate_predicate_q2(ans: str) -> bool:
    has_bnss = ("bnss" in ans or "bharatiya nagarik" in ans)
    has_wrong = any(w in ans for w in ["bsa", "bncp", "bncrcp", "bordeau", "ipc"])
    return has_bnss and not has_wrong

def evaluate_predicate_q3(ans: str) -> bool:
    has_bsa = ("bsa" in ans or "bharatiya sakshya" in ans)
    has_wrong = any(w in ans for w in ["bnss", "it act", "information technology"])
    return has_bsa and not has_wrong

def evaluate_predicate_q4(ans: str) -> bool:
    positive = (
        "pocso" in ans
        and (
            "not repealed" in ans
            or "not repeal" in ans
            or "remains in force" in ans
            or "remains a separate" in ans
            or "separate special statute" in ans
            or "separate special law" in ans
            or "remains separate" in ans
            or "unrepealed" in ans
        )
    )
    negative = (
        "bns repeals pocso" in ans
        or "bns repealed pocso" in ans
        or "bns replaces pocso" in ans
        or "pocso is subsumed" in ans
        or "pocso has been subsumed" in ans
        or "replaced the pocso" in ans
    )
    return positive and not negative

def evaluate_predicate_q5(ans: str) -> bool:
    declares_no = ans.startswith("no") or "does not replace" in ans or "bnss replaces" in ans
    claims_yes = ans.startswith("yes") or "bns replaces the crpc" in ans
    return declares_no and not claims_yes

def evaluate_predicate_q6(ans: str) -> bool:
    return ("bns" in ans or "bharatiya nyaya" in ans) and not any(w in ans for w in ["bnss", "bsa", "bncp"])

def evaluate_predicate_q7(ans: str) -> bool:
    return ("bnss" in ans or "bharatiya nagarik" in ans) and not any(w in ans for w in ["bordeau", "bncp", "bncrcp"])

def evaluate_predicate_q8(ans: str) -> bool:
    return ("bsa" in ans or "bharatiya sakshya" in ans) and not any(w in ans for w in ["it act", "information technology", "dpdp"])

def evaluate_predicate_q9(ans: str) -> bool:
    positive = (
        "pocso" in ans
        and (
            "not subsumed" in ans
            or "is not subsumed" in ans
            or "remains separate" in ans
            or "separate special statute" in ans
            or "independent special law" in ans
            or "independent statute" in ans
        )
    )
    negative = (
        "pocso is subsumed" in ans
        or "pocso has been subsumed" in ans
        or "subsumed into bns" in ans
        or "rewritten in bns" in ans
        or "replaced by bns" in ans
    )
    return positive and not negative

def evaluate_predicate_q10(ans: str) -> bool:
    if ans.startswith("yes"):
        return False
    substantive = (
        "bns" in ans
        and (
            "substantive" in ans
            or "substantive offence" in ans
            or "substantive criminal" in ans
            or "substantive law" in ans
        )
    )
    procedure = (
        "bnss" in ans
        and (
            "criminal procedure" in ans
            or "procedure" in ans
            or "procedural" in ans
        )
    )
    wrong = (
        "bns governs criminal procedure" in ans
        or "bns replaces crpc" in ans
    )
    return substantive and procedure and not wrong

PREDICATE_EVALUATORS = {
    "Q1": evaluate_predicate_q1,
    "Q2": evaluate_predicate_q2,
    "Q3": evaluate_predicate_q3,
    "Q4": evaluate_predicate_q4,
    "Q5": evaluate_predicate_q5,
    "Q6": evaluate_predicate_q6,
    "Q7": evaluate_predicate_q7,
    "Q8": evaluate_predicate_q8,
    "Q9": evaluate_predicate_q9,
    "Q10": evaluate_predicate_q10
}

STRICT_TEST_QUESTIONS = [
    {"id": "Q1", "question": "Which statute replaced the Indian Penal Code, 1860?"},
    {"id": "Q2", "question": "Which statute replaced the Code of Criminal Procedure, 1973?"},
    {"id": "Q3", "question": "Which statute replaced the Indian Evidence Act, 1872?"},
    {"id": "Q4", "question": "Did the Bharatiya Nyaya Sanhita, 2023 repeal or replace the POCSO Act, 2012?"},
    {"id": "Q5", "question": "Does BNS 2023 replace the Code of Criminal Procedure?"},
    {"id": "Q6", "question": "Which legislation succeeded the IPC?"},
    {"id": "Q7", "question": "What replaced the 1973 criminal-procedure code?"},
    {"id": "Q8", "question": "What is the successor to the Indian Evidence Act?"},
    {"id": "Q9", "question": "Is POCSO subsumed into BNS?"},
    {"id": "Q10", "question": "Does BNS govern criminal procedure?"}
]

SUBSTANTIVE_HALLUCINATION_TERMS = [
    "bncp", "bncr", "bncrcp", "bordeau", "bordeau-nariman",
    "bns replaces crpc", "bns repeals pocso", "pocso subsumed",
    "bsa replaced by it act", "bnss = bharatiya nyaya", "january 1, 2024",
    "bharatiya nyaya sanhita sangha"
]
