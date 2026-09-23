from datetime import datetime, timedelta, timezone

from filter_candidates import is_in_cooldown, get_candidates
from _history_db import init_db, upsert_tier_state


NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)

THRESHOLDS = {
    "price_change": {
        "5m": {"cooldown_minutes": 15},
        "1h": {"cooldown_minutes": 60},
        "24h": {"cooldown_minutes": 240},
    },
    "volume_spike": {"cooldown_minutes": 15},
}


def make_signals(**tier_overrides):
    conditions = {
        "5m": {"triggered": False, "tier": None},
        "1h": {"triggered": False, "tier": None},
        "24h": {"triggered": False, "tier": None},
        "volume_spike": {"triggered": False, "tier": None},
    }
    for key, triggered in tier_overrides.items():
        conditions[key]["triggered"] = triggered
        conditions[key]["tier"] = f"{key}_up" if key != "volume_spike" else "volume_spike"
    return {"conditions": conditions}


def test_is_in_cooldown_true_when_recently_fired():
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    last_fired_at = (now - timedelta(minutes=5)).isoformat()
    assert is_in_cooldown(last_fired_at, cooldown_minutes=15, now=now) is True


def test_is_in_cooldown_false_when_past_cooldown_window():
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    last_fired_at = (now - timedelta(minutes=20)).isoformat()
    assert is_in_cooldown(last_fired_at, cooldown_minutes=15, now=now) is False


def test_is_in_cooldown_false_when_never_fired():
    assert is_in_cooldown(None, cooldown_minutes=15, now=NOW) is False


def test_get_candidates_returns_triggered_tier_never_fired_before(tmp_path):
    db_path = str(tmp_path / "history.db")
    init_db(db_path)
    signals = make_signals(**{"5m": True})
    candidates = get_candidates(signals, THRESHOLDS, db_path, now=NOW)
    assert [c["key"] for c in candidates] == ["5m"]


def test_get_candidates_suppresses_tier_in_cooldown(tmp_path):
    db_path = str(tmp_path / "history.db")
    init_db(db_path)
    upsert_tier_state(db_path, tier="5m_up", fired_at=(NOW - timedelta(minutes=5)).isoformat(), price=100.0, value=1.0)
    signals = make_signals(**{"5m": True})
    candidates = get_candidates(signals, THRESHOLDS, db_path, now=NOW)
    assert candidates == []


def test_get_candidates_refires_after_cooldown_elapsed(tmp_path):
    db_path = str(tmp_path / "history.db")
    init_db(db_path)
    upsert_tier_state(db_path, tier="5m_up", fired_at=(NOW - timedelta(minutes=20)).isoformat(), price=100.0, value=1.0)
    signals = make_signals(**{"5m": True})
    candidates = get_candidates(signals, THRESHOLDS, db_path, now=NOW)
    assert [c["key"] for c in candidates] == ["5m"]


def test_get_candidates_tiers_are_independent(tmp_path):
    db_path = str(tmp_path / "history.db")
    init_db(db_path)
    upsert_tier_state(db_path, tier="5m_up", fired_at=(NOW - timedelta(minutes=5)).isoformat(), price=100.0, value=1.0)
    signals = make_signals(**{"5m": True, "1h": True})
    candidates = get_candidates(signals, THRESHOLDS, db_path, now=NOW)
    assert [c["key"] for c in candidates] == ["1h"]
