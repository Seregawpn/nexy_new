"""
Провайдер фильтрации контента
"""

import logging
import sys
import os
from typing import Dict, Any, Optional, List

# Добавляем путь к корневой директории сервера
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from integrations.core.universal_provider_interface import UniversalProviderInterface, ProviderStatus

logger = logging.getLogger(__name__)

class ContentFilteringProvider(UniversalProviderInterface):
    """Провайдер для фильтрации контента"""
    
    def __init__(self, config):
        """
        Инициализация провайдера фильтрации контента
        
        Args:
            config: Конфигурация провайдера
        """
        super().__init__("content_filtering_provider", 1, config.config)
        
        self.config = config
        self.filtering_stats = {
            "total_filtered": 0,
            "total_blocked": 0,
            "total_allowed": 0,
            "total_errors": 0
        }
        
        logger.info("Content Filtering Provider created")
    
    async def initialize(self) -> bool:
        """
        Инициализация провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing Content Filtering Provider...")
            
            # Загружаем конфигурацию
            self.content_config = self.config.get_content_filtering_config()
            self.validation_config = self.config.get_validation_config()
            
            self.is_initialized = True
            self.status = ProviderStatus.HEALTHY
            
            logger.info("Content Filtering Provider initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Content Filtering Provider: {e}")
            self.report_error(str(e))
            return False
    
    async def process(self, input_data: Any) -> Any:
        """
        Основная обработка фильтрации контента
        
        Args:
            input_data: Данные для обработки
            
        Returns:
            Результат обработки
        """
        try:
            operation = input_data.get("operation", "filter_content")
            text = input_data.get("text", "")
            
            if operation == "filter_content":
                return await self.filter_content(text)
            elif operation == "validate_content":
                return await self.validate_content(text)
            else:
                logger.warning(f"Unknown operation: {operation}")
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            logger.error(f"Error processing content filtering request: {e}")
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def filter_content(self, text: str) -> Dict[str, Any]:
        """
        Фильтрация контента
        
        Args:
            text: Текст для фильтрации
            
        Returns:
            Результат фильтрации
        """
        try:
            if not text:
                return {"success": True, "filtered_text": "", "filtered": False, "reasons": []}
            
            reasons = []
            filtered_text = text
            is_filtered = False
            
            # Проверка длины
            min_length = self.content_config.get("min_length", 1)
            max_length = self.content_config.get("max_length", 10000)
            
            if len(text) < min_length:
                reasons.append(f"Text too short: {len(text)} < {min_length}")
                is_filtered = True
                filtered_text = ""
            elif len(text) > max_length:
                reasons.append(f"Text too long: {len(text)} > {max_length}")
                is_filtered = True
                filtered_text = text[:max_length] + "..."
            
            # Проверка на пустой текст
            if not is_filtered and self.content_config.get("block_empty", True) and not text.strip():
                reasons.append("Empty text not allowed")
                is_filtered = True
                filtered_text = ""
            
            # Проверка на пробелы
            if not is_filtered and self.content_config.get("block_whitespace_only", True) and not text.strip():
                reasons.append("Whitespace-only text not allowed")
                is_filtered = True
                filtered_text = ""
            
            # Проверка на один символ
            if not is_filtered and self.content_config.get("block_single_char", False) and len(text.strip()) == 1:
                reasons.append("Single character text not allowed")
                is_filtered = True
                filtered_text = ""
            
            # Обновляем статистику
            self.filtering_stats["total_filtered"] += 1
            if is_filtered:
                self.filtering_stats["total_blocked"] += 1
            else:
                self.filtering_stats["total_allowed"] += 1
            
            self.report_success()
            
            return {
                "success": True,
                "original_text": text,
                "filtered_text": filtered_text,
                "filtered": is_filtered,
                "reasons": reasons
            }
            
        except Exception as e:
            logger.error(f"Error filtering content: {e}")
            self.filtering_stats["total_errors"] += 1
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def validate_content(self, text: str) -> Dict[str, Any]:
        """
        Валидация контента
        
        Args:
            text: Текст для валидации
            
        Returns:
            Результат валидации
        """
        try:
            if not text:
                return {"success": True, "valid": True, "errors": []}
            
            errors = []
            
            # Проверка кодировки
            if self.validation_config.get("check_encoding", True):
                try:
                    text.encode('utf-8')
                except UnicodeEncodeError:
                    errors.append("Invalid UTF-8 encoding")
            
            # Проверка Unicode
            if self.validation_config.get("validate_unicode", True):
                try:
                    text.encode('unicode_escape').decode('unicode_escape')
                except UnicodeDecodeError:
                    errors.append("Invalid Unicode characters")
            
            # Проверка длины предложений
            max_sentence_length = self.validation_config.get("max_sentence_length", 500)
            sentences = text.split('.')
            for i, sentence in enumerate(sentences):
                if len(sentence.strip()) > max_sentence_length:
                    errors.append(f"Sentence {i+1} too long: {len(sentence.strip())} > {max_sentence_length}")
            
            # Проверка языка (если включена)
            if self.validation_config.get("check_language", False):
                allowed_languages = self.validation_config.get("allowed_languages", ["en", "ru", "uk"])
                # Простая проверка на основе символов
                detected_language = self._detect_language(text)
                if detected_language not in allowed_languages:
                    errors.append(f"Language not allowed: {detected_language}")
            
            return {
                "success": True,
                "valid": len(errors) == 0,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error validating content: {e}")
            self.filtering_stats["total_errors"] += 1
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    def _detect_language(self, text: str) -> str:
        """
        Простое определение языка по символам
        
        Args:
            text: Текст для анализа
            
        Returns:
            Код языка
        """
        if not text:
            return "unknown"
        
        # Подсчитываем символы разных алфавитов
        cyrillic_count = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        latin_count = sum(1 for char in text if char.isalpha() and ord(char) < 128)
        
        total_alpha = cyrillic_count + latin_count
        if total_alpha == 0:
            return "unknown"
        
        if cyrillic_count / total_alpha > 0.5:
            return "ru"  # Русский/украинский
        elif latin_count / total_alpha > 0.5:
            return "en"  # Английский
        else:
            return "mixed"
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов провайдера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up Content Filtering Provider...")
            
            # Сбрасываем статистику
            self.filtering_stats = {
                "total_filtered": 0,
                "total_blocked": 0,
                "total_allowed": 0,
                "total_errors": 0
            }
            
            self.is_initialized = False
            self.status = ProviderStatus.STOPPED
            
            logger.info("Content Filtering Provider cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up Content Filtering Provider: {e}")
            self.report_error(str(e))
            return False



