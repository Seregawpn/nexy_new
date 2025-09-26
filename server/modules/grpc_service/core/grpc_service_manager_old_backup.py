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

from integrations.core.universal_module_interface import UniversalModuleInterface, ModuleStatus
from integrations.core.universal_grpc_integration import UniversalGrpcIntegration
from modules.grpc_service.config import GrpcServiceConfig

logger = logging.getLogger(__name__)

class GrpcServiceManager(UniversalModuleInterface):
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
        # Инициализируем базовый класс
        config_dict = config.__dict__ if config else {}
        super().__init__("grpc_service", config_dict)
        
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
                from integrations.grpc_integrations.text_processing_integration import TextProcessingIntegration
                return TextProcessingIntegration(module_name, module)
            elif module_name == "audio_generation":
                from integrations.grpc_integrations.audio_generation_integration import AudioGenerationIntegration
                return AudioGenerationIntegration(module_name, module)
            elif module_name == "session_management":
                from integrations.grpc_integrations.session_management_integration import SessionManagementIntegration
                return SessionManagementIntegration(module_name, module)
            elif module_name == "database":
                from integrations.grpc_integrations.database_integration import DatabaseIntegration
                return DatabaseIntegration(module_name, module)
            elif module_name == "memory_management":
                from integrations.grpc_integrations.memory_management_integration import MemoryManagementIntegration
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
        modules_status = {}
        for name, module in self.modules.items():
            if hasattr(module, 'get_status'):
                try:
                    modules_status[name] = module.get_status()
                except Exception as e:
                    modules_status[name] = f"error: {str(e)}"
            else:
                modules_status[name] = "initialized"
        
        integrations_status = {}
        for name, integration in self.integrations.items():
            if hasattr(integration, 'get_status'):
                try:
                    integrations_status[name] = integration.get_status()
                except Exception as e:
                    integrations_status[name] = f"error: {str(e)}"
            else:
                integrations_status[name] = "initialized"
        
        return {
            "status": "ready" if self.is_initialized else "not_initialized",
            "active_sessions": len(self.active_sessions),
            "modules": modules_status,
            "integrations": integrations_status,
            "global_interrupt_flag": self.global_interrupt_flag,
            "interrupt_hardware_id": self.interrupt_hardware_id
        }
    
    async def start(self) -> bool:
        """Запуск gRPC сервиса"""
        try:
            logger.info("Starting gRPC Service Manager...")
            
            # Запускаем все модули
            for name, module in self.modules.items():
                if hasattr(module, 'start'):
                    await module.start()
                    logger.info(f"Module {name} started successfully")
            
            # Запускаем все интеграции
            for name, integration in self.integrations.items():
                if hasattr(integration, 'start'):
                    await integration.start()
                    logger.info(f"Integration {name} started successfully")
            
            logger.info("gRPC Service Manager started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting gRPC Service Manager: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка gRPC сервиса"""
        try:
            logger.info("Stopping gRPC Service Manager...")
            
            # Останавливаем все интеграции
            for name, integration in self.integrations.items():
                if hasattr(integration, 'stop'):
                    await integration.stop()
                    logger.info(f"Integration {name} stopped successfully")
            
            # Останавливаем все модули
            for name, module in self.modules.items():
                if hasattr(module, 'stop'):
                    await module.stop()
                    logger.info(f"Module {name} stopped successfully")
            
            # Очищаем активные сессии
            self.active_sessions.clear()
            
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
            
            # Обрабатываем запрос через process_request
            result = await self.process_request(input_data)
            
            yield result
            
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
        Обработка запроса через все модули
        
        Args:
            request_data: Данные запроса (hardware_id, text, screenshot, session_id, interrupt_flag)
            
        Returns:
            Результат обработки (success, text_response, audio_chunks, error)
        """
        try:
            session_id = request_data.get('session_id', 'unknown')
            hardware_id = request_data.get('hardware_id', 'unknown')
            text = request_data.get('text', '')
            screenshot = request_data.get('screenshot', b'')
            
            logger.info(f"🔄 Обработка запроса {session_id} через модули...")
            
            # Проверяем прерывание
            if request_data.get('interrupt_flag', False):
                logger.info(f"🛑 Запрос на прерывание для {session_id}")
                return {
                    'success': True,
                    'text_response': 'Сессия прервана',
                    'audio_chunks': [],
                    'error': ''
                }
            
            # Обрабатываем текст через Text Processing модуль
            text_result = None
            if text and 'text_processing' in self.modules:
                try:
                    # Проверяем, есть ли метод process_text
                    if hasattr(self.modules['text_processing'], 'process_text'):
                        # TextProcessor.process_text возвращает async generator
                        text_generator = self.modules['text_processing'].process_text(text)
                        # Получаем первый результат из генератора
                        text_result = await text_generator.__anext__()
                        logger.info(f"✅ Текст обработан для {session_id}")
                    else:
                        logger.warning(f"⚠️ TextProcessor не имеет метода process_text")
                        text_result = f"TextProcessor не инициализирован"
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка обработки текста: {e}")
                    text_result = f"Ошибка обработки текста: {str(e)}"
            
            # Генерируем аудио через Audio Generation модуль
            audio_chunks = []
            if text_result and 'audio_generation' in self.modules:
                try:
                    # Проверяем, есть ли метод generate_audio
                    if hasattr(self.modules['audio_generation'], 'generate_audio'):
                        audio_result = await self.modules['audio_generation'].generate_audio(text_result)
                        if audio_result:
                            audio_chunks = [audio_result]
                        logger.info(f"✅ Аудио сгенерировано для {session_id}")
                    else:
                        logger.warning(f"⚠️ AudioProcessor не имеет метода generate_audio")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка генерации аудио: {e}")
            
            # Сохраняем в память через Memory Management модуль
            if text_result and 'memory_management' in self.modules:
                try:
                    # Проверяем, есть ли метод store_memory
                    if hasattr(self.modules['memory_management'], 'store_memory'):
                        await self.modules['memory_management'].store_memory(
                            hardware_id=hardware_id,
                            content=text_result,
                            memory_type='conversation'
                        )
                        logger.info(f"✅ Память сохранена для {session_id}")
                    else:
                        logger.warning(f"⚠️ MemoryManager не имеет метода store_memory")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка сохранения памяти: {e}")
            
            # Сохраняем в базу данных через Database модуль
            if text_result and 'database' in self.modules:
                try:
                    # Проверяем, есть ли метод store_conversation
                    if hasattr(self.modules['database'], 'store_conversation'):
                        await self.modules['database'].store_conversation(
                            hardware_id=hardware_id,
                            session_id=session_id,
                            user_input=text,
                            ai_response=text_result
                        )
                        logger.info(f"✅ Данные сохранены в БД для {session_id}")
                    else:
                        logger.warning(f"⚠️ DatabaseManager не имеет метода store_conversation")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка сохранения в БД: {e}")
            
            logger.info(f"✅ Запрос {session_id} успешно обработан")
            
            return {
                'success': True,
                'text_response': text_result or 'Обработка завершена',
                'audio_chunks': audio_chunks,
                'error': ''
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки запроса: {e}")
            return {
                'success': False,
                'text_response': '',
                'audio_chunks': [],
                'error': str(e)
            }

    async def cleanup(self) -> bool:
        """Очистка всех ресурсов"""
        try:
            logger.info("Cleaning up gRPC Service Manager...")
            
            # Очищаем все интеграции
            for integration in self.integrations.values():
                if hasattr(integration, 'cleanup'):
                    await integration.cleanup()
            
            # Очищаем все модули
            for module in self.modules.values():
                if hasattr(module, 'cleanup'):
                    await module.cleanup()
            
            # Очищаем активные сессии
            self.active_sessions.clear()
            
            logger.info("gRPC Service Manager cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up gRPC Service Manager: {e}")
            return False
