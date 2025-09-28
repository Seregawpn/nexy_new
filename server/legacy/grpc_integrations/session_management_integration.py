"""
Интеграция Session Management Module с gRPC сервисом
"""

import logging
from typing import Dict, Any, AsyncGenerator

from integrations.core.universal_grpc_integration import UniversalGrpcIntegration

logger = logging.getLogger(__name__)

class SessionManagementIntegration(UniversalGrpcIntegration):
    """Интеграция Session Management Module с gRPC сервисом"""
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            if self.module and hasattr(self.module, 'initialize'):
                success = await self.module.initialize()
                if success:
                    self.is_initialized = True
                    logger.info(f"Session Management Integration initialized successfully")
                return success
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Session Management Integration: {e}")
            return False
    
    async def process_request(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Обработка запроса через Session Management Module"""
        try:
            if not self.is_initialized or not self.module:
                logger.error("Session Management Integration not initialized")
                return
            
            # Извлекаем данные из запроса
            hardware_id = request_data.get("hardware_id", "")
            session_id = request_data.get("session_id", "")
            
            # Создаем параметры для модуля
            module_input = {
                "hardware_id": hardware_id,
                "session_id": session_id,
                "request_data": request_data
            }
            
            # Обрабатываем через модуль
            async for result in self.module.process(module_input):
                # Формируем ответ в стандартном формате
                yield {
                    "type": "session_info",
                    "content": result.get("session_data", {}),
                    "metadata": {
                        "module": "session_management",
                        "timestamp": result.get("timestamp"),
                        "hardware_id": hardware_id,
                        "session_id": session_id
                    }
                }
                
        except Exception as e:
            logger.error(f"Error processing request in Session Management Integration: {e}")
            yield {
                "type": "error",
                "content": f"Session management error: {e}",
                "metadata": {
                    "module": "session_management",
                    "error": True
                }
            }
    
    async def interrupt(self, hardware_id: str) -> bool:
        """Прерывание обработки Session Management Module"""
        try:
            if self.module and hasattr(self.module, 'interrupt_session'):
                success = await self.module.interrupt_session(hardware_id)
                logger.info(f"Session Management interrupted for hardware_id: {hardware_id}")
                return success
            return False
        except Exception as e:
            logger.error(f"Error interrupting Session Management: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """Очистка ресурсов интеграции"""
        try:
            if self.module and hasattr(self.module, 'cleanup'):
                success = await self.module.cleanup()
                if success:
                    self.is_initialized = False
                    logger.info("Session Management Integration cleaned up")
                return success
            return True
        except Exception as e:
            logger.error(f"Error cleaning up Session Management Integration: {e}")
            return False
