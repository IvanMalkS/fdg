
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func

from db.models import DAMAQuestion, DAMACase
from repositories.base import BaseRepository

class QuestionRepository(BaseRepository[DAMAQuestion]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, DAMAQuestion)

    async def get_by_role_and_competence(self, role: str, competence: str) -> List[DAMAQuestion]:
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.dama_role_name == role,
                    self.model.dama_competence_name == competence
                )
            )
        )
        return list(result.scalars().all())

    async def get_random_question(self, role: str, competence: str) -> Optional[DAMAQuestion]:
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.dama_role_name == role,
                    self.model.dama_competence_name == competence
                )
            ).order_by(func.random()).limit(1)
        )
        return result.scalar_one_or_none()

class CaseRepository(BaseRepository[DAMACase]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, DAMACase)

    async def get_by_role_and_competence(self, role: str, competence: str) -> List[DAMACase]:
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.dama_role_name == role,
                    self.model.dama_competence_name == competence
                )
            )
        )
        return list(result.scalars().all())

    async def get_random_case(self, role: str, competence: str) -> Optional[DAMACase]:
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.dama_role_name == role,
                    self.model.dama_competence_name == competence
                )
            ).order_by(func.random()).limit(1)
        )
        return result.scalar_one_or_none()
