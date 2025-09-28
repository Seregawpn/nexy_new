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

from integrations.core.universal_provider_interface import UniversalProviderInterface, ProviderStatus

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
            
            operations = []
            
            # Очищаем текст перед разбиением
            cleaned_text = ' '.join(text.split())
            if cleaned_text != text:
                operations.append("clean_whitespace")
            
            # Используем улучшенную логику разбиения с защитой технических фраз
            sentences, remainder = self._split_complete_sentences(cleaned_text)
            
            operations.append("smart_sentence_splitting")
            
            self.processing_stats["total_split"] += 1
            self.processing_stats["total_sentences"] += len(sentences)
            self.report_success()
            
            return {
                "success": True,
                "sentences": sentences,
                "remainder": remainder,
                "operations": operations
            }
            
        except Exception as e:
            logger.error(f"Error splitting sentences: {e}")
            self.processing_stats["total_errors"] += 1
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    def _split_complete_sentences(self, text: str) -> tuple[list[str], str]:
        """
        Делит текст на законченные предложения и остаток (незавершённый хвост).
        Сохраняет завершающую пунктуацию в предложениях.
        Учитывает технические фразы типа "main.py", "12.10", "v1.2.3".
        """
        sentences: list[str] = []
        remainder = (text or "")
        if not remainder:
            return sentences, ""
        try:
            # Более простой и надёжный подход: сначала защищаем технические фразы
            # Заменяем технические точки на временные маркеры
            protected_text = remainder
            
            # Защищаем файловые расширения: main.py -> main__DOT__py
            protected_text = re.sub(r'(\w+)\.(\w{1,4})\b', r'\1__DOT__\2', protected_text)
            
            # Защищаем версии: 1.2.3 -> 1__DOT__2__DOT__3
            protected_text = re.sub(r'(\d+)\.(\d+)(?:\.(\d+))?', r'\1__DOT__\2\3', protected_text)
            
            # Защищаем IP адреса: 192.168.1.1 -> 192__DOT__168__DOT__1__DOT__1
            protected_text = re.sub(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', r'\1__DOT__\2__DOT__\3__DOT__\4', protected_text)
            
            # Защищаем порты: :8080 -> __COLON__8080
            protected_text = re.sub(r':(\d+)', r'__COLON__\1', protected_text)
            
            # Теперь разбиваем по обычным знакам препинания
            parts = re.split(r'([.!?]+)', protected_text)
            sentences = []
            current = ""
            
            for part in parts:
                if part in '.!?':
                    current += part
                    if current.strip():
                        # Восстанавливаем технические фразы
                        restored = current.replace('__DOT__', '.').replace('__COLON__', ':')
                        sentences.append(restored.strip())
                    current = ""
                else:
                    current += part
            
            # Восстанавливаем остаток
            tail = current.replace('__DOT__', '.').replace('__COLON__', ':').strip()
            return sentences, tail
        except Exception:
            # Fallback к простому разбиению
            parts = re.split(r'([.!?]+)', remainder)
            sentences = []
            current = ""
            for part in parts:
                if part in '.!?':
                    current += part
                    if current.strip():
                        sentences.append(current.strip())
                    current = ""
                else:
                    current += part
            return sentences, current.strip()
    
    def count_meaningful_words(self, text: str) -> int:
        """
        Умный подсчёт значимых слов в тексте.
        Учитывает технические фразы, версии, файлы как отдельные "слова".
        
        Примеры:
        - "main.py" = 1 слово (не 2)
        - "12.10" = 1 слово (не 2) 
        - "v1.2.3" = 1 слово (не 3)
        - "192.168.1.1" = 1 слово (не 4)
        - "Hello world!" = 2 слова
        """
        if not text:
            return 0
        
        try:
            # Разбиваем по пробелам и фильтруем пустые
            parts = [p.strip() for p in text.split() if p.strip()]
            
            # Подсчитываем значимые части
            meaningful_count = 0
            for part in parts:
                # Убираем пунктуацию с концов для анализа, но сохраняем двоеточие для портов
                clean_part = part.strip('.,!?;')
                
                # Технические паттерны считаем как одно "слово"
                if (re.match(r'^[a-zA-Z0-9_-]+\.\w{1,4}$', clean_part) or  # файлы: main.py, config.json
                    re.match(r'^\d+\.\d+(\.\d+)*$', clean_part) or          # версии: 1.2.3, 12.10
                    re.match(r'^v\d+\.\d+(\.\d+)*$', clean_part) or         # версии: v1.2.3
                    re.match(r'^\d+\.\d+\.\d+\.\d+$', clean_part) or        # IP: 192.168.1.1
                    re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', clean_part) or    # IP:PORT: 192.168.1.1:8080
                    re.match(r'^[a-zA-Z0-9_-]+$', clean_part)):             # обычные слова
                    meaningful_count += 1
                else:
                    # Для сложных случаев разбиваем по знакам препинания
                    sub_parts = re.findall(r'[a-zA-Z0-9_-]+', clean_part)
                    meaningful_count += len(sub_parts) if sub_parts else 1
            
            return meaningful_count
            
        except Exception:
            # Fallback к простому подсчёту
            return len([w for w in text.split() if w.strip()])
    
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



