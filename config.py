import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
    TELEGRAM_TOKEN = str(os.getenv('TELEGRAM_TOKEN'))
    DB_HOST = str(os.getenv('DB_HOST'))
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_USER = str(os.getenv('DB_USER'))
    DB_PASSWORD = str(os.getenv('DB_PASSWORD'))
    DB_NAME = str(os.getenv('DB_NAME'))
    LOG_LEVEL = str(os.getenv('LOG_LEVEL'))
    DROP_DB_ON_STARTUP =   bool(os.getenv('DROP_DB_ON_STARTUP', 'false').lower() in ('true', '1', 'yes'))
    REDIS_USER_PASSWORD = str(os.getenv('REDIS_USER_PASSWORD'))
    REDIS_HOST = str(os.getenv('REDIS_HOST'))
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6380))
    REDIS_USER = str(os.getenv('REDIS_USER'))
    REDIS_EXPIRE_TIME = int(os.getenv('REDIS_EXPIRE_TIME', 604800))
    MINIO_USER = str(os.getenv('MINIO_ROOT_USER'))
    MINIO_PASSWORD = str(os.getenv('MINIO_ROOT_PASSWORD'))
    MINIO_HOST = str(os.getenv('MINIO_HOST', 'localhost'))
    MINIO_PORT = int(os.getenv('MINIO_PORT', 9000))
    RETRIES_AI_ASK = int(os.getenv('RETRIES_AI_ASK', 1))
    SECURE = bool(os.getenv('SECURE', 'false').lower() in ('true', '1', 'yes'))
    DEFAULT_PROMPT = (
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
    DEFAULT_TEMPERATURE = float(os.getenv('DEFAULT_TEMPERATURE', 0.7))
    ADMIN_PASSWORD = str(os.getenv('ADMIN_PASSWORD'))

