"""
Режим обработки - обработка команд и данных
"""

import logging
import time
from typing import Optional, Dict, Any
from ..core.types import AppMode, ModeEvent, ModeStatus

logger = logging.getLogger(__name__)

class ProcessingMode:
    """Режим обработки - обработка команд и данных"""
    
    def __init__(self, grpc_client=None, state_manager=None):
        self.grpc_client = grpc_client
        self.state_manager = state_manager
        self.is_active = False
        self.processing_start_time = None
        self.current_task = None
        
    async def enter_mode(self, context: Dict[str, Any] = None):
        """Вход в режим обработки"""
        try:
            logger.info("⚙️ Вход в режим обработки")
            self.is_active = True
            self.processing_start_time = time.time()
            self.current_task = context.get('task') if context else None
            
            # Логика входа в режим обработки
            if self.state_manager:
                try:
                    # Обновляем состояние системы
                    await self.state_manager.set_processing_state(True)
                    logger.info("📊 Состояние обработки обновлено")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось обновить состояние: {e}")
                    
            logger.info("✅ Режим обработки активирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка входа в режим обработки: {e}")
            self.is_active = False
            
    async def exit_mode(self):
        """Выход из режима обработки"""
        try:
            logger.info("🛑 Выход из режима обработки")
            self.is_active = False
            self.current_task = None
            
            # Логика выхода из режима обработки
            if self.state_manager:
                try:
                    await self.state_manager.set_processing_state(False)
                    logger.info("📊 Состояние обработки сброшено")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось сбросить состояние: {e}")
                    
            self.processing_start_time = None
            logger.info("✅ Режим обработки деактивирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка выхода из режима обработки: {e}")
            
    async def process_command(self, command: str, data: Dict[str, Any] = None):
        """Обработка команды"""
        try:
            logger.info(f"🔧 Обработка команды: {command}")
            
            # Отправляем команду на сервер
            if self.grpc_client:
                try:
                    response = await self.grpc_client.process_command(command, data)
                    logger.info(f"📡 Команда отправлена на сервер: {response}")
                    return response
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки команды на сервер: {e}")
                    return None
            else:
                logger.warning("⚠️ gRPC клиент недоступен")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки команды: {e}")
            return None
            
    async def handle_interrupt(self):
        """Обработка прерывания в режиме обработки"""
        try:
            logger.info("⚠️ Прерывание в режиме обработки")
            
            # Прерываем текущую обработку
            if self.current_task:
                logger.info(f"🛑 Прерывание задачи: {self.current_task}")
                self.current_task = None
                
            logger.info("✅ Прерывание обработано")
            
        except Exception as e:
            logger.error(f"❌ Ошибка прерывания в режиме обработки: {e}")
            
    def is_processing(self) -> bool:
        """Проверяет, идет ли обработка"""
        return self.is_active and self.current_task is not None
            
    def get_processing_duration(self) -> float:
        """Возвращает длительность обработки в секундах"""
        if not self.processing_start_time:
            return 0.0
            
        try:
            return time.time() - self.processing_start_time
        except Exception as e:
            logger.warning(f"⚠️ Ошибка расчета длительности обработки: {e}")
            return 0.0
            
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус режима обработки"""
        return {
            "is_active": self.is_active,
            "is_processing": self.is_processing(),
            "processing_duration": self.get_processing_duration(),
            "current_task": self.current_task,
            "grpc_client_available": self.grpc_client is not None,
            "state_manager_available": self.state_manager is not None,
        }