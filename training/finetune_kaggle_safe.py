"""Safe, resumable Kaggle training for the Nyaya Darshana legal adapter.

Run on a Kaggle notebook with a GPU and train.jsonl / validation.jsonl attached.
The script saves the final adapter before evaluation and never loads a second
copy of the base model into the same GPU process.
"""

from __future__ import annotations

import gc
import json
import os
from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
import time
from typing import Any


os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


try:
    from model_quality import CORRECTIVE_RECORDS, LEGAL_PROBES, audit_splits, evaluate_answers, read_jsonl
except ImportError:
    try:
        from training.model_quality import CORRECTIVE_RECORDS, LEGAL_PROBES, audit_splits, evaluate_answers, read_jsonl
    except ImportError:
        from __main__ import CORRECTIVE_RECORDS, LEGAL_PROBES, audit_splits, evaluate_answers, read_jsonl


MODEL_NAME = os.getenv("NYAYA_BASE_MODEL", "unsloth/Meta-Llama-3.1-8B-Instruct")
WORKING_ROOT = Path(os.getenv("NYAYA_WORKING_ROOT", "/kaggle/working"))
if not WORKING_ROOT.is_dir():
    WORKING_ROOT = Path.cwd()
RUN_ID = os.getenv("NYAYA_RUN_ID", "r3").strip() or "r3"
OUTPUT_ROOT = WORKING_ROOT / f"nyaya_model_release_{RUN_ID}"
ADAPTER_DIR = OUTPUT_ROOT / "adapter"
CHECKPOINT_DIR = WORKING_ROOT / f"nyaya_training_checkpoints_{RUN_ID}"
REPORT_DIR = OUTPUT_ROOT / "reports"
ARCHIVE_PATH = WORKING_ROOT / f"nyaya_model_release_{RUN_ID}.zip"
HF_TOKEN = os.getenv("HF_TOKEN")
MINIMUM_ACCURACY = float(os.getenv("NYAYA_MINIMUM_ACCURACY", "0.90"))
MAX_LENGTH = int(os.getenv("NYAYA_MAX_LENGTH", "768"))
MAX_STEPS = int(os.getenv("NYAYA_MAX_STEPS", "-1"))
CORRECTION_REPEATS = max(1, int(os.getenv("NYAYA_CORRECTION_REPEATS", "8")))
REFINE_EXISTING = os.getenv("NYAYA_REFINE_EXISTING", "0") == "1"
INITIAL_ADAPTER = Path(
    os.getenv(
        "NYAYA_INIT_ADAPTER",
        str(WORKING_ROOT / "nyaya_model_release" / "adapter"),
    )
)
SYSTEM_PROMPT = (
    "You are Nyaya Darshana, a precise Indian legal assistant. "
    "Use only genuine statutory names and provisions. "
    "IPC was replaced by Bharatiya Nyaya Sanhita (BNS); "
    "CrPC was replaced by Bharatiya Nagarik Suraksha Sanhita (BNSS); "
    "the Indian Evidence Act was replaced by Bharatiya Sakshya Adhiniyam (BSA). "
    "POCSO remains an independent special statute. "
    "Never invent a statute, section number, date, or judicial decision. "
    "If authority is uncertain, acknowledge that uncertainty."
)


def announce(message: str) -> None:
    print(f"[NYAYA] {message}", flush=True)


def resolve_dataset(filename: str, environment_name: str, *, required: bool) -> Path | None:
    override = os.getenv(environment_name)
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override))
    candidates.extend(
        [
            Path.cwd() / filename,
            Path.cwd() / "training" / filename,
            WORKING_ROOT / filename,
            Path("/content") / filename,
        ]
    )
    kaggle_input = Path("/kaggle/input")
    if kaggle_input.is_dir():
        candidates.extend(sorted(kaggle_input.rglob(filename)))

    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            announce(f"Using {filename}: {candidate}")
            return candidate
    if required:
        raise FileNotFoundError(
            f"Could not locate a non-empty {filename}. Attach the original Kaggle dataset "
            f"or set {environment_name} to its absolute path."
        )
    return None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def directory_size_mb(path: Path) -> float:
    return round(
        sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) / 1024**2,
        2,
    )


