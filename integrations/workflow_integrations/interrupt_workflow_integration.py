#!/usr/bin/env python3
"""
InterruptWorkflowIntegration - управляет прерываниями на каждом этапе
"""

import asyncio
import logging
from typing import Dict, Any, Callable, Optional, AsyncGenerator
from datetime import datetime

logger = logging.getLogger(__name__)


class InterruptException(Exception):
    """Исключение для прерываний"""
    pass


class InterruptWorkflowIntegration:
    """
    Управляет прерываниями на каждом этапе обработки
    """
    
    def __init__(self, interrupt_manager=None):
        """
        Инициализация InterruptWorkflowIntegration
        
        Args:
            interrupt_manager: Модуль управления прерываниями
        """
        self.interrupt_manager = interrupt_manager
        self.is_initialized = False
        self.active_sessions = {}  # Отслеживание активных сессий
        
        logger.info("InterruptWorkflowIntegration создан")
    
    async def initialize(self) -> bool:
        """
        Инициализация интеграции
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Инициализация InterruptWorkflowIntegration...")
            
            # Проверяем доступность InterruptManager
            if not self.interrupt_manager:
                logger.warning("⚠️ InterruptManager не предоставлен")
            
            self.is_initialized = True
            logger.info("✅ InterruptWorkflowIntegration инициализирован успешно")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации InterruptWorkflowIntegration: {e}")
            return False
    
    async def check_interrupts(self, hardware_id: str) -> bool:
        """
        Проверка активных прерываний
        
        Args:
            hardware_id: Идентификатор оборудования
            
        Returns:
            True если есть активные прерывания, False иначе
        """
        if not self.is_initialized:
            logger.error("❌ InterruptWorkflowIntegration не инициализирован")
            return False
        
        try:
            if not self.interrupt_manager:
                logger.debug("InterruptManager не доступен, прерывания не проверяются")
                return False
            
            # Проверяем через InterruptManager
            should_interrupt = self.interrupt_manager.should_interrupt(hardware_id)
            
            if should_interrupt:
                logger.info(f"🛑 Обнаружено прерывание для {hardware_id}")
            
            return should_interrupt
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки прерываний: {e}")
            return False
    
    async def process_with_interrupts(self, workflow_func: Callable, hardware_id: str, session_id: Optional[str] = None) -> AsyncGenerator[Any, None]:
        """
        Обработка с проверкой прерываний на каждом этапе
        
        Args:
            workflow_func: Функция для выполнения
            hardware_id: Идентификатор оборудования
            session_id: Идентификатор сессии (опционально)
            
        Returns:
            Результат выполнения workflow_func
            
        Raises:
            InterruptException: При обнаружении прерывания
        """
        if not self.is_initialized:
            logger.error("❌ InterruptWorkflowIntegration не инициализирован")
            raise InterruptException("InterruptWorkflowIntegration not initialized")
        
        try:
            # Регистрируем активную сессию
            if session_id:
                self.active_sessions[session_id] = {
                    'hardware_id': hardware_id,
                    'start_time': datetime.now(),
                    'status': 'processing'
                }
                logger.debug(f"Зарегистрирована активная сессия: {session_id}")
            
            # Проверяем прерывания в начале
            if await self.check_interrupts(hardware_id):
                logger.info(f"🛑 Прерывание активно для {hardware_id}, отменяем выполнение")
                await self._cleanup_session(session_id)
                raise InterruptException(f"Global interrupt active for {hardware_id}")
            
            logger.debug(f"Выполнение workflow для {hardware_id}")
            
            # Выполняем основную функцию как async generator
            async for result in workflow_func():
                # Проверяем прерывания перед каждым yield
                if await self.check_interrupts(hardware_id):
                    logger.info(f"🛑 Прерывание обнаружено во время выполнения для {hardware_id}")
                    await self._cleanup_session(session_id)
                    raise InterruptException(f"Interrupted during processing for {hardware_id}")
                
                yield result
            
            # Проверяем прерывания после завершения
            if await self.check_interrupts(hardware_id):
                logger.info(f"🛑 Прерывание обнаружено после выполнения для {hardware_id}")
                await self._cleanup_session(session_id)
                raise InterruptException(f"Interrupted after processing for {hardware_id}")
            
            # Отмечаем сессию как завершенную
            if session_id:
                await self._complete_session(session_id)
            
            logger.debug(f"✅ Workflow завершен успешно для {hardware_id}")
            
        except InterruptException:
            # Перебрасываем InterruptException
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения workflow: {e}")
            await self._cleanup_session(session_id)
            raise
    
    async def cleanup_on_interrupt(self, hardware_id: str, session_id: Optional[str] = None):
        """
        Очистка ресурсов при прерывании
        
        Args:
            hardware_id: Идентификатор оборудования
            session_id: Идентификатор сессии (опционально)
        """
        try:
            logger.info(f"🧹 Очистка ресурсов при прерывании для {hardware_id}")
            
            # Очищаем активную сессию
            if session_id:
                await self._cleanup_session(session_id)
            
            # Очищаем все сессии для данного hardware_id
            sessions_to_cleanup = []
            for sid, session_data in self.active_sessions.items():
                if session_data.get('hardware_id') == hardware_id:
                    sessions_to_cleanup.append(sid)
            
            for sid in sessions_to_cleanup:
                await self._cleanup_session(sid)
            
            logger.info(f"✅ Ресурсы очищены для {hardware_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки ресурсов: {e}")
    
    async def _cleanup_session(self, session_id: Optional[str]):
        """
        Очистка конкретной сессии
        
        Args:
            session_id: Идентификатор сессии
        """
        if not session_id:
            return
        
        try:
            if session_id in self.active_sessions:
                session_data = self.active_sessions[session_id]
                session_data['status'] = 'interrupted'
                session_data['end_time'] = datetime.now()
                
                logger.debug(f"Сессия {session_id} отмечена как прерванная")
                
                # Удаляем из активных сессий
                del self.active_sessions[session_id]
                
                logger.debug(f"Сессия {session_id} удалена из активных")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка очистки сессии {session_id}: {e}")
    
    async def _complete_session(self, session_id: Optional[str]):
        """
        Завершение сессии
        
        Args:
            session_id: Идентификатор сессии
        """
        if not session_id:
            return
        
        try:
            if session_id in self.active_sessions:
                session_data = self.active_sessions[session_id]
                session_data['status'] = 'completed'
                session_data['end_time'] = datetime.now()
                
                logger.debug(f"Сессия {session_id} отмечена как завершенная")
                
                # Удаляем из активных сессий
                del self.active_sessions[session_id]
                
                logger.debug(f"Сессия {session_id} удалена из активных")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка завершения сессии {session_id}: {e}")
    
    def get_active_sessions(self, hardware_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Получение активных сессий
        
        Args:
            hardware_id: Фильтр по hardware_id (опционально)
            
        Returns:
            Словарь активных сессий
        """
        try:
            if hardware_id:
                # Фильтруем по hardware_id
                filtered_sessions = {}
                for sid, session_data in self.active_sessions.items():
                    if session_data.get('hardware_id') == hardware_id:
                        filtered_sessions[sid] = session_data
                return filtered_sessions
            else:
                # Возвращаем все активные сессии
                return self.active_sessions.copy()
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения активных сессий: {e}")
            return {}
    
    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            logger.info("Очистка InterruptWorkflowIntegration...")
            
            # Очищаем все активные сессии
            for session_id in list(self.active_sessions.keys()):
                await self._cleanup_session(session_id)
            
            self.is_initialized = False
            logger.info("✅ InterruptWorkflowIntegration очищен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки InterruptWorkflowIntegration: {e}")
