
from .settings import settings, AppSettings

# Create a Config class that provides access to the settings
class Config:
    @property
    def TELEGRAM_TOKEN(self):
        return settings.telegram.token
    
    @property
    def LOG_LEVEL(self):
        return settings.log_level
    
    @property
    def DB_HOST(self):
        return settings.database.host
    
    @property
    def DB_PORT(self):
        return settings.database.port
    
    @property
    def DB_USER(self):
        return settings.database.user
    
    @property
    def DB_PASSWORD(self):
        return settings.database.password
    
    @property
    def DB_NAME(self):
        return settings.database.name
    
    @property
    def DROP_DB_ON_STARTUP(self):
        return settings.database.drop_on_startup
    
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
    def REDIS_USER_PASSWORD(self):
        return settings.redis.password
    
    @property
    def REDIS_EXPIRE_TIME(self):
        return settings.redis.expire_time
    
    @property
    def MINIO_HOST(self):
        return settings.minio.host
    
    @property
    def MINIO_PORT(self):
        return settings.minio.port
    
    @property
    def MINIO_USER(self):
        return settings.minio.user
    
    @property
    def MINIO_PASSWORD(self):
        return settings.minio.password
    
    @property
    def SECURE(self):
        return settings.minio.secure
    
    @property
    def RETRIES_AI_ASK(self):
        return settings.ai.retries
    
    @property
    def DEFAULT_TEMPERATURE(self):
        return settings.ai.default_temperature
    
    @property
    def DEFAULT_PROMPT(self):
        return settings.ai.default_prompt
    
    @property
    def ADMIN_PASSWORD(self):
        return settings.admin_password

# Create a global instance
Config = Config()

__all__ = ['settings', 'AppSettings', 'Config']
