"""
Провайдер обработки предложений
"""

import re
import logging
import sys
import os
from typing import Dict, Any, Optional, List

# Добавляем путь к корневой директории сервера
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from integration.core.universal_provider_interface import UniversalProviderInterface, ProviderStatus

logger = logging.getLogger(__name__)

class SentenceProcessingProvider(UniversalProviderInterface):
    """Провайдер для обработки предложений"""
    
    def __init__(self, config):
        """
        Инициализация провайдера обработки предложений
        
        Args:
            config: Конфигурация провайдера
        """
        super().__init__("sentence_processing_provider", 1, config.config)
        
        self.config = config
        self.processing_stats = {
            "total_split": 0,
            "total_sentences": 0,
            "total_errors": 0
        }
        
        logger.info("Sentence Processing Provider created")
    
    async def initialize(self) -> bool:
        """
        Инициализация провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing Sentence Processing Provider...")
            
            # Загружаем конфигурацию
            self.sentence_config = self.config.get_sentence_splitting_config()
            
            self.is_initialized = True
            self.status = ProviderStatus.HEALTHY
            
            logger.info("Sentence Processing Provider initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Sentence Processing Provider: {e}")
            self.report_error(str(e))
            return False
    
    async def process(self, input_data: Any) -> Any:
        """
        Основная обработка предложений
        
        Args:
            input_data: Данные для обработки
            
        Returns:
            Результат обработки
        """
        try:
            operation = input_data.get("operation", "split_sentences")
            text = input_data.get("text", "")
            options = input_data.get("options", {})
            
            if operation == "split_sentences":
                return await self.split_sentences(text, options)
            elif operation == "is_sentence_complete":
                return await self.is_sentence_complete(text)
            else:
                logger.warning(f"Unknown operation: {operation}")
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            logger.error(f"Error processing sentence request: {e}")
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def split_sentences(self, text: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Разбиение текста на предложения
        
        Args:
            text: Текст для разбиения
            options: Дополнительные опции
            
        Returns:
            Результат разбиения на предложения
        """
        try:
            if not text:
                return {"success": True, "sentences": [], "operations": []}
            
            operations = []
            
            # Очищаем текст перед разбиением
            cleaned_text = ' '.join(text.split())
            if cleaned_text != text:
                operations.append("clean_whitespace")
            
            # Используем конфигурацию для разбиения
            sentence_pattern = self.sentence_config.get("sentence_pattern", r'(?<=[.!?])\s*(?=[A-ZА-Я0-9])|(?<=[.!?])\s*$')
            sentence_endings = self.sentence_config.get("sentence_endings", ['.', '!', '?', '...', '?!', '!?'])
            auto_add_period = self.sentence_config.get("auto_add_period", True)
            
            # Разбиваем по паттерну
            sentences = re.split(sentence_pattern, cleaned_text)
            
            # Фильтруем и обрабатываем предложения
            result_sentences = []
            for i, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if sentence:
                    # Если это не последнее предложение, проверяем знак препинания
                    if i < len(sentences) - 1 and auto_add_period:
                        # Ищем знак препинания в конце
                        if not any(sentence.endswith(ending) for ending in sentence_endings):
                            sentence += '.'
                            operations.append("auto_add_period")
                    
                    result_sentences.append(sentence)
            
            operations.append("split_sentences")
            
            # Обновляем статистику
            self.processing_stats["total_split"] += 1
            self.processing_stats["total_sentences"] += len(result_sentences)
            self.report_success()
            
            return {
                "success": True,
                "original_text": text,
                "sentences": result_sentences,
                "sentence_count": len(result_sentences),
                "operations": operations
            }
            
        except Exception as e:
            logger.error(f"Error splitting sentences: {e}")
            self.processing_stats["total_errors"] += 1
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def is_sentence_complete(self, text: str) -> Dict[str, Any]:
        """
        Проверка завершенности предложения
        
        Args:
            text: Текст для проверки
            
        Returns:
            Результат проверки
        """
        try:
            if not text or not text.strip():
                return {"success": True, "complete": False, "reason": "empty_text"}
            
            text = text.strip()
            
            # Проверяем, заканчивается ли текст знаком окончания предложения
            sentence_endings = self.sentence_config.get("sentence_endings", ['.', '!', '?', '...', '?!', '!?'])
            is_complete = any(text.endswith(ending) for ending in sentence_endings)
            
            return {
                "success": True,
                "complete": is_complete,
                "text": text,
                "reason": "sentence_endings" if is_complete else "no_ending"
            }
            
        except Exception as e:
            logger.error(f"Error checking sentence completeness: {e}")
            self.processing_stats["total_errors"] += 1
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов провайдера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up Sentence Processing Provider...")
            
            # Сбрасываем статистику
            self.processing_stats = {
                "total_split": 0,
                "total_sentences": 0,
                "total_errors": 0
            }
            
            self.is_initialized = False
            self.status = ProviderStatus.STOPPED
            
            logger.info("Sentence Processing Provider cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up Sentence Processing Provider: {e}")
            self.report_error(str(e))
            return False
