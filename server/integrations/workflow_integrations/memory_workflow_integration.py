#!/usr/bin/env python3
"""
MemoryWorkflowIntegration - управляет памятью параллельно основному потоку
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MemoryWorkflowIntegration:
    """
    Управляет памятью параллельно основному потоку обработки
    """
    
    def __init__(self, memory_manager=None):
        """
        Инициализация MemoryWorkflowIntegration
        
        Args:
            memory_manager: Модуль управления памятью
        """
        self.memory_manager = memory_manager
        self.is_initialized = False
        self.memory_cache = {}  # Кэш для быстрого доступа
        self.cache_ttl = 300  # 5 минут TTL для кэша
        
        logger.info("MemoryWorkflowIntegration создан")
    
    async def initialize(self) -> bool:
        """
        Инициализация интеграции
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Инициализация MemoryWorkflowIntegration...")
            
            # Проверяем доступность модуля памяти
            if not self.memory_manager:
                logger.warning("⚠️ MemoryManager не предоставлен")
            
            self.is_initialized = True
            logger.info("✅ MemoryWorkflowIntegration инициализирован успешно")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации MemoryWorkflowIntegration: {e}")
            return False
    
    async def get_memory_context_parallel(self, hardware_id: str) -> Optional[Dict[str, Any]]:
        """
        Асинхронное получение контекста памяти (неблокирующее)
        
        Args:
            hardware_id: Идентификатор оборудования
            
        Returns:
            Контекст памяти или None при ошибке
        """
        if not self.is_initialized:
            logger.error("❌ MemoryWorkflowIntegration не инициализирован")
            return None
        
        try:
            logger.debug(f"Получение контекста памяти для {hardware_id}")
            
            # Проверяем кэш
            cached_context = self._get_cached_memory(hardware_id)
            if cached_context:
                logger.debug("✅ Используем кэшированный контекст памяти")
                return cached_context
            
            # Получаем контекст из памяти
            if self.memory_manager and hasattr(self.memory_manager, 'get_user_context'):
                logger.debug("Запрос контекста памяти через MemoryManager")
                
                # Запускаем получение памяти в фоне
                memory_task = asyncio.create_task(
                    self._fetch_memory_context(hardware_id)
                )
                
                try:
                    memory_context = await asyncio.wait_for(memory_task, timeout=5.0)
                    
                    # Кэшируем результат
                    self._cache_memory(hardware_id, memory_context)
                    
                    logger.debug(f"✅ Получен контекст памяти: {len(memory_context) if memory_context else 0} элементов")
                    return memory_context
                    
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ Таймаут получения контекста памяти для {hardware_id}")
                    return None
            else:
                logger.debug("MemoryManager не доступен или не имеет метода get_user_context")
                return None
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения контекста памяти: {e}")
            return None
    
    async def save_to_memory_background(self, data: Dict[str, Any]) -> bool:
        """
        Фоновое сохранение в память (неблокирующее)
        
        Args:
            data: Данные для сохранения
            
        Returns:
            True если сохранение запущено, False при ошибке
        """
        if not self.is_initialized:
            logger.error("❌ MemoryWorkflowIntegration не инициализирован")
            return False
        
        try:
            logger.debug("Запуск фонового сохранения в память")
            
            # Проверяем доступность MemoryManager
            if not self.memory_manager:
                logger.warning("⚠️ MemoryManager не доступен для сохранения")
                return False
            
            if not hasattr(self.memory_manager, 'update_memory_background'):
                logger.warning("⚠️ MemoryManager не имеет метода update_memory_background")
                return False
            
            # Запускаем сохранение в фоне
            asyncio.create_task(
                self._save_memory_background(data)
            )
            
            logger.debug("✅ Фоновое сохранение в память запущено")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска фонового сохранения: {e}")
            return False
    
    async def _fetch_memory_context(self, hardware_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение контекста памяти из MemoryManager
        
        Args:
            hardware_id: Идентификатор оборудования
            
        Returns:
            Контекст памяти
        """
        try:
            if not self.memory_manager:
                return None
            
            # Вызываем метод MemoryManager
            memory_context = await self.memory_manager.get_user_context(hardware_id)
            
            if memory_context:
                logger.debug(f"Получен контекст памяти: {type(memory_context)}")
                return memory_context
            else:
                logger.debug("Контекст памяти пуст")
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения контекста из MemoryManager: {e}")
            return None
    
    async def _save_memory_background(self, data: Dict[str, Any]):
        """
        Фоновое сохранение данных в память
        
        Args:
            data: Данные для сохранения
        """
        try:
            logger.debug("Выполнение фонового сохранения в память")
            
            # Подготавливаем данные для сохранения
            memory_data = self._prepare_memory_data(data)
            
            # Сохраняем через MemoryManager
            await self.memory_manager.update_memory_background(memory_data)
            
            logger.debug("✅ Фоновое сохранение в память завершено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка фонового сохранения в память: {e}")
    
    def _prepare_memory_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Подготовка данных для сохранения в память
        
        Args:
            data: Исходные данные
            
        Returns:
            Подготовленные данные
        """
        try:
            # Добавляем метаданные
            memory_data = {
                'timestamp': datetime.now().isoformat(),
                'hardware_id': data.get('hardware_id'),
                'session_id': data.get('session_id'),
                'text': data.get('text', ''),
                'screenshot': data.get('screenshot'),
                'processed_text': data.get('processed_text', ''),
                'audio_generated': data.get('audio_generated', False)
            }
            
            logger.debug(f"Подготовлены данные для сохранения: {len(memory_data)} полей")
            return memory_data
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка подготовки данных для памяти: {e}")
            return data
    
    def _get_cached_memory(self, hardware_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение кэшированного контекста памяти
        
        Args:
            hardware_id: Идентификатор оборудования
            
        Returns:
            Кэшированный контекст или None
        """
        try:
            if hardware_id not in self.memory_cache:
                return None
            
            cache_entry = self.memory_cache[hardware_id]
            cache_time = cache_entry.get('timestamp')
            
            # Проверяем TTL
            if cache_time:
                cache_age = datetime.now() - cache_time
                if cache_age > timedelta(seconds=self.cache_ttl):
                    # Кэш устарел, удаляем
                    del self.memory_cache[hardware_id]
                    logger.debug(f"Кэш памяти для {hardware_id} устарел и удален")
                    return None
            
            logger.debug(f"Используем кэшированную память для {hardware_id}")
            return cache_entry.get('context')
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения кэшированной памяти: {e}")
            return None
    
    def _cache_memory(self, hardware_id: str, memory_context: Dict[str, Any]):
        """
        Кэширование контекста памяти
        
        Args:
            hardware_id: Идентификатор оборудования
            memory_context: Контекст памяти
        """
        try:
            self.memory_cache[hardware_id] = {
                'context': memory_context,
                'timestamp': datetime.now()
            }
            
            logger.debug(f"Контекст памяти для {hardware_id} закэширован")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка кэширования памяти: {e}")
    
    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            logger.info("Очистка MemoryWorkflowIntegration...")
            
            # Очищаем кэш
            self.memory_cache.clear()
            
            self.is_initialized = False
            logger.info("✅ MemoryWorkflowIntegration очищен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки MemoryWorkflowIntegration: {e}")
