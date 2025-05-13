import json
import aiohttp

from config import Config
from services.logger import logger
from services.redis_service import RedisService


async def analyze_with_chatgpt(
        question_text: str,
        correct_answer: str,
        user_answer: str,
        role: str,
        competence: str,
        user_id: int,
        question_id: int,
) -> dict:
    redis_service = RedisService()
    prompt = await redis_service.load_prompt()

    if not prompt:
        prompt = Config.DEFAULT_PROMPT

    system_prompt = (
        f"Ты - строгий экзаменатор DAMA для роли {role}. Проверь ответ по компетенции '{competence}'.\n\n"
        f"ВОПРОС: {question_text}\n"
        f"ЭТАЛОННЫЙ ОТВЕТ: {correct_answer}\n"
        f"ОТВЕТ КАНДИДАТА: {user_answer}\n\n"
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

    for attempt in range(1, Config.RETRIES_AI_ASK + 1):
        try:
            ai_model_data = await redis_service.load_selected_ai_model()
            token = await redis_service.load_openai_token()
            url = await redis_service.load_selected_url()
            temperature = await redis_service.load_model_temperature()
            logger.info(f"Попытка #{attempt}: модель={ai_model_data}, url={url}, temperature={temperature}")

            if not ai_model_data or not token or not url:
                raise ValueError("Не удалось получить данные из Redis")

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": ai_model_data,
                "messages": [{"role": "user", "content": system_prompt}],
                "temperature": float(temperature or 0.3),
                "response_format": {"type": "json_object"}
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=360)
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"Raw API response: {response_text}")

                    if response.status != 200:
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

                    try:
                        response_data = json.loads(response_text)
                        content = response_data['choices'][0]['message']['content']
                        logger.debug(f"API content: {content}")
                        try:
                            result = json.loads(content)
                        except json.JSONDecodeError:
                            json_start = content.find('{')
                            json_end = content.rfind('}') + 1
                            if json_start != -1 and json_end != -1:
                                result = json.loads(content[json_start:json_end])
                            else:
                                raise ValueError("invalid_json_response")


                        score = result.get('score', 0)
                        try:
                            normalized_score = round(min(5.0, max(0.0, float(score))), 1)
                        except (ValueError, TypeError):
                            logger.warning(f"Некорректный формат score: {score}, устанавливаем 0")
                            normalized_score = 0.0
                        result['score'] = normalized_score


                        detailed_scores = result.get('detailed_scores', [])
                        normalized_detailed = []
                        for item in detailed_scores:
                            if isinstance(item, dict):
                                normalized_detailed.append(0.0)
                            else:
                                try:
                                    normalized_detailed.append(
                                        round(min(5.0, max(0.0, float(item))), 1)
                                    )
                                except (ValueError, TypeError):
                                    normalized_detailed.append(0.0)

                        if not normalized_detailed:
                            normalized_detailed = [normalized_score] * 4

                        result['detailed_scores'] = normalized_detailed

                        result.setdefault('strengths', ["Вы продемонстрировали понимание темы"])
                        result.setdefault('weaknesses', ["Можно добавить больше деталей"])
                        result.setdefault('recommendations', [f"Рекомендуем изучить раздел DMBOK по {competence}"])

                        usage = response_data.get('usage', {})
                        tokens_used = {
                            'prompt_tokens': usage.get('prompt_tokens', 0),
                            'completion_tokens': usage.get('completion_tokens', 0),
                            'total_tokens': usage.get('total_tokens', 0)
                        }
                        await redis_service.save_analytics(user_id=user_id, question_id=question_id, data=tokens_used)

                        return result

                    except ValueError as e:
                        if str(e) == "invalid_json_response":
                            if attempt < Config.RETRIES_AI_ASK:
                                continue
                        raise

        except ValueError as e:
            if str(e) == "insufficient_quota":
                logger.error("Недостаточно токенов для выполнения запроса")
                return {
                    "score": 0,
                    "needs_clarification": False,
                    "clarification_question": "",
                    "detailed_scores": [0, 0, 0, 0],
                    "strengths": [],
                    "weaknesses": ["Обратитесь к администратору, чтобы он обновил модель (мало токенов)"],
                    "recommendations": []
                }
            elif str(e) == "context_length_exceeded":
                logger.error("Превышена максимальная длина контекста")
                return {
                    "score": 0,
                    "needs_clarification": False,
                    "clarification_question": "",
                    "detailed_scores": [0, 0, 0, 0],
                    "strengths": [],
                    "weaknesses": ["Ваш ответ слишком длинный. Пожалуйста, сократите его и отправьте снова"],
                    "recommendations": []
                }
            elif attempt < Config.RETRIES_AI_ASK:
                continue
            raise
        except Exception as e:
            logger.error(f"Ошибка при попытке #{attempt}: {str(e)}", exc_info=True)
            if attempt == Config.RETRIES_AI_ASK:
                break

    # Фолбек
    return {
        "score": 4.5,
        "needs_clarification": False,
        "clarification_question": "",
        "detailed_scores": [4.5, 4.5, 4.5, 4.5],
        "strengths": ["Спасибо за ваш ответ"],
        "weaknesses": ["Произошла техническая ошибка при оценке"],
        "recommendations": ["Пожалуйста, попробуйте ответить еще раз"]
    }
