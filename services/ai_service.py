
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.ai_repository import AiCreatorRepository, ModelRepository, AiSettingsRepository
from db.models import AiCreators, Models, AiSettings
from services.redis_service import RedisService
from services.logger import logger

class AiService:
    def __init__(self, session: AsyncSession):
        self.ai_creator_repo = AiCreatorRepository(session)
        self.model_repo = ModelRepository(session)
        self.settings_repo = AiSettingsRepository(session)
        self.redis_service = RedisService()

    async def get_selected_ai_creator(self) -> Optional[AiCreators]:
        """Получить выбранного AI провайдера"""
        return await self.ai_creator_repo.get_selected()

    async def get_selected_model(self) -> Optional[Models]:
        """Получить выбранную модель"""
        return await self.model_repo.get_selected()

    async def get_models_by_creator(self, creator_id: int) -> List[Models]:
        """Получить модели по ID провайдера"""
        return await self.model_repo.get_by_creator_id(creator_id)

    async def get_ai_settings(self) -> Optional[AiSettings]:
        """Получить настройки AI"""
        return await self.settings_repo.get_settings()

    async def update_prompt(self, prompt: str) -> bool:
        """Обновить системный промпт"""
        if len(prompt) > 4000:
            logger.warning("Prompt too long")
            return False
        
        success = await self.settings_repo.update_prompt(prompt)
        if success:
            await self.redis_service.save_prompt(prompt)
        return success

    async def update_temperature(self, temperature: float) -> bool:
        """Обновить температуру модели"""
        if not (0.0 <= temperature <= 2.0):
            logger.warning(f"Invalid temperature value: {temperature}")
            return False
        
        success = await self.settings_repo.update_temperature(temperature)
        if success:
            await self.redis_service.save_model_temperature(temperature)
        return success

    async def create_ai_creator(self, name: str, token: str, url: str) -> AiCreators:
        """Создать нового AI провайдера"""
        creator = await self.ai_creator_repo.create(
            name=name,
            token=token,
            url=url,
            selected=False
        )
        logger.info(f"Created AI creator: {name}")
        return creator

    async def select_ai_creator(self, creator_id: int) -> bool:
        """Выбрать AI провайдера"""
        # Сначала снимаем выделение со всех
        creators = await self.ai_creator_repo.get_all()
        for creator in creators:
            creator.selected = False
        
        # Выделяем нужного
        creator = await self.ai_creator_repo.get_by_id(creator_id)
        if creator:
            creator.selected = True
            await self.ai_creator_repo.session.commit()
            
            # Обновляем Redis
            await self.redis_service.save_openai_token(creator.token)
            await self.redis_service.save_selected_url(creator.url)
            return True
        return False

    async def select_model(self, model_id: int) -> bool:
        """Выбрать модель"""
        # Снимаем выделение со всех моделей
        models = await self.model_repo.get_all()
        for model in models:
            model.selected = False
        
        # Выделяем нужную
        model = await self.model_repo.get_by_id(model_id)
        if model:
            model.selected = True
            await self.model_repo.session.commit()
            
            # Обновляем Redis
            await self.redis_service.save_selected_ai_model(model.name)
            return True
        return False

    async def get_ai_configuration(self) -> Dict[str, Any]:
        """Получить полную конфигурацию AI"""
        creator = await self.get_selected_ai_creator()
        model = await self.get_selected_model()
        settings = await self.get_ai_settings()
        
        return {
            'creator': {
                'id': creator.id if creator else None,
                'name': creator.name if creator else None,
                'url': creator.url if creator else None,
                'token': creator.token if creator else None
            },
            'model': {
                'id': model.id if model else None,
                'name': model.name if model else None
            },
            'settings': {
                'temperature': settings.temperature if settings else None,
                'prompt': settings.prompt if settings else None
            }
        }
