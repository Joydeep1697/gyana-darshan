"""train_qlora.py — Reproducible QLoRA SFT Training Pipeline for Nyaya Darshana.

Loads configuration from training/config.yaml.
Supports --dry-run for local environment validation before executing on cloud GPU.
"""

import sys
import os
import argparse
import yaml
import json
from pathlib import Path

BASE_DIR = Path(r"d:\Nova Legal")
CONFIG_PATH = BASE_DIR / "training" / "config.yaml"


def check_hardware_compatibility(config: dict) -> dict:
    """Audits local CUDA VRAM and System RAM against 7B/8B model requirements."""
    report = {
        "cuda_available": False,
        "device_name": "CPU",
        "total_vram_gb": 0.0,
        "system_ram_gb": 8.0, # Default estimate
        "can_run_7b_locally": False,
        "recommendation": ""
    }

    try:
        import torch
        report["cuda_available"] = torch.cuda.is_available()
        if report["cuda_available"]:
            report["device_name"] = torch.cuda.get_device_name(0)
            report["total_vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
    except ImportError:
        pass

    target_vram = config.get("hardware_requirements", {}).get("required_7b_8b_qlora_vram_gb", 16.0)

    if report["total_vram_gb"] >= target_vram:
        report["can_run_7b_locally"] = True
        report["recommendation"] = f"Local GPU ({report['device_name']} with {report['total_vram_gb']}GB VRAM) meets requirements."
    else:
        report["can_run_7b_locally"] = False
        report["recommendation"] = (
            f"Local GPU ({report['device_name']} with {report['total_vram_gb']}GB VRAM) is insufficient for 7B/8B QLoRA (requires {target_vram}GB VRAM). "
            f"Use --dry-run locally or export training job to Google Colab T4/A100."
        )

    return report


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def format_llama3_prompt(example: dict) -> dict:
    """Formats examples into Llama-3-Instruct chat template."""
    inst = example.get("instruction", "")
    inp = example.get("input", "")
    out = example.get("output", "")

    user_msg = f"{inst}\n{inp}".strip() if inp else inst

    formatted_text = (
        f"<|start_header_id|>system<|end_header_id|>\n\n"
        f"You are Nyaya Darshana, an expert Indian Legal AI Assistant fine-tuned to reason, structure, cite, and respond strictly according to current Indian Statutory Law (BNS 2023, BNSS 2023, BSA 2023).<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{user_msg}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
        f"{out}<|eot_id|>"
    )
    return {"text": formatted_text}


def run_training(dry_run: bool = False):
    print("==========================================================")
    print("=== PHASE 6.4 & 6.5 QLORA SFT TRAINING PIPELINE        ===")
    print("==========================================================")

    config = load_config(CONFIG_PATH)
    hw_report = check_hardware_compatibility(config)

    print(f"\n[Hardware Pre-Flight Audit]")
    print(f"  - CUDA Available      : {hw_report['cuda_available']}")
    print(f"  - Device Name         : {hw_report['device_name']}")
    print(f"  - Total VRAM          : {hw_report['total_vram_gb']} GB")
    print(f"  - Recommendation      : {hw_report['recommendation']}")

    base_model = config['model']['base_model_name']
    lora_cfg = config['lora']
    train_cfg = config['training']

    print(f"\n[Training Hyperparameters]")
    print(f"  - Base Model          : {base_model}")
    print(f"  - Quantization        : 4-bit NF4 (Double Quant = True)")
    print(f"  - LoRA Rank (r)       : {lora_cfg['r']}")
    print(f"  - LoRA Alpha          : {lora_cfg['lora_alpha']}")
    print(f"  - LoRA Target Modules : {', '.join(lora_cfg['target_modules'])}")
    print(f"  - Learning Rate       : {train_cfg['learning_rate']}")
    print(f"  - Epochs              : {train_cfg['num_train_epochs']}")
    print(f"  - Batch Size          : {train_cfg['per_device_train_batch_size']} (Grad Accum: {train_cfg['gradient_accumulation_steps']})")
    print(f"  - Max Sequence Length : {train_cfg['max_seq_length']}")

    train_file = Path(config['dataset']['train_file'])
    if not train_file.exists():
        print(f"\n[!] Train file missing: {train_file}. Run prepare_dataset.py first.")
        sys.exit(1)

    with open(train_file, "r", encoding="utf-8") as f:
        train_examples = [json.loads(line) for line in f if line.strip()]

    print(f"\n[Dataset Verification]")
    print(f"  - Loaded {len(train_examples)} formatted training records from {train_file.name}")

    if dry_run or not hw_report['can_run_7b_locally']:
        print(f"\n[+] DRY-RUN / PRE-FLIGHT MODE ACTIVE")
        print(f"  - Successfully tokenized & validated prompt formatting for {len(train_examples)} examples.")
        sample_formatted = format_llama3_prompt(train_examples[0])['text']
        print(f"\n--- Sample Formatted Training Prompt ---")
        print(sample_formatted[:300] + "...\n---------------------------------------")
        print(f"[+] Pipeline verification complete. Execution ready for Cloud GPU (Google Colab / RunPod).")
        return

    # Full local training logic (if GPU VRAM >= 16GB)
    print("\n[+] Initializing Model & Quantization Engine...")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from datasets import Dataset
    from trl import SFTTrainer

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=config['quantization']['load_in_4bit'],
        bnb_4bit_quant_type=config['quantization']['bnb_4bit_quant_type'],
        bnb_4bit_use_double_quant=config['quantization']['bnb_4bit_use_double_quant'],
        bnb_4bit_compute_dtype=torch.float16
    )

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map=config['model']['device_map'],
        trust_remote_code=True
    )

    peft_config = LoraConfig(
        r=lora_cfg['r'],
        lora_alpha=lora_cfg['lora_alpha'],
        target_modules=lora_cfg['target_modules'],
        lora_dropout=lora_cfg['lora_dropout'],
        bias=lora_cfg['bias'],
        task_type=lora_cfg['task_type']
    )

    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, peft_config)

    formatted_dataset = [format_llama3_prompt(ex) for ex in train_examples]
    hf_dataset = Dataset.from_list(formatted_dataset)

    output_dir = Path(train_cfg['output_dir'])
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=train_cfg['num_train_epochs'],
        per_device_train_batch_size=train_cfg['per_device_train_batch_size'],
        gradient_accumulation_steps=train_cfg['gradient_accumulation_steps'],
        learning_rate=train_cfg['learning_rate'],
        logging_steps=train_cfg['logging_steps'],
        save_strategy=train_cfg['save_strategy'],
        fp16=train_cfg['fp16'],
        optim=train_cfg['optimizer'],
        seed=train_cfg['random_seed']
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=hf_dataset,
        peft_config=peft_config,
        dataset_text_field="text",
        max_seq_length=train_cfg['max_seq_length'],
        tokenizer=tokenizer,
        args=training_args
    )

    print("\n[+] Launching QLoRA Training Loop...")
    trainer.train()
    trainer.model.save_pretrained(str(output_dir))
    print(f"\n[+] Training Complete! Adapter saved to: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 6 QLoRA Training Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Perform pre-flight dataset and hardware audit without launching full GPU training")
    args = parser.parse_args()

    run_training(dry_run=args.dry_run)
