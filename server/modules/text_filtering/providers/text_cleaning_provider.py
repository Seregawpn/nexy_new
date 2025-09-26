"""
Провайдер очистки текста
"""

import re
import logging
import sys
import os
from typing import Dict, Any, Optional

# Добавляем путь к корневой директории сервера
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from integrations.core.universal_provider_interface import UniversalProviderInterface, ProviderStatus

logger = logging.getLogger(__name__)

class TextCleaningProvider(UniversalProviderInterface):
    """Провайдер для очистки и предобработки текста"""
    
    def __init__(self, config):
        """
        Инициализация провайдера очистки текста
        
        Args:
            config: Конфигурация провайдера
        """
        super().__init__("text_cleaning_provider", 1, config.config)
        
        self.config = config
        self.cleaning_stats = {
            "total_cleaned": 0,
            "total_preprocessed": 0,
            "total_errors": 0
        }
        
        logger.info("Text Cleaning Provider created")
    
    async def initialize(self) -> bool:
        """
        Инициализация провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing Text Cleaning Provider...")
            
            # Загружаем конфигурацию
            self.cleaning_config = self.config.get_text_cleaning_config()
            self.preprocessing_config = self.config.get_preprocessing_config()
            
            self.is_initialized = True
            self.status = ProviderStatus.HEALTHY
            
            logger.info("Text Cleaning Provider initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Text Cleaning Provider: {e}")
            self.report_error(str(e))
            return False
    
    async def process(self, input_data: Any) -> Any:
        """
        Основная обработка очистки текста
        
        Args:
            input_data: Данные для обработки
            
        Returns:
            Результат обработки
        """
        try:
            operation = input_data.get("operation", "clean_text")
            text = input_data.get("text", "")
            options = input_data.get("options", {})
            
            if operation == "clean_text":
                return await self.clean_text(text, options)
            elif operation == "preprocess_text":
                return await self.preprocess_text(text, options)
            else:
                logger.warning(f"Unknown operation: {operation}")
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            logger.error(f"Error processing text cleaning request: {e}")
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def clean_text(self, text: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Очистка текста
        
        Args:
            text: Текст для очистки
            options: Дополнительные опции
            
        Returns:
            Результат очистки
        """
        try:
            if text is None:
                return {"success": False, "error": "Text cannot be None"}
            
            if not text:
                return {"success": True, "cleaned_text": "", "operations": []}
            
            operations = []
            cleaned_text = text
            
            # Убираем лишние пробелы и переносы строк
            if self.cleaning_config.get("remove_extra_whitespace", True):
                cleaned_text = ' '.join(cleaned_text.split())
                operations.append("remove_extra_whitespace")
            
            # Убираем специальные символы
            if self.cleaning_config.get("remove_special_chars", True):
                allowed_chars = self.cleaning_config.get("allowed_chars", r'[^\w\s\.\,\!\?\-\:\;\(\)\[\]\{\}\"\'@#$%&*+=<>/\\|~`]')
                cleaned_text = re.sub(allowed_chars, '', cleaned_text)
                operations.append("remove_special_chars")
            
            # Нормализация Unicode
            if self.cleaning_config.get("normalize_unicode", True):
                import unicodedata
                cleaned_text = unicodedata.normalize('NFKC', cleaned_text)
                operations.append("normalize_unicode")
            
            # Удаление управляющих символов
            if self.cleaning_config.get("remove_control_chars", True):
                cleaned_text = ''.join(char for char in cleaned_text if ord(char) >= 32 or char in '\n\r\t')
                operations.append("remove_control_chars")
            
            cleaned_text = cleaned_text.strip()
            
            self.cleaning_stats["total_cleaned"] += 1
            self.report_success()
            
            return {
                "success": True,
                "original_text": text,
                "cleaned_text": cleaned_text,
                "operations": operations
            }
            
        except Exception as e:
            logger.error(f"Error cleaning text: {e}")
            self.cleaning_stats["total_errors"] += 1
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def preprocess_text(self, text: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Предобработка текста
        
        Args:
            text: Текст для предобработки
            options: Дополнительные опции
            
        Returns:
            Результат предобработки
        """
        try:
            if not text:
                return {"success": True, "processed_text": "", "operations": []}
            
            operations = []
            processed_text = text
            
            # Нормализация кавычек
            if self.preprocessing_config.get("normalize_quotes", True):
                processed_text = self._normalize_quotes(processed_text)
                operations.append("normalize_quotes")
            
            # Исправление кодировки
            if self.preprocessing_config.get("fix_encoding", True):
                processed_text = self._fix_encoding(processed_text)
                operations.append("fix_encoding")
            
            # Удаление URL
            if self.preprocessing_config.get("remove_urls", False):
                processed_text = self._remove_urls(processed_text)
                operations.append("remove_urls")
            
            # Удаление email адресов
            if self.preprocessing_config.get("remove_emails", False):
                processed_text = self._remove_emails(processed_text)
                operations.append("remove_emails")
            
            # Удаление номеров телефонов
            if self.preprocessing_config.get("remove_phone_numbers", False):
                processed_text = self._remove_phone_numbers(processed_text)
                operations.append("remove_phone_numbers")
            
            # Удаление чувствительных данных
            if self.preprocessing_config.get("remove_sensitive_data", False):
                processed_text = self._remove_sensitive_data(processed_text)
                operations.append("remove_sensitive_data")
            
            self.cleaning_stats["total_preprocessed"] += 1
            self.report_success()
            
            return {
                "success": True,
                "original_text": text,
                "processed_text": processed_text,
                "operations": operations
            }
            
        except Exception as e:
            logger.error(f"Error preprocessing text: {e}")
            self.cleaning_stats["total_errors"] += 1
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    def _normalize_quotes(self, text: str) -> str:
        """Нормализация кавычек"""
        # Заменяем различные типы кавычек на стандартные
        replacements = {
            '"': '"',  # Левая двойная кавычка
            '"': '"',  # Правая двойная кавычка
            ''': "'",  # Левая одинарная кавычка
            ''': "'",  # Правая одинарная кавычка
            '„': '"',  # Немецкая левая кавычка
            '«': '"',  # Французская левая кавычка
            '»': '"',  # Французская правая кавычка
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def _fix_encoding(self, text: str) -> str:
        """Исправление проблем с кодировкой"""
        try:
            # Попытка декодировать как UTF-8
            text.encode('utf-8').decode('utf-8')
            return text
        except UnicodeDecodeError:
            try:
                # Попытка декодировать как Latin-1
                return text.encode('latin-1').decode('utf-8')
            except (UnicodeDecodeError, UnicodeEncodeError):
                # Если не получается, возвращаем исходный текст
                return text
    
    def _remove_urls(self, text: str) -> str:
        """Удаление URL из текста"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.sub(url_pattern, '[URL]', text)
    
    def _remove_emails(self, text: str) -> str:
        """Удаление email адресов из текста"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.sub(email_pattern, '[EMAIL]', text)
    
    def _remove_phone_numbers(self, text: str) -> str:
        """Удаление номеров телефонов из текста"""
        phone_pattern = r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        return re.sub(phone_pattern, '[PHONE]', text)
    
    def _remove_sensitive_data(self, text: str) -> str:
        """Удаление чувствительных данных из текста"""
        # Удаление номеров кредитных карт
        credit_card_pattern = r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
        text = re.sub(credit_card_pattern, '[CARD]', text)
        
        # Удаление SSN (американский формат)
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        text = re.sub(ssn_pattern, '[SSN]', text)
        
        return text
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов провайдера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up Text Cleaning Provider...")
            
            # Сбрасываем статистику
            self.cleaning_stats = {
                "total_cleaned": 0,
                "total_preprocessed": 0,
                "total_errors": 0
            }
            
            self.is_initialized = False
            self.status = ProviderStatus.STOPPED
            
            logger.info("Text Cleaning Provider cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up Text Cleaning Provider: {e}")
            self.report_error(str(e))
            return False
