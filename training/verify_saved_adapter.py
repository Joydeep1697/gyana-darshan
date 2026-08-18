# verify_saved_adapter.py — Quick Verification Script for Existing Saved Adapter Checkpoint
#
# Run this in Google Colab to test clean reload & inference on your ALREADY TRAINED 258 MB checkpoint
# without re-running the 100 training steps!

import os
import gc
import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

MODEL_NAME = "unsloth/Meta-Llama-3.1-8B-Instruct"
HF_TOKEN = os.getenv("HF_TOKEN", None)
OUTPUT_DIR = "./nyaya_legal_adapter_smoke"

device_map_target = {"": 0} if torch.cuda.is_available() else "auto"

print("==========================================================")
print("=== NYAYA LEGAL OS — CLEAN ADAPTER RELOAD & INFERENCE  ===")
print("==========================================================")

if torch.cuda.is_available():
    gc.collect()
    torch.cuda.empty_cache()

print("[+] Loading CLEAN base model onto GPU...")
reload_bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.float16,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

base_model_reload = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=reload_bnb_config,
    device_map=device_map_target,
    token=HF_TOKEN,
    trust_remote_code=True,
)

print(f"[+] Loading trained LoRA adapter from '{OUTPUT_DIR}'...")
reloaded_model = PeftModel.from_pretrained(
    base_model_reload,
    OUTPUT_DIR,
    is_trainable=False,
)

# Robust active_adapters retrieval for all PEFT versions
if hasattr(reloaded_model, "active_adapters"):
    val = reloaded_model.active_adapters
    active_adapters = val() if callable(val) else val
else:
    active_adapters = [getattr(reloaded_model, "active_adapter", "default")]

reload_passed = (reloaded_model is not None and len(active_adapters) > 0)
print(f"[+] Active adapters: {active_adapters}")

adapter_parameter_count = sum(param.numel() for name, param in reloaded_model.named_parameters() if "lora_" in name)
print(f"[+] Loaded LoRA parameters: {adapter_parameter_count:,}")

if adapter_parameter_count > 0:
    print("[+] Adapter weights detected successfully.")
else:
    print("[!] WARNING: No LoRA parameters detected.")

print("\n==========================================================")
print("=== ADAPTER INFERENCE TEST                              ===")
print("==========================================================")
reloaded_model.eval()
test_prompt = (
    "<|start_header_id|>system<|end_header_id|>\n\n"
    "You are Nyaya Darshana, an expert Indian Legal AI Assistant fine-tuned to reason, structure, cite, and respond strictly according to current Indian Statutory Law (BNS 2023, BNSS 2023, BSA 2023).<|eot_id|>"
    "<|start_header_id|>user<|end_header_id|>\n\n"
    "What is the purpose of the Bharatiya Nyaya Sanhita, 2023?<|eot_id|>"
    "<|start_header_id|>assistant<|end_header_id|>\n\n"
)

inputs = tokenizer(test_prompt, return_tensors="pt").to(reloaded_model.device)
with torch.no_grad():
    outputs = reloaded_model.generate(
        **inputs,
        max_new_tokens=200,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )
generated_text = tokenizer.decode(outputs[0], skip_special_tokens=False)

print(generated_text)
print("==========================================================\n")
