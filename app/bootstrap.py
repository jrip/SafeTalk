from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.billing.controller import BillingController
from app.modules.billing.service import BillingService
from app.modules.billing.storage_sqlalchemy import SqlAlchemyBalanceStore
from app.modules.feedback.controller import FeedbackController
from app.modules.feedback.service import FeedbackService
from app.modules.feedback.storage_sqlalchemy import SqlAlchemyFeedbackStore
from app.modules.history.controller import HistoryController
from app.modules.history.service import HistoryService
from app.modules.history.storage_sqlalchemy import SqlAlchemyHistoryStore
from app.modules.neural.controller import NeuralController
from app.modules.neural.service import NeuralService
from app.modules.neural.storage_sqlalchemy import SqlAlchemyMlModelCatalog, SqlAlchemyMlTaskStore
from app.modules.users.controller import UsersController
from app.modules.users.service import UserService
from app.modules.users.storage_sqlalchemy import SqlAlchemyUserStore


@dataclass
class AppContainer:
    users: UsersController
    billing: BillingController
    history: HistoryController
    neural: NeuralController
    feedback: FeedbackController


def build_app_container(session: Session) -> AppContainer:
    user_store = SqlAlchemyUserStore(session)
    balance_store = SqlAlchemyBalanceStore(session)
    history_store = SqlAlchemyHistoryStore(session)
    feedback_store = SqlAlchemyFeedbackStore(session)

    user_service = UserService(user_store, balance_store, session)
    billing_service = BillingService(user_service, balance_store, session)
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
        users=UsersController(user_service),
        billing=BillingController(billing_service),
        history=HistoryController(history_service),
        neural=NeuralController(neural_service),
        feedback=FeedbackController(feedback_service),
    )
