"""Build the self-contained Kaggle notebook from the reviewed Python sources."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
QUALITY_SOURCE = (HERE / "model_quality.py").read_text(encoding="utf-8")
TRAINING_SOURCE = (HERE / "finetune_kaggle_safe.py").read_text(encoding="utf-8")


def markdown(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


notebook = {
    "cells": [
        markdown(
            "# Nyaya Darshana — Safe Legal-Model Training\n\n"
            "1. Attach the original dataset containing `train.jsonl` and `validation.jsonl`.\n"
            "2. Enable a GPU accelerator and internet access in Kaggle settings.\n"
            "3. Run all cells.\n"
            "4. Download `nyaya_model_release.zip` from the Output tab.\n\n"
            "The adapter is exported before evaluation. A failed legal-quality gate never deletes it, "
            "but it must not be deployed until the evaluation report passes.\n"
        ),
        code(
            "# Install only when the required package is missing.\n"
            "import importlib.util, subprocess, sys\n"
            "packages = {'trl': 'trl', 'peft': 'peft', 'bitsandbytes': 'bitsandbytes', "
            "'accelerate': 'accelerate', 'datasets': 'datasets'}\n"
            "missing = [pip_name for module, pip_name in packages.items() "
            "if importlib.util.find_spec(module) is None]\n"
            "if missing:\n"
            "    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *missing])\n"
            "print('Dependencies ready:', ', '.join(packages))\n"
        ),
        code(QUALITY_SOURCE),
        code(TRAINING_SOURCE),
    ],
    "metadata": {
        "accelerator": "GPU",
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


destination = HERE / "nyaya_kaggle_recovery.ipynb"
destination.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(destination)
