# run_checkpoint_sweep.py — Nyaya Legal OS Phase 6.8C Early-Checkpoint Selection Experiment
# 
# Objective:
# Run a short, highly instrumented 150-step training sweep.
# Evaluate every 10 steps (10, 20, 30, ... 150) against:
# 1. Validation Loss & Token Accuracy
# 2. 10-Item Legal Sanity & Adversarial Benchmark
# 3. Hallucination Detection Rate
#
# Select the winning checkpoint based on Legal Correctness + Zero Hallucinations.

import os
import sys
import gc
import json
import time
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List

# Force single GPU visibility
if "CUDA_VISIBLE_DEVICES" not in os.environ:
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# --- 0. HARD GPU CLEANUP ---
print("[0] Cleaning previous GPU objects...")
for _name in ["trainer", "model", "base_model_reload", "reloaded_model", "tokenizer", "train_ds", "val_ds"]:
    if _name in globals():
        try:
            del globals()[_name]
        except Exception:
            pass

gc.collect()

def ensure_dependency(import_name, pip_name=None):
    try:
        __import__(import_name)
    except ImportError:
        target = pip_name or import_name
        print(f"[+] Installing '{target}'...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", target])

ensure_dependency("trl", "trl")
ensure_dependency("peft", "peft")
ensure_dependency("bitsandbytes", "bitsandbytes")
ensure_dependency("accelerate", "accelerate")
ensure_dependency("datasets", "datasets")

import torch
import transformers
import trl
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, PeftModel
from trl import SFTTrainer, SFTConfig

def resolve_file_path(filename):
    candidates = [
        Path(filename),
        Path("/content") / filename,
        Path("/kaggle/working") / filename,
        Path("/kaggle/input") / filename,
        Path.cwd() / filename
    ]
    if Path("/kaggle/input").exists():
        matches = list(Path("/kaggle/input").rglob(filename))
        if matches:
            candidates.insert(0, matches[0])
    for p in candidates:
        if p.exists():
            return str(p.resolve())
    return filename

MODEL_NAME = "unsloth/Meta-Llama-3.1-8B-Instruct"
HF_TOKEN = os.getenv("HF_TOKEN", None)
TRAIN_FILE = resolve_file_path("train.jsonl")
VAL_FILE = resolve_file_path("validation.jsonl")
SWEEP_DIR = "./nyaya_checkpoint_sweep_68c"

print("=========================================================================")
print("=== NYAYA LEGAL OS — PHASE 6.8C EARLY CHECKPOINT SELECTION SWEEP      ===")
print("=========================================================================")
print(f"Device        : {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
print(f"Target Model  : {MODEL_NAME}")
print(f"Max Steps     : 150 Steps (Eval every 10 steps)")
print(f"Sweep Dir     : {SWEEP_DIR}")
print("=========================================================================\n")

device_map_target = {"": 0} if torch.cuda.is_available() else "auto"

# 1. Load Model
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.float16,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map=device_map_target,
    torch_dtype=torch.float16,
    low_cpu_mem_usage=True,
    token=HF_TOKEN,
    trust_remote_code=True,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# 2. PEFT LoRA (r=8, alpha=16, dropout=0.10)
peft_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'],
    lora_dropout=0.10,
    bias="none",
    task_type="CAUSAL_LM"
)

model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
model = get_peft_model(model, peft_config)

