from compute_signals import pct_change, trailing_average, volume_ratio, evaluate_signals


THRESHOLDS = {
    "price_change": {
        "5m": {"threshold_pct": 1.0},
        "1h": {"threshold_pct": 3.0},
        "24h": {"threshold_pct": 5.0},
    },
    "volume_spike": {
        "lookback_periods": 20,
        "multiplier": 3.0,
        "min_avg_volume": 0.01,
    },
}


def make_snapshot(**overrides):
    base = {
        "timestamp": "2026-09-22T05:35:00+00:00",
        "current_price": 100.0,
        "price_5m_ago": 100.0,
        "price_1h_ago": 100.0,
        "price_24h_ago": 100.0,
        "current_volume": 1.0,
        "trailing_volumes": [1.0] * 20,
    }
    base.update(overrides)
    return base


def test_pct_change_positive_move():
    assert pct_change(current=110.0, past=100.0) == 10.0


def test_pct_change_negative_move():
    assert pct_change(current=90.0, past=100.0) == -10.0


def test_trailing_average_of_volumes():
    assert trailing_average([1.0, 2.0, 3.0]) == 2.0


def test_volume_ratio_normal_case():
    assert volume_ratio(current_volume=9.0, avg_volume=3.0, min_avg_volume=0.01) == 3.0


def test_volume_ratio_none_when_avg_below_floor():
    assert volume_ratio(current_volume=9.0, avg_volume=0.005, min_avg_volume=0.01) is None


def test_evaluate_signals_triggers_5m_up_above_threshold():
    snapshot = make_snapshot(current_price=102.0, price_5m_ago=100.0)
    result = evaluate_signals(snapshot, THRESHOLDS)
    cond = result["conditions"]["5m"]
    assert cond["triggered"] is True
    assert cond["direction"] == "up"
    assert cond["tier"] == "5m_up"


def test_evaluate_signals_not_triggered_below_threshold():
    snapshot = make_snapshot(current_price=100.5, price_5m_ago=100.0)
    result = evaluate_signals(snapshot, THRESHOLDS)
    cond = result["conditions"]["5m"]
    assert cond["triggered"] is False
    assert cond["tier"] is None


def test_evaluate_signals_boundary_exact_threshold_triggers():
    snapshot = make_snapshot(current_price=101.0, price_5m_ago=100.0)
    result = evaluate_signals(snapshot, THRESHOLDS)
    assert result["conditions"]["5m"]["triggered"] is True


def test_evaluate_signals_triggers_down_direction():
    snapshot = make_snapshot(current_price=94.0, price_24h_ago=100.0)
    result = evaluate_signals(snapshot, THRESHOLDS)
    cond = result["conditions"]["24h"]
    assert cond["triggered"] is True
    assert cond["direction"] == "down"
    assert cond["tier"] == "24h_down"


def test_evaluate_signals_volume_spike_triggered():
    snapshot = make_snapshot(current_volume=5.0, trailing_volumes=[1.0] * 20)
    result = evaluate_signals(snapshot, THRESHOLDS)
    cond = result["conditions"]["volume_spike"]
    assert cond["triggered"] is True
    assert cond["tier"] == "volume_spike"
    assert cond["volume_ratio"] == 5.0


def test_evaluate_signals_volume_spike_not_triggered_below_avg_floor():
    snapshot = make_snapshot(current_volume=5.0, trailing_volumes=[0.001] * 20)
    result = evaluate_signals(snapshot, THRESHOLDS)
    cond = result["conditions"]["volume_spike"]
    assert cond["triggered"] is False
    assert cond["volume_ratio"] is None
    assert cond["tier"] is None
