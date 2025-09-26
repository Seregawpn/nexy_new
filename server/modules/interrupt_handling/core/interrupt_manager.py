"""
Основной координатор Interrupt Handling Module

Управляет прерываниями, глобальными флагами и отменой операций
"""

import asyncio
import logging
import time
import sys
import os
from typing import Dict, Any, Optional, Set, Callable
from datetime import datetime

# Добавляем путь к корневой директории сервера
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from integrations.core.universal_module_interface import UniversalModuleInterface, ModuleStatus
from modules.interrupt_handling.config import InterruptHandlingConfig

logger = logging.getLogger(__name__)

class InterruptManager(UniversalModuleInterface):
    """
    Основной координатор обработки прерываний
    
    Управляет глобальными флагами, активными сессиями и отменой операций
    """
    
    def __init__(self, config: Optional[InterruptHandlingConfig] = None):
        """
        Инициализация менеджера прерываний
        
        Args:
            config: Конфигурация модуля прерываний
        """
        super().__init__("interrupt_handling", config.config if config else {})
        
        self.config = config or InterruptHandlingConfig()
        
        # Глобальные флаги прерывания
        self.global_interrupt_flag = False
        self.interrupt_hardware_id: Optional[str] = None
        self.interrupt_timestamp: Optional[float] = None
        
        # Активные сессии
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_counter = 0
        
        # Зарегистрированные модули для прерывания
        self.registered_modules: Dict[str, Any] = {}
        
        # Callback функции для прерывания
        self.interrupt_callbacks: Set[Callable] = set()
        
        # Статистика
        self.total_interrupts = 0
        self.successful_interrupts = 0
        self.failed_interrupts = 0
        
        logger.info("Interrupt Manager created")
    
    async def initialize(self) -> bool:
        """
        Инициализация модуля прерываний
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing Interrupt Manager...")
            
            self.set_status(ModuleStatus.INITIALIZING)
            
            # Проверяем конфигурацию
            if not self.config.get("global_interrupt_enabled", True):
                logger.warning("Global interrupt is disabled in configuration")
            
            # Инициализируем базовые компоненты
            await self._initialize_components()
            
            self.set_status(ModuleStatus.READY)
            self.is_initialized = True
            
            logger.info("Interrupt Manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Interrupt Manager: {e}")
            self.set_status(ModuleStatus.ERROR)
            return False
    
    async def _initialize_components(self):
        """Инициализация базовых компонентов"""
        try:
            # Инициализируем провайдеры прерывания
            from modules.interrupt_handling.providers.global_flag_provider import GlobalFlagProvider
            from modules.interrupt_handling.providers.session_tracker_provider import SessionTrackerProvider
            
            self.global_flag_provider = GlobalFlagProvider(self.config)
            self.session_tracker_provider = SessionTrackerProvider(self.config)
            
            await self.global_flag_provider.initialize()
            await self.session_tracker_provider.initialize()
            
            logger.info("Interrupt providers initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize interrupt providers: {e}")
            raise
    
    async def process(self, input_data: Dict[str, Any]) -> Any:
        """
        Основная обработка прерываний
        
        Args:
            input_data: Данные для обработки прерывания
            
        Returns:
            Результат обработки прерывания
        """
        try:
            operation = input_data.get("operation", "interrupt_session")
            
            if operation == "interrupt_session":
                return await self.interrupt_session(input_data.get("hardware_id", ""))
            elif operation == "register_module":
                return await self.register_module(
                    input_data.get("module_name", ""),
                    input_data.get("module_instance")
                )
            elif operation == "register_callback":
                return await self.register_callback(input_data.get("callback"))
            elif operation == "check_interrupt":
                return self.should_interrupt(input_data.get("hardware_id", ""))
            else:
                logger.warning(f"Unknown interrupt operation: {operation}")
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            logger.error(f"Error processing interrupt request: {e}")
            return {"success": False, "error": str(e)}
    
    async def interrupt_session(self, hardware_id: str) -> Dict[str, Any]:
        """
        Прерывание сессии для указанного hardware_id
        
        Args:
            hardware_id: ID оборудования для прерывания
            
        Returns:
            Результат прерывания
        """
        try:
            interrupt_start_time = time.time()
            
            logger.warning(f"🚨 Interrupt session requested for hardware_id: {hardware_id}")
            
            # Устанавливаем глобальные флаги
            await self._set_global_interrupt_flags(hardware_id)
            
            # Прерываем все зарегистрированные модули
            interrupted_modules = await self._interrupt_all_modules(hardware_id)
            
            # Очищаем активные сессии
            cleaned_sessions = await self._cleanup_sessions(hardware_id)
            
            # Обновляем статистику
            self.total_interrupts += 1
            self.successful_interrupts += 1
            
            interrupt_end_time = time.time()
            total_time = (interrupt_end_time - interrupt_start_time) * 1000
            
            logger.warning(f"✅ Interrupt completed for {hardware_id} in {total_time:.1f}ms")
            
            return {
                "success": True,
                "hardware_id": hardware_id,
                "interrupted_modules": interrupted_modules,
                "cleaned_sessions": cleaned_sessions,
                "total_time_ms": total_time,
                "timestamp": interrupt_start_time
            }
            
        except Exception as e:
            logger.error(f"Error interrupting session for {hardware_id}: {e}")
            self.failed_interrupts += 1
            
            return {
                "success": False,
                "hardware_id": hardware_id,
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def _set_global_interrupt_flags(self, hardware_id: str):
        """Установка глобальных флагов прерывания"""
        try:
            self.global_interrupt_flag = True
            self.interrupt_hardware_id = hardware_id
            self.interrupt_timestamp = time.time()
            
            # Обновляем провайдер глобальных флагов
            if hasattr(self, 'global_flag_provider'):
                await self.global_flag_provider.set_interrupt_flag(hardware_id)
            
            logger.warning(f"🚨 Global interrupt flags set for {hardware_id}")
            
        except Exception as e:
            logger.error(f"Error setting global interrupt flags: {e}")
            raise
    
    async def _interrupt_all_modules(self, hardware_id: str) -> list:
        """Прерывание всех зарегистрированных модулей"""
        interrupted_modules = []
        
        try:
            for module_name, module_instance in self.registered_modules.items():
                try:
                    if not self.config.is_module_interrupt_enabled(module_name):
                        logger.debug(f"Interrupt disabled for module: {module_name}")
                        continue
                    
                    # Получаем методы прерывания для модуля
                    interrupt_methods = self.config.get_module_interrupt_methods(module_name)
                    module_timeout = self.config.get_module_timeout(module_name)
                    
                    # Вызываем методы прерывания
                    for method_name in interrupt_methods:
                        if hasattr(module_instance, method_name):
                            method = getattr(module_instance, method_name)
                            
                            # Вызываем метод с таймаутом
                            try:
                                if asyncio.iscoroutinefunction(method):
                                    await asyncio.wait_for(method(), timeout=module_timeout)
                                else:
                                    method()
                                
                                logger.warning(f"🚨 Module {module_name}.{method_name} interrupted for {hardware_id}")
                                
                            except asyncio.TimeoutError:
                                logger.error(f"Timeout interrupting {module_name}.{method_name}")
                            except Exception as e:
                                logger.error(f"Error interrupting {module_name}.{method_name}: {e}")
                    
                    interrupted_modules.append(module_name)
                    
                except Exception as e:
                    logger.error(f"Error interrupting module {module_name}: {e}")
            
            # Вызываем callback функции
            for callback in self.interrupt_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(hardware_id)
                    else:
                        callback(hardware_id)
                except Exception as e:
                    logger.error(f"Error in interrupt callback: {e}")
            
            logger.info(f"Interrupted {len(interrupted_modules)} modules for {hardware_id}")
            
        except Exception as e:
            logger.error(f"Error interrupting modules: {e}")
        
        return interrupted_modules
    
    async def _cleanup_sessions(self, hardware_id: str) -> list:
        """Очистка активных сессий для hardware_id"""
        cleaned_sessions = []
        
        try:
            sessions_to_remove = []
            
            for session_id, session_data in self.active_sessions.items():
                if session_data.get("hardware_id") == hardware_id:
                    sessions_to_remove.append(session_id)
                    cleaned_sessions.append(session_id)
            
            # Удаляем сессии
            for session_id in sessions_to_remove:
                del self.active_sessions[session_id]
            
            logger.info(f"Cleaned {len(cleaned_sessions)} sessions for {hardware_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
        
        return cleaned_sessions
    
    async def register_module(self, module_name: str, module_instance: Any) -> bool:
        """
        Регистрация модуля для прерывания
        
        Args:
            module_name: Имя модуля
            module_instance: Экземпляр модуля
            
        Returns:
            True если регистрация успешна, False иначе
        """
        try:
            self.registered_modules[module_name] = module_instance
            logger.info(f"Module {module_name} registered for interrupt handling")
            return True
            
        except Exception as e:
            logger.error(f"Error registering module {module_name}: {e}")
            return False
    
    async def register_callback(self, callback: Callable) -> bool:
        """
        Регистрация callback функции для прерывания
        
        Args:
            callback: Функция обратного вызова
            
        Returns:
            True если регистрация успешна, False иначе
        """
        try:
            self.interrupt_callbacks.add(callback)
            logger.info("Callback registered for interrupt handling")
            return True
            
        except Exception as e:
            logger.error(f"Error registering callback: {e}")
            return False
    
    def should_interrupt(self, hardware_id: str) -> bool:
        """
        Проверка, нужно ли прерывать операцию для указанного hardware_id
        
        Args:
            hardware_id: ID оборудования
            
        Returns:
            True если нужно прерывать, False иначе
        """
        if not self.global_interrupt_flag:
            return False
        
        if self.interrupt_hardware_id != hardware_id:
            return False
        
        # Проверяем таймаут прерывания
        if self.interrupt_timestamp:
            current_time = time.time()
            interrupt_timeout = self.config.get("interrupt_timeout", 5.0)
            
            if current_time - self.interrupt_timestamp > interrupt_timeout:
                logger.warning(f"Interrupt timeout for {hardware_id}, resetting flags")
                self._reset_interrupt_flags()
                return False
        
        return True
    
    def _reset_interrupt_flags(self):
        """Сброс глобальных флагов прерывания"""
        self.global_interrupt_flag = False
        self.interrupt_hardware_id = None
        self.interrupt_timestamp = None
        
        logger.info("Global interrupt flags reset")
    
    def register_session(self, session_id: str, hardware_id: str, session_data: Dict[str, Any]) -> bool:
        """
        Регистрация активной сессии
        
        Args:
            session_id: ID сессии
            hardware_id: ID оборудования
            session_data: Данные сессии
            
        Returns:
            True если регистрация успешна, False иначе
        """
        try:
            self.active_sessions[session_id] = {
                "hardware_id": hardware_id,
                "start_time": time.time(),
                "data": session_data
            }
            
            self.session_counter += 1
            
            logger.debug(f"Session {session_id} registered for hardware_id: {hardware_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering session {session_id}: {e}")
            return False
    
    def unregister_session(self, session_id: str) -> bool:
        """
        Отмена регистрации сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            True если отмена успешна, False иначе
        """
        try:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                logger.debug(f"Session {session_id} unregistered")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error unregistering session {session_id}: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов модуля
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up Interrupt Manager...")
            
            # Сбрасываем флаги
            self._reset_interrupt_flags()
            
            # Очищаем сессии
            self.active_sessions.clear()
            
            # Очищаем зарегистрированные модули
            self.registered_modules.clear()
            
            # Очищаем callback функции
            self.interrupt_callbacks.clear()
            
            # Очищаем провайдеры
            if hasattr(self, 'global_flag_provider'):
                await self.global_flag_provider.cleanup()
            if hasattr(self, 'session_tracker_provider'):
                await self.session_tracker_provider.cleanup()
            
            self.set_status(ModuleStatus.STOPPED)
            self.is_initialized = False
            
            logger.info("Interrupt Manager cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up Interrupt Manager: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики прерываний"""
        return {
            "total_interrupts": self.total_interrupts,
            "successful_interrupts": self.successful_interrupts,
            "failed_interrupts": self.failed_interrupts,
            "success_rate": (
                self.successful_interrupts / self.total_interrupts 
                if self.total_interrupts > 0 else 0
            ),
            "active_sessions": len(self.active_sessions),
            "registered_modules": len(self.registered_modules),
            "registered_callbacks": len(self.interrupt_callbacks),
            "global_interrupt_flag": self.global_interrupt_flag,
            "interrupt_hardware_id": self.interrupt_hardware_id
        }
