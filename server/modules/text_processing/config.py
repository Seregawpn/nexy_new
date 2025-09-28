"""
Конфигурация модуля Text Processing
Использует централизованную конфигурацию
"""

import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# Добавляем корневую директорию для импорта централизованной конфигурации
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from config.unified_config import get_config

class TextProcessingConfig:
    """Конфигурация модуля обработки текста"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация конфигурации из централизованной системы
        
        Args:
            config: Словарь с конфигурацией (опционально, переопределяет централизованную)
        """
        # Получаем централизованную конфигурацию
        unified_config = get_config()
        self.config = config or {}
        
        # Используем централизованные настройки с возможностью переопределения
        self.gemini_api_key = self.config.get('gemini_api_key', unified_config.text_processing.gemini_api_key)
        
        # Live API настройки
        self.gemini_live_model = self.config.get('gemini_live_model', 'gemini-live-2.5-flash-preview')
        self.gemini_live_temperature = self.config.get('gemini_live_temperature', 0.7)
        self.gemini_live_max_tokens = self.config.get('gemini_live_max_tokens', 2048)
        self.gemini_live_tools = self.config.get('gemini_live_tools', ['google_search'])
        
        # Настройки изображений
        self.image_format = self.config.get('image_format', 'jpeg')
        self.image_mime_type = self.config.get('image_mime_type', 'image/jpeg')
        self.image_max_size = self.config.get('image_max_size', 10 * 1024 * 1024)
        self.streaming_chunk_size = self.config.get('streaming_chunk_size', 8192)
        
        
        # Настройки fallback
        self.fallback_timeout = self.config.get('fallback_timeout', unified_config.text_processing.fallback_timeout)
        self.circuit_breaker_threshold = self.config.get('circuit_breaker_threshold', unified_config.text_processing.circuit_breaker_threshold)
        self.circuit_breaker_timeout = self.config.get('circuit_breaker_timeout', unified_config.text_processing.circuit_breaker_timeout)
        
        # Настройки логирования
        self.log_level = self.config.get('log_level', unified_config.logging.level)
        self.log_requests = self.config.get('log_requests', unified_config.logging.log_requests)
        self.log_responses = self.config.get('log_responses', unified_config.logging.log_responses)
        
        # Настройки производительности
        self.max_concurrent_requests = self.config.get('max_concurrent_requests', unified_config.text_processing.max_concurrent_requests)
        self.request_timeout = self.config.get('request_timeout', unified_config.text_processing.request_timeout)
        
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """
        Получение конфигурации для конкретного провайдера
        
        Args:
            provider_name: Имя провайдера
            
        Returns:
            Словарь с конфигурацией провайдера
        """
        provider_configs = {
            'gemini_live': {
                'api_key': self.gemini_api_key,
                'model': self.gemini_live_model,
                'temperature': self.gemini_live_temperature,
                'max_tokens': self.gemini_live_max_tokens,
                'tools': self.gemini_live_tools,
                'image_mime_type': self.image_mime_type,
                'image_max_size': self.image_max_size,
                'streaming_chunk_size': self.streaming_chunk_size,
                'timeout': self.request_timeout
            },
        }
        
        return provider_configs.get(provider_name, {})
    
    def get_fallback_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации fallback менеджера
        
        Returns:
            Словарь с конфигурацией fallback
        """
        return {
            'timeout': self.fallback_timeout,
            'circuit_breaker_threshold': self.circuit_breaker_threshold,
            'circuit_breaker_timeout': self.circuit_breaker_timeout,
            'max_concurrent_requests': self.max_concurrent_requests
        }
    
    def validate(self) -> bool:
        """
        Валидация конфигурации
        
        Returns:
            True если конфигурация валидна, False иначе
        """
        # Проверяем наличие API ключа
        if not self.gemini_api_key:
            print("⚠️ GEMINI_API_KEY не установлен")
            return False
            
        # Проверяем корректность параметров
        if not (0 <= self.gemini_live_temperature <= 2):
            print("❌ gemini_live_temperature должен быть между 0 и 2")
            return False
            
        if self.gemini_live_max_tokens <= 0:
            print("❌ gemini_live_max_tokens должен быть положительным")
            return False
            
        if self.fallback_timeout <= 0:
            print("❌ fallback_timeout должен быть положительным")
            return False
            
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса конфигурации
        
        Returns:
            Словарь со статусом конфигурации
        """
        return {
            'gemini_api_key_set': bool(self.gemini_api_key),
            'gemini_live_model': self.gemini_live_model,
            'gemini_live_temperature': self.gemini_live_temperature,
            'gemini_live_max_tokens': self.gemini_live_max_tokens,
            'gemini_live_tools': self.gemini_live_tools,
            'image_format': self.image_format,
            'image_mime_type': self.image_mime_type,
            'image_max_size': self.image_max_size,
            'streaming_chunk_size': self.streaming_chunk_size,
            'fallback_timeout': self.fallback_timeout,
            'circuit_breaker_threshold': self.circuit_breaker_threshold,
            'circuit_breaker_timeout': self.circuit_breaker_timeout,
            'log_level': self.log_level,
            'log_requests': self.log_requests,
            'log_responses': self.log_responses,
            'max_concurrent_requests': self.max_concurrent_requests,
            'request_timeout': self.request_timeout
        }
