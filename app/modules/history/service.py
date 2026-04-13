from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.history.storage_sqlalchemy import SqlAlchemyHistoryStore
from app.modules.history.types import HistoryView


class HistoryService:
    def __init__(self, history: SqlAlchemyHistoryStore, session: Session) -> None:
        self._history = history
        self._session = session

    def get_api_history(self, user_id: UUID) -> list[HistoryView]:
        return self._history.list_for_user(user_id)

    def count_all_records(self) -> int:
        return self._history.count_all_records()

    def update_result_for_ml_task(
        self,
        user_id: UUID,
        ml_task_id: UUID,
        result: str,
        *,
        tokens_charged: Decimal | None = None,
        commit: bool = True,
    ) -> None:
        self._history.update_result_for_ml_task(
            user_id, ml_task_id, result, tokens_charged=tokens_charged
        )
        if commit:
            self._session.commit()

    def save_api_request(
        self,
        user_id: UUID,
        request: str,
        result: str,
        *,
        ml_model_id: UUID | None = None,
        ml_task_id: UUID | None = None,
        tokens_charged: Decimal | None = None,
        commit: bool = True,
    ) -> None:
        self._history.append(
            user_id,
            request,
            result,
            ml_model_id=ml_model_id,
            ml_task_id=ml_task_id,
            tokens_charged=tokens_charged,
        )
        if commit:
            self._session.commit()
