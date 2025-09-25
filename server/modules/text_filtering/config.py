"""
Конфигурация Text Filtering Module
"""

import os
from typing import Dict, Any

class TextFilteringConfig:
    """Конфигурация модуля фильтрации текста"""
    
    def __init__(self):
        """Инициализация конфигурации"""
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации"""
        return {
            # Настройки очистки текста
            "text_cleaning": {
                "enabled": os.getenv("TEXT_CLEANING_ENABLED", "true").lower() == "true",
                "remove_extra_whitespace": True,
                "remove_special_chars": True,
                "allowed_chars": r'[^\w\s\.\,\!\?\-\:\;\(\)\[\]\{\}\"\'@#$%&*+=<>/\\|~`]',
                "normalize_unicode": True,
                "remove_control_chars": True
            },
            
            # Настройки фильтрации контента
            "content_filtering": {
                "enabled": os.getenv("CONTENT_FILTERING_ENABLED", "true").lower() == "true",
                "max_length": int(os.getenv("MAX_TEXT_LENGTH", "10000")),
                "min_length": int(os.getenv("MIN_TEXT_LENGTH", "1")),
                "block_empty": True,
                "block_whitespace_only": True,
                "block_single_char": False
            },
            
            # Настройки разбиения на предложения
            "sentence_splitting": {
                "enabled": True,
                "sentence_pattern": r'(?<=[.!?])\s*(?=[A-ZА-Я0-9])|(?<=[.!?])\s*$',
                "sentence_endings": ['.', '!', '?', '...', '?!', '!?'],
                "auto_add_period": True,
                "preserve_formatting": True
            },
            
            # Настройки предобработки
            "preprocessing": {
                "enabled": True,
                "normalize_quotes": True,
                "fix_encoding": True,
                "remove_urls": os.getenv("REMOVE_URLS", "false").lower() == "true",
                "remove_emails": os.getenv("REMOVE_EMAILS", "false").lower() == "true",
                "remove_phone_numbers": os.getenv("REMOVE_PHONE_NUMBERS", "false").lower() == "true",
                "remove_sensitive_data": os.getenv("REMOVE_SENSITIVE_DATA", "false").lower() == "true"
            },
            
            # Настройки валидации
            "validation": {
                "enabled": True,
                "check_encoding": True,
                "validate_unicode": True,
                "check_language": os.getenv("CHECK_LANGUAGE", "false").lower() == "true",
                "allowed_languages": ["en", "ru", "uk"],
                "max_sentence_length": int(os.getenv("MAX_SENTENCE_LENGTH", "500"))
            },
            
            # Настройки производительности
            "performance": {
                "cache_enabled": os.getenv("TEXT_FILTER_CACHE_ENABLED", "true").lower() == "true",
                "cache_size": int(os.getenv("TEXT_FILTER_CACHE_SIZE", "1000")),
                "cache_ttl": int(os.getenv("TEXT_FILTER_CACHE_TTL", "3600")),
                "batch_processing": os.getenv("BATCH_PROCESSING_ENABLED", "false").lower() == "true",
                "max_batch_size": int(os.getenv("MAX_BATCH_SIZE", "100"))
            },
            
            # Настройки логирования
            "logging": {
                "log_filtered_content": os.getenv("LOG_FILTERED_CONTENT", "false").lower() == "true",
                "log_statistics": True,
                "log_performance": os.getenv("LOG_PERFORMANCE", "true").lower() == "true",
                "log_errors": True
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получение значения конфигурации"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_text_cleaning_config(self) -> Dict[str, Any]:
        """Получение конфигурации очистки текста"""
        return self.config.get("text_cleaning", {})
    
    def get_content_filtering_config(self) -> Dict[str, Any]:
        """Получение конфигурации фильтрации контента"""
        return self.config.get("content_filtering", {})
    
    def get_sentence_splitting_config(self) -> Dict[str, Any]:
        """Получение конфигурации разбиения на предложения"""
        return self.config.get("sentence_splitting", {})
    
    def get_preprocessing_config(self) -> Dict[str, Any]:
        """Получение конфигурации предобработки"""
        return self.config.get("preprocessing", {})
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Получение конфигурации валидации"""
        return self.config.get("validation", {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Получение конфигурации производительности"""
        return self.config.get("performance", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Получение конфигурации логирования"""
        return self.config.get("logging", {})
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Проверка, включена ли функция"""
        return self.get(f"{feature}.enabled", False)
    
    def get_feature_config(self, feature: str) -> Dict[str, Any]:
        """Получение конфигурации функции"""
        return self.config.get(feature, {})
