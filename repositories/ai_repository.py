
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from db.models import AiCreators, Models, AiSettings
from repositories.base import BaseRepository

class AiCreatorRepository(BaseRepository[AiCreators]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AiCreators)

    async def get_selected(self) -> Optional[AiCreators]:
        result = await self.session.execute(
            select(self.model).where(self.model.selected == True)
        )
        return result.scalar_one_or_none()

class ModelRepository(BaseRepository[Models]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Models)

    async def get_by_creator_id(self, creator_id: int) -> List[Models]:
        result = await self.session.execute(
            select(self.model).where(self.model.ai_creator_id == creator_id)
        )
        return list(result.scalars().all())

    async def get_selected(self) -> Optional[Models]:
        result = await self.session.execute(
            select(self.model).where(self.model.selected == True)
        )
        return result.scalar_one_or_none()

class AiSettingsRepository(BaseRepository[AiSettings]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AiSettings)

    async def get_settings(self) -> Optional[AiSettings]:
        result = await self.session.execute(select(self.model))
        return result.scalar_one_or_none()

    async def update_prompt(self, prompt: str) -> bool:
        settings = await self.get_settings()
        if settings:
            settings.prompt = prompt
            await self.session.commit()
            return True
        return False

    async def update_temperature(self, temperature: float) -> bool:
        settings = await self.get_settings()
        if settings:
            settings.temperature = temperature
            await self.session.commit()
            return True
        return False
