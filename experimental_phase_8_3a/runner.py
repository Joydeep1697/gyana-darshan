# runner.py — Phase 8.3A Experimental Query Runner CLI
#
# Usage:
# python -m experimental_phase_8_3a.runner "Query text" --config [A|B|C|D]

import sys
import argparse
from pathlib import Path

BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from experimental_phase_8_3a.pipeline import Phase83ALegalPipeline
from retrieval.experimental_phase_8_3a.phase_8_3a_config import (
    get_config_a, get_config_b, get_config_c, get_config_d
)

def main():
    parser = argparse.ArgumentParser(description="Phase 8.3A Experimental Pipeline Runner")
    parser.add_argument("query", type=str, help="Legal query string to process")
    parser.add_argument("--config", choices=["A", "B", "C", "D"], default="C", help="Configuration preset (default: C)")
    args = parser.parse_args()

    cfg_map = {
        "A": get_config_a(),
        "B": get_config_b(),
        "C": get_config_c(),
        "D": get_config_d()
    }

    selected_cfg = cfg_map[args.config]
    pipeline = Phase83ALegalPipeline(config=selected_cfg)

    print(f"=== Running Phase 8.3A Pipeline ({selected_cfg.name}) ===")
    print(f"Query: {args.query}\n")

    res = pipeline.process_query(args.query)

    print("--- Retrieved Sections ---")
    for sec in res["retrieved_sections"]:
        prot = " [PROTECTED]" if sec.get("is_protected") else ""
        print(f"[{sec['rank']}]{prot} {sec['statute']} Section {sec['section']} — {sec.get('heading', '')} (Score: {sec.get('score', 0)})")

    print("\n--- Evidence Sufficiency ---")
    print(f"Status: {res['evidence_sufficiency']['overall_status']} (Ratio: {res['evidence_sufficiency']['sufficiency_ratio']*100:.0f}%)")

    print("\n--- Synthesized Answer ---")
    print(res["answer"])

if __name__ == "__main__":
    main()
