import json
import os
import sys
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv

AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"


def _make_handler(result_holder):
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            code = query.get("code", [None])[0]
            result_holder["code"] = code
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("인증이 완료되었습니다. 이 창을 닫으셔도 됩니다.".encode("utf-8"))

        def log_message(self, format, *args):
            pass

    return CallbackHandler


def wait_for_authorization_code(redirect_uri: str) -> str:
    parsed = urlparse(redirect_uri)
    port = parsed.port or 80
    result_holder = {}
    server = HTTPServer(("localhost", port), _make_handler(result_holder))
    print(f"로컬 서버가 {redirect_uri} 에서 대기 중입니다. 브라우저에서 인증을 완료해주세요...")
    while "code" not in result_holder:
        server.handle_request()
    server.server_close()
    return result_holder["code"]


def exchange_code_for_token(client_id: str, redirect_uri: str, code: str, client_secret: str | None) -> dict:
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    if client_secret:
        data["client_secret"] = client_secret
    response = requests.post(TOKEN_URL, data=data, timeout=10)
    response.raise_for_status()
    return response.json()


def main():
    load_dotenv()
    client_id = os.environ["KAKAO_REST_API_KEY"]
    redirect_uri = os.environ.get("KAKAO_REDIRECT_URI", "http://localhost:8910/oauth/callback")
    client_secret = os.environ.get("KAKAO_CLIENT_SECRET") or None
    token_store_path = os.environ.get("KAKAO_TOKEN_STORE_PATH", "secrets/kakao_token.json")

    authorize_url = (
        f"{AUTHORIZE_URL}?client_id={client_id}&redirect_uri={redirect_uri}"
        f"&response_type=code&scope=talk_message"
    )
    print(f"다음 URL을 브라우저에서 열어 카카오 로그인 동의를 진행하세요:\n{authorize_url}\n")
    webbrowser.open(authorize_url)

    code = wait_for_authorization_code(redirect_uri)
    payload = exchange_code_for_token(client_id, redirect_uri, code, client_secret)

    obtained_at = datetime.now(timezone.utc).isoformat()
    token = {
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
        "obtained_at": obtained_at,
        "expires_in": payload["expires_in"],
        "refresh_token_expires_in": payload.get("refresh_token_expires_in"),
        "refresh_token_obtained_at": obtained_at,
    }

    output_path = Path(token_store_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(token, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"토큰이 저장되었습니다: {output_path}")


if __name__ == "__main__":
    sys.exit(main())
