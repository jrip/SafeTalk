from __future__ import annotations

import logging
import secrets
from typing import Any
from uuid import UUID

from app.core import NotFoundError, ValidationError
from app.core.settings import get_settings
from app.modules.neural.types import RunPredictionInput
from app.modules.telegram.client import TelegramApiClient
from app.modules.users.types import CreateUserInput

log = logging.getLogger(__name__)
_MAIN_BUTTONS = [["/balance", "/history"], ["/predict "]]


def _build_bot_client() -> TelegramApiClient:
    token = (get_settings().TELEGRAM_BOT_TOKEN or "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    return TelegramApiClient(token)


def _display_name(message: dict[str, Any]) -> str:
    user = message.get("from") or {}
    username = (user.get("username") or "").strip()
    if username:
        return username
    first_name = (user.get("first_name") or "").strip()
    last_name = (user.get("last_name") or "").strip()
    full = f"{first_name} {last_name}".strip()
    if full:
        return full
    return "Telegram User"


def _extract_message(update: dict[str, Any]) -> tuple[int, int, str] | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    from_user = message.get("from") or {}
    chat = message.get("chat") or {}
    telegram_id = from_user.get("id")
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    if not isinstance(telegram_id, int) or not isinstance(chat_id, int):
        return None
    return telegram_id, chat_id, text


def _ensure_telegram_user(c: Any, telegram_id: int, name: str) -> Any:
    identity = c.users.find_telegram_identity(telegram_id)
    if identity is not None:
        return c.users.get_profile(identity.user_id)
    user = c.users.register(CreateUserInput(name=name))
    c.users.register_telegram_identity(user.id, telegram_id)
    return user


def _verified_email_login(c: Any, user_id: UUID) -> str | None:
    identities = c.users.get_identities(user_id)
    for identity in identities:
        if identity.identity_type == "email" and identity.is_verified:
            return identity.identifier
    return None


def _pending_email_login(c: Any, user_id: UUID) -> str | None:
    identities = c.users.get_identities(user_id)
    for identity in identities:
        if identity.identity_type == "email" and not identity.is_verified:
            return identity.identifier
    return None


def _send_help(bot: TelegramApiClient, chat_id: int) -> None:
    bot.send_message(
        chat_id,
        "Выбери действие кнопками ниже. "
        "Для предикта нажми /predict и добавь текст после команды.",
        buttons=_MAIN_BUTTONS,
    )


def handle_telegram_update(update: dict[str, Any], c: Any) -> None:
    parsed = _extract_message(update)
    if parsed is None:
        return
    telegram_id, chat_id, text = parsed
    bot = _build_bot_client()
    name = _display_name(update["message"])
    user = _ensure_telegram_user(c, telegram_id, name)

    verified_email = _verified_email_login(c, user.id)
    pending_email = _pending_email_login(c, user.id)

    if text == "/start":
        if verified_email:
            _send_help(bot, chat_id)
            return
        prompt = "Для продолжения отправь email в чат."
        if pending_email:
            prompt = (
                f"У тебя уже привязан email {pending_email}, но он не подтвержден.\n"
                "Отправь код подтверждения или новый email."
            )
        bot.send_message(chat_id, prompt)
        return

    if not verified_email:
        if "@" in text and "." in text:
            login = text.strip().lower()
            existing = c.users.get_email_identity(login)
            if existing is None:
                c.users.register_email_identity(user.id, login, secrets.token_urlsafe(24))
            elif existing.user_id != user.id:
                bot.send_message(chat_id, "Этот email уже используется другим аккаунтом.")
                return

            c.users.start_email_verification(login)
            bot.send_message(
                chat_id,
                "Код подтверждения отправлен на email. Отправь код сюда.",
            )
            return

        if pending_email:
            try:
                c.users.verify_email_code(pending_email, text)
                bot.send_message(chat_id, "Email подтвержден. Доступ открыт.")
                _send_help(bot, chat_id)
            except ValidationError as exc:
                bot.send_message(chat_id, str(exc))
            except NotFoundError:
                bot.send_message(chat_id, "Email для подтверждения не найден. Отправь email заново.")
            return

        bot.send_message(chat_id, "Сначала отправь email для привязки.")
        return

    if text.startswith("/balance"):
        balance = c.billing.get_count_tokens(user.id)
        bot.send_message(chat_id, f"Баланс: {balance.token_count}")
        return

    if text.startswith("/history"):
        history = c.history.get_api_history(user.id)
        if not history:
            bot.send_message(chat_id, "История пуста.")
            return
        lines = []
        for item in history[:5]:
            lines.append(f"- {item.created_at:%Y-%m-%d %H:%M}: {item.request[:50]} -> {item.result}")
        bot.send_message(chat_id, "Последние запросы:\n" + "\n".join(lines))
        return

    if text.startswith("/predict"):
        payload_text = text.replace("/predict", "", 1).strip()
        if not payload_text:
            bot.send_message(chat_id, "Использование: /predict <текст>")
            return
        try:
            default_model_id = c.neural.get_default_model_id()
            task = c.neural.create_prediction_task(
                RunPredictionInput(
                    user_id=user.id,
                    model_id=default_model_id,
                    text=payload_text,
                )
            )
            bot.send_message(
                chat_id,
                f"ML задача создана: {task.task_id}\n"
                f"Списано токенов: {task.charged_tokens}\n"
                f"Статус: {task.status}",
            )
        except (ValidationError, NotFoundError) as exc:
            bot.send_message(chat_id, str(exc))
        return

    _send_help(bot, chat_id)

