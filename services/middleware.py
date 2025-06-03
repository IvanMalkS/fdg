
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from sqlalchemy import select
from db.database import get_async_session
from db.models import User
from db.enums import UserRole
from services.logger import logger


class BanCheckMiddleware(BaseMiddleware):
    """Middleware для проверки забаненных пользователей"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            
            # Пропускаем команду /start для забаненных пользователей
            # чтобы они могли получить уведомление о бане
            if event.text and event.text.startswith('/start'):
                return await handler(event, data)
            
            if await self.is_user_banned(user_id):
                await event.answer("Вы заблокированы и не можете использовать бота.")
                return
        
        return await handler(event, data)
    
    async def is_user_banned(self, user_id: int) -> bool:
        """Проверяет, забанен ли пользователь"""
        try:
            async with get_async_session() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalars().first()
                return user and str(user.role) == UserRole.BANNED
        except Exception as e:
            logger.error(f"Error checking user ban status: {e}")
            return False
