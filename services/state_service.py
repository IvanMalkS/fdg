from typing import Optional, Dict, Any
import json
from aiogram.fsm.state import State
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from config import Config
from services.logger import logger
from datetime import datetime


class RedisStateStorage:

    def __init__(self):
        self.redis = Redis(host=Config.REDIS_HOST,
                           port=Config.REDIS_PORT,
                           db=0,
                           password=Config.REDIS_USER_PASSWORD,
                           username=Config.REDIS_USER,
                           decode_responses=False)
        self.storage = RedisStorage(redis=self.redis)

    def _serialize_sqlalchemy_obj(self, obj):
        if obj is None:
            return None

        if isinstance(obj, list):
            return [self._serialize_sqlalchemy_obj(item) for item in obj]

        if isinstance(obj, dict):
            return {
                k: self._serialize_sqlalchemy_obj(v)
                for k, v in obj.items()
            }

        if isinstance(obj, datetime):
            return obj.isoformat()

        if hasattr(obj, '__table__'):
            # Специальная обработка для DAMAQuestion и DAMACase
            if obj.__class__.__name__ == 'DAMAQuestion':
                return {
                    'id': obj.id,
                    'dama_role_name': obj.dama_role_name,
                    'dama_competence_name': obj.dama_competence_name,
                    'question_type': obj.question_type,
                    'question': obj.question,
                    'question_answer': obj.question_answer,
                    'dama_knowledge_area': obj.dama_knowledge_area,
                    'dama_main_job': obj.dama_main_job
                }
            elif obj.__class__.__name__ == 'DAMACase':
                return {
                    'id': obj.id,
                    'dama_role_name': obj.dama_role_name,
                    'dama_competence_name': obj.dama_competence_name,
                    'dama_main_job': obj.dama_main_job,
                    'situation': obj.situation,
                    'case_task': obj.case_task,
                    'case_answer': obj.case_answer,
                    'dama_knowledge_area': obj.dama_knowledge_area
                }
            return {
                c.name: getattr(obj, c.name)
                for c in obj.__table__.columns
            }

        return obj

    async def save_state(self, user_id: int, state: State,
                         data: Dict[str, Any]) -> bool:
        try:
            key = f"state:{user_id}"
            serialized_data = self._serialize_sqlalchemy_obj(data)
            state_data = {
                "state": state.state if state else None,
                "data": serialized_data
            }
            result = await self.redis.set(key, json.dumps(state_data))
            await self.redis.expire(key, Config.REDIS_EXPIRE_TIME)
            return bool(result)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
            return False

    async def get_state(
            self, user_id: int) -> tuple[Optional[State], Dict[str, Any]]:
        try:
            key = f"state:{user_id}"
            data = await self.redis.get(key)
            if not data:
                return None, {}

            state_data = json.loads(data)
            state = State(
                state=state_data["state"]) if state_data["state"] else None
            return state, state_data.get("data", {})
        except json.JSONDecodeError:
            return None, {}
        except Exception as e:
            logger.error(f"Error getting state: {e}")
            return None, {}

    async def clear_state(self, user_id: int) -> bool:
        try:
            key = f"state:{user_id}"
            result = await self.redis.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Error clearing state: {e}")
            return False

    async def update_data(self, user_id: int, new_data: Dict[str,
                                                             Any]) -> bool:
        try:
            key = f"state:{user_id}"
            existing = await self.redis.get(key)
            if not existing:
                return False

            state_data = json.loads(existing)
            current_data = state_data.get("data", {})
            current_data.update(self._serialize_sqlalchemy_obj(new_data))

            state_data["data"] = current_data
            result = await self.redis.set(key, json.dumps(state_data))
            await self.redis.expire(key, Config.REDIS_EXPIRE_TIME)
            return bool(result)
        except Exception as e:
            logger.error(f"Error updating data: {e}")
            return False

    async def get_storage(self):
        return self.storage


state_storage = RedisStateStorage()
