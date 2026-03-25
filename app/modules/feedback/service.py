from __future__ import annotations

from app.modules.feedback.interfaces import FeedbackInternalService
from app.modules.feedback.types import CreateFeedbackInput, FeedbackView


class FeedbackService(FeedbackInternalService):
    def __init__(self) -> None:
        """Сервис Feedback без реализации хранения (на этапе проектирования)."""

    def create_feedback(self, payload: CreateFeedbackInput) -> FeedbackView:
        """Внешний метод: сохранить пользовательский фидбек по анализу."""
        raise NotImplementedError("Feedback persistence is mocked at this stage")
