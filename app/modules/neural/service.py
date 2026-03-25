from __future__ import annotations

from app.modules.neural.interfaces import NeuralInternalService
from app.modules.neural.types import PredictionView, RunPredictionInput


class NeuralService(NeuralInternalService):
    def __init__(self) -> None:
        """Сервис Neural без реализации хранения и ML-раннера."""

    def get_toxicity(self, payload: RunPredictionInput) -> PredictionView:
        """Внешний/внутренний метод: получить токсичность диалога."""
        raise NotImplementedError("Neural processing is mocked at this stage")
