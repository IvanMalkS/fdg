
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from db.models import User, TestResults
from db.enums import UserRole
from repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(self.model).where(self.model.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_role(self, role: UserRole) -> List[User]:
        result = await self.session.execute(
            select(self.model).where(self.model.role == role)
        )
        return list(result.scalars().all())

    async def get_banned_users(self) -> List[User]:
        result = await self.session.execute(
            select(self.model).where(self.model.is_banned == True)
        )
        return list(result.scalars().all())

    async def ban_user(self, telegram_id: int) -> bool:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.is_banned = True
            await self.session.commit()
            return True
        return False

    async def unban_user(self, telegram_id: int) -> bool:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.is_banned = False
            await self.session.commit()
            return True
        return False

    async def get_paginated(self, page: int, page_size: int = 10) -> tuple[List[User], int]:
        offset = page * page_size
        
        # Get users for current page
        result = await self.session.execute(
            select(self.model)
            .offset(offset)
            .limit(page_size)
        )
        users = list(result.scalars().all())
        
        # Get total count
        count_result = await self.session.execute(
            select(self.model.id)
        )
        total_count = len(list(count_result.scalars().all()))
        
        return users, total_count
