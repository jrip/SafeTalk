from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.core.settings import get_settings
from app.db.database import get_db
from app.modules.telegram.webhook_service import handle_telegram_update


def _container(session: Session = Depends(get_db)):
    return build_app_container(session)


def _require_webhook_secret(
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> None:
    configured = (get_settings().TELEGRAM_WEBHOOK_SECRET_TOKEN or "").strip()
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram webhook is disabled by server configuration",
        )
    if x_telegram_bot_api_secret_token is None or not secrets.compare_digest(
        x_telegram_bot_api_secret_token,
        configured,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram webhook secret token",
        )


router = APIRouter(
    prefix="/telegram",
    tags=["telegram"],
    dependencies=[Depends(_require_webhook_secret)],
)


@router.post("/webhook")
def telegram_webhook(payload: dict[str, Any], c=Depends(_container)) -> dict[str, bool]:
    handle_telegram_update(payload, c)
    return {"ok": True}

