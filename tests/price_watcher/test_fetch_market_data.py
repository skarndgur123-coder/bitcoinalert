from datetime import datetime, timezone

from fetch_market_data import fetch_snapshot

THRESHOLDS = {"volume_spike": {"lookback_periods": 20}}


def make_candle(trade_price, volume):
    return {"trade_price": trade_price, "candle_acc_trade_volume": volume}


def fake_get_json(url, params=None, **kwargs):
    if "ticker" in url:
        return [{"trade_price": 105.0}]
    if "minutes/5" in url:
        candles = [make_candle(999.0, 999.0)]  # index 0: in-progress, skip
        candles.append(make_candle(100.0, 9.0))  # index 1: last complete 5m candle
        for i in range(20):  # index 2..21: trailing volumes for avg
            candles.append(make_candle(50.0, 1.0))
        candles[12] = make_candle(103.0, 1.0)  # index 12 (60min back) -> price_1h_ago
        return candles
    if "minutes/60" in url:
        candles = [make_candle(0.0, 0.0)] * 25
        candles[24] = make_candle(101.0, 0.0)  # 24h back
        return candles
    raise AssertionError(f"unexpected url {url}")


def test_fetch_snapshot_builds_expected_shape():
    fixed_now = datetime(2026, 9, 22, 5, 35, 0, tzinfo=timezone.utc)
    snapshot = fetch_snapshot(
        market="KRW-BTC",
        thresholds=THRESHOLDS,
        get_json_fn=fake_get_json,
        now_fn=lambda: fixed_now,
    )
    assert snapshot["timestamp"] == fixed_now.isoformat()
    assert snapshot["current_price"] == 105.0
    assert snapshot["price_5m_ago"] == 100.0
    assert snapshot["price_1h_ago"] == 103.0
    assert snapshot["price_24h_ago"] == 101.0
    assert snapshot["current_volume"] == 9.0
    assert snapshot["trailing_volumes"] == [1.0] * 20
