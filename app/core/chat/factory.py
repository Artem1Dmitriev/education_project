# app/core/chat/factory.py
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chat import ChatService
from app.core.chat.prompt import PromptService
from app.core.chat.calculation import TokenizerService
from app.core.chat.calculation import CostCalculator
from app.core.providers.service import ProviderService
from app.core.validator import ChatValidator
from app.database.repositories import get_repository

logger = logging.getLogger(__name__)

class ChatServiceFactory:
    """Фабрика для создания ChatService с его инфраструктурой"""

    def __init__(self):
        # self._cached_services = {}
        self._prompt_service = PromptService()
        self._tokenizer = TokenizerService()
        self._cost_calculator = CostCalculator()

    def create_service(
            self,
            provider_service: ProviderService,
            session: AsyncSession
    ) -> ChatService:
        """
        Создать экземпляр ChatService с его инфраструктурой

        Args:
            provider_service: Сервис провайдеров
            session: Сессия БД для этого запроса

        Returns:
            ChatService
        """
        request_repo = get_repository("request", session)
        user_repo = get_repository("user", session)
        self._validator = ChatValidator(request_repo,user_repo)

        return ChatService(
            provider_service=provider_service,
            request_repo=request_repo,
            user_repo=user_repo,
            prompt_service=self._prompt_service,
            tokenizer=self._tokenizer,
            cost_calculator=self._cost_calculator,
            validator=self._validator,
            db_session=session
        )