"""Nyaya Darshan — Server Entry Point.

Usage:
    python run.py
"""

import os
import logging
import uvicorn
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

if __name__ == "__main__":
    from app.config import HOST, PORT

    # Hot-reload is only enabled in local development (RELOAD_ON_CHANGE=1).
    # It must never be enabled in production — it spawns a watchdog process
    # that causes double-startup side effects and wastes resources.
    reload_flag = os.environ.get("RELOAD_ON_CHANGE", "0") == "1"

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=reload_flag,
        log_level="info",
    )
