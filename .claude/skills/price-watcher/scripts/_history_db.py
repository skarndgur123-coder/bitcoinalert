import sqlite3


def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tier_state (
                tier TEXT PRIMARY KEY,
                last_fired_at TEXT NOT NULL,
                last_fired_price REAL NOT NULL,
                last_fired_value REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_tier_state(db_path: str, tier: str) -> dict | None:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT tier, last_fired_at, last_fired_price, last_fired_value, updated_at "
            "FROM tier_state WHERE tier = ?",
            (tier,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {
        "tier": row[0],
        "last_fired_at": row[1],
        "last_fired_price": row[2],
        "last_fired_value": row[3],
        "updated_at": row[4],
    }


def upsert_tier_state(db_path: str, tier: str, fired_at: str, price: float, value: float) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO tier_state (tier, last_fired_at, last_fired_price, last_fired_value, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(tier) DO UPDATE SET
                last_fired_at = excluded.last_fired_at,
                last_fired_price = excluded.last_fired_price,
                last_fired_value = excluded.last_fired_value,
                updated_at = excluded.updated_at
            """,
            (tier, fired_at, price, value, fired_at),
        )
        conn.commit()
    finally:
        conn.close()
