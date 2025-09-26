"""
Провайдер глобальных флагов прерывания
"""

import time
import logging
import sys
import os
from typing import Dict, Any, Optional

# Добавляем путь к корневой директории сервера
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from integrations.core.universal_provider_interface import UniversalProviderInterface, ProviderStatus

logger = logging.getLogger(__name__)

class GlobalFlagProvider(UniversalProviderInterface):
    """Провайдер для управления глобальными флагами прерывания"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация провайдера глобальных флагов
        
        Args:
            config: Конфигурация провайдера
        """
        super().__init__("global_flag_provider", 1, config)
        
        # Глобальные флаги
        self.global_interrupt_flag = False
        self.interrupt_hardware_id: Optional[str] = None
        self.interrupt_timestamp: Optional[float] = None
        
        # Статистика
        self.flag_set_count = 0
        self.flag_reset_count = 0
        self.last_interrupt_time: Optional[float] = None
        
        logger.info("Global Flag Provider created")
    
    async def initialize(self) -> bool:
        """
        Инициализация провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing Global Flag Provider...")
            
            # Сбрасываем флаги в начальное состояние
            self._reset_flags()
            
            self.is_initialized = True
            self.status = ProviderStatus.HEALTHY
            
            logger.info("Global Flag Provider initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Global Flag Provider: {e}")
            self.report_error(str(e))
            return False
    
    async def process(self, input_data: Any) -> Any:
        """
        Основная обработка флагов
        
        Args:
            input_data: Данные для обработки
            
        Returns:
            Результат обработки
        """
        try:
            operation = input_data.get("operation", "get_status")
            
            if operation == "set_interrupt_flag":
                return await self.set_interrupt_flag(input_data.get("hardware_id", ""))
            elif operation == "reset_flags":
                return await self.reset_flags()
            elif operation == "check_flag":
                return self.check_interrupt_flag(input_data.get("hardware_id", ""))
            elif operation == "get_status":
                return self.get_flag_status()
            else:
                logger.warning(f"Unknown operation: {operation}")
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            logger.error(f"Error processing flag request: {e}")
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def set_interrupt_flag(self, hardware_id: str) -> Dict[str, Any]:
        """
        Установка глобального флага прерывания
        
        Args:
            hardware_id: ID оборудования для прерывания
            
        Returns:
            Результат установки флага
        """
        try:
            start_time = time.time()
            
            self.global_interrupt_flag = True
            self.interrupt_hardware_id = hardware_id
            self.interrupt_timestamp = start_time
            self.last_interrupt_time = start_time
            
            self.flag_set_count += 1
            self.report_success()
            
            end_time = time.time()
            set_time = (end_time - start_time) * 1000
            
            logger.warning(f"🚨 Global interrupt flag set for {hardware_id} in {set_time:.1f}ms")
            
            return {
                "success": True,
                "hardware_id": hardware_id,
                "timestamp": start_time,
                "set_time_ms": set_time
            }
            
        except Exception as e:
            logger.error(f"Error setting interrupt flag for {hardware_id}: {e}")
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def reset_flags(self) -> Dict[str, Any]:
        """
        Сброс глобальных флагов прерывания
        
        Returns:
            Результат сброса флагов
        """
        try:
            start_time = time.time()
            
            old_hardware_id = self.interrupt_hardware_id
            
            self._reset_flags()
            
            self.flag_reset_count += 1
            self.report_success()
            
            end_time = time.time()
            reset_time = (end_time - start_time) * 1000
            
            logger.info(f"✅ Global interrupt flags reset (was: {old_hardware_id}) in {reset_time:.1f}ms")
            
            return {
                "success": True,
                "old_hardware_id": old_hardware_id,
                "timestamp": start_time,
                "reset_time_ms": reset_time
            }
            
        except Exception as e:
            logger.error(f"Error resetting interrupt flags: {e}")
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    def check_interrupt_flag(self, hardware_id: str) -> Dict[str, Any]:
        """
        Проверка глобального флага прерывания
        
        Args:
            hardware_id: ID оборудования для проверки
            
        Returns:
            Статус флага
        """
        try:
            should_interrupt = (
                self.global_interrupt_flag and 
                self.interrupt_hardware_id == hardware_id
            )
            
            # Проверяем таймаут
            timeout_expired = False
            if self.interrupt_timestamp:
                current_time = time.time()
                timeout = self.config.get("interrupt_timeout", 5.0)
                timeout_expired = current_time - self.interrupt_timestamp > timeout
            
            if timeout_expired:
                logger.warning(f"Interrupt timeout for {hardware_id}, flag should be reset")
                should_interrupt = False
            
            return {
                "should_interrupt": should_interrupt,
                "global_flag": self.global_interrupt_flag,
                "interrupt_hardware_id": self.interrupt_hardware_id,
                "timeout_expired": timeout_expired,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error checking interrupt flag: {e}")
            self.report_error(str(e))
            return {"should_interrupt": False, "error": str(e)}
    
    def get_flag_status(self) -> Dict[str, Any]:
        """
        Получение статуса флагов
        
        Returns:
            Статус всех флагов
        """
        try:
            return {
                "global_interrupt_flag": self.global_interrupt_flag,
                "interrupt_hardware_id": self.interrupt_hardware_id,
                "interrupt_timestamp": self.interrupt_timestamp,
                "flag_set_count": self.flag_set_count,
                "flag_reset_count": self.flag_reset_count,
                "last_interrupt_time": self.last_interrupt_time,
                "uptime": time.time() - (self.last_interrupt_time or time.time())
            }
            
        except Exception as e:
            logger.error(f"Error getting flag status: {e}")
            self.report_error(str(e))
            return {"error": str(e)}
    
    def _reset_flags(self):
        """Внутренний метод сброса флагов"""
        self.global_interrupt_flag = False
        self.interrupt_hardware_id = None
        self.interrupt_timestamp = None
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов провайдера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up Global Flag Provider...")
            
            # Сбрасываем флаги
            self._reset_flags()
            
            # Сбрасываем статистику
            self.flag_set_count = 0
            self.flag_reset_count = 0
            self.last_interrupt_time = None
            
            self.is_initialized = False
            self.status = ProviderStatus.STOPPED
            
            logger.info("Global Flag Provider cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up Global Flag Provider: {e}")
            self.report_error(str(e))
            return False
