from datetime import datetime
from zoneinfo import ZoneInfo

PRICE_LABELS = {"5m": "5분", "1h": "1시간", "24h": "24시간"}
UPBIT_CHART_URL = "https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC"


def _direction_label(direction: str) -> str:
    return "급등" if direction == "up" else "급락"


def _render_candidate_line(candidate: dict) -> str:
    key = candidate["key"]
    condition = candidate["condition"]
    if key == "volume_spike":
        return (
            f"• 거래량 급증: 평균 대비 {condition['volume_ratio']:.1f}배 "
            f"(기준 {condition['multiplier']:.1f}배)"
        )
    label = PRICE_LABELS[key]
    direction = _direction_label(condition["direction"])
    return (
        f"• {label} {direction}: {condition['pct_change']:+.2f}% "
        f"(기준 ±{condition['threshold_pct']:.1f}%)"
    )


def build_message(signals: dict, candidates: list[dict]) -> str:
    lines = [f"🚨 Bitcoinalert 알림 ({len(candidates)}건)", ""]
    lines.extend(_render_candidate_line(c) for c in candidates)
    lines.append("")

    current_price = signals["current_price"]
    pct_24h = signals["conditions"]["24h"]["pct_change"]
    timestamp = datetime.fromisoformat(signals["timestamp"]).astimezone(ZoneInfo("Asia/Seoul"))

    lines.append(f"현재가: {current_price:,.0f}원")
    lines.append(f"24시간 변동: {pct_24h:+.1f}%")
    lines.append(f"기준시각: {timestamp.strftime('%Y-%m-%d %H:%M:%S')} (KST)")
    return "\n".join(lines)


def build_template_object(text: str, link_url: str = UPBIT_CHART_URL) -> dict:
    return {
        "object_type": "text",
        "text": text,
        "link": {"web_url": link_url, "mobile_web_url": link_url},
        "button_title": "차트 보기",
    }
