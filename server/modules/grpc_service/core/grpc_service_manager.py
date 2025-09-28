#!/usr/bin/env python3
"""
Новый GrpcServiceManager с интеграцией всех service интеграций
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from integrations.core.universal_module_interface import UniversalModuleInterface, ModuleStatus
from integrations.service_integrations.grpc_service_integration import GrpcServiceIntegration
from integrations.service_integrations.module_coordinator_integration import ModuleCoordinatorIntegration
from integrations.workflow_integrations.streaming_workflow_integration import StreamingWorkflowIntegration
from integrations.workflow_integrations.memory_workflow_integration import MemoryWorkflowIntegration
from integrations.workflow_integrations.interrupt_workflow_integration import InterruptWorkflowIntegration

# Импорты модулей
from modules.text_processing import TextProcessor
from modules.audio_generation import AudioProcessor
from modules.memory_management import MemoryManager
from modules.database import DatabaseManager
from modules.session_management import SessionManager
from modules.interrupt_handling import InterruptManager

from modules.grpc_service.config import GrpcServiceConfig

logger = logging.getLogger(__name__)

class GrpcServiceManager(UniversalModuleInterface):
    """
    Новый GrpcServiceManager с полной интеграцией всех service интеграций
    
    Использует новую архитектуру:
    - Service интеграции для координации
    - Workflow интеграции для потоков данных
    - Модули для бизнес-логики
    """
    
    def __init__(self, config: Optional[GrpcServiceConfig] = None):
        """
        Инициализация нового менеджера gRPC сервиса
        
        Args:
            config: Конфигурация gRPC сервиса
        """
        # Инициализируем базовый класс
        config_dict = config.__dict__ if config else {}
        super().__init__("grpc_service", config_dict)
        
        self.config = config or GrpcServiceConfig()
        
        # Модули
        self.modules: Dict[str, UniversalModuleInterface] = {}
        
        # Workflow интеграции
        self.streaming_workflow: Optional[StreamingWorkflowIntegration] = None
        self.memory_workflow: Optional[MemoryWorkflowIntegration] = None
        self.interrupt_workflow: Optional[InterruptWorkflowIntegration] = None
        
        # Service интеграции
        self.grpc_service_integration: Optional[GrpcServiceIntegration] = None
        self.module_coordinator: Optional[ModuleCoordinatorIntegration] = None
        
        logger.info("gRPC Service Manager created")
    
    async def initialize(self) -> bool:
        """
        Инициализация нового менеджера gRPC сервиса
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing gRPC Service Manager...")
            
            # 1. Инициализируем все модули
            await self._initialize_modules()
            
            # 2. Создаем workflow интеграции
            await self._create_workflow_integrations()
            
            # 3. Создаем service интеграции
            await self._create_service_integrations()
            
            # 4. Инициализируем все интеграции
            await self._initialize_integrations()
            
            # Устанавливаем флаг инициализации и статус
            self.is_initialized = True
            self.set_status(ModuleStatus.READY)
            
            logger.info("gRPC Service Manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize gRPC Service Manager: {e}")
            return False
    
    async def _initialize_modules(self):
        """Инициализация всех модулей"""
        logger.info("Initializing modules...")
        
        try:
            # Создаем модули
            self.modules['text_processing'] = TextProcessor()
            self.modules['audio_generation'] = AudioProcessor()
            self.modules['memory_management'] = MemoryManager()
            self.modules['database'] = DatabaseManager()
            self.modules['session_management'] = SessionManager()
            self.modules['interrupt_handling'] = InterruptManager()
            
            # Инициализируем модули
            for name, module in self.modules.items():
                try:
                    logger.info(f"🔍 ДИАГНОСТИКА: Инициализация модуля {name}")
                    logger.info(f"   → module type: {type(module)}")
                    logger.info(f"   → module object: {module}")
                    
                    result = await module.initialize()
                    logger.info(f"   → initialize() result: {result}")
                    
                    # Проверяем состояние после инициализации
                    if hasattr(module, 'is_initialized'):
                        logger.info(f"   → module.is_initialized: {module.is_initialized}")
                    
                    logger.info(f"✅ Module {name} initialized")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize module {name}: {e}")
                    import traceback
                    logger.error(f"❌ Traceback: {traceback.format_exc()}")
            
        except Exception as e:
            logger.error(f"❌ Error initializing modules: {e}")
            raise
    
    async def _create_workflow_integrations(self):
        """Создание workflow интеграций"""
        logger.info("Creating workflow integrations...")
        
        try:
            # ДИАГНОСТИКА: проверяем модули перед созданием интеграций
            logger.info(f"🔍 ДИАГНОСТИКА: Создание workflow интеграций")
            text_processor = self.modules.get('text_processing')
            audio_processor = self.modules.get('audio_generation')
            
            logger.info(f"   → text_processor: {text_processor}")
            logger.info(f"   → audio_processor: {audio_processor}")
            
            if text_processor:
                logger.info(f"   → text_processor.is_initialized: {getattr(text_processor, 'is_initialized', 'NO_ATTR')}")
            if audio_processor:
                logger.info(f"   → audio_processor.is_initialized: {getattr(audio_processor, 'is_initialized', 'NO_ATTR')}")
            
            # Создаем workflow интеграции с модулями
            self.streaming_workflow = StreamingWorkflowIntegration(
                text_processor=text_processor,
                audio_processor=audio_processor,
                memory_workflow=None  # Будет установлен ниже
            )
            
            self.memory_workflow = MemoryWorkflowIntegration(
                memory_manager=self.modules.get('memory_management')
            )
            
            self.interrupt_workflow = InterruptWorkflowIntegration(
                interrupt_manager=self.modules.get('interrupt_handling')
            )
            
            # Устанавливаем memory_workflow в streaming_workflow
            self.streaming_workflow.memory_workflow = self.memory_workflow
            
            logger.info("✅ Workflow integrations created")
            
        except Exception as e:
            logger.error(f"❌ Error creating workflow integrations: {e}")
            raise
    
    async def _create_service_integrations(self):
        """Создание service интеграций"""
        logger.info("Creating service integrations...")
        
        try:
            # Создаем service интеграции
            self.grpc_service_integration = GrpcServiceIntegration(
                streaming_workflow=self.streaming_workflow,
                memory_workflow=self.memory_workflow,
                interrupt_workflow=self.interrupt_workflow
            )
            
            self.module_coordinator = ModuleCoordinatorIntegration(self.modules)
            
            logger.info("✅ Service integrations created")
            
        except Exception as e:
            logger.error(f"❌ Error creating service integrations: {e}")
            raise
    
    async def _initialize_integrations(self):
        """Инициализация всех интеграций"""
        logger.info("Initializing integrations...")
        
        try:
            # Инициализируем workflow интеграции
            if self.streaming_workflow:
                await self.streaming_workflow.initialize()
                logger.info("✅ StreamingWorkflowIntegration initialized")
            
            if self.memory_workflow:
                await self.memory_workflow.initialize()
                logger.info("✅ MemoryWorkflowIntegration initialized")
            
            if self.interrupt_workflow:
                await self.interrupt_workflow.initialize()
                logger.info("✅ InterruptWorkflowIntegration initialized")
            
            # Инициализируем service интеграции
            if self.grpc_service_integration:
                await self.grpc_service_integration.initialize()
                logger.info("✅ GrpcServiceIntegration initialized")
            
            if self.module_coordinator:
                await self.module_coordinator.initialize()
                logger.info("✅ ModuleCoordinatorIntegration initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing integrations: {e}")
            raise
    
    async def start(self) -> bool:
        """Запуск gRPC сервиса"""
        try:
            logger.info("Starting gRPC Service Manager...")
            
            # Запускаем все модули через ModuleCoordinatorIntegration
            if self.module_coordinator:
                start_result = await self.module_coordinator.start_all_modules()
                if not start_result.get('success', False):
                    logger.error("Failed to start some modules")
                    return False
            
            logger.info("gRPC Service Manager started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting gRPC Service Manager: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка gRPC сервиса"""
        try:
            logger.info("Stopping gRPC Service Manager...")
            
            # Останавливаем все модули через ModuleCoordinatorIntegration
            if self.module_coordinator:
                stop_result = await self.module_coordinator.stop_all_modules()
                if not stop_result.get('success', False):
                    logger.error("Failed to stop some modules")
                    return False
            
            logger.info("gRPC Service Manager stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping gRPC Service Manager: {e}")
            return False
    
    async def process(self, input_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Основная обработка данных через gRPC сервис
        
        Args:
            input_data: Входные данные для обработки
            
        Yields:
            Результаты обработки
        """
        try:
            self.set_status(ModuleStatus.PROCESSING)
            
            # Обрабатываем через GrpcServiceIntegration
            if self.grpc_service_integration:
                async for result in self.grpc_service_integration.process_request_complete(input_data):
                    yield result
            else:
                logger.error("GrpcServiceIntegration not available")
                yield {
                    'success': False,
                    'text_response': '',
                    'audio_chunks': [],
                    'error': 'GrpcServiceIntegration not available'
                }
                
        except Exception as e:
            logger.error(f"Error in gRPC Service Manager process: {e}")
            yield {
                'success': False,
                'text_response': '',
                'audio_chunks': [],
                'error': str(e)
            }
        finally:
            self.set_status(ModuleStatus.READY)
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка запроса через новые интеграции (для совместимости)
        
        Args:
            request_data: Данные запроса
            
        Returns:
            Результат обработки
        """
        try:
            logger.info(f"🔄 Processing request through integrated architecture...")
            
            # Получаем первый результат из process()
            async for result in self.process(request_data):
                return result
                
        except Exception as e:
            logger.error(f"Error in process_request: {e}")
            return {
                'success': False,
                'text_response': '',
                'audio_chunks': [],
                'error': str(e)
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса gRPC сервиса
        
        Returns:
            Словарь со статусом
        """
        try:
            status = {
                'module_name': 'grpc_service',
                'is_initialized': self.is_initialized,
                'status': 'ready' if self.is_initialized else 'not_initialized',
                'modules_count': len(self.modules),
                'modules_status': {}
            }
            
            # Получаем статус модулей
            for name, module in self.modules.items():
                try:
                    if hasattr(module, 'get_status'):
                        module_status = await module.get_status()
                        status['modules_status'][name] = module_status
                    else:
                        status['modules_status'][name] = 'no_status_method'
                except Exception as e:
                    status['modules_status'][name] = f'error: {str(e)}'
            
            # Получаем статус service интеграций
            if self.grpc_service_integration:
                status['grpc_service_integration'] = await self.grpc_service_integration.get_status()
            
            if self.module_coordinator:
                status['module_coordinator'] = await self.module_coordinator.get_status()
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                'module_name': 'grpc_service',
                'is_initialized': False,
                'error': str(e)
            }
    
    async def cleanup(self):
        """Очистка ресурсов gRPC сервиса"""
        try:
            logger.info("Cleaning up gRPC Service Manager...")
            
            # Очищаем service интеграции
            if self.grpc_service_integration:
                await self.grpc_service_integration.cleanup()
                logger.info("✅ GrpcServiceIntegration cleaned up")
            
            if self.module_coordinator:
                await self.module_coordinator.cleanup()
                logger.info("✅ ModuleCoordinatorIntegration cleaned up")
            
            # Очищаем модули
            for name, module in self.modules.items():
                try:
                    if hasattr(module, 'cleanup'):
                        await module.cleanup()
                        logger.info(f"✅ Module {name} cleaned up")
                except Exception as e:
                    logger.error(f"❌ Error cleaning up module {name}: {e}")
            
            # Очищаем workflow интеграции
            if self.streaming_workflow:
                await self.streaming_workflow.cleanup()
                logger.info("✅ StreamingWorkflowIntegration cleaned up")
            
            if self.memory_workflow:
                await self.memory_workflow.cleanup()
                logger.info("✅ MemoryWorkflowIntegration cleaned up")
            
            if self.interrupt_workflow:
                await self.interrupt_workflow.cleanup()
                logger.info("✅ InterruptWorkflowIntegration cleaned up")
            
            self.is_initialized = False
            logger.info("✅ gRPC Service Manager cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up gRPC Service Manager: {e}")
