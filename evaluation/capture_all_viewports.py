# capture_all_viewports.py — Clean Edge Headless Screenshot Generator

import os
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(r"d:\Gyana Darshan")
SCREENSHOTS_DIR = BASE_DIR / "evaluation" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

VIEWPORTS = [
    ("desktop_1920x1080", 1920, 1080),
    ("desktop_1440x900", 1440, 900),
    ("laptop_1366x768", 1366, 768),
    ("tablet_768x1024", 768, 1024),
    ("mobile_390x844", 390, 844)
]

def capture():
    print(f"Capturing with Edge: {EDGE_PATH}")
    for name, w, h in VIEWPORTS:
        out_file = SCREENSHOTS_DIR / f"{name}.png"
        cmd = [
            EDGE_PATH,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            f"--window-size={w},{h}",
            f"--screenshot={str(out_file)}",
            "http://127.0.0.1:8000/"
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if out_file.exists():
                print(f"  [+] Captured {name}: {out_file.name} ({out_file.stat().st_size} bytes)")
        except Exception as e:
            print(f"  [-] Error on {name}: {e}")

if __name__ == "__main__":
    capture()
