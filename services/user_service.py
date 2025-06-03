
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.user_repository import UserRepository
from db.models import User
from db.enums import UserRole
from services.logger import logger

class UserService:
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)

    async def get_or_create_user(self, telegram_id: int, name: str, username: str = None) -> User:
        """Получить пользователя или создать нового"""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            user = await self.user_repo.create(
                telegram_id=telegram_id,
                name=name,
                username=username,
                role=UserRole.USER
            )
            logger.info(f"Created new user: {name} (ID: {telegram_id})")
        return user

    async def is_admin(self, telegram_id: int) -> bool:
        """Проверить, является ли пользователь администратором"""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        return user and user.role == UserRole.ADMIN

    async def is_banned(self, telegram_id: int) -> bool:
        """Проверить, забанен ли пользователь"""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        return user and user.is_banned

    async def ban_user(self, telegram_id: int) -> bool:
        """Забанить пользователя"""
        return await self.user_repo.ban_user(telegram_id)

    async def unban_user(self, telegram_id: int) -> bool:
        """Разбанить пользователя"""
        return await self.user_repo.unban_user(telegram_id)

    async def get_users_paginated(self, page: int, page_size: int = 10) -> Dict[str, Any]:
        """Получить пользователей с пагинацией"""
        users, total_count = await self.user_repo.get_paginated(page, page_size)
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            'users': users,
            'current_page': page,
            'total_pages': total_pages,
            'total_count': total_count,
            'has_next': page < total_pages - 1,
            'has_prev': page > 0
        }

    async def promote_to_admin(self, telegram_id: int) -> bool:
        """Сделать пользователя администратором"""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user:
            user.role = UserRole.ADMIN
            await self.user_repo.session.commit()
            return True
        return False
