"""Check OPENAI_API_KEY: list models, then one cheap chat completion. Does not print the key."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from pathlib import Path

MODELS_URL = "https://api.openai.com/v1/models"
CHAT_URL = "https://api.openai.com/v1/chat/completions"


def _load_dotenv() -> None:
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


def _request(url: str, key: str, payload: dict | None = None) -> tuple[int, dict | str]:
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Authorization": f"Bearer {key}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = body[:500]
        return e.code, parsed
    except urllib.error.URLError as e:
        return 0, str(e)


def main() -> int:
    _load_dotenv()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        print("Set OPENAI_API_KEY in the environment.", file=sys.stderr)
        return 2

    code, models = _request(MODELS_URL, key)
    if code != 200 or not isinstance(models, dict):
        print(f"models: HTTP {code} {models}", file=sys.stderr)
        return 1
    ids = [m.get("id") for m in models.get("data", []) if m.get("id")]
    print(f"models ok — {len(ids)} listed")

    code, chat = _request(
        CHAT_URL,
        key,
        {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Reply with the single word ok"}],
            "max_tokens": 8,
        },
    )
    if code != 200 or not isinstance(chat, dict):
        print(f"chat: HTTP {code} {chat}", file=sys.stderr)
        return 1
    text = chat["choices"][0]["message"]["content"]
    print(f"chat ok — gpt-4o-mini said: {text!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
