import json
import aiohttp
from typing import Optional, Dict, Any
from dataclasses import dataclass
from config import Config
from services.logger import logger
from services.redis_service import RedisService


@dataclass
class AnalysisRequest:
    """Структура запроса на анализ ответа"""
    question_text: str
    correct_answer: str
    user_answer: str
    role: str
    competence: str
    user_id: int
    question_id: int
    prev_answer: Optional[str] = None


@dataclass
class AnalysisResult:
    """Структура результата анализа"""
    score: float
    needs_clarification: bool
    clarification_question: str
    detailed_scores: list
    strengths: list
    weaknesses: list
    recommendations: list
    tokens_used: Optional[Dict[str, int]] = None


class GptService:
    """Сервис для работы с GPT API"""
    
    def __init__(self):
        self.redis_service = RedisService()

    async def analyze_answer(self, request: AnalysisRequest) -> AnalysisResult:
        """Основной метод анализа ответа"""
        prompt = await self._build_prompt(request)
        
        for attempt in range(1, Config.RETRIES_AI_ASK + 1):
            try:
                result = await self._make_api_request(prompt, attempt)
                if result:
                    await self._save_analytics(request.user_id, request.question_id, result.tokens_used)
                    return result
            except Exception as e:
                logger.error(f"Attempt #{attempt} failed: {str(e)}")
                if attempt == Config.RETRIES_AI_ASK:
                    return self._get_fallback_result()
        
        return self._get_fallback_result()

    async def _build_prompt(self, request: AnalysisRequest) -> str:
        """Построение промпта для GPT"""
        prompt = await self.redis_service.load_prompt()
        if not prompt:
            prompt = Config.DEFAULT_PROMPT

        system_prompt = (
            f"Ты - строгий экзаменатор DAMA для роли {request.role}. "
            f"Проверь ответ по компетенции '{request.competence}'.\n\n"
            f"ВОПРОС: {request.question_text}\n"
            f"ЭТАЛОННЫЙ ОТВЕТ: {request.correct_answer}\n"
        )

        if request.prev_answer:
            system_prompt += (
                f"ПРЕДЫДУЩИЙ ОТВЕТ КАНДИДАТА: {request.prev_answer}\n"
                f"УТОЧНЯЮЩИЙ ОТВЕТ: {request.user_answer}\n\n"
            )
        else:
            system_prompt += f"ОТВЕТ КАНДИДАТА: {request.user_answer}\n\n"

        system_prompt += (
            f"{prompt}"
            "Формат ответа (JSON):\n"
            "{\n"
            "  \"score\": средний_балл (0-5),\n"
            "  \"needs_clarification\": true/false,\n"
            "  \"clarification_question\": \"уточняющий вопрос\",\n"
            "  \"detailed_scores\": [оценки_по_критериям],\n"
            "  \"strengths\": [\"сильные стороны\"],\n"
            "  \"weaknesses\": [\"пробелы\"],\n"
            "  \"recommendations\": [\"материалы для изучения\"]\n"
            "}"
        )
        
        return system_prompt

    async def _make_api_request(self, prompt: str, attempt: int) -> Optional[AnalysisResult]:
        """Выполнение запроса к API"""
        ai_model_data = await self.redis_service.load_selected_ai_model()
        token = await self.redis_service.load_openai_token()
        url = await self.redis_service.load_selected_url()
        temperature = await self.redis_service.load_model_temperature()
        
        logger.info(f"Attempt #{attempt}: model={ai_model_data}, url={url}, temperature={temperature}")

        if not ai_model_data or not token or not url:
            raise ValueError("Не удалось получить данные из Redis")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": ai_model_data,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(temperature or 0.3),
            "response_format": {"type": "json_object"}
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=360)
            ) as response:
                return await self._process_response(response)

    async def _process_response(self, response) -> Optional[AnalysisResult]:
        """Обработка ответа от API"""
        response_text = await response.text()
        logger.debug(f"Raw API response: {response_text}")

        if response.status != 200:
            await self._handle_api_error(response, response_text)
            return None

        try:
            response_data = json.loads(response_text)
            content = response_data['choices'][0]['message']['content']
            logger.debug(f"API content: {content}")
            
            result_dict = self._parse_json_content(content)
            usage = response_data.get('usage', {})
            
            return self._build_analysis_result(result_dict, usage)
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error processing response: {e}")
            raise

    def _parse_json_content(self, content: str) -> dict:
        """Парсинг JSON из ответа GPT"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Попытка извлечь JSON из строки
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                return json.loads(content[json_start:json_end])
            else:
                raise ValueError("invalid_json_response")

    def _build_analysis_result(self, result_dict: dict, usage: dict) -> AnalysisResult:
        """Построение объекта результата анализа"""
        # Нормализация оценки
        score = result_dict.get('score', 0)
        try:
            normalized_score = round(min(5.0, max(0.0, float(score))), 1)
        except (ValueError, TypeError):
            logger.warning(f"Incorrect score format: {score}, set 0")
            normalized_score = 0.0

        # Нормализация детальных оценок
        detailed_scores = result_dict.get('detailed_scores', [])
        normalized_detailed = []
        for item in detailed_scores:
            if isinstance(item, dict):
                normalized_detailed.append(0.0)
            else:
                try:
                    normalized_detailed.append(round(min(5.0, max(0.0, float(item))), 1))
                except (ValueError, TypeError):
                    normalized_detailed.append(0.0)

        if not normalized_detailed:
            normalized_detailed = [normalized_score] * 4

        # Значения по умолчанию
        strengths = result_dict.get('strengths', ["Вы продемонстрировали понимание темы"])
        weaknesses = result_dict.get('weaknesses', ["Можно добавить больше деталей"])
        recommendations = result_dict.get('recommendations', 
                                        [f"Рекомендуем изучить раздел DMBOK по {result_dict.get('competence', 'данной теме')}"])

        tokens_used = {
            'prompt_tokens': usage.get('prompt_tokens', 0),
            'completion_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0)
        }

        return AnalysisResult(
            score=normalized_score,
            needs_clarification=result_dict.get('needs_clarification', False),
            clarification_question=result_dict.get('clarification_question', ''),
            detailed_scores=normalized_detailed,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            tokens_used=tokens_used
        )

    async def _handle_api_error(self, response, response_text: str):
        """Обработка ошибок API"""
        error_message = response_text
        try:
            error_data = json.loads(response_text)
            error_message = error_data.get('error', {}).get('message', error_message)
        except Exception:
            pass

        if 'insufficient_quota' in error_message.lower():
            raise ValueError("insufficient_quota")
        if 'context_length' in error_message.lower():
            raise ValueError("context_length_exceeded")
        
        raise Exception(f"API error {response.status}: {error_message}")

    async def _save_analytics(self, user_id: int, question_id: int, tokens_used: Optional[Dict[str, int]]):
        """Сохранение аналитики"""
        if tokens_used:
            await self.redis_service.save_analytics(
                user_id=user_id,
                question_id=question_id,
                data=tokens_used
            )

    def _get_fallback_result(self) -> AnalysisResult:
        """Получение результата по умолчанию при ошибке"""
        return AnalysisResult(
            score=4.5,
            needs_clarification=False,
            clarification_question="",
            detailed_scores=[4.5, 4.5, 4.5, 4.5],
            strengths=["Спасибо за ваш ответ"],
            weaknesses=["Произошла техническая ошибка при оценке"],
            recommendations=["Пожалуйста, попробуйте ответить еще раз"]
        )

    def _get_error_result(self, error_type: str) -> AnalysisResult:
        """Получение результата при специфических ошибках"""
        if error_type == "insufficient_quota":
            return AnalysisResult(
                score=0,
                needs_clarification=False,
                clarification_question="",
                detailed_scores=[0, 0, 0, 0],
                strengths=[],
                weaknesses=["Обратитесь к администратору, чтобы он обновил модель (мало токенов)"],
                recommendations=[]
            )
        elif error_type == "context_length_exceeded":
            return AnalysisResult(
                score=0,
                needs_clarification=False,
                clarification_question="",
                detailed_scores=[0, 0, 0, 0],
                strengths=[],
                weaknesses=["Ваш ответ слишком длинный. Пожалуйста, сократите его и отправьте снова"],
                recommendations=[]
            )
        else:
            return self._get_fallback_result()


# Фабричная функция для обратной совместимости
async def analyze_with_chatgpt(question_text: str,
                               correct_answer: str,
                               user_answer: str,
                               role: str,
                               competence: str,
                               user_id: int,
                               question_id: int,
                               prev_answer: Optional[str] = None) -> dict:
    """Фабричная функция для обратной совместимости"""
    gpt_service = GptService()
    
    request = AnalysisRequest(
        question_text=question_text,
        correct_answer=correct_answer,
        user_answer=user_answer,
        role=role,
        competence=competence,
        user_id=user_id,
        question_id=question_id,
        prev_answer=prev_answer
    )
    
    result = await gpt_service.analyze_answer(request)
    
    # Преобразуем в словарь для обратной совместимости
    return {
        "score": result.score,
        "needs_clarification": result.needs_clarification,
        "clarification_question": result.clarification_question,
        "detailed_scores": result.detailed_scores,
        "strengths": result.strengths,
        "weaknesses": result.weaknesses,
        "recommendations": result.recommendations
    }
