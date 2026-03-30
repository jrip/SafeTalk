from __future__ import annotations

from dataclasses import dataclass

from app.modules.billing.controller import BillingController
from app.modules.billing.service import BillingService
from app.modules.feedback.controller import FeedbackController
from app.modules.feedback.service import FeedbackService
from app.modules.history.controller import HistoryController
from app.modules.history.service import HistoryService
from app.modules.neural.controller import NeuralController
from app.modules.neural.service import NeuralService
from app.modules.users.controller import UsersController
from app.modules.users.service import UserService


@dataclass
class AppContainer:
    users: UsersController
    billing: BillingController
    history: HistoryController
    neural: NeuralController
    feedback: FeedbackController


def build_app_container() -> AppContainer:
    user_service = UserService()
    billing_service = BillingService()
    history_service = HistoryService()
    feedback_service = FeedbackService()
    neural_service = NeuralService()

    return AppContainer(
        users=UsersController(user_service),
        billing=BillingController(billing_service),
        history=HistoryController(history_service),
        neural=NeuralController(neural_service),
        feedback=FeedbackController(feedback_service),
    )
