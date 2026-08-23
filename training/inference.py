"""inference.py — Inference execution script for Nyaya Darshana QLoRA Adapter.

Loads the base LLM with the trained LoRA adapter and optional RAG context.
"""

import sys
import argparse
import json
import yaml
from pathlib import Path

BASE_DIR = Path(r"d:\Gyana Darshan")
CONFIG_PATH = BASE_DIR / "training" / "config.yaml"


def format_prompt(query: str, rag_context: str = "") -> str:
    user_content = query
    if rag_context:
        user_content = f"Legal Context:\n{rag_context}\n\nUser Question:\n{query}"

    formatted_text = (
        f"<|start_header_id|>system<|end_header_id|>\n\n"
        f"You are Nyaya Darshana, an expert Indian Legal AI Assistant fine-tuned to reason, structure, cite, and respond strictly according to current Indian Statutory Law (BNS 2023, BNSS 2023, BSA 2023).<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{user_content}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )
    return formatted_text


def generate_response(query: str, rag_context: str = "", mock: bool = True) -> str:
    prompt = format_prompt(query, rag_context)

    if mock:
        return (
            f"[Nyaya Darshana - Mock Inference Response]\n\n"
            f"Query: {query}\n"
            f"Statutory Authority: Bharatiya Nyaya Sanhita, 2023 (BNS) / BNSS 2023\n"
            f"Analysis: Under current Indian statutory framework enacted in 2023, applicable provisions are evaluated against retrieved legal context.\n"
            f"Note: Full neural weight generation available when loaded with GPU adapter checkpoint."
        )

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    base_model_name = config["model"]["base_model_name"]
    adapter_path = Path(config["training"]["output_dir"])

    print(f"[+] Loading Base Model: {base_model_name}...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )

    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )

    if adapter_path.exists():
        print(f"[+] Loading QLoRA Adapter from: {adapter_path}...")
        model = PeftModel.from_pretrained(base_model, str(adapter_path))
    else:
        print(f"[!] Adapter not found at {adapter_path}. Using base model.")
        model = base_model

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=512, temperature=0.2)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response


def main():
    parser = argparse.ArgumentParser(description="Nyaya Darshana Inference Tool")
    parser.add_argument("--query", type=str, help="Legal question to evaluate")
    parser.add_argument("--context", type=str, default="", help="Optional RAG context")
    parser.add_argument("--mock", action="store_true", help="Run in CPU mock demonstration mode")

    args = parser.parse_args()

    query = args.query or "What section of BNSS governs Zero FIR registration?"
    response = generate_response(query, rag_context=args.context, mock=args.mock or not torch_available())

    print("\n--- INFERENCE RESULT ---")
    print(response)


def torch_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


if __name__ == "__main__":
    main()
