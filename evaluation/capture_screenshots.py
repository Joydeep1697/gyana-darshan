# capture_screenshots.py — Visual QA Screenshot Capture across Viewports

import os
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(r"d:\Nova Legal")
SCREENSHOTS_DIR = BASE_DIR / "evaluation" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

VIEWPORTS = [
    ("desktop_1920x1080", 1920, 1080),
    ("desktop_1440x900", 1440, 900),
    ("laptop_1366x768", 1366, 768),
    ("tablet_768x1024", 768, 1024),
    ("mobile_390x844", 390, 844)
]

def capture_all():
    print(f"Using Browser: {CHROME_PATH}")
    for name, w, h in VIEWPORTS:
        out_file = SCREENSHOTS_DIR / f"{name}.png"
        cmd = [
            CHROME_PATH,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            f"--window-size={w},{h}",
            f"--screenshot={str(out_file)}",
            "http://127.0.0.1:8000/"
        ]
        print(f"Capturing {name} ({w}x{h})...")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            if out_file.exists():
                print(f"  [+] Saved: {out_file.name} ({out_file.stat().st_size // 1024} KB)")
            else:
                print(f"  [-] Failed to capture {name}: {res.stderr}")
        except Exception as e:
            print(f"  [-] Exception for {name}: {e}")

if __name__ == "__main__":
    capture_all()
