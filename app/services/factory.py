from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from repositories.uow import UnitOfWork
from services.analytics import AnalyticsService
from services.category import CategoryService
from services.groq_service import GroqService
from services.transaction import TransactionService
from services.user import UserService


class ServiceFactory:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._groq = GroqService(api_key=config.groq_api_key.get_secret_value())

    def _uow(self) -> UnitOfWork:
        return UnitOfWork(self.session)

    def user_service(self) -> UserService:
        return UserService(self._uow())

    def category_service(self) -> CategoryService:
        return CategoryService(self._uow())

    def analytics_service(self) -> AnalyticsService:
        return AnalyticsService(self._uow())

    def transaction_service(self) -> TransactionService:
        return TransactionService(
            uow=self._uow(),
            category_service=self.category_service(),
            groq_service=self._groq,
        )
