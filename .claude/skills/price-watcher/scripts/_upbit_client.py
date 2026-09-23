import time

import requests


class UpbitFetchError(Exception):
    pass


def get_json(
    url: str,
    params: dict | None = None,
    max_retries: int = 3,
    backoff_base_seconds: float = 2,
    timeout_seconds: float = 10,
    sleep_fn=time.sleep,
) -> dict:
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout_seconds)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                sleep_fn(backoff_base_seconds * (2**attempt))
    raise UpbitFetchError(f"Failed to fetch {url} after {max_retries} attempts: {last_error}")
