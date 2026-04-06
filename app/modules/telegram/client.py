from __future__ import annotations

import json
from urllib import error, request


class TelegramApiClient:
    def __init__(self, bot_token: str) -> None:
        self._base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, chat_id: int, text: str, buttons: list[list[str]] | None = None) -> None:
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        if buttons:
            payload["reply_markup"] = {
                "keyboard": [[{"text": label} for label in row] for row in buttons],
                "resize_keyboard": True,
            }
        req = request.Request(
            url=f"{self._base_url}/sendMessage",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    raise RuntimeError(f"Telegram API responded with {resp.status}")
        except error.URLError as exc:
            raise RuntimeError(f"Telegram API request failed: {exc}") from exc