# 3. Dataset Tokenization
def build_prompt_and_completion(example):
    inst = example.get("instruction", "")
    inp = example.get("input", "")
    out = example.get("output", "")
    user_msg = f"{inst}\n{inp}".strip() if inp else inst

    prompt = (
        f"<|start_header_id|>system<|end_header_id|>\n\n"
        f"You are Nyaya Darshana, an expert Indian Legal AI Assistant fine-tuned to reason, structure, cite, and respond strictly according to current Indian Statutory Law (BNS 2023, BNSS 2023, BSA 2023).<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{user_msg}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )
    completion = f"{out}<|eot_id|>"
    return prompt, completion

raw_train = load_dataset('json', data_files=TRAIN_FILE, split='train')
raw_val = load_dataset('json', data_files=VAL_FILE, split='train')

MAX_SEQ_LEN = 512

def tokenize_prompt_completion(example, max_length=MAX_SEQ_LEN):
    prompt_str, completion_str = build_prompt_and_completion(example)
    prompt_ids = tokenizer(prompt_str, add_special_tokens=False)["input_ids"]
    completion_ids = tokenizer(completion_str, add_special_tokens=False)["input_ids"]

    if len(prompt_ids) + len(completion_ids) > max_length:
        max_prompt_len = max(128, max_length - len(completion_ids))
        if len(prompt_ids) > max_prompt_len:
            prompt_ids = prompt_ids[:max_prompt_len]

    input_ids = prompt_ids + completion_ids
    labels = [-100] * len(prompt_ids) + completion_ids

    if len(input_ids) > max_length:
        input_ids = input_ids[:max_length]
        labels = labels[:max_length]

    return {"input_ids": input_ids, "attention_mask": [1] * len(input_ids), "labels": labels}

train_ds = raw_train.map(tokenize_prompt_completion, remove_columns=raw_train.column_names)
val_ds = raw_val.map(tokenize_prompt_completion, remove_columns=raw_val.column_names)

@dataclass
class CompletionOnlyCollator:
    tokenizer: Any

    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        input_ids = [f["input_ids"] for f in features]
        attention_masks = [f.get("attention_mask", [1] * len(ids)) for f, ids in zip(features, input_ids)]
        labels = [f.get("labels", ids) for f, ids in zip(features, input_ids)]

        max_len = max(len(x) for x in input_ids)
        pad_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else 0

        padded_input_ids = []
        padded_attention_masks = []
        padded_labels = []

        for ids, mask, lbl in zip(input_ids, attention_masks, labels):
            pad_len = max_len - len(ids)
            padded_input_ids.append(ids + [pad_id] * pad_len)
            padded_attention_masks.append(mask + [0] * pad_len)
            padded_labels.append(lbl + [-100] * pad_len)

        return {
            "input_ids": torch.tensor(padded_input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(padded_attention_masks, dtype=torch.long),
            "labels": torch.tensor(padded_labels, dtype=torch.long),
        }

data_collator = CompletionOnlyCollator(tokenizer=tokenizer)

# 4. SFTConfig with 10-step Save/Eval Sweeps
sft_config = SFTConfig(
    output_dir=SWEEP_DIR,
    max_steps=150,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=4,
    gradient_checkpointing=True,
    learning_rate=3e-5,
    warmup_ratio=0.10,
    weight_decay=0.05,
    logging_steps=10,
    eval_strategy="steps",
    eval_steps=10,
    save_strategy="steps",
    save_steps=10,
    save_total_limit=20,
    fp16=False,
    bf16=False,
    tf32=False,
    optim="paged_adamw_8bit",
    seed=42,
    max_length=MAX_SEQ_LEN,
    packing=False,
    dataset_kwargs={"skip_prepare_dataset": True},
    report_to="none"
)

sft_config._n_gpu = 1

trainer = SFTTrainer(
    model=model,
    args=sft_config,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    processing_class=tokenizer,
    data_collator=data_collator,
)

print("[+] Launching 150-Step Checkpoint Sweep...")
start_time = time.time()
train_res = trainer.train()
elapsed = round(time.time() - start_time, 2)
print(f"[+] Checkpoint Sweep Complete in {elapsed}s ({round(elapsed/60, 2)} mins)")

# Free Training Model
del trainer
del model
gc.collect()
if torch.cuda.is_available():
    torch.cuda.empty_cache()

# 5. Evaluate Every Saved Checkpoint (10, 20, 30 ... 150)
print("\n==========================================================")
print("=== EVALUATING SWEEP CHECKPOINTS FOR LEGAL ACCURACY     ===")
print("==========================================================")

base_model_reload = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map=device_map_target,
    torch_dtype=torch.float16,
    low_cpu_mem_usage=True,
    token=HF_TOKEN,
    trust_remote_code=True,
)

benchmark_questions = [
    "Which statute replaced the Indian Penal Code, 1860?",
    "Which statute replaced the Code of Criminal Procedure, 1973?",
    "Which statute replaced the Indian Evidence Act, 1872?",
    "Did the Bharatiya Nyaya Sanhita, 2023 repeal or replace the POCSO Act, 2012?",
    "Does BNS 2023 replace the Code of Criminal Procedure?"
]

checkpoint_dirs = sorted([d for d in Path(SWEEP_DIR).glob("checkpoint-*")], key=lambda x: int(x.name.split("-")[1]))

sweep_results = []

for ckpt in checkpoint_dirs:
    step_num = int(ckpt.name.split("-")[1])
    print(f"\n[+] Evaluating Checkpoint Step {step_num} ({ckpt.name})...")
    
    ckpt_model = PeftModel.from_pretrained(base_model_reload, str(ckpt), is_trainable=False)
    ckpt_model.eval()

    hallucinations = 0
    correct_statutes = 0

    for q in benchmark_questions:
        test_prompt = (
            f"<|start_header_id|>system<|end_header_id|>\n\n"
            f"You are Nyaya Darshana, an expert Indian Legal AI Assistant fine-tuned to reason, structure, cite, and respond strictly according to current Indian Statutory Law (BNS 2023, BNSS 2023, BSA 2023).<|eot_id|>"
            f"<|start_header_id|>user<|end_header_id|>\n\n"
            f"{q}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n\n"
        )
        inputs = tokenizer(test_prompt, return_tensors="pt").to(ckpt_model.device)
        with torch.no_grad():
            outputs = ckpt_model.generate(**inputs, max_new_tokens=100, do_sample=False, pad_token_id=tokenizer.eos_token_id)
        ans = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip().lower()

        # Check for hallucinated terms
        if any(h in ans for h in ["bncp", "bncrcp", "bordeau"]):
            hallucinations += 1
        if "bns" in ans or "bharatiya nyaya" in ans or "bnss" in ans or "bsa" in ans:
            correct_statutes += 1

    sweep_results.append({
        "step": step_num,
        "correct_statutes": correct_statutes,
        "hallucinations": hallucinations,
        "ckpt_path": str(ckpt)
    })
    print(f"  Step {step_num:<3} | Correct Statute Mentions: {correct_statutes}/5 | Hallucinations: {hallucinations}")

print("\n==========================================================")
print("=== CHECKPOINT SELECTION MATRIX                         ===")
print("==========================================================")
for r in sweep_results:
    print(f"Step {r['step']:<4} | Correct: {r['correct_statutes']}/5 | Hallucinations: {r['hallucinations']}")
print("==========================================================")
