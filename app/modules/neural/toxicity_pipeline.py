from __future__ import annotations

from uuid import UUID

from app.ml_models.outcomes import ToxicityPrediction
from app.ml_models.service import MlModelsService


def toxicity_predict(text: str, *, model_id: UUID) -> ToxicityPrediction:
    return MlModelsService.predict(text, model_id=model_id)
