import json
import sys
import time

import requests

SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


class KakaoSendError(Exception):
    pass


def send_with_retry(
    access_token: str,
    template_object: dict,
    max_attempts: int = 3,
    backoff_base_seconds: float = 2,
    timeout_seconds: float = 10,
    sleep_fn=time.sleep,
) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {"template_object": json.dumps(template_object, ensure_ascii=False)}

    last_error = None
    for attempt in range(max_attempts):
        try:
            response = requests.post(SEND_URL, headers=headers, data=data, timeout=timeout_seconds)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts - 1:
                sleep_fn(backoff_base_seconds * (2**attempt))

    print(f"ESCALATE: kakao send failed after {max_attempts} attempts: {last_error}", file=sys.stderr)
    raise KakaoSendError(f"Failed to send Kakao message after {max_attempts} attempts: {last_error}")
