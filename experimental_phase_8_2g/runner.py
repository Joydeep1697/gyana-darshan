# runner.py — Standalone Runner for Experimental Phase 8.2G Pipeline

import sys
import json
from pathlib import Path

BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from experimental_phase_8_2g.pipeline import ExperimentalLegalPipeline

def run_sample():
    pipeline = ExperimentalLegalPipeline()
    q = "A cashier secretly pocketed cash from store register and police seized CCTV hard drive"
    print(f"Executing Query: {q}\n")
    res = pipeline.process_query(q)
    print("Answer:")
    print(res["answer"])
    print("\nEvidence Pack:")
    print(res["evidence_pack"])

if __name__ == "__main__":
    run_sample()
