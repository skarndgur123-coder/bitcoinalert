import pytest

from _upbit_client import get_json, UpbitFetchError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_get_json_returns_payload_on_first_success(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return FakeResponse({"ok": True})

    monkeypatch.setattr("_upbit_client.requests.get", fake_get)
    result = get_json("https://api.upbit.com/v1/ticker", params={"markets": "KRW-BTC"}, max_retries=3, timeout_seconds=10)
    assert result == {"ok": True}


def test_get_json_retries_then_succeeds(monkeypatch):
    calls = {"count": 0}

    def fake_get(url, params=None, timeout=None):
        calls["count"] += 1
        if calls["count"] < 3:
            raise Exception("network blip")
        return FakeResponse({"ok": True})

    sleeps = []
    monkeypatch.setattr("_upbit_client.requests.get", fake_get)
    result = get_json(
        "https://api.upbit.com/v1/ticker",
        max_retries=3,
        backoff_base_seconds=2,
        timeout_seconds=10,
        sleep_fn=sleeps.append,
    )
    assert result == {"ok": True}
    assert calls["count"] == 3
    assert sleeps == [2, 4]


def test_get_json_raises_upbit_fetch_error_after_exhausting_retries(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise Exception("still down")

    monkeypatch.setattr("_upbit_client.requests.get", fake_get)
    with pytest.raises(UpbitFetchError):
        get_json(
            "https://api.upbit.com/v1/ticker",
            max_retries=3,
            backoff_base_seconds=2,
            timeout_seconds=10,
            sleep_fn=lambda seconds: None,
        )
