
from typing import Optional
import re

class UserValidators:
    """Валидаторы для пользовательских данных"""
    
    @staticmethod
    def validate_telegram_id(telegram_id: int) -> bool:
        """Валидация Telegram ID"""
        return isinstance(telegram_id, int) and telegram_id > 0
    
    @staticmethod
    def validate_username(username: Optional[str]) -> bool:
        """Валидация username"""
        if username is None:
            return True
        return isinstance(username, str) and len(username) <= 32
    
    @staticmethod
    def validate_name(name: str) -> bool:
        """Валидация имени пользователя"""
        if not isinstance(name, str):
            return False
        return 1 <= len(name.strip()) <= 100
    
    @staticmethod
    def validate_role_name(role: str) -> bool:
        """Валидация названия роли"""
        if not isinstance(role, str):
            return False
        return len(role.strip()) > 0 and len(role) <= 200
    
    @staticmethod
    def validate_competence_name(competence: str) -> bool:
        """Валидация названия компетенции"""
        if not isinstance(competence, str):
            return False
        return len(competence.strip()) > 0 and len(competence) <= 300

class AiValidators:
    """Валидаторы для AI настроек"""
    
    @staticmethod
    def validate_temperature(temperature: float) -> bool:
        """Валидация температуры модели"""
        return isinstance(temperature, (int, float)) and 0.0 <= temperature <= 2.0
    
    @staticmethod
    def validate_prompt(prompt: str) -> bool:
        """Валидация промпта"""
        if not isinstance(prompt, str):
            return False
        return 10 <= len(prompt.strip()) <= 4000
    
    @staticmethod
    def validate_model_name(model_name: str) -> bool:
        """Валидация названия модели"""
        if not isinstance(model_name, str):
            return False
        return len(model_name.strip()) > 0 and len(model_name) <= 100
    
    @staticmethod
    def validate_api_url(url: str) -> bool:
        """Валидация URL API"""
        if not isinstance(url, str):
            return False
        url_pattern = re.compile(
            r'^https?://'  # http:// или https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...или ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None
    
    @staticmethod
    def validate_api_token(token: str) -> bool:
        """Валидация API токена"""
        if not isinstance(token, str):
            return False
        return 10 <= len(token.strip()) <= 200
