# kakao-notifier

카카오톡 "나에게 보내기" API로 알림 메시지를 발송하고, OAuth 토큰 수명주기와 쿨다운 기록을 관리한다.

## 스크립트

- `kakao_auth_setup.py` — **1회성 수동 실행.** 로컬 HTTP 서버로 OAuth 인가 코드를 받아 최초 access/refresh 토큰을 발급받아 `secrets/kakao_token.json`에 저장. 대화형(브라우저 필요)이라 자동 테스트 없음.
- `refresh_access_token.py` — `ensure_valid_access_token(token_store_path, client_id, client_secret, safety_margin_minutes, now_fn, post_fn) -> str`: 만료 임박(기본 30분 여유)시에만 refresh_token으로 갱신. 앱에 Client Secret이 켜져 있으면 client_secret 필수(없으면 401 KOE010). 카카오가 새 refresh_token을 내려줄 때만 교체 저장.
- `render_message.py` — `build_message(signals, candidates) -> str`, `build_template_object(text, link_url) -> dict`: 트리거된 tier들을 하나의 한국어 메시지로 묶고, 카카오 기본 text 템플릿 객체로 변환 (순수 함수).
- `send_kakao_message.py` — `send_with_retry(access_token, template_object, max_attempts, backoff_base_seconds, sleep_fn) -> dict`: `https://kapi.kakao.com/v2/api/talk/memo/default/send` 호출, 재시도/백오프. 소진 시 `KakaoSendError` + stderr에 `ESCALATE:` 출력.
- `record_history.py` — `record_fired(db_path, tier, fired_at, price, value)`: 발송 성공 후에만 `tier_state` 갱신 (price-watcher의 `_history_db.py` 재사용). `append_jsonl(log_path, entry)`: `output/logs/{run,errors}.jsonl`에 한 줄씩 추가.

## 사용자가 수동으로 준비할 것

1. [Kakao Developers](https://developers.kakao.com)에서 앱 생성 → "카카오톡 메시지" 활성화 → REST API 키 확인
2. 앱 설정에 Redirect URI 등록 (`.env`의 `KAKAO_REDIRECT_URI`와 동일한 값, 기본 `http://localhost:8910/oauth/callback`)
3. 카카오 로그인 동의항목에 `talk_message` 스코프 추가
4. `.env` 작성 후 `python .claude/skills/kakao-notifier/scripts/kakao_auth_setup.py` 1회 실행

## 메시지 글자수 제한

카카오 기본 `text` 템플릿은 글자수 제한이 있다(카카오 문서 기준 변동 가능성 있음, 구현/운영 중 재확인). 여러 tier가 동시 트리거되어 메시지가 길어지면 심각도 상위 2~3개만 표시하는 방향으로 `render_message.py`를 조정할 것.
