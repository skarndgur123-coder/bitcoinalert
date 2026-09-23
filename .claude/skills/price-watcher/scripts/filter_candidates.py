from datetime import datetime

from _history_db import get_tier_state

PRICE_KEYS = ("5m", "1h", "24h")


def is_in_cooldown(last_fired_at: str | None, cooldown_minutes: float, now: datetime) -> bool:
    if last_fired_at is None:
        return False
    last_fired = datetime.fromisoformat(last_fired_at)
    elapsed_minutes = (now - last_fired).total_seconds() / 60
    return elapsed_minutes < cooldown_minutes


def _cooldown_minutes_for(key: str, thresholds: dict) -> float:
    if key in PRICE_KEYS:
        return thresholds["price_change"][key]["cooldown_minutes"]
    return thresholds["volume_spike"]["cooldown_minutes"]


def get_candidates(signals: dict, thresholds: dict, db_path: str, now: datetime) -> list[dict]:
    candidates = []
    for key, condition in signals["conditions"].items():
        if not condition["triggered"]:
            continue
        tier = condition["tier"]
        state = get_tier_state(db_path, tier)
        last_fired_at = state["last_fired_at"] if state else None
        cooldown_minutes = _cooldown_minutes_for(key, thresholds)
        if is_in_cooldown(last_fired_at, cooldown_minutes, now):
            continue
        candidates.append({"key": key, "tier": tier, "condition": condition})
    return candidates
