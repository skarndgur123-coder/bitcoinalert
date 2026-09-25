import json
from datetime import datetime, timedelta, timezone

from refresh_access_token import check_refresh_token_expiry, ensure_valid_access_token


def write_token_file(path, obtained_at, expires_in=21599, refresh_token="old_refresh"):
    path.write_text(
        json.dumps(
            {
                "access_token": "old_access",
                "refresh_token": refresh_token,
                "obtained_at": obtained_at,
                "expires_in": expires_in,
                "refresh_token_expires_in": 5183999,
            }
        ),
        encoding="utf-8",
    )


def test_returns_existing_token_when_not_near_expiry(tmp_path):
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    token_path = tmp_path / "kakao_token.json"
    write_token_file(token_path, obtained_at=(now - timedelta(minutes=5)).isoformat())

    def fail_post(*args, **kwargs):
        raise AssertionError("should not call token endpoint when not near expiry")

    token = ensure_valid_access_token(
        str(token_path),
        client_id="client123",
        safety_margin_minutes=30,
        now_fn=lambda: now,
        post_fn=fail_post,
    )
    assert token == "old_access"


def test_refreshes_and_persists_new_refresh_token_when_kakao_rotates_it(tmp_path):
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    token_path = tmp_path / "kakao_token.json"
    write_token_file(token_path, obtained_at=(now - timedelta(hours=6)).isoformat())

    def fake_post(url, data=None, timeout=None):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"access_token": "new_access", "refresh_token": "new_refresh", "expires_in": 21599}

        return FakeResponse()

    token = ensure_valid_access_token(
        str(token_path),
        client_id="client123",
        safety_margin_minutes=30,
        now_fn=lambda: now,
        post_fn=fake_post,
    )
    assert token == "new_access"
    saved = json.loads(token_path.read_text(encoding="utf-8"))
    assert saved["access_token"] == "new_access"
    assert saved["refresh_token"] == "new_refresh"
    assert saved["obtained_at"] == now.isoformat()


def test_refresh_keeps_old_refresh_token_when_kakao_omits_it(tmp_path):
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    token_path = tmp_path / "kakao_token.json"
    write_token_file(token_path, obtained_at=(now - timedelta(hours=6)).isoformat(), refresh_token="keep_me")

    def fake_post(url, data=None, timeout=None):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"access_token": "new_access", "expires_in": 21599}

        return FakeResponse()

    ensure_valid_access_token(
        str(token_path),
        client_id="client123",
        safety_margin_minutes=30,
        now_fn=lambda: now,
        post_fn=fake_post,
    )
    saved = json.loads(token_path.read_text(encoding="utf-8"))
    assert saved["refresh_token"] == "keep_me"


def test_refresh_sets_refresh_token_obtained_at_when_kakao_rotates_it(tmp_path):
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    token_path = tmp_path / "kakao_token.json"
    write_token_file(token_path, obtained_at=(now - timedelta(hours=6)).isoformat())

    def fake_post(url, data=None, timeout=None):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"access_token": "new_access", "refresh_token": "new_refresh", "expires_in": 21599}

        return FakeResponse()

    ensure_valid_access_token(
        str(token_path),
        client_id="client123",
        safety_margin_minutes=30,
        now_fn=lambda: now,
        post_fn=fake_post,
    )
    saved = json.loads(token_path.read_text(encoding="utf-8"))
    assert saved["refresh_token_obtained_at"] == now.isoformat()


def test_refresh_keeps_refresh_token_obtained_at_when_kakao_does_not_rotate(tmp_path):
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    token_path = tmp_path / "kakao_token.json"
    write_token_file(token_path, obtained_at=(now - timedelta(hours=6)).isoformat())
    original = json.loads(token_path.read_text(encoding="utf-8"))
    original["refresh_token_obtained_at"] = "2026-08-01T00:00:00+00:00"
    token_path.write_text(json.dumps(original), encoding="utf-8")

    def fake_post(url, data=None, timeout=None):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                # Kakao omits refresh_token when it isn't being rotated.
                return {"access_token": "new_access", "expires_in": 21599}

        return FakeResponse()

    ensure_valid_access_token(
        str(token_path),
        client_id="client123",
        safety_margin_minutes=30,
        now_fn=lambda: now,
        post_fn=fake_post,
    )
    saved = json.loads(token_path.read_text(encoding="utf-8"))
    assert saved["refresh_token_obtained_at"] == "2026-08-01T00:00:00+00:00"


def _capture_post(captured):
    def fake_post(url, data=None, timeout=None):
        captured.update(data)

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"access_token": "new_access", "expires_in": 21599}

        return FakeResponse()

    return fake_post


def test_refresh_sends_client_secret_when_provided(tmp_path):
    # Kakao apps with Client Secret enabled reject refresh without it (401 KOE010).
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    token_path = tmp_path / "kakao_token.json"
    write_token_file(token_path, obtained_at=(now - timedelta(hours=6)).isoformat())
    captured = {}

    ensure_valid_access_token(
        str(token_path),
        client_id="client123",
        client_secret="s3cret",
        now_fn=lambda: now,
        post_fn=_capture_post(captured),
    )
    assert captured["client_secret"] == "s3cret"


def test_refresh_omits_client_secret_when_not_provided(tmp_path):
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    token_path = tmp_path / "kakao_token.json"
    write_token_file(token_path, obtained_at=(now - timedelta(hours=6)).isoformat())
    captured = {}

    ensure_valid_access_token(
        str(token_path),
        client_id="client123",
        now_fn=lambda: now,
        post_fn=_capture_post(captured),
    )
    assert "client_secret" not in captured


def test_check_refresh_token_expiry_warns_within_threshold(tmp_path):
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    token_path = tmp_path / "kakao_token.json"
    write_token_file(token_path, obtained_at=now.isoformat())
    token = json.loads(token_path.read_text(encoding="utf-8"))
    token["refresh_token_obtained_at"] = (now - timedelta(days=55)).isoformat()
    token["refresh_token_expires_in"] = 60 * 24 * 3600  # 60 days
    token_path.write_text(json.dumps(token), encoding="utf-8")

    result = check_refresh_token_expiry(str(token_path), warn_within_days=14, now_fn=lambda: now)
    assert result["warn"] is True
    assert result["days_remaining"] == 5


def test_check_refresh_token_expiry_does_not_warn_when_far(tmp_path):
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    token_path = tmp_path / "kakao_token.json"
    write_token_file(token_path, obtained_at=now.isoformat())
    token = json.loads(token_path.read_text(encoding="utf-8"))
    token["refresh_token_obtained_at"] = (now - timedelta(days=10)).isoformat()
    token["refresh_token_expires_in"] = 60 * 24 * 3600  # 60 days
    token_path.write_text(json.dumps(token), encoding="utf-8")

    result = check_refresh_token_expiry(str(token_path), warn_within_days=14, now_fn=lambda: now)
    assert result["warn"] is False
    assert result["days_remaining"] == 50


def test_check_refresh_token_expiry_falls_back_to_obtained_at_when_missing(tmp_path):
    now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
    token_path = tmp_path / "kakao_token.json"
    write_token_file(token_path, obtained_at=(now - timedelta(days=55)).isoformat())
    token = json.loads(token_path.read_text(encoding="utf-8"))
    token["refresh_token_expires_in"] = 60 * 24 * 3600  # 60 days
    token_path.write_text(json.dumps(token), encoding="utf-8")

    result = check_refresh_token_expiry(str(token_path), warn_within_days=14, now_fn=lambda: now)
    assert result["warn"] is True
    assert result["days_remaining"] == 5
