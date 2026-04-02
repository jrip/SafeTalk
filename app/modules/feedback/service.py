from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import ValidationError
from app.modules.feedback.entities import Feedback
from app.modules.feedback.interfaces import FeedbackInternalService
from app.modules.feedback.ports import FeedbackStore
from app.modules.feedback.types import CreateFeedbackInput, FeedbackView
from app.modules.history.ports import HistoryStore


class FeedbackService(FeedbackInternalService):
    def __init__(self, feedback: FeedbackStore, history: HistoryStore, session: Session) -> None:
        self._feedback = feedback
        self._history = history
        self._session = session

    def create_feedback(self, payload: CreateFeedbackInput) -> FeedbackView:
        if self._history.get_own_record(payload.user_id, payload.history_id) is None:
            raise ValidationError("History record not found")
        entity = Feedback(
            history_id=payload.history_id,
            user_id=payload.user_id,
            is_toxic=payload.is_toxic,
            comment=payload.comment,
        )
        self._feedback.add(entity)
        self._session.commit()
        return FeedbackView(
            id=entity.id,
            history_id=entity.history_id,
            user_id=entity.user_id,
            is_toxic=entity.is_toxic,
            comment=entity.comment,
            created_at=entity.created_at,
        )
