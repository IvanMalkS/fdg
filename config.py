from config.settings import settings

class Config:
    @property
    def TELEGRAM_TOKEN(self):
        return settings.telegram.token

    @property
    def LOG_LEVEL(self):
        return settings.log_level

    @property
    def DB_HOST(self):
        return settings.db.host

    @property
    def DB_PORT(self):
        return settings.db.port

    @property
    def DB_USER(self):
        return settings.db.user

    @property
    def DB_PASSWORD(self):
        return settings.db.password

    @property
    def DB_NAME(self):
        return settings.db.name

    @property
    def DROP_DB_ON_STARTUP(self):
        return settings.drop_db_on_startup

    @property
    def REDIS_USER_PASSWORD(self):
        return settings.redis.user_password

    @property
    def REDIS_HOST(self):
        return settings.redis.host

    @property
    def REDIS_PORT(self):
        return settings.redis.port

    @property
    def REDIS_USER(self):
        return settings.redis.user

    @property
    def REDIS_EXPIRE_TIME(self):
        return settings.redis.expire_time
    
    @property
    def MINIO_USER(self):
        return settings.minio.user
    
    @property
    def MINIO_PASSWORD(self):
        return settings.minio.password

    @property
    def MINIO_HOST(self):
        return settings.minio.host
    
    @property
    def MINIO_PORT(self):
        return settings.minio.port

    @property
    def RETRIES_AI_ASK(self):
        return settings.retries_ai_ask
    
    @property
    def SECURE(self):
        return settings.secure
    
    @property
    def DEFAULT_PROMPT(self):
        return settings.default_prompt

    @property
    def DEFAULT_TEMPERATURE(self):
        return settings.default_temperature
    
    @property
    def ADMIN_PASSWORD(self):
        return settings.admin_password


# For backwards compatibility
Config = Config()