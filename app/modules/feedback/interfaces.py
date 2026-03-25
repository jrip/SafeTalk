from __future__ import annotations

from typing import Protocol

from app.modules.feedback.types import CreateFeedbackInput, FeedbackView


class FeedbackPublicService(Protocol):
    def create_feedback(self, payload: CreateFeedbackInput) -> FeedbackView:
        """Внешний метод: отправить фидбек на анализ."""


class FeedbackInternalService(FeedbackPublicService, Protocol):
    """Внутренний интерфейс модуля Feedback."""

    pass
