#!/usr/bin/env python3
"""Dependency-free release checks. Never print secret values."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDERS = ("replace", "changeme", "your-key", "example", "placeholder")


def is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or any(marker in lowered for marker in PLACEHOLDERS)


def check_environment() -> list[str]:
    failures: list[str] = []
    if os.getenv("ENVIRONMENT", "").strip().lower() not in {"production", "prod"}:
        failures.append("ENVIRONMENT must be production")

    for name in ("NYAYA_API_KEY", "NYAYA_JWT_SECRET"):
        value = os.getenv(name, "").strip()
        if is_placeholder(value) or len(value) < 32:
            failures.append(f"{name} must be a non-placeholder secret of at least 32 characters")

    if os.getenv("LLM_PROVIDER", "nvidia").strip().lower() != "nvidia":
        failures.append("LLM_PROVIDER must be nvidia")
    if is_placeholder(os.getenv("NVIDIA_API_KEY", "")):
        failures.append("NVIDIA_API_KEY must be configured")

    origins = [part.strip() for part in os.getenv("ALLOWED_ORIGINS", "").split(",") if part.strip()]
    if not origins:
        failures.append("ALLOWED_ORIGINS must contain explicit HTTPS origins")
    for origin in origins:
        parsed = urlparse(origin)
        if origin == "*" or parsed.scheme != "https" or not parsed.netloc or parsed.path:
            failures.append(f"ALLOWED_ORIGINS contains an invalid production origin: {origin!r}")

    razorpay_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    razorpay_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if bool(razorpay_id) != bool(razorpay_secret):
        failures.append("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be configured together")
    if razorpay_id and (is_placeholder(razorpay_id) or is_placeholder(razorpay_secret)):
        failures.append("Razorpay credentials cannot contain placeholder values")

    google_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    google_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    google_redirect = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    google_values = (google_id, google_secret, google_redirect)
    if any(google_values) and not all(google_values):
        failures.append("GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI must be configured together")
    if all(google_values):
        redirect = urlparse(google_redirect)
        if redirect.scheme != "https" or not redirect.netloc or redirect.path != "/api/auth/google/callback":
            failures.append("GOOGLE_REDIRECT_URI must be an HTTPS /api/auth/google/callback URL in production")
        if is_placeholder(google_id) or is_placeholder(google_secret):
            failures.append("Google OAuth credentials cannot contain placeholder values")

    return failures


def check_repository() -> list[str]:
    failures: list[str] = []
    for relative in ("app/main.py", "requirements.txt", "render.yaml", "Dockerfile", ".dockerignore", ".env.example"):
        if not (ROOT / relative).is_file():
            failures.append(f"Required deployment file missing: {relative}")

    for name in (".gitignore", ".dockerignore"):
        candidate = ROOT / name
        if candidate.exists():
            patterns = {line.strip() for line in candidate.read_text(encoding="utf-8").splitlines()}
            if ".env" not in patterns:
                failures.append(f"{name} must exclude .env")

    example = ROOT / ".env.example"
    if example.exists():
        example_text = example.read_text(encoding="utf-8")
        for match in re.finditer(r"(?m)^\s*(NVIDIA_API_KEY|RAZORPAY_KEY_SECRET|NYAYA_JWT_SECRET)\s*=\s*([^\s#]+)", example_text):
            name, value = match.groups()
            if not is_placeholder(value) and (value.startswith("nvapi-") or len(value) >= 24):
                failures.append(f".env.example appears to contain a real credential for {name}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--environment-only", action="store_true")
    group.add_argument("--repository-only", action="store_true")
    options = parser.parse_args()

    failures: list[str] = []
    if not options.repository_only:
        failures.extend(check_environment())
    if not options.environment_only:
        failures.extend(check_repository())

    if failures:
        print(f"Release preflight FAILED: {len(failures)} issue(s)", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1

    print("Release preflight PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
