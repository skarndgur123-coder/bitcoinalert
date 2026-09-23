import json

from record_history import record_fired, append_jsonl
from _history_db import init_db, get_tier_state


def test_record_fired_upserts_tier_state(tmp_path):
    db_path = str(tmp_path / "history.db")
    init_db(db_path)
    record_fired(db_path, tier="5m_up", fired_at="2026-09-22T12:00:00+00:00", price=100.0, value=1.5)
    state = get_tier_state(db_path, "5m_up")
    assert state["last_fired_price"] == 100.0
    assert state["last_fired_value"] == 1.5


def test_append_jsonl_writes_one_line_per_call(tmp_path):
    log_path = tmp_path / "run.jsonl"
    append_jsonl(str(log_path), {"a": 1})
    append_jsonl(str(log_path), {"b": 2})
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"a": 1}
    assert json.loads(lines[1]) == {"b": 2}
