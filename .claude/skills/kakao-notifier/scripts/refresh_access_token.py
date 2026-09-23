import json
from datetime import datetime, timedelta, timezone

import requests

TOKEN_URL = "https://kauth.kakao.com/oauth/token"


def _load_token(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_token(path: str, token: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(token, f, ensure_ascii=False, indent=2)


def _is_near_expiry(token: dict, safety_margin_minutes: float, now: datetime) -> bool:
    obtained_at = datetime.fromisoformat(token["obtained_at"])
    expires_at = obtained_at + timedelta(seconds=token["expires_in"])
    return now >= expires_at - timedelta(minutes=safety_margin_minutes)


def ensure_valid_access_token(
    token_store_path: str,
    client_id: str,
    safety_margin_minutes: float = 30,
    now_fn=lambda: datetime.now(timezone.utc),
    post_fn=requests.post,
) -> str:
    token = _load_token(token_store_path)
    now = now_fn()

    if not _is_near_expiry(token, safety_margin_minutes, now):
        return token["access_token"]

    response = post_fn(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": token["refresh_token"],
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()

    token["access_token"] = payload["access_token"]
    token["expires_in"] = payload["expires_in"]
    token["obtained_at"] = now.isoformat()
    if "refresh_token" in payload:
        token["refresh_token"] = payload["refresh_token"]
        token["refresh_token_obtained_at"] = now.isoformat()
    if "refresh_token_expires_in" in payload:
        token["refresh_token_expires_in"] = payload["refresh_token_expires_in"]

    _save_token(token_store_path, token)
    return token["access_token"]


def check_refresh_token_expiry(
    token_store_path: str,
    warn_within_days: float = 14,
    now_fn=lambda: datetime.now(timezone.utc),
) -> dict:
    token = _load_token(token_store_path)
    now = now_fn()

    reference = datetime.fromisoformat(token.get("refresh_token_obtained_at", token["obtained_at"]))
    expires_at = reference + timedelta(seconds=token["refresh_token_expires_in"])
    days_remaining = (expires_at - now).total_seconds() / 86400

    return {"days_remaining": days_remaining, "warn": days_remaining <= warn_within_days}
