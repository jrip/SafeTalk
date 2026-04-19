from __future__ import annotations

import logging
from uuid import UUID

from app.core.settings import get_settings
from app.ml_models.constants import ML_MODEL_RUBERT_TOXICITY_ID
from app.ml_models.outcomes import ToxicityPrediction

logger = logging.getLogger(__name__)


class MlModelsService:
    _RUBERT_MODEL_ID = ML_MODEL_RUBERT_TOXICITY_ID

    @classmethod
    def predict(cls, text: str, *, model_id: UUID) -> ToxicityPrediction:
        stripped = (text or "").strip()
        if not stripped:
            raise ValueError("empty text")
        if model_id == cls._RUBERT_MODEL_ID:
            return cls._run_rubert_tiny_toxicity(stripped)
        raise ValueError(f"no handler for model_id={model_id}")

    @classmethod
    def supports_local_engine(cls, model_id: UUID) -> bool:
        return model_id == cls._RUBERT_MODEL_ID

    @classmethod
    def _run_rubert_tiny_toxicity(cls, text: str) -> ToxicityPrediction:
        settings = get_settings()
        if settings.ml_toxicity_backend != "rubert":
            return ToxicityPrediction(
                summary=(
                    "toxicity: stub; "
                    f"ML_TOXICITY_BACKEND={settings.ml_toxicity_backend!r}; "
                    f"chars={len(text)}"
                ),
                is_toxic=False,
                toxicity_probability=0.0,
                breakdown={"stub": 0.0},
            )
        try:
            from app.ml_models.rubert_tiny_toxicity.inference import rubert_toxicity_prediction

            return rubert_toxicity_prediction(text, max_length=settings.ml_toxicity_max_length)
        except ImportError:
            logger.exception("missing torch/transformers")
            raise RuntimeError(
                "install torch and transformers (see app/requirements.txt)",
            ) from None
