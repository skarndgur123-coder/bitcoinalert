def pct_change(current: float, past: float) -> float:
    return (current - past) / past * 100


def trailing_average(volumes: list[float]) -> float:
    return sum(volumes) / len(volumes)


def volume_ratio(current_volume: float, avg_volume: float, min_avg_volume: float) -> float | None:
    if avg_volume < min_avg_volume:
        return None
    return current_volume / avg_volume


def _evaluate_price_leg(key: str, current_price: float, past_price: float, threshold_pct: float) -> dict:
    change = pct_change(current_price, past_price)
    direction = "up" if change >= 0 else "down"
    triggered = abs(change) >= threshold_pct
    return {
        "pct_change": change,
        "threshold_pct": threshold_pct,
        "direction": direction,
        "triggered": triggered,
        "tier": f"{key}_{direction}" if triggered else None,
    }


def _evaluate_volume_leg(snapshot: dict, volume_cfg: dict) -> dict:
    lookback = volume_cfg["lookback_periods"]
    volumes = snapshot["trailing_volumes"][:lookback]
    avg_volume = trailing_average(volumes)
    current_volume = snapshot["current_volume"]
    ratio = volume_ratio(current_volume, avg_volume, volume_cfg["min_avg_volume"])
    multiplier = volume_cfg["multiplier"]
    triggered = ratio is not None and ratio >= multiplier
    return {
        "volume_ratio": ratio,
        "multiplier": multiplier,
        "current_volume": current_volume,
        "avg_volume": avg_volume,
        "triggered": triggered,
        "tier": "volume_spike" if triggered else None,
    }


def evaluate_signals(snapshot: dict, thresholds: dict) -> dict:
    price_cfg = thresholds["price_change"]
    conditions = {
        "5m": _evaluate_price_leg("5m", snapshot["current_price"], snapshot["price_5m_ago"], price_cfg["5m"]["threshold_pct"]),
        "1h": _evaluate_price_leg("1h", snapshot["current_price"], snapshot["price_1h_ago"], price_cfg["1h"]["threshold_pct"]),
        "24h": _evaluate_price_leg("24h", snapshot["current_price"], snapshot["price_24h_ago"], price_cfg["24h"]["threshold_pct"]),
        "volume_spike": _evaluate_volume_leg(snapshot, thresholds["volume_spike"]),
    }
    return {
        "timestamp": snapshot["timestamp"],
        "current_price": snapshot["current_price"],
        "conditions": conditions,
    }
