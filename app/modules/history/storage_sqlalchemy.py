from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.history.entities import HistoryRecord
from app.modules.history.models import HistoryRecordModel
from app.modules.history.types import HistoryView


class SqlAlchemyHistoryStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_user(self, user_id: UUID) -> list[HistoryView]:
        stmt = (
            select(HistoryRecordModel)
            .where(HistoryRecordModel.user_id == user_id)
            .order_by(HistoryRecordModel.created_at.desc())
        )
        rows = self._session.scalars(stmt).all()
        return [
            HistoryView(
                id=r.id,
                user_id=r.user_id,
                request=r.request,
                result=r.result,
                created_at=r.created_at,
                ml_model_id=r.ml_model_id,
                ml_task_id=r.ml_task_id,
                tokens_charged=r.tokens_charged,
            )
            for r in rows
        ]

    def append(
        self,
        user_id: UUID,
        request: str,
        result: str,
        *,
        ml_model_id: UUID | None = None,
        ml_task_id: UUID | None = None,
        tokens_charged: Decimal | None = None,
    ) -> None:
        self._session.add(
            HistoryRecordModel(
                user_id=user_id,
                request=request,
                result=result,
                ml_model_id=ml_model_id,
                ml_task_id=ml_task_id,
                tokens_charged=tokens_charged,
            )
        )
        self._session.flush()

    def get_own_record(self, user_id: UUID, record_id: UUID) -> HistoryRecord | None:
        row = self._session.get(HistoryRecordModel, record_id)
        if row is None or row.user_id != user_id:
            return None
        return HistoryRecord(
            id=row.id,
            user_id=row.user_id,
            request=row.request,
            result=row.result,
            created_at=row.created_at,
            ml_model_id=row.ml_model_id,
            ml_task_id=row.ml_task_id,
            tokens_charged=row.tokens_charged,
        )
