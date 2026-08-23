"""Server-side Google OpenID Connect helpers for Nyaya Darshan sign-in."""

from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def google_oauth_config() -> dict[str, str]:
    return {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
        "redirect_uri": os.getenv(
            "GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/google/callback"
        ).strip(),
    }


def google_oauth_enabled() -> bool:
    config = google_oauth_config()
    return bool(config["client_id"] and config["client_secret"] and config["redirect_uri"])


def google_authorization_url(state: str) -> str:
    config = google_oauth_config()
    return GOOGLE_AUTHORIZE_URL + "?" + urlencode({
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    })


def exchange_google_code(code: str) -> dict:
    config = google_oauth_config()
    body = urlencode({
        "code": code,
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "redirect_uri": config["redirect_uri"],
        "grant_type": "authorization_code",
    }).encode("utf-8")
    token_request = Request(
        GOOGLE_TOKEN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST",
    )
    with urlopen(token_request, timeout=15) as response:
        tokens = json.loads(response.read())
    user_request = Request(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": "Bearer " + tokens["access_token"]}, method="GET",
    )
    with urlopen(user_request, timeout=15) as response:
        profile = json.loads(response.read())
    if not profile.get("email_verified") or not profile.get("email"):
        raise ValueError("Google account does not have a verified email address.")
    return profile
