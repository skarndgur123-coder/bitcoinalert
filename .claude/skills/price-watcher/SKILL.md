# price-watcher

업비트 KRW-BTC 시세를 조회하고, 설정된 임계값(5분/1시간/24시간 변동률, 거래량 급증) 대비 신호를 계산하며, 쿨다운을 적용해 실제로 알림을 보낼 후보만 골라낸다. 순수 계산 로직이며 LLM 호출 없음.

## 스크립트

- `_upbit_client.py` — `get_json(url, params, max_retries, backoff_base_seconds, timeout_seconds, sleep_fn)`: 재시도/백오프가 있는 업비트 공개 API 호출 래퍼. 소진 시 `UpbitFetchError`.
- `_config.py` — `load_thresholds(path) -> dict`: `config/thresholds.yaml` 로드.
- `_history_db.py` — SQLite `tier_state` 테이블 관리 (`init_db`, `get_tier_state`, `upsert_tier_state`). kakao-notifier 스킬도 이 모듈을 재사용.
- `fetch_market_data.py` — `fetch_snapshot(market, thresholds, get_json_fn, now_fn) -> dict`: 현재가, 5분/1시간/24시간 전 종가, 현재 거래량, 거래량 이동평균용 데이터를 하나의 스냅샷으로 조합. CLI로 단독 실행하면 `output/last_run/snapshot.json`에 기록.
- `compute_signals.py` — `pct_change`, `trailing_average`, `volume_ratio`, `evaluate_signals(snapshot, thresholds) -> dict`: 7개 tier(`5m_up/5m_down/1h_up/1h_down/24h_up/24h_down/volume_spike`) 각각의 트리거 여부를 순수 계산.
- `filter_candidates.py` — `is_in_cooldown`, `get_candidates(signals, thresholds, db_path, now) -> list[dict]`: 트리거된 tier 중 쿨다운 중이 아닌 것만 반환 (읽기 전용, DB 기록은 발송 성공 후 kakao-notifier 쪽에서 수행).

## 입출력 계약

- 입력: `config/thresholds.yaml`, 업비트 공개 API (인증 불필요)
- 출력: snapshot/signals dict (인메모리, `run_check.py`가 직접 함수 호출로 전달), 디버그용 `output/last_run/{snapshot,signals}.json`

## 단독 실행

```
python .claude/skills/price-watcher/scripts/fetch_market_data.py
```
