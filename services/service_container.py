
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from services.user_service import UserService
from services.test_management_service import TestManagementService
from services.ai_service import AiService
from db.database import get_async_session

class ServiceContainer:
    """Контейнер для всех сервисов"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._user_service = None
        self._test_service = None
        self._ai_service = None

    @property
    def user_service(self) -> UserService:
        if self._user_service is None:
            self._user_service = UserService(self.session)
        return self._user_service

    @property
    def test_service(self) -> TestManagementService:
        if self._test_service is None:
            self._test_service = TestManagementService(self.session)
        return self._test_service

    @property
    def ai_service(self) -> AiService:
        if self._ai_service is None:
            self._ai_service = AiService(self.session)
        return self._ai_service

@asynccontextmanager
async def get_service_container():
    """Контекстный менеджер для получения контейнера сервисов"""
    async with get_async_session() as session:
        yield ServiceContainer(session)