def save_release_archive() -> Path:
    archive = Path(shutil.make_archive(str(ARCHIVE_PATH.with_suffix("")), "zip", OUTPUT_ROOT))
    announce(f"Durable release archive: {archive} ({archive.stat().st_size / 1024**2:.2f} MB)")
    return archive


def build_chat_prompt(tokenizer: Any, question: str, answer: str | None = None) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    if answer is not None:
        messages.append({"role": "assistant", "content": answer})
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def prepare_text_record(tokenizer: Any, record: dict[str, Any]) -> dict[str, str]:
    question = "\n".join(
        value for value in (str(record.get("instruction", "")).strip(), str(record.get("input", "")).strip()) if value
    )
    return {"text": build_chat_prompt(tokenizer, question, str(record["output"]).strip())}


def tokenize_completion_only(tokenizer: Any, record: dict[str, Any]) -> dict[str, list[int]]:
    question = "\n".join(
        value
        for value in (
            str(record.get("instruction", "")).strip(),
            str(record.get("input", "")).strip(),
        )
        if value
    )
    prompt = build_chat_prompt(tokenizer, question)
    completion = str(record["output"]).strip() + tokenizer.eos_token
    prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    completion_ids = tokenizer(completion, add_special_tokens=False)["input_ids"]

    if len(completion_ids) >= MAX_LENGTH:
        completion_ids = completion_ids[: MAX_LENGTH - 1]
    allowed_prompt = max(1, MAX_LENGTH - len(completion_ids))
    prompt_ids = prompt_ids[-allowed_prompt:]
    input_ids = prompt_ids + completion_ids

    return {
        "input_ids": input_ids,
        "attention_mask": [1] * len(input_ids),
        "labels": [-100] * len(prompt_ids) + completion_ids,
    }


