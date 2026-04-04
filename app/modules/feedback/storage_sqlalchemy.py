from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.feedback.models import FeedbackModel
from app.modules.feedback.entities import Feedback
from app.modules.feedback.ports import FeedbackStore


class SqlAlchemyFeedbackStore(FeedbackStore):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, feedback: Feedback) -> None:
        self._session.add(
            FeedbackModel(
                id=feedback.id,
                history_id=feedback.history_id,
                user_id=feedback.user_id,
                is_toxic=feedback.is_toxic,
                comment=feedback.comment,
                created_at=feedback.created_at,
            )
        )
        self._session.flush()
