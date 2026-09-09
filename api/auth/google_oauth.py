"""Server-side Google OpenID Connect helpers for Nyaya Darshan sign-in."""

from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleOAuthError(RuntimeError):
    """Safe-to-display Google OAuth failure with secrets and tokens excluded."""


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
    try:
        with urlopen(token_request, timeout=15) as response:
            tokens = json.loads(response.read())
    except HTTPError as exc:
        raise GoogleOAuthError(_google_error_detail(exc, "Google token exchange failed")) from exc
    except (URLError, TimeoutError, ValueError, KeyError) as exc:
        raise GoogleOAuthError("Google token exchange failed.") from exc
    if not tokens.get("access_token"):
        raise GoogleOAuthError("Google token exchange did not return an access token.")
    user_request = Request(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": "Bearer " + tokens["access_token"]}, method="GET",
    )
    try:
        with urlopen(user_request, timeout=15) as response:
            profile = json.loads(response.read())
    except HTTPError as exc:
        raise GoogleOAuthError(_google_error_detail(exc, "Google profile lookup failed")) from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise GoogleOAuthError("Google profile lookup failed.") from exc
    if not profile.get("email_verified") or not profile.get("email"):
        raise GoogleOAuthError("Google account does not have a verified email address.")
    return profile


def _google_error_detail(exc: HTTPError, fallback: str) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8", errors="replace"))
    except (ValueError, OSError):
        return f"{fallback}."
    code = str(payload.get("error") or "").strip()
    description = str(payload.get("error_description") or "").strip()
    if code and description:
        return f"{fallback}: {code} - {description}"
    if code:
        return f"{fallback}: {code}"
    return f"{fallback}."