@dataclass
class CompletionOnlyCollator:
    tokenizer: Any

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, Any]:
        import torch

        maximum_length = max(len(item["input_ids"]) for item in features)
        pad_token = self.tokenizer.pad_token_id
        inputs: list[list[int]] = []
        masks: list[list[int]] = []
        labels: list[list[int]] = []
        for item in features:
            pad_count = maximum_length - len(item["input_ids"])
            inputs.append(item["input_ids"] + [pad_token] * pad_count)
            # Some Transformers/TRL versions prune attention_mask before the
            # custom collator sees pre-tokenized examples. Reconstructing the
            # mask here is safe because every original token is real and only
            # this collator adds right-padding.
            attention_mask = item.get("attention_mask", [1] * len(item["input_ids"]))
            if len(attention_mask) != len(item["input_ids"]):
                raise ValueError("attention_mask length does not match input_ids length")
            masks.append(attention_mask + [0] * pad_count)
            labels.append(item["labels"] + [-100] * pad_count)
        return {
            "input_ids": torch.tensor(inputs, dtype=torch.long),
            "attention_mask": torch.tensor(masks, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


def adapter_weight_path() -> Path:
    candidates = list(ADAPTER_DIR.glob("adapter_model.safetensors")) + list(ADAPTER_DIR.glob("adapter_model.bin"))
    if not candidates:
        raise RuntimeError(f"Training finished but no adapter weights were saved in {ADAPTER_DIR}")
    candidate = candidates[0]
    if candidate.stat().st_size < 1024 * 1024:
        raise RuntimeError(f"Adapter weights are unexpectedly small: {candidate.stat().st_size} bytes")
    return candidate


def find_latest_checkpoint() -> str | None:
    if not CHECKPOINT_DIR.is_dir():
        return None
    checkpoints = [item for item in CHECKPOINT_DIR.glob("checkpoint-*") if item.is_dir()]
    if not checkpoints:
        return None
    checkpoints.sort(key=lambda item: int(item.name.rsplit("-", 1)[-1]))
    return str(checkpoints[-1])


def generate_answer(model: Any, tokenizer: Any, question: str) -> str:
    import torch

    prompt = build_chat_prompt(tokenizer, question)
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {key: value.to(model.device) for key, value in inputs.items()}
    with torch.inference_mode():
        result = model.generate(
            **inputs,
            max_new_tokens=180,
            do_sample=False,
            use_cache=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    generated = result[0][inputs["input_ids"].shape[1] :]
    answer = tokenizer.decode(generated, skip_special_tokens=True).strip()
    del inputs, generated, result
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return answer


def main() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    train_path = resolve_dataset("train.jsonl", "NYAYA_TRAIN_FILE", required=True)
    validation_path = resolve_dataset("validation.jsonl", "NYAYA_VALIDATION_FILE", required=True)
    test_path = resolve_dataset("test.jsonl", "NYAYA_TEST_FILE", required=False)
    assert train_path is not None and validation_path is not None

    train_records = read_jsonl(train_path)
    validation_records = read_jsonl(validation_path)
    test_records = read_jsonl(test_path) if test_path else None
    dataset_report = audit_splits(train_records, validation_records, test_records)
    write_json(REPORT_DIR / "dataset_audit.json", dataset_report)
    if not dataset_report["passed"]:
        raise RuntimeError("Dataset audit failed: " + "; ".join(dataset_report["errors"]))
    known_ids = {str(record.get("id", "")) for record in train_records}
    unique_anchors = [record for record in CORRECTIVE_RECORDS if record["id"] not in known_ids]
    added_anchors = []
    for repeat_index in range(CORRECTION_REPEATS):
        for anchor in unique_anchors:
            added_anchors.append({**anchor, "id": f"{anchor['id']}_r{repeat_index + 1}"})
    train_records.extend(added_anchors)
    announce(
        f"Dataset audit passed: train={len(train_records)}, validation={len(validation_records)}, "
        f"test={len(test_records or [])}; verified anchors added={len(added_anchors)}; run={RUN_ID}"
    )

    import torch
    from datasets import Dataset
    from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, EarlyStoppingCallback
    from trl import SFTConfig, SFTTrainer

    if not torch.cuda.is_available():
        raise RuntimeError("A CUDA GPU is required. Enable a Kaggle GPU accelerator before running.")

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    announce(f"GPU: {torch.cuda.get_device_name(0)}; visible GPUs: {torch.cuda.device_count()}")
    announce(f"Base model: {MODEL_NAME}")

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.float16,
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=quantization,
        device_map={"": 0},
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
        token=HF_TOKEN,
        trust_remote_code=True,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    if REFINE_EXISTING:
        if not (INITIAL_ADAPTER / "adapter_config.json").is_file():
            raise FileNotFoundError(
                f"Refinement requested, but no adapter_config.json exists in {INITIAL_ADAPTER}. "
                "Download or restore the prior adapter, or set NYAYA_INIT_ADAPTER."
            )
        announce(f"Refining preserved adapter: {INITIAL_ADAPTER}")
        model = PeftModel.from_pretrained(model, INITIAL_ADAPTER, is_trainable=True)
    else:
        model = get_peft_model(
            model,
            LoraConfig(
                r=8,
                lora_alpha=16,
                lora_dropout=0.10,
                bias="none",
                task_type="CAUSAL_LM",
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            ),
        )

    train_dataset = Dataset.from_list(train_records).map(
        lambda record: tokenize_completion_only(tokenizer, record),
        remove_columns=list(train_records[0].keys()),
    )
    validation_dataset = Dataset.from_list(validation_records).map(
        lambda record: tokenize_completion_only(tokenizer, record),
        remove_columns=list(validation_records[0].keys()),
    )
    data_collator = CompletionOnlyCollator(tokenizer=tokenizer)
    example_labels = train_dataset[0]["labels"]
    active_tokens = sum(value != -100 for value in example_labels)
    if not active_tokens:
        raise RuntimeError("Completion-only masking removed all supervised answer tokens")
    announce(f"Completion-only supervision active: {active_tokens} answer tokens in the first example")

    options: dict[str, Any] = {
        "output_dir": str(CHECKPOINT_DIR),
        "num_train_epochs": 2,
        "per_device_train_batch_size": 1,
        "per_device_eval_batch_size": 1,
        "gradient_accumulation_steps": 4,
        "gradient_checkpointing": True,
        "learning_rate": 2e-5,
        "warmup_ratio": 0.08,
        "weight_decay": 0.08,
        "logging_steps": 10,
        "eval_strategy": "steps",
        "eval_steps": 50,
        "save_strategy": "steps",
        "save_steps": 50,
        "save_total_limit": 2,
        "load_best_model_at_end": True,
        "metric_for_best_model": "eval_loss",
        "greater_is_better": False,
        "optim": "paged_adamw_8bit",
        "max_length": MAX_LENGTH,
        "packing": False,
        "dataset_kwargs": {"skip_prepare_dataset": True},
        "remove_unused_columns": False,
        "report_to": "none",
        "seed": 42,
        "fp16": False,
        "bf16": False,
    }
    if MAX_STEPS > 0:
        options["max_steps"] = MAX_STEPS

    training_config = SFTConfig(**options)
    training_config._n_gpu = 1
    trainer = SFTTrainer(
        model=model,
        args=training_config,
        train_dataset=train_dataset,
        eval_dataset=validation_dataset,
        processing_class=tokenizer,
        data_collator=data_collator,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    resume_from = find_latest_checkpoint()
    if resume_from:
        announce(f"Resuming from existing checkpoint: {resume_from}")

    started = time.time()
    training_result = trainer.train(resume_from_checkpoint=resume_from)
    metrics = trainer.evaluate()
    elapsed = round(time.time() - started, 2)

    announce("Saving final adapter and tokenizer before any inference evaluation")
    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(ADAPTER_DIR, safe_serialization=True)
    tokenizer.save_pretrained(ADAPTER_DIR)
    weight_path = adapter_weight_path()

    training_report = {
        "base_model": MODEL_NAME,
        "run_id": RUN_ID,
        "refined_from": str(INITIAL_ADAPTER) if REFINE_EXISTING else None,
        "adapter_path": str(ADAPTER_DIR),
        "adapter_weight_file": weight_path.name,
        "adapter_size_mb": directory_size_mb(ADAPTER_DIR),
        "elapsed_seconds": elapsed,
        "global_step": training_result.global_step,
        "training_loss": float(training_result.training_loss),
        "validation_loss": float(metrics.get("eval_loss", 0.0)),
        "best_checkpoint": trainer.state.best_model_checkpoint,
        "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1024**3, 2),
        "release_ready": False,
        "evaluation_status": "pending",
    }
    write_json(REPORT_DIR / "training_report.json", training_report)
    save_release_archive()

    announce("Evaluating legal correctness using the existing model; no second base model is loaded")
    trainer.model.eval()
    trainer.model.config.use_cache = True
    answers: dict[str, str] = {}
    for probe in LEGAL_PROBES:
        answer = generate_answer(trainer.model, tokenizer, probe.question)
        answers[probe.name] = answer
        announce(f"Probe {probe.name}: {answer[:180]}")

    quality_report = evaluate_answers(answers, minimum_accuracy=MINIMUM_ACCURACY)
    write_json(REPORT_DIR / "legal_evaluation.json", quality_report)
    training_report["release_ready"] = quality_report["release_ready"]
    training_report["evaluation_status"] = "passed" if quality_report["release_ready"] else "failed"
    training_report["legal_accuracy"] = quality_report["accuracy"]
    write_json(REPORT_DIR / "training_report.json", training_report)
    save_release_archive()

    announce(
        f"Training complete. Accuracy={quality_report['accuracy']:.0%}; "
        f"release_ready={quality_report['release_ready']}; adapter={weight_path}"
    )
    if not quality_report["release_ready"]:
        announce(
            "The adapter was preserved, but deployment is blocked: "
            + ", ".join(quality_report["critical_failures"] or ["minimum accuracy not met"])
        )

    del trainer, model, train_dataset, validation_dataset
    gc.collect()
    torch.cuda.empty_cache()
    return {"training": training_report, "quality": quality_report, "dataset": dataset_report}


if __name__ == "__main__":
    main()
