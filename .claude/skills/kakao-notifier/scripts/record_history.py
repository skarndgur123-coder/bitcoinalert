import json
from pathlib import Path

from _history_db import upsert_tier_state


def record_fired(db_path: str, tier: str, fired_at: str, price: float, value: float) -> None:
    upsert_tier_state(db_path, tier=tier, fired_at=fired_at, price=price, value=value)


def append_jsonl(log_path: str, entry: dict) -> None:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
