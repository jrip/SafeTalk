from __future__ import annotations

from app.modules.neural.interfaces import NeuralPublicService
from app.modules.neural.types import PredictionView, RunPredictionInput


class NeuralController:
    def __init__(self, service: NeuralPublicService) -> None:
        self._service = service

    def get_toxicity(self, payload: RunPredictionInput) -> PredictionView:
        """Получить токсичность одного диалога."""
        return self._service.get_toxicity(payload)
