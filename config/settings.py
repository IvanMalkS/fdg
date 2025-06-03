
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=True)

@dataclass
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    name: str
    drop_on_startup: bool

@dataclass
class RedisConfig:
    host: str
    port: int
    user: str
    password: str
    expire_time: int

@dataclass
class MinioConfig:
    host: str
    port: int
    user: str
    password: str
    secure: bool

@dataclass
class TelegramConfig:
    token: str

@dataclass
class AiConfig:
    retries: int
    default_temperature: float
    default_prompt: str

@dataclass
class AppSettings:
    database: DatabaseConfig
    redis: RedisConfig
    minio: MinioConfig
    telegram: TelegramConfig
    ai: AiConfig
    log_level: str
    admin_password: str

def load_settings() -> AppSettings:
    """Загрузка настроек из переменных окружения"""
    return AppSettings(
        database=DatabaseConfig(
            host=str(os.getenv('DB_HOST')),
            port=int(os.getenv('DB_PORT', 5432)),
            user=str(os.getenv('DB_USER')),
            password=str(os.getenv('DB_PASSWORD')),
            name=str(os.getenv('DB_NAME')),
            drop_on_startup=bool(os.getenv('DROP_DB_ON_STARTUP', 'false').lower() in ('true', '1', 'yes'))
        ),
        redis=RedisConfig(
            host=str(os.getenv('REDIS_HOST')),
            port=int(os.getenv('REDIS_PORT', 6380)),
            user=str(os.getenv('REDIS_USER')),
            password=str(os.getenv('REDIS_USER_PASSWORD')),
            expire_time=int(os.getenv('REDIS_EXPIRE_TIME', 604800))
        ),
        minio=MinioConfig(
            host=str(os.getenv('MINIO_HOST', 'localhost')),
            port=int(os.getenv('MINIO_PORT', 9000)),
            user=str(os.getenv('MINIO_ROOT_USER')),
            password=str(os.getenv('MINIO_ROOT_PASSWORD')),
            secure=bool(os.getenv('SECURE', 'false').lower() in ('true', '1', 'yes'))
        ),
        telegram=TelegramConfig(
            token=str(os.getenv('TELEGRAM_TOKEN'))
        ),
        ai=AiConfig(
            retries=int(os.getenv('RETRIES_AI_ASK', 1)),
            default_temperature=float(os.getenv('DEFAULT_TEMPERATURE', 0.7)),
            default_prompt=(
                "Оцени по критериям (0-5 баллов):\n"
                "1. Полнота (покрытие пунктов эталона)\n"
                "2. Точность терминов DAMA\n"
                "3. Практическая применимость\n"
                "4. Соответствие DMBOK\n\n"
                "Алгоритм действий:\n"
                "1. Если ответ полный (≥80% эталона) - верни оценку 5.\n"
                "2. Если ответ частичный (30-80%) - задай 1 уточняющий вопрос.\n"
                "3. Если ответ неверный (<30%) или отсутствует (например, 'None', пусто, 'не знаю') — НЕ задавай уточняющий вопрос, сразу оценивай.\n\n"
                "Если ответ пустой, 'None', 'нет опыта', 'не знаю', 'не могу ответить', 'N/A' или аналогичный — оцени ответ как неверный и НЕ задавай уточняющий вопрос\n"
                "Полностью пропускай этап уточнения для таких ответо\n"
                "При ответе не по теме ставь 0 баллов.\n"
                "В рекомендации желательно еще добавлять источники со ссылками.\n"
                "Если считаешь, что эталонный вопрос недостаточно раскрывает тему, можешь добавить уточняющий вопрос (если пользователь хоть что-то ответил).\n"
            )
        ),
        log_level=str(os.getenv('LOG_LEVEL')),
        admin_password=str(os.getenv('ADMIN_PASSWORD'))
    )

# Глобальный объект настроек
settings = load_settings()
