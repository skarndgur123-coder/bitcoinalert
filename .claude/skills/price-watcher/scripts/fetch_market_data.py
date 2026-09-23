import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from _upbit_client import get_json

TICKER_URL = "https://api.upbit.com/v1/ticker"
CANDLES_5M_URL = "https://api.upbit.com/v1/candles/minutes/5"
CANDLES_60M_URL = "https://api.upbit.com/v1/candles/minutes/60"

HOUR_BACK_5M_INDEX = 12  # 12 * 5min = 60min
DAY_BACK_60M_INDEX = 24  # 24 * 60min = 24h


def fetch_snapshot(
    market: str,
    thresholds: dict,
    get_json_fn=get_json,
    now_fn=lambda: datetime.now(timezone.utc),
) -> dict:
    lookback = thresholds["volume_spike"]["lookback_periods"]

    ticker = get_json_fn(TICKER_URL, params={"markets": market})
    current_price = ticker[0]["trade_price"]

    candles_5m = get_json_fn(CANDLES_5M_URL, params={"market": market, "count": lookback + 2})
    last_complete_5m = candles_5m[1]
    trailing_volumes = [c["candle_acc_trade_volume"] for c in candles_5m[2 : 2 + lookback]]

    candles_60m = get_json_fn(CANDLES_60M_URL, params={"market": market, "count": DAY_BACK_60M_INDEX + 1})

    return {
        "timestamp": now_fn().isoformat(),
        "current_price": current_price,
        "price_5m_ago": last_complete_5m["trade_price"],
        "price_1h_ago": candles_5m[HOUR_BACK_5M_INDEX]["trade_price"],
        "price_24h_ago": candles_60m[DAY_BACK_60M_INDEX]["trade_price"],
        "current_volume": last_complete_5m["candle_acc_trade_volume"],
        "trailing_volumes": trailing_volumes,
    }


def main():
    from _config import load_thresholds

    thresholds = load_thresholds("config/thresholds.yaml")
    snapshot = fetch_snapshot(thresholds["market"], thresholds)
    output_path = Path("output/last_run/snapshot.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(snapshot, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
