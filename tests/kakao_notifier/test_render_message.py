from render_message import build_message, build_template_object


def make_signals(current_price=143250000.0, pct_24h=4.9):
    return {
        "timestamp": "2026-09-22T05:35:05+00:00",
        "current_price": current_price,
        "conditions": {
            "24h": {"pct_change": pct_24h, "threshold_pct": 5.0, "direction": "up", "triggered": False, "tier": None},
        },
    }


def test_build_message_single_tier():
    signals = make_signals()
    candidates = [
        {
            "key": "5m",
            "tier": "5m_up",
            "condition": {"pct_change": 1.23, "threshold_pct": 1.0, "direction": "up", "triggered": True, "tier": "5m_up"},
        }
    ]
    message = build_message(signals, candidates)
    assert "5분 급등: +1.23% (기준 ±1.0%)" in message
    assert "143,250,000원" in message
    assert "+4.9%" in message


def test_build_message_multiple_tiers_shows_each_line():
    signals = make_signals()
    candidates = [
        {
            "key": "5m",
            "tier": "5m_up",
            "condition": {"pct_change": 1.23, "threshold_pct": 1.0, "direction": "up", "triggered": True, "tier": "5m_up"},
        },
        {
            "key": "volume_spike",
            "tier": "volume_spike",
            "condition": {"volume_ratio": 3.4, "multiplier": 3.0, "triggered": True, "tier": "volume_spike"},
        },
    ]
    message = build_message(signals, candidates)
    assert "5분 급등: +1.23% (기준 ±1.0%)" in message
    assert "거래량 급증: 평균 대비 3.4배 (기준 3.0배)" in message
    assert "(2건)" in message


def test_build_template_object_shape():
    template = build_template_object("hello")
    assert template["object_type"] == "text"
    assert template["text"] == "hello"
    assert "web_url" in template["link"]
