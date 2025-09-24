"""
Основной координатор gRPC Service Module

Интегрирует все модули через универсальный стандарт взаимодействия
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from integration.core.universal_module_interface import UniversalModuleInterface, ModuleStatus
from integration.core.universal_grpc_integration import UniversalGrpcIntegration
from modules.grpc_service.config import GrpcServiceConfig

logger = logging.getLogger(__name__)

class GrpcServiceManager:
    """
    Основной координатор gRPC сервиса
    
    Управляет всеми модулями через универсальный стандарт взаимодействия
    """
    
    def __init__(self, config: Optional[GrpcServiceConfig] = None):
        """
        Инициализация менеджера gRPC сервиса
        
        Args:
            config: Конфигурация gRPC сервиса
        """
        self.config = config or GrpcServiceConfig()
        self.modules: Dict[str, UniversalModuleInterface] = {}
        self.integrations: Dict[str, UniversalGrpcIntegration] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.global_interrupt_flag = False
        self.interrupt_hardware_id: Optional[str] = None
        
        logger.info("gRPC Service Manager created")
    
    async def initialize(self) -> bool:
        """
        Инициализация всех модулей и интеграций
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing gRPC Service Manager...")
            
            # Инициализируем все модули
            await self._initialize_modules()
            
            # Инициализируем все интеграции
            await self._initialize_integrations()
            
            logger.info("gRPC Service Manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize gRPC Service Manager: {e}")
            return False
    
    async def _initialize_modules(self):
        """Инициализация всех модулей"""
        # Импортируем и инициализируем модули
        try:
            # Text Processing Module
            if self.config.is_module_enabled("text_processing"):
                from modules.text_processing import TextProcessor
                text_processor = TextProcessor()
                await text_processor.initialize()
                self.modules["text_processing"] = text_processor
                logger.info("Text Processing Module initialized")
            
            # Audio Generation Module
            if self.config.is_module_enabled("audio_generation"):
                from modules.audio_generation import AudioProcessor
                audio_processor = AudioProcessor()
                await audio_processor.initialize()
                self.modules["audio_generation"] = audio_processor
                logger.info("Audio Generation Module initialized")
            
            # Session Management Module
            if self.config.is_module_enabled("session_management"):
                from modules.session_management import SessionManager
                session_manager = SessionManager()
                await session_manager.initialize()
                self.modules["session_management"] = session_manager
                logger.info("Session Management Module initialized")
            
            # Database Module
            if self.config.is_module_enabled("database"):
                from modules.database import DatabaseManager
                database_manager = DatabaseManager()
                await database_manager.initialize()
                self.modules["database"] = database_manager
                logger.info("Database Module initialized")
            
            # Memory Management Module
            if self.config.is_module_enabled("memory_management"):
                from modules.memory_management import MemoryManager
                memory_manager = MemoryManager()
                await memory_manager.initialize()
                self.modules["memory_management"] = memory_manager
                logger.info("Memory Management Module initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize modules: {e}")
            raise
    
    async def _initialize_integrations(self):
        """Инициализация всех интеграций"""
        try:
            # Создаем интеграции для каждого модуля
            for module_name, module in self.modules.items():
                integration = await self._create_integration(module_name, module)
                if integration:
                    await integration.initialize()
                    self.integrations[module_name] = integration
                    logger.info(f"Integration for {module_name} initialized")
                    
        except Exception as e:
            logger.error(f"Failed to initialize integrations: {e}")
            raise
    
    async def _create_integration(self, module_name: str, module: UniversalModuleInterface) -> Optional[UniversalGrpcIntegration]:
        """Создание интеграции для модуля"""
        try:
            if module_name == "text_processing":
                from modules.grpc_service.integrations.text_processing_integration import TextProcessingIntegration
                return TextProcessingIntegration(module_name, module)
            elif module_name == "audio_generation":
                from modules.grpc_service.integrations.audio_generation_integration import AudioGenerationIntegration
                return AudioGenerationIntegration(module_name, module)
            elif module_name == "session_management":
                from modules.grpc_service.integrations.session_management_integration import SessionManagementIntegration
                return SessionManagementIntegration(module_name, module)
            elif module_name == "database":
                from modules.grpc_service.integrations.database_integration import DatabaseIntegration
                return DatabaseIntegration(module_name, module)
            elif module_name == "memory_management":
                from modules.grpc_service.integrations.memory_management_integration import MemoryManagementIntegration
                return MemoryManagementIntegration(module_name, module)
            else:
                logger.warning(f"No integration found for module: {module_name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create integration for {module_name}: {e}")
            return None
    
    async def process_stream_request(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Обработка StreamRequest через все модули
        
        Args:
            request_data: Данные запроса
            
        Yields:
            Результаты обработки
        """
        session_id = request_data.get("session_id", "unknown")
        hardware_id = request_data.get("hardware_id", "unknown")
        
        try:
            # Регистрируем сессию
            await self._register_session(session_id, hardware_id, request_data)
            
            # Обрабатываем через Text Processing
            if "text_processing" in self.integrations:
                async for result in self.integrations["text_processing"].process_request(request_data):
                    if self._should_interrupt(hardware_id):
                        break
                    yield result
            
            # Обрабатываем через Audio Generation
            if "audio_generation" in self.integrations:
                async for result in self.integrations["audio_generation"].process_request(request_data):
                    if self._should_interrupt(hardware_id):
                        break
                    yield result
            
            # Обновляем память в фоне
            if "memory_management" in self.integrations:
                asyncio.create_task(
                    self._update_memory_background(hardware_id, request_data)
                )
                
        except Exception as e:
            logger.error(f"Error processing stream request: {e}")
            yield {"error": str(e)}
        finally:
            # Очищаем сессию
            await self._cleanup_session(session_id)
    
    async def interrupt_session(self, hardware_id: str) -> Dict[str, Any]:
        """
        Прерывание сессии для указанного hardware_id
        
        Args:
            hardware_id: ID оборудования для прерывания
            
        Returns:
            Результат прерывания
        """
        try:
            logger.warning(f"Interrupting session for hardware_id: {hardware_id}")
            
            # Устанавливаем глобальный флаг прерывания
            self.global_interrupt_flag = True
            self.interrupt_hardware_id = hardware_id
            
            # Прерываем все интеграции
            interrupted_sessions = []
            for integration_name, integration in self.integrations.items():
                try:
                    success = await integration.interrupt(hardware_id)
                    if success:
                        interrupted_sessions.append(integration_name)
                except Exception as e:
                    logger.error(f"Error interrupting {integration_name}: {e}")
            
            # Очищаем активные сессии для этого hardware_id
            sessions_to_remove = [
                session_id for session_id, session_data in self.active_sessions.items()
                if session_data.get("hardware_id") == hardware_id
            ]
            
            for session_id in sessions_to_remove:
                await self._cleanup_session(session_id)
            
            return {
                "success": True,
                "interrupted_sessions": interrupted_sessions,
                "message": f"Session interrupted for hardware_id: {hardware_id}"
            }
            
        except Exception as e:
            logger.error(f"Error interrupting session: {e}")
            return {
                "success": False,
                "interrupted_sessions": [],
                "message": f"Error interrupting session: {e}"
            }
    
    async def _register_session(self, session_id: str, hardware_id: str, request_data: Dict[str, Any]):
        """Регистрация активной сессии"""
        self.active_sessions[session_id] = {
            "hardware_id": hardware_id,
            "start_time": datetime.now(),
            "request_data": request_data
        }
        logger.info(f"Session {session_id} registered for hardware_id: {hardware_id}")
    
    async def _cleanup_session(self, session_id: str):
        """Очистка сессии"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Session {session_id} cleaned up")
    
    async def _update_memory_background(self, hardware_id: str, request_data: Dict[str, Any]):
        """Обновление памяти в фоновом режиме"""
        try:
            if "memory_management" in self.integrations:
                # Здесь можно добавить логику обновления памяти
                pass
        except Exception as e:
            logger.error(f"Error updating memory in background: {e}")
    
    def _should_interrupt(self, hardware_id: str) -> bool:
        """Проверка, нужно ли прерывать обработку"""
        return (
            self.global_interrupt_flag and 
            self.interrupt_hardware_id == hardware_id
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса gRPC сервиса"""
        return {
            "active_sessions": len(self.active_sessions),
            "modules": {
                name: module.get_status() 
                for name, module in self.modules.items()
            },
            "integrations": {
                name: integration.get_status() 
                for name, integration in self.integrations.items()
            },
            "global_interrupt_flag": self.global_interrupt_flag,
            "interrupt_hardware_id": self.interrupt_hardware_id
        }
    
    async def cleanup(self) -> bool:
        """Очистка всех ресурсов"""
        try:
            logger.info("Cleaning up gRPC Service Manager...")
            
            # Очищаем все интеграции
            for integration in self.integrations.values():
                await integration.cleanup()
            
            # Очищаем все модули
            for module in self.modules.values():
                await module.cleanup()
            
            # Очищаем активные сессии
            self.active_sessions.clear()
            
            logger.info("gRPC Service Manager cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up gRPC Service Manager: {e}")
            return False
