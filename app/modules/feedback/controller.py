from __future__ import annotations

from app.modules.feedback.interfaces import FeedbackPublicService
from app.modules.feedback.types import CreateFeedbackInput, FeedbackView


class FeedbackController:
    def __init__(self, service: FeedbackPublicService) -> None:
        self._service = service

    def give_feedback(self, payload: CreateFeedbackInput) -> FeedbackView:
        """Отправить фидбек на результат анализа."""
        return self._service.create_feedback(payload)
