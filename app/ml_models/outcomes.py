from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToxicityPrediction:
    summary: str
    is_toxic: bool
    toxicity_probability: float
    breakdown: dict[str, float]
