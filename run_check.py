import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / ".claude/skills/price-watcher/scripts"))
sys.path.insert(0, str(ROOT / ".claude/skills/kakao-notifier/scripts"))

from dotenv import load_dotenv

from _config import load_thresholds
from _history_db import init_db, get_tier_state
from _upbit_client import UpbitFetchError
from fetch_market_data import fetch_snapshot
from compute_signals import evaluate_signals
from filter_candidates import get_candidates, is_in_cooldown
from refresh_access_token import ensure_valid_access_token, check_refresh_token_expiry
from render_message import build_message, build_template_object
from send_kakao_message import send_with_retry, KakaoSendError
from record_history import record_fired, append_jsonl

THRESHOLDS_PATH = ROOT / "config/thresholds.yaml"
DB_PATH = ROOT / "output/history.db"
RUN_LOG_PATH = ROOT / "output/logs/run.jsonl"
ERROR_LOG_PATH = ROOT / "output/logs/errors.jsonl"
LAST_RUN_DIR = ROOT / "output/last_run"

AUTH_WARNING_TIER = "auth_expiry_warning"
AUTH_WARNING_COOLDOWN_MINUTES = 1440
AUTH_WARNING_WITHIN_DAYS = 14


def _maybe_warn_auth_expiry(now: datetime, client_id: str, token_store_path: Path) -> None:
    expiry = check_refresh_token_expiry(
        str(token_store_path), warn_within_days=AUTH_WARNING_WITHIN_DAYS, now_fn=lambda: now
    )
    if not expiry["warn"]:
        return

    state = get_tier_state(str(DB_PATH), AUTH_WARNING_TIER)
    last_fired_at = state["last_fired_at"] if state else None
    if is_in_cooldown(last_fired_at, AUTH_WARNING_COOLDOWN_MINUTES, now):
        return

    days_remaining = expiry["days_remaining"]
    text = (
        "⚠️ Bitcoinalert 인증 만료 임박\n\n"
        f"카카오 refresh_token이 약 {days_remaining:.1f}일 후 만료됩니다.\n"
        "kakao_auth_setup.py를 재실행하고 GitHub Secret(KAKAO_TOKEN_JSON)을 갱신해주세요."
    )
    template_object = build_template_object(text)

    try:
        access_token = ensure_valid_access_token(str(token_store_path), client_id=client_id)
        send_with_retry(access_token, template_object)
    except KakaoSendError as exc:
        append_jsonl(
            str(ERROR_LOG_PATH), {"ts": now.isoformat(), "stage": "auth_expiry_warning", "error": str(exc)}
        )
        print(f"ESCALATE: {exc}", file=sys.stderr)
        return

    record_fired(str(DB_PATH), tier=AUTH_WARNING_TIER, fired_at=now.isoformat(), price=0.0, value=days_remaining)


def _write_last_run_debug(snapshot: dict, signals: dict) -> None:
    LAST_RUN_DIR.mkdir(parents=True, exist_ok=True)
    (LAST_RUN_DIR / "snapshot.json").write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    (LAST_RUN_DIR / "signals.json").write_text(json.dumps(signals, indent=2, ensure_ascii=False), encoding="utf-8")


def run_once(dry_run: bool = False) -> int:
    load_dotenv(ROOT / ".env")
    thresholds = load_thresholds(str(THRESHOLDS_PATH))
    init_db(str(DB_PATH))

    now = datetime.now(timezone.utc)

    token_store_path = ROOT / os.environ.get("KAKAO_TOKEN_STORE_PATH", "secrets/kakao_token.json")
    client_id = os.environ["KAKAO_REST_API_KEY"]

    if not dry_run:
        _maybe_warn_auth_expiry(now, client_id=client_id, token_store_path=token_store_path)

    try:
        snapshot = fetch_snapshot(thresholds["market"], thresholds)
    except UpbitFetchError as exc:
        append_jsonl(str(ERROR_LOG_PATH), {"ts": now.isoformat(), "stage": "fetch", "error": str(exc)})
        print(f"ESCALATE: {exc}", file=sys.stderr)
        return 1

    signals = evaluate_signals(snapshot, thresholds)
    _write_last_run_debug(snapshot, signals)

    candidates = get_candidates(signals, thresholds, str(DB_PATH), now=now)

    if not candidates:
        append_jsonl(
            str(RUN_LOG_PATH),
            {
                "ts": now.isoformat(),
                "current_price": signals["current_price"],
                "triggered_tiers": [],
                "candidates_sent": [],
                "send_status": "not_sent",
            },
        )
        return 0

    tier_names = [c["tier"] for c in candidates]

    if dry_run:
        append_jsonl(
            str(RUN_LOG_PATH),
            {
                "ts": now.isoformat(),
                "current_price": signals["current_price"],
                "triggered_tiers": tier_names,
                "candidates_sent": [],
                "send_status": "dry_run",
            },
        )
        print(f"[dry-run] would send: {tier_names}")
        return 0

    message = build_message(signals, candidates)
    template_object = build_template_object(message)

    try:
        access_token = ensure_valid_access_token(str(token_store_path), client_id=client_id)
        send_with_retry(access_token, template_object)
    except KakaoSendError as exc:
        append_jsonl(str(ERROR_LOG_PATH), {"ts": now.isoformat(), "stage": "send", "error": str(exc)})
        append_jsonl(
            str(RUN_LOG_PATH),
            {
                "ts": now.isoformat(),
                "current_price": signals["current_price"],
                "triggered_tiers": tier_names,
                "candidates_sent": [],
                "send_status": "failed",
            },
        )
        print(f"ESCALATE: {exc}", file=sys.stderr)
        return 1

    for candidate in candidates:
        condition = candidate["condition"]
        value = condition.get("pct_change", condition.get("volume_ratio"))
        record_fired(str(DB_PATH), tier=candidate["tier"], fired_at=now.isoformat(), price=signals["current_price"], value=value)

    append_jsonl(
        str(RUN_LOG_PATH),
        {
            "ts": now.isoformat(),
            "current_price": signals["current_price"],
            "triggered_tiers": tier_names,
            "candidates_sent": tier_names,
            "send_status": "sent",
        },
    )
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="fetch/compute/log only, skip Kakao send and cooldown recording")
    parser.add_argument("--loop", action="store_true", help="local dev convenience: run repeatedly instead of once (not used in production; Task Scheduler runs this once per invocation)")
    parser.add_argument("--interval", type=int, default=300, help="seconds between iterations when --loop is set")
    args = parser.parse_args()

    if args.loop:
        while True:
            run_once(dry_run=args.dry_run)
            time.sleep(args.interval)
    else:
        sys.exit(run_once(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
