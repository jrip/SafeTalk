from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core import InsufficientBalanceError, ValidationError
from app.ml_models.constants import ML_MODEL_RUBERT_TOXICITY_ID, ML_MODEL_TOXIC_LITE_ID
from app.ml_models.outcomes import ToxicityPrediction
from app.modules.neural.models import MlPredictionTaskModel
from app.modules.neural.types import RunPredictionInput, TaskStatus


def test_create_prediction_task_completes_and_persists_side_effects(
    app_container,
    registered_user_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registered_user = registered_user_factory()
    app_container.billing.add_tokens(registered_user.user.id, Decimal("20.00"))
    input_text = "toxic test"

    monkeypatch.setattr(
        "app.modules.neural.service.toxicity_predict",
        lambda text, model_id: ToxicityPrediction(
            summary=f"processed:{text}",
            is_toxic=True,
            toxicity_probability=0.875,
            breakdown={"toxicity": 0.875},
        ),
    )

    task = app_container.neural.create_prediction_task(
        RunPredictionInput(
            user_id=registered_user.user.id,
            model_id=ML_MODEL_RUBERT_TOXICITY_ID,
            text=input_text,
        )
    )

    assert task.status is TaskStatus.COMPLETED
    assert task.charged_tokens == Decimal(str(len(input_text)))
    assert task.result_summary == f"processed:{input_text}"
    assert task.is_toxic is True

    balance = app_container.billing.get_count_tokens(registered_user.user.id)
    assert balance.token_count == Decimal("10.00")

    persisted_task = app_container.neural.get_task_for_user(registered_user.user.id, task.task_id)
    assert persisted_task.status is TaskStatus.COMPLETED
    assert persisted_task.result_summary == f"processed:{input_text}"
    assert persisted_task.toxicity_probability == Decimal("0.875")

    history = app_container.history.get_api_history(registered_user.user.id)
    assert len(history) == 1
    assert history[0].request == input_text
    assert history[0].result == f"processed:{input_text}"
    assert history[0].ml_task_id == task.task_id
    assert history[0].tokens_charged == Decimal(str(len(input_text)))

    ledger = app_container.billing.get_ledger_history(registered_user.user.id)
    assert [entry.kind for entry in ledger] == ["debit", "credit"]
    assert ledger[0].task_id == task.task_id
    assert ledger[0].amount == Decimal(str(len(input_text)))


def test_create_prediction_task_rejects_when_balance_is_insufficient(
    app_container,
    registered_user_factory,
    session,
) -> None:
    registered_user = registered_user_factory()

    with pytest.raises(InsufficientBalanceError, match="Недостаточно кредитов"):
        app_container.neural.create_prediction_task(
            RunPredictionInput(
                user_id=registered_user.user.id,
                model_id=ML_MODEL_RUBERT_TOXICITY_ID,
                text="need credits",
            )
        )

    assert app_container.history.get_api_history(registered_user.user.id) == []
    assert app_container.billing.get_ledger_history(registered_user.user.id) == []
    task_count = session.scalar(select(func.count()).select_from(MlPredictionTaskModel))
    assert task_count == 0


def test_create_prediction_task_rolls_back_on_inference_error_without_charge(
    app_container,
    registered_user_factory,
    monkeypatch: pytest.MonkeyPatch,
    session,
) -> None:
    registered_user = registered_user_factory()
    app_container.billing.add_tokens(registered_user.user.id, Decimal("30.00"))

    monkeypatch.setattr(
        "app.modules.neural.service.toxicity_predict",
        lambda text, model_id: (_ for _ in ()).throw(RuntimeError("model exploded")),
    )

    with pytest.raises(RuntimeError, match="model exploded"):
        app_container.neural.create_prediction_task(
            RunPredictionInput(
                user_id=registered_user.user.id,
                model_id=ML_MODEL_RUBERT_TOXICITY_ID,
                text="safe rollback",
            )
        )

    session.rollback()

    balance = app_container.billing.get_count_tokens(registered_user.user.id)
    ledger = app_container.billing.get_ledger_history(registered_user.user.id)
    history = app_container.history.get_api_history(registered_user.user.id)
    tasks = session.scalars(select(MlPredictionTaskModel)).all()

    assert balance.token_count == Decimal("30.00")
    assert len(ledger) == 1
    assert ledger[0].kind == "credit"
    assert history == []
    assert tasks == []


def test_create_prediction_task_rejects_blank_text(app_container, registered_user_factory) -> None:
    registered_user = registered_user_factory()

    with pytest.raises(ValidationError, match="Task text cannot be empty"):
        app_container.neural.create_prediction_task(
            RunPredictionInput(
                user_id=registered_user.user.id,
                model_id=ML_MODEL_RUBERT_TOXICITY_ID,
                text="   ",
            )
        )


def test_create_prediction_task_rejects_unsupported_lite_model(app_container, registered_user_factory) -> None:
    registered_user = registered_user_factory()
    app_container.billing.add_tokens(registered_user.user.id, Decimal("30.00"))

    with pytest.raises(ValidationError, match="Toxicity lite"):
        app_container.neural.create_prediction_task(
            RunPredictionInput(
                user_id=registered_user.user.id,
                model_id=ML_MODEL_TOXIC_LITE_ID,
                text="lite is unsupported",
            )
        )
