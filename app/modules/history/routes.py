from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.bootstrap import build_app_container
from app.db.database import get_db

router = APIRouter(prefix="/history", tags=["history"])


def _container(session: Session = Depends(get_db)):
    return build_app_container(session)


@router.get("/{user_id}")
def history(user_id: UUID, c=Depends(_container)) -> list[dict[str, Any]]:
    return [asdict(x) for x in c.history.get_api_history(user_id)]
