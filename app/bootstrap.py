from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.modules.neural.service import NeuralService

from app.modules.billing.service import BillingService
from app.modules.billing.storage_sqlalchemy import SqlAlchemyBalanceStore
from app.modules.feedback.service import FeedbackService
from app.modules.feedback.storage_sqlalchemy import SqlAlchemyFeedbackStore
from app.modules.history.service import HistoryService
from app.modules.history.storage_sqlalchemy import SqlAlchemyHistoryStore
from app.modules.users.service import UserService
from app.modules.users.storage_sqlalchemy import SqlAlchemyUserStore


@dataclass
class AppContainer:
    users: UserService
    billing: BillingService
    history: HistoryService
    neural: NeuralService
    feedback: FeedbackService


def build_user_and_billing(session: Session) -> tuple[UserService, BillingService]:
    user_store = SqlAlchemyUserStore(session)
    balance_store = SqlAlchemyBalanceStore(session)
    user_service = UserService(user_store, balance_store, session)
    billing_service = BillingService(user_service, balance_store, session)
    return user_service, billing_service


def build_app_container(session: Session) -> AppContainer:
    from app.modules.neural.service import NeuralService
    from app.modules.neural.storage_sqlalchemy import SqlAlchemyMlModelCatalog, SqlAlchemyMlTaskStore

    user_service, billing_service = build_user_and_billing(session)
    history_store = SqlAlchemyHistoryStore(session)
    feedback_store = SqlAlchemyFeedbackStore(session)

    history_service = HistoryService(history_store, session)
    feedback_service = FeedbackService(feedback_store, history_store, session)

    ml_catalog = SqlAlchemyMlModelCatalog(session)
    ml_task_store = SqlAlchemyMlTaskStore(session)
    neural_service = NeuralService(
        session,
        billing_service,
        ml_catalog,
        history_service,
        ml_task_store,
    )

    return AppContainer(
        users=user_service,
        billing=billing_service,
        history=history_service,
        neural=neural_service,
        feedback=feedback_service,
    )
