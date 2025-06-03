
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import random

from repositories.question_repository import QuestionRepository, CaseRepository
from db.models import DAMAQuestion, DAMACase
from services.logger import logger

class TestManagementService:
    def __init__(self, session: AsyncSession):
        self.question_repo = QuestionRepository(session)
        self.case_repo = CaseRepository(session)

    async def get_random_question(self, role: str, competence: str) -> Optional[DAMAQuestion]:
        """Получить случайный вопрос для роли и компетенции"""
        return await self.question_repo.get_random_question(role, competence)

    async def get_random_case(self, role: str, competence: str) -> Optional[DAMACase]:
        """Получить случайный кейс для роли и компетенции"""
        return await self.case_repo.get_random_case(role, competence)

    async def get_questions_for_role_competence(self, role: str, competence: str) -> List[DAMAQuestion]:
        """Получить все вопросы для роли и компетенции"""
        return await self.question_repo.get_by_role_and_competence(role, competence)

    async def get_cases_for_role_competence(self, role: str, competence: str) -> List[DAMACase]:
        """Получить все кейсы для роли и компетенции"""
        return await self.case_repo.get_by_role_and_competence(role, competence)

    async def generate_test_sequence(self, role: str, competence: str, 
                                   questions_count: int = 5, cases_count: int = 2) -> Dict[str, List]:
        """Сгенерировать последовательность вопросов и кейсов для теста"""
        questions = await self.get_questions_for_role_competence(role, competence)
        cases = await self.get_cases_for_role_competence(role, competence)

        if len(questions) < questions_count:
            logger.warning(f"Not enough questions for {role}/{competence}. Available: {len(questions)}, Required: {questions_count}")
            questions_count = len(questions)

        if len(cases) < cases_count:
            logger.warning(f"Not enough cases for {role}/{competence}. Available: {len(cases)}, Required: {cases_count}")
            cases_count = len(cases)

        selected_questions = random.sample(questions, min(questions_count, len(questions)))
        selected_cases = random.sample(cases, min(cases_count, len(cases)))

        return {
            'questions': selected_questions,
            'cases': selected_cases,
            'total_items': len(selected_questions) + len(selected_cases)
        }

    async def validate_role_competence(self, role: str, competence: str) -> bool:
        """Проверить, есть ли вопросы/кейсы для данной роли и компетенции"""
        questions = await self.get_questions_for_role_competence(role, competence)
        cases = await self.get_cases_for_role_competence(role, competence)
        return len(questions) > 0 or len(cases) > 0
