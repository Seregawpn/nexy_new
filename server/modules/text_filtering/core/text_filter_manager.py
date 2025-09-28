"""
Основной координатор Text Filtering Module

Управляет предобработкой, фильтрацией и очисткой текста
"""

import asyncio
import logging
import time
import sys
import os
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

# Добавляем путь к корневой директории сервера
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from integrations.core.universal_module_interface import UniversalModuleInterface, ModuleStatus
from modules.text_filtering.config import TextFilteringConfig

logger = logging.getLogger(__name__)

class TextFilterManager(UniversalModuleInterface):
    """
    Основной координатор фильтрации текста
    
    Управляет предобработкой, очисткой и фильтрацией текстовых данных
    """
    
    def __init__(self, config: Optional[TextFilteringConfig] = None):
        """
        Инициализация менеджера фильтрации текста
        
        Args:
            config: Конфигурация модуля фильтрации текста
        """
        super().__init__("text_filtering", config.config if config else {})
        
        self.config = config or TextFilteringConfig()
        
        # Кэш для производительности
        self.cache = {} if self.config.is_feature_enabled("performance") else None
        self.cache_stats = {"hits": 0, "misses": 0, "size": 0}
        
        # Статистика
        self.total_processed = 0
        self.total_filtered = 0
        self.total_errors = 0
        self.processing_times = []
        
        logger.info("Text Filter Manager created")
    
    async def initialize(self) -> bool:
        """
        Инициализация модуля фильтрации текста
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing Text Filter Manager...")
            
            self.set_status(ModuleStatus.INITIALIZING)
            
            # Инициализируем провайдеры фильтрации
            await self._initialize_providers()
            
            self.set_status(ModuleStatus.READY)
            self.is_initialized = True
            
            logger.info("Text Filter Manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Text Filter Manager: {e}")
            self.set_status(ModuleStatus.ERROR)
            return False
    
    async def _initialize_providers(self):
        """Инициализация провайдеров фильтрации"""
        try:
            # Инициализируем провайдеры фильтрации
            from modules.text_filtering.providers.text_cleaning_provider import TextCleaningProvider
            from modules.text_filtering.providers.content_filtering_provider import ContentFilteringProvider
            from modules.text_filtering.providers.sentence_processing_provider import SentenceProcessingProvider
            
            self.text_cleaning_provider = TextCleaningProvider(self.config)
            self.content_filtering_provider = ContentFilteringProvider(self.config)
            self.sentence_processing_provider = SentenceProcessingProvider(self.config)
            
            await self.text_cleaning_provider.initialize()
            await self.content_filtering_provider.initialize()
            await self.sentence_processing_provider.initialize()
            
            logger.info("Text filter providers initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize text filter providers: {e}")
            raise
    
    async def process(self, input_data: Dict[str, Any]) -> Any:
        """
        Основная обработка фильтрации текста
        
        Args:
            input_data: Данные для обработки фильтрации
            
        Returns:
            Результат фильтрации текста
        """
        try:
            operation = input_data.get("operation", "filter_text")
            text = input_data.get("text", "")
            
            if operation == "filter_text":
                return await self.filter_text(text, input_data.get("options", {}))
            elif operation == "clean_text":
                return await self.clean_text(text, input_data.get("options", {}))
            elif operation == "split_sentences":
                return await self.split_sentences(text, input_data.get("options", {}))
            elif operation == "validate_text":
                return await self.validate_text(text, input_data.get("options", {}))
            elif operation == "preprocess_text":
                return await self.preprocess_text(text, input_data.get("options", {}))
            elif operation == "get_statistics":
                return self.get_statistics()
            else:
                logger.warning(f"Unknown text filtering operation: {operation}")
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            logger.error(f"Error processing text filtering request: {e}")
            return {"success": False, "error": str(e)}
    
    async def filter_text(self, text: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Полная фильтрация текста
        
        Args:
            text: Текст для фильтрации
            options: Дополнительные опции
            
        Returns:
            Результат фильтрации
        """
        try:
            start_time = time.time()
            
            if text is None:
                self.total_errors += 1
                return {"success": False, "error": "Text cannot be None"}
            
            if not text:
                return {"success": True, "filtered_text": "", "operations": []}
            
            # Проверяем кэш
            cache_key = self._get_cache_key(text, options or {})
            if self.cache and cache_key in self.cache:
                self.cache_stats["hits"] += 1
                cached_result = self.cache[cache_key]
                cached_result["cached"] = True
                return cached_result
            
            self.cache_stats["misses"] += 1
            
            operations = []
            filtered_text = text
            
            # 1. Предобработка
            if self.config.is_feature_enabled("preprocessing"):
                preprocessed = await self.preprocess_text(filtered_text, options or {})
                if preprocessed["success"]:
                    filtered_text = preprocessed["processed_text"]
                    operations.append("preprocessing")
            
            # 2. Очистка текста
            if self.config.is_feature_enabled("text_cleaning"):
                cleaned = await self.clean_text(filtered_text, options or {})
                if cleaned["success"]:
                    filtered_text = cleaned["cleaned_text"]
                    operations.append("text_cleaning")
            
            # 3. Фильтрация контента
            if self.config.is_feature_enabled("content_filtering"):
                if hasattr(self, 'content_filtering_provider'):
                    content_filtered = await self.content_filtering_provider.filter_content(filtered_text)
                    if content_filtered["success"]:
                        filtered_text = content_filtered["filtered_text"]
                        operations.append("content_filtering")
                else:
                    # Простая фильтрация без провайдера
                    content_config = self.config.get_content_filtering_config()
                    max_length = content_config.get("max_length", 10000)
                    if len(filtered_text) > max_length:
                        filtered_text = filtered_text[:max_length] + "..."
                        operations.append("content_filtering")
            
            # 4. Валидация
            if self.config.is_feature_enabled("validation"):
                validation = await self.validate_text(filtered_text, options or {})
                if not validation["success"]:
                    self.total_errors += 1
                    return {
                        "success": False,
                        "error": "Text validation failed",
                        "validation_errors": validation.get("errors", [])
                    }
                operations.append("validation")
            
            # Обновляем статистику
            self.total_processed += 1
            if filtered_text != text:
                self.total_filtered += 1
            
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            
            # Ограничиваем размер массива времени обработки
            if len(self.processing_times) > 1000:
                self.processing_times = self.processing_times[-500:]
            
            result = {
                "success": True,
                "original_text": text,
                "filtered_text": filtered_text,
                "operations": operations,
                "processing_time_ms": processing_time * 1000,
                "cached": False
            }
            
            # Сохраняем в кэш
            if self.cache and self._should_cache(text):
                self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error filtering text: {e}")
            self.total_errors += 1
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
            if not text:
                return {"success": True, "cleaned_text": "", "operations": []}
            
            # Если провайдер не инициализирован, используем простую очистку
            if not hasattr(self, 'text_cleaning_provider'):
                return self._simple_clean_text(text, options or {})
            
            result = await self.text_cleaning_provider.clean_text(text, options or {})
            return result
            
        except Exception as e:
            logger.error(f"Error cleaning text: {e}")
            return {"success": False, "error": str(e)}
    
    async def split_sentences(self, text: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Разбиение текста на предложения с учётом технических фраз
        
        Args:
            text: Текст для разбиения
            options: Дополнительные опции
            
        Returns:
            Результат разбиения на предложения
        """
        try:
            if not text:
                return {"success": True, "sentences": [], "remainder": "", "operations": []}
            
            # Если провайдер не инициализирован, используем простое разбиение
            if not hasattr(self, 'sentence_processing_provider'):
                return self._simple_split_sentences(text, options or {})
            
            result = await self.sentence_processing_provider.split_sentences(text, options or {})
            return result
            
        except Exception as e:
            logger.error(f"Error splitting sentences: {e}")
            return {"success": False, "error": str(e)}
    
    def count_meaningful_words(self, text: str) -> int:
        """
        Умный подсчёт значимых слов в тексте
        
        Args:
            text: Текст для подсчёта
            
        Returns:
            Количество значимых слов
        """
        try:
            if not text:
                return 0
            
            # Если провайдер инициализирован, используем его метод
            if hasattr(self, 'sentence_processing_provider'):
                return self.sentence_processing_provider.count_meaningful_words(text)
            
            # Fallback к простому подсчёту
            return len([w for w in text.split() if w.strip()])
            
        except Exception as e:
            logger.error(f"Error counting words: {e}")
            return len([w for w in text.split() if w.strip()])
    
    async def validate_text(self, text: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Валидация текста
        
        Args:
            text: Текст для валидации
            options: Дополнительные опции
            
        Returns:
            Результат валидации
        """
        try:
            if not text:
                # Пустой текст считается невалидным по умолчанию
                return {"success": True, "valid": False, "errors": ["Empty text not allowed"]}
            
            errors = []
            
            # Проверка длины
            content_config = self.config.get_content_filtering_config()
            min_length = content_config.get("min_length", 1)
            max_length = content_config.get("max_length", 10000)
            
            if len(text) < min_length:
                errors.append(f"Text too short: {len(text)} < {min_length}")
            
            if len(text) > max_length:
                errors.append(f"Text too long: {len(text)} > {max_length}")
            
            # Проверка на пустой текст
            if content_config.get("block_empty", True) and not text.strip():
                errors.append("Empty text not allowed")
            
            # Проверка на пробелы (только если текст не пустой)
            if text and content_config.get("block_whitespace_only", True) and not text.strip():
                errors.append("Whitespace-only text not allowed")
            
            # Проверка на один символ
            if content_config.get("block_single_char", False) and len(text.strip()) == 1:
                errors.append("Single character text not allowed")
            
            return {
                "success": True,
                "valid": len(errors) == 0,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error validating text: {e}")
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
            
            # Если провайдер не инициализирован, используем простую предобработку
            if not hasattr(self, 'text_cleaning_provider'):
                return self._simple_preprocess_text(text, options or {})
            
            result = await self.text_cleaning_provider.preprocess_text(text, options or {})
            return result
            
        except Exception as e:
            logger.error(f"Error preprocessing text: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_cache_key(self, text: str, options: Dict[str, Any]) -> str:
        """Генерация ключа кэша"""
        import hashlib
        content = f"{text}_{str(sorted(options.items()))}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _should_cache(self, text: str) -> bool:
        """Проверка, стоит ли кэшировать результат"""
        if not self.cache:
            return False
        
        performance_config = self.config.get_performance_config()
        max_length = performance_config.get("cache_size", 1000)
        
        return len(text) < 1000 and len(self.cache) < max_length
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Сохранение результата в кэш"""
        if not self.cache:
            return
        
        performance_config = self.config.get_performance_config()
        max_size = performance_config.get("cache_size", 1000)
        
        if len(self.cache) >= max_size:
            # Удаляем самые старые записи
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[cache_key] = result
        self.cache_stats["size"] = len(self.cache)
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов модуля
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up Text Filter Manager...")
            
            # Очищаем кэш
            if self.cache:
                self.cache.clear()
                self.cache_stats = {"hits": 0, "misses": 0, "size": 0}
            
            # Очищаем провайдеры
            if hasattr(self, 'text_cleaning_provider'):
                await self.text_cleaning_provider.cleanup()
            if hasattr(self, 'content_filtering_provider'):
                await self.content_filtering_provider.cleanup()
            if hasattr(self, 'sentence_processing_provider'):
                await self.sentence_processing_provider.cleanup()
            
            # Сбрасываем статистику
            self.total_processed = 0
            self.total_filtered = 0
            self.total_errors = 0
            self.processing_times.clear()
            
            self.set_status(ModuleStatus.STOPPED)
            self.is_initialized = False
            
            logger.info("Text Filter Manager cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up Text Filter Manager: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики фильтрации"""
        avg_processing_time = (
            sum(self.processing_times) / len(self.processing_times) * 1000
            if self.processing_times else 0
        )
        
        cache_hit_rate = (
            self.cache_stats["hits"] / (self.cache_stats["hits"] + self.cache_stats["misses"])
            if (self.cache_stats["hits"] + self.cache_stats["misses"]) > 0 else 0
        )
        
        return {
            "total_processed": self.total_processed,
            "total_filtered": self.total_filtered,
            "total_errors": self.total_errors,
            "filter_rate": self.total_filtered / self.total_processed if self.total_processed > 0 else 0,
            "error_rate": self.total_errors / self.total_processed if self.total_processed > 0 else 0,
            "avg_processing_time_ms": avg_processing_time,
            "cache_stats": self.cache_stats.copy(),
            "cache_hit_rate": cache_hit_rate,
            "processing_times_count": len(self.processing_times)
        }
    
    def _simple_clean_text(self, text: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Простая очистка текста без провайдеров"""
        try:
            if not text:
                return {"success": True, "cleaned_text": "", "operations": []}
            
            operations = []
            cleaned_text = text
            
            # Убираем лишние пробелы
            cleaned_text = ' '.join(cleaned_text.split())
            operations.append("remove_extra_whitespace")
            
            # Убираем специальные символы
            import re
            cleaned_text = re.sub(r'[^\w\s\.\,\!\?\-\:\;\(\)\[\]\{\}\"\'@#$%&*+=<>/\\|~`]', '', cleaned_text)
            operations.append("remove_special_chars")
            
            cleaned_text = cleaned_text.strip()
            
            return {
                "success": True,
                "original_text": text,
                "cleaned_text": cleaned_text,
                "operations": operations
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _simple_split_sentences(self, text: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Простое разбиение на предложения без провайдеров"""
        try:
            if not text:
                return {"success": True, "sentences": [], "operations": []}
            
            import re
            operations = []
            
            # Очищаем текст
            cleaned_text = ' '.join(text.split())
            if cleaned_text != text:
                operations.append("clean_whitespace")
            
            # Разбиваем на предложения
            sentence_pattern = r'(?<=[.!?])\s*(?=[A-ZА-Я0-9])|(?<=[.!?])\s*$'
            sentences = re.split(sentence_pattern, cleaned_text)
            
            # Фильтруем и обрабатываем предложения
            result_sentences = []
            for i, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if sentence:
                    # Добавляем точку если нужно
                    if i < len(sentences) - 1 and not any(sentence.endswith(ending) for ending in ['.', '!', '?', '...', '?!', '!?']):
                        sentence += '.'
                        operations.append("auto_add_period")
                    
                    result_sentences.append(sentence)
            
            operations.append("split_sentences")
            
            return {
                "success": True,
                "original_text": text,
                "sentences": result_sentences,
                "sentence_count": len(result_sentences),
                "operations": operations
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _simple_preprocess_text(self, text: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Простая предобработка текста без провайдеров"""
        try:
            if not text:
                return {"success": True, "processed_text": "", "operations": []}
            
            operations = []
            processed_text = text
            
            # Нормализация кавычек
            replacements = {
                '"': '"',  # Левая двойная кавычка
                '"': '"',  # Правая двойная кавычка
                ''': "'",  # Левая одинарная кавычка
                ''': "'",  # Правая одинарная кавычка
            }
            
            for old, new in replacements.items():
                if old in processed_text:
                    processed_text = processed_text.replace(old, new)
                    operations.append("normalize_quotes")
                    break
            
            return {
                "success": True,
                "original_text": text,
                "processed_text": processed_text,
                "operations": operations
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
