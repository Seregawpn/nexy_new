"""
Memory Manager - координатор всех операций с памятью

Обеспечивает:
- Получение контекста памяти для LLM
- Координацию анализа и обновления памяти
- Интеграцию с Database Module
- Совместимость с существующим TextProcessor
"""

import asyncio
import logging
from typing import Dict, Optional, Tuple

from ..config import MemoryConfig
from ..providers.memory_analyzer import MemoryAnalyzer

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Координатор всех операций с памятью пользователей.
    
    Интегрируется с существующим TextProcessor без изменения его логики.
    Предоставляет те же методы, которые ожидает TextProcessor.
    """
    
    def __init__(self, db_manager=None):
        """
        Инициализация MemoryManager.
        
        Args:
            db_manager: Экземпляр DatabaseManager для работы с БД
        """
        self.config = MemoryConfig()
        self.db_manager = db_manager
        self.memory_analyzer = None
        self.is_initialized = False
        
    async def initialize(self):
        """Инициализация MemoryManager"""
        try:
            # Инициализируем MemoryAnalyzer если доступен API ключ
            if self.config.gemini_api_key and self.config.validate_config():
                try:
                    self.memory_analyzer = MemoryAnalyzer(self.config.gemini_api_key)
                    logger.info("✅ MemoryAnalyzer initialized successfully")
                except Exception as e:
                    logger.warning(f"⚠️ MemoryAnalyzer initialization failed: {e}")
                    self.memory_analyzer = None
            else:
                logger.warning("⚠️ MemoryAnalyzer not initialized - missing API key or invalid config")
            
            self.is_initialized = True
            logger.info("✅ MemoryManager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ MemoryManager initialization failed: {e}")
            raise
    
    def set_database_manager(self, db_manager):
        """
        Устанавливает DatabaseManager для работы с памятью.
        
        Args:
            db_manager: Экземпляр DatabaseManager
        
        Этот метод нужен для совместимости с существующим TextProcessor.
        """
        self.db_manager = db_manager
        logger.info("✅ DatabaseManager set in MemoryManager")
    
    async def get_memory_context(self, hardware_id: str) -> str:
        """
        Получает контекст памяти для LLM.
        
        Args:
            hardware_id: Аппаратный ID пользователя
            
        Returns:
            Строка с контекстом памяти или пустая строка
            
        Этот метод заменяет логику из text_processor.py (строки 254-282)
        """
        if not hardware_id or not self.db_manager:
            return ""
        
        try:
            # Таймаут 2 секунды на получение памяти (как в оригинале)
            memory_data = await asyncio.wait_for(
                asyncio.to_thread(self.db_manager.get_user_memory, hardware_id),
                timeout=self.config.memory_timeout
            )
            
            if memory_data.get('short') or memory_data.get('long'):
                memory_context = f"""
🧠 MEMORY CONTEXT (for response context):

📋 SHORT-TERM MEMORY (current session):
{memory_data.get('short', 'No short-term memory')}

📚 LONG-TERM MEMORY (user information):
{memory_data.get('long', 'No long-term memory')}

💡 MEMORY USAGE INSTRUCTIONS:
- Use short-term memory to understand current conversation context
- Use long-term memory for response personalization (name, preferences, important details)
- If memory is not relevant to current request - ignore it
- Memory should complement the answer, not replace it
- Priority: current request > short-term memory > long-term memory
                """
                
                logger.info(f"🧠 Memory obtained for {hardware_id}: short-term ({len(memory_data.get('short', ''))} chars), long-term ({len(memory_data.get('long', ''))} chars)")
                return memory_context
            else:
                logger.info(f"🧠 No memory found for {hardware_id}")
                return ""
                    
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Memory retrieval timeout for {hardware_id}")
            return ""
        except Exception as e:
            logger.error(f"❌ Error getting memory context for {hardware_id}: {e}")
            return ""
    
    async def analyze_conversation(self, prompt: str, response: str) -> Tuple[str, str]:
        """
        Анализирует диалог для извлечения памяти.
        
        Args:
            prompt: Запрос пользователя
            response: Ответ ассистента
            
        Returns:
            Кортеж (short_memory, long_memory)
            
        Этот метод заменяет вызов memory_analyzer.analyze_conversation()
        """
        if not self.memory_analyzer:
            logger.debug("🧠 MemoryAnalyzer not available - skipping memory analysis")
            return "", ""
        
        try:
            return await self.memory_analyzer.analyze_conversation(prompt, response)
        except Exception as e:
            logger.error(f"❌ Error analyzing conversation: {e}")
            return "", ""
    
    async def update_memory_background(self, hardware_id: str, prompt: str, response: str):
        """
        Фоновое обновление памяти пользователя.
        
        Args:
            hardware_id: Аппаратный ID пользователя
            prompt: Запрос пользователя
            response: Ответ ассистента
            
        Этот метод заменяет _update_memory_background() из text_processor.py
        """
        try:
            logger.debug(f"🔄 Starting background memory update for {hardware_id}")
            
            # Анализируем разговор для извлечения памяти
            short_memory, long_memory = await self.analyze_conversation(prompt, response)
            
            # Если есть что сохранять
            if short_memory or long_memory:
                # Проверяем наличие менеджера базы данных
                if not self.db_manager:
                    logger.warning("⚠️ DatabaseManager is not set in MemoryManager; skipping memory update")
                    return
                # Обновляем память в базе данных
                success = await asyncio.to_thread(
                    self.db_manager.update_user_memory,
                    hardware_id,
                    short_memory,
                    long_memory
                )
                
                if success:
                    logger.info(f"✅ Memory for {hardware_id} updated: short-term ({len(short_memory)} chars), long-term ({len(long_memory)} chars)")
                else:
                    logger.warning(f"⚠️ Could not update memory for {hardware_id}")
            else:
                logger.debug(f"🧠 No information found for {hardware_id} to remember")
                
        except Exception as e:
            logger.error(f"❌ Error in background memory update for {hardware_id}: {e}")
            # НЕ поднимаем исключение - это фоновая задача
    
    def is_available(self) -> bool:
        """
        Проверяет доступность модуля памяти.
        
        Returns:
            True если модуль готов к работе
        """
        return self.memory_analyzer is not None and self.db_manager is not None
    
    async def cleanup_expired_memory(self, hours: int = 24) -> int:
        """
        Очищает устаревшую краткосрочную память.
        
        Args:
            hours: Количество часов, после которых память считается устаревшей
            
        Returns:
            Количество очищенных записей
        """
        if not self.db_manager:
            return 0
        
        try:
            return await asyncio.to_thread(
                self.db_manager.cleanup_expired_short_term_memory,
                hours
            )
        except Exception as e:
            logger.error(f"❌ Error cleaning up expired memory: {e}")
            return 0
