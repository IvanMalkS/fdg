import json
from typing import Dict, List, Optional

from numpy.f2py.auxfuncs import throw_error
from redis.asyncio import Redis
from sqlalchemy import false

from config import Config
from sqlalchemy.future import select

from db.database import get_async_session, get_selected_ai_creator
from db.models import Models, AiSettings
from services.logger import logger


class RedisService:

    def __init__(self):
        self.redis_client = Redis(host=Config.REDIS_HOST,
                                  port=Config.REDIS_PORT,
                                  db=0,
                                  password=Config.REDIS_USER_PASSWORD,
                                  username=Config.REDIS_USER,
                                  decode_responses=False)

    async def save_user_metadata(self, user_id: int, metadata: Dict) -> bool:
        try:
            key = f"user:{user_id}:metadata"
            result = await self.redis_client.set(key, json.dumps(metadata))
            await self.redis_client.expire(key, Config.REDIS_EXPIRE_TIME)
            return bool(result)
        except Exception as e:
            logger.error(f"Error saving user metadata: {e}")
            return False

    async def get_user_metadata(self, user_id: int) -> Dict:
        try:
            key = f"user:{user_id}:metadata"
            data = await self.redis_client.get(key)
            return json.loads(data) if data else {}
        except json.JSONDecodeError:
            return {}
        except Exception as e:
            logger.error(f"Error getting user metadata: {e}")
            return {}

    async def save_answers_to_redis(self, user_id: int, question_id: int,
                                    data: Dict) -> bool:
        try:
            key = f"user:{user_id}:question:{question_id}"
            result = await self.redis_client.set(key, json.dumps(data))
            await self.redis_client.expire(key, Config.REDIS_EXPIRE_TIME)
            return bool(result)
        except Exception as e:
            logger.error(f"Error saving answer: {e}")
            return False

    async def get_user_answers(self, user_id: int) -> List[Dict]:
        try:
            pattern = f"user:{user_id}:question:*"
            keys = [
                key async for key in self.redis_client.scan_iter(match=pattern)
            ]

            answers = []
            for key in keys:
                data = await self.redis_client.get(key)
                if data:
                    try:
                        answers.append(json.loads(data))
                    except json.JSONDecodeError:
                        continue
            return answers
        except Exception as e:
            logger.error(f"Error getting user answers: {e}")
            return []

    async def clear_user_answers(self, user_id: int) -> int:
        try:
            pattern = f"user:{user_id}:question:*"
            keys = [
                key async for key in self.redis_client.scan_iter(match=pattern)
            ]
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing user answers: {e}")
            return 0

    async def clear_user_metadata(self, user_id: int) -> int:
        try:
            key = f"user:{user_id}:metadata"
            return await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Error clearing user metadata: {e}")
            return 0

    async def save_openai_token(self, token: str) -> bool:
        try:
            key = "openai:token"
            result = await self.redis_client.set(key, token)
            return bool(result)
        except Exception as e:
            logger.error(f"Error saving OpenAI token in redis: {e}")
            return False

    async def load_openai_token(self) -> Optional[str]:
        try:
            key = "openai:token"
            redis_token = await self.redis_client.get(key)

            if redis_token:
                return redis_token.decode('utf-8') if isinstance(
                    redis_token, bytes) else redis_token

            ai_creator = await get_selected_ai_creator()
            if ai_creator:
                token = str(ai_creator.token)
                await self.save_openai_token(token)
                return token

            return None

        except Exception as e:
            logger.error(f"Error loading OpenAI token from redis: {e}")
            return None

    async def save_selected_ai_model(self, model_name: str) -> bool:
        try:
            result_name = await self.redis_client.set("openai:model",
                                                      model_name)
            return result_name
        except Exception as e:
            logger.error(f"Error saving model in redis: {e}")
            return False

    async def load_selected_ai_model(self) -> Optional[str]:
        try:
            key = "openai:model"
            redis_model = await self.redis_client.get(key)

            if redis_model:
                return redis_model.decode('utf-8') if isinstance(
                    redis_model, bytes) else redis_model

            async with get_async_session() as session:
                result = await session.execute(
                    select(Models).where(Models.selected == True))
                selected_model = result.scalar_one_or_none()
                if selected_model:
                    model_name = str(selected_model.name)
                    await self.save_selected_ai_model(model_name)
                    return model_name

            return None
        except Exception as e:
            logger.error(f"Error loading model from redis: {e}")
            return None

    async def save_selected_url(self, url: str) -> bool:
        try:
            key = "openai:url"
            result = await self.redis_client.set(key, url)
            return bool(result)
        except Exception as e:
            logger.error(f"Error saving url in redis: {e}")
            return False

    async def load_selected_url(self):
        try:
            key = "openai:url"
            redis_url = await self.redis_client.get(key)
            if redis_url:
                return redis_url.decode('utf-8') if isinstance(
                    redis_url, bytes) else redis_url

            ai_creator = await get_selected_ai_creator()
            if ai_creator:
                url = str(ai_creator.url)
                await self.save_selected_url(url)
                return url
            return None
        except Exception as e:
            logger.error(f"Error loading url from redis: {e}")

    async def save_model_temperature(self, temperature: float) -> bool:
        try:
            result = await self.redis_client.set("openai:model_temperature",
                                                 str(temperature))
            return bool(result)
        except Exception as e:
            logger.error(f"Error saving model temperature in redis: {e}")
            return False

    async def load_model_temperature(self) -> Optional[float]:
        try:
            redis_temp = await self.redis_client.get("openai:model_temperature"
                                                     )
            if redis_temp:
                try:
                    return float(redis_temp.decode('utf-8')) if isinstance(
                        redis_temp, bytes) else float(redis_temp)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid temperature value in Redis: {e}")

            async with get_async_session() as session:
                result = await session.execute(select(AiSettings.temperature))
                temp_value = result.scalar_one_or_none()

                if temp_value is not None:
                    try:
                        temperature = float(temp_value)
                        await self.save_model_temperature(temperature)
                        return temperature
                    except (ValueError, TypeError) as e:
                        logger.error(f"Invalid temperature value in DB: {e}")

            return None
        except Exception as e:
            logger.error(f"Error loading model temperature: {e}")
            return None

    async def save_prompt(self, prompt: str) -> bool:
        try:
            result = await self.redis_client.set("prompt", prompt)
            return bool(result)
        except Exception as e:
            logger.error(f"Error saving prompt in redis: {e}")
            return False

    async def load_prompt(self) -> Optional[str]:
        try:
            redis_temp = await self.redis_client.get("prompt")
            if redis_temp:
                return str(redis_temp.decode('utf-8')) if isinstance(
                    redis_temp, bytes) else str(redis_temp)

            async with get_async_session() as session:
                result = await session.execute(select(AiSettings))
                ai_settings = result.scalar_one_or_none()
                if ai_settings:
                    prompt = str(ai_settings.prompt)
                    await self.save_prompt(prompt)
                    return prompt

            return None
        except Exception as e:
            logger.error(f"Error loading prompt from redis: {e}")
            return None


    async def save_analytics(self, user_id: int,data: Dict, question_id: int)\
            -> Optional[bool]:
        try:
            model = await self.load_selected_ai_model()
            if not model:
                throw_error('Model not found')

            key = f"user:{user_id}:question:analytics:{question_id}"
            result = await self.redis_client.set(key, json.dumps(data))
            await self.redis_client.expire(key, Config.REDIS_EXPIRE_TIME)
            return bool(result)
        except Exception as e:
            logger.error(f"Error saving answer: {e}")
            return False

    async def load_analytics(self, user_id: int) -> List[Dict]:
        try:
            pattern = f"user:{user_id}:question:analytics:*"
            keys = [
                key async for key in self.redis_client.scan_iter(match=pattern)
            ]

            answers = []
            for key in keys:
                data = await self.redis_client.get(key)
                if data:
                    try:
                        answers.append(json.loads(data))
                    except json.JSONDecodeError:
                        continue
            return answers
        except Exception as e:
            logger.error(f"Error getting user answers: {e}")
            return []
