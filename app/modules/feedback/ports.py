from __future__ import annotations

from typing import Protocol

from app.modules.feedback.entities import Feedback


class FeedbackStore(Protocol):
    def add(self, feedback: Feedback) -> None: ...
