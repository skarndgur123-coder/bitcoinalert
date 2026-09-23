import json
from datetime import datetime, timedelta, timezone

from refresh_access_token import ensure_valid_access_token


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
