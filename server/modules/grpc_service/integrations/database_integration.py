"""
Интеграция Database Module с gRPC сервисом
"""

import logging
from typing import Dict, Any, AsyncGenerator

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from integration.core.universal_grpc_integration import UniversalGrpcIntegration

logger = logging.getLogger(__name__)

class DatabaseIntegration(UniversalGrpcIntegration):
    """Интеграция Database Module с gRPC сервисом"""
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            if self.module and hasattr(self.module, 'initialize'):
                success = await self.module.initialize()
                if success:
                    self.is_initialized = True
                    logger.info(f"Database Integration initialized successfully")
                return success
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Database Integration: {e}")
            return False
    
    async def process_request(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Обработка запроса через Database Module"""
        try:
            if not self.is_initialized or not self.module:
                logger.error("Database Integration not initialized")
                return
            
            # Извлекаем данные из запроса
            hardware_id = request_data.get("hardware_id", "")
            operation = request_data.get("operation", "read")
            
            # Создаем параметры для модуля
            module_input = {
                "hardware_id": hardware_id,
                "operation": operation,
                "request_data": request_data
            }
            
            # Обрабатываем через модуль
            async for result in self.module.process(module_input):
                # Формируем ответ в стандартном формате
                yield {
                    "type": "database_result",
                    "content": result.get("data", {}),
                    "metadata": {
                        "module": "database",
                        "operation": operation,
                        "timestamp": result.get("timestamp"),
                        "hardware_id": hardware_id
                    }
                }
                
        except Exception as e:
            logger.error(f"Error processing request in Database Integration: {e}")
            yield {
                "type": "error",
                "content": f"Database error: {e}",
                "metadata": {
                    "module": "database",
                    "error": True
                }
            }
    
    async def interrupt(self, hardware_id: str) -> bool:
        """Прерывание обработки Database Module"""
        try:
            # Database операции обычно не прерываются, но можно очистить кэш
            if self.module and hasattr(self.module, 'clear_cache'):
                self.module.clear_cache()
                logger.info(f"Database cache cleared for hardware_id: {hardware_id}")
            return True
        except Exception as e:
            logger.error(f"Error interrupting Database: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """Очистка ресурсов интеграции"""
        try:
            if self.module and hasattr(self.module, 'cleanup'):
                success = await self.module.cleanup()
                if success:
                    self.is_initialized = False
                    logger.info("Database Integration cleaned up")
                return success
            return True
        except Exception as e:
            logger.error(f"Error cleaning up Database Integration: {e}")
            return False
