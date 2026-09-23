import json

import pytest

from send_kakao_message import send_with_retry, KakaoSendError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_send_with_retry_succeeds_on_first_try(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, data=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        return FakeResponse({"result_code": 0})

    monkeypatch.setattr("send_kakao_message.requests.post", fake_post)
    result = send_with_retry(
        access_token="token123",
        template_object={"object_type": "text", "text": "hi"},
        max_attempts=3,
        backoff_base_seconds=2,
        sleep_fn=lambda s: None,
    )
    assert result == {"result_code": 0}
    assert captured["headers"]["Authorization"] == "Bearer token123"
    assert json.loads(captured["data"]["template_object"]) == {"object_type": "text", "text": "hi"}


def test_send_with_retry_raises_kakao_send_error_after_exhausting_attempts(monkeypatch):
    def fake_post(url, headers=None, data=None, timeout=None):
        raise Exception("network down")

    monkeypatch.setattr("send_kakao_message.requests.post", fake_post)
    with pytest.raises(KakaoSendError):
        send_with_retry(
            access_token="token123",
            template_object={"object_type": "text", "text": "hi"},
            max_attempts=3,
            backoff_base_seconds=2,
            sleep_fn=lambda s: None,
        )
