from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.ml_models.outcomes import ToxicityPrediction

logger = logging.getLogger(__name__)

HF_MODEL_ID = "cointegrated/rubert-tiny-toxicity"

SAFE_NON_TOXIC_MIN = 0.5
SAFE_DANGEROUS_MAX = 0.5

_LOCAL_DIR = Path(__file__).resolve().parent


def _normalize_id2label(raw: Any, num_logits: int) -> dict[int, str]:
    if not isinstance(raw, dict) or not raw:
        return {i: str(i) for i in range(num_logits)}
    out: dict[int, str] = {}
    for k, v in raw.items():
        idx = int(k) if isinstance(k, str) and k.isdigit() else int(k)
        out[idx] = str(v)
    return out


def _pretrained_source() -> str:
    if (_LOCAL_DIR / "config.json").is_file():
        return str(_LOCAL_DIR)
    return HF_MODEL_ID


@lru_cache(maxsize=1)
def _tokenizer_and_model() -> tuple[Any, Any]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    src = _pretrained_source()
    logger.info("load weights: %s", src)
    tokenizer = AutoTokenizer.from_pretrained(src)
    model = AutoModelForSequenceClassification.from_pretrained(src)
    model.eval()
    model.to("cpu")
    return tokenizer, model


def multilabel_scores(text: str, *, max_length: int = 384) -> dict[str, float]:
    import torch

    raw = text.strip() if text.strip() else " "
    tokenizer, model = _tokenizer_and_model()
    inputs = tokenizer(raw, return_tensors="pt", truncation=True, max_length=max_length)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.sigmoid(logits[0]).tolist()
    id2label = _normalize_id2label(model.config.id2label, len(probs))
    out: dict[str, float] = {}
    for i, p in enumerate(probs):
        label = id2label.get(i, str(i))
        out[str(label)] = float(p)
    return out


def is_conditionally_safe(scores: dict[str, float]) -> bool:
    nt = scores.get("non-toxic")
    dng = scores.get("dangerous")
    if nt is None or dng is None:
        return False
    return nt >= SAFE_NON_TOXIC_MIN and dng <= SAFE_DANGEROUS_MAX


def _summary_line_from_scores(scores: dict[str, float]) -> str:
    order = ("non-toxic", "insult", "obscenity", "threat", "dangerous")
    parts = []
    for key in order:
        if key in scores:
            parts.append(f"{key}={scores[key]:.4f}")
    for key, v in sorted(scores.items()):
        if key not in order:
            parts.append(f"{key}={v:.4f}")
    safe = is_conditionally_safe(scores)
    joined = "; ".join(parts)
    return (
        f"rubert_tiny_multilabel: {joined}; "
        f"conditionally_safe={'yes' if safe else 'no'}; "
        f"rule: non-toxic>={SAFE_NON_TOXIC_MIN} and dangerous<={SAFE_DANGEROUS_MAX}"
    )


def format_rubert_toxicity_summary(text: str, *, max_length: int = 384) -> str:
    return _summary_line_from_scores(multilabel_scores(text, max_length=max_length))


def rubert_toxicity_prediction(text: str, *, max_length: int) -> ToxicityPrediction:
    scores = multilabel_scores(text, max_length=max_length)
    summary = _summary_line_from_scores(scores)
    is_toxic = not is_conditionally_safe(scores)
    bad_keys = ("insult", "obscenity", "threat", "dangerous")
    p_max = max((float(scores.get(k, 0.0)) for k in bad_keys), default=0.0)
    return ToxicityPrediction(
        summary=summary,
        is_toxic=is_toxic,
        toxicity_probability=min(1.0, p_max),
        breakdown=dict(scores),
    )
