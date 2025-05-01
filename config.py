import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_NAME = os.getenv('DB_NAME')
    LOG_LEVEL = os.getenv('LOG_LEVEL')
    DROP_DB_ON_STARTUP = os.getenv('DROP_DB_ON_STARTUP')
    REDIS_USER_PASSWORD = os.getenv('REDIS_USER_PASSWORD')
    REDIS_HOST = os.getenv('REDIS_HOST')
    REDIS_PORT = os.getenv('REDIS_PORT')
    REDIS_USER = os.getenv('REDIS_USER')
    REDIS_EXPIRE_TIME = os.getenv('REDIS_EXPIRE_TIME')
    MINIO_USER = os.getenv('MINIO_ROOT_USER')
    MINIO_PASSWORD = os.getenv('MINIO_ROOT_PASSWORD')
    MINIO_HOST = os.getenv('MINIO_HOST', 'localhost')
    MINIO_PORT = os.getenv('MINIO_PORT', '9000')
    RETRIES_AI_ASK = os.getenv('RETRIES_AI_ASK', 1)
    SECURE = os.getenv('SECURE', 'false').lower() in ('true', '1', 'yes')