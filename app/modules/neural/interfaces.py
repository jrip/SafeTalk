from __future__ import annotations

from typing import Protocol
from app.modules.neural.types import PredictionView, RunPredictionInput


class NeuralPublicService(Protocol):
    def get_toxicity(self, payload: RunPredictionInput) -> PredictionView:
        """Внешний метод: получить токсичность диалога."""


class NeuralInternalService(NeuralPublicService, Protocol):
    pass
