"""
Интеграция Text Processing Module с gRPC сервисом
"""

import logging
from typing import Dict, Any, AsyncGenerator

from integrations.core.universal_grpc_integration import UniversalGrpcIntegration

logger = logging.getLogger(__name__)

class TextProcessingIntegration(UniversalGrpcIntegration):
    """Интеграция Text Processing Module с gRPC сервисом"""
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            if self.module and hasattr(self.module, 'initialize'):
                success = await self.module.initialize()
                if success:
                    self.is_initialized = True
                    logger.info(f"Text Processing Integration initialized successfully")
                return success
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Text Processing Integration: {e}")
            return False
    
    async def process_request(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Обработка запроса через Text Processing Module"""
        try:
            if not self.is_initialized or not self.module:
                logger.error("Text Processing Integration not initialized")
                return
            
            # Извлекаем данные из запроса
            prompt = request_data.get("prompt", "")
            hardware_id = request_data.get("hardware_id", "")
            screenshot_base64 = request_data.get("screenshot", "")
            
            # Создаем параметры для модуля
            module_input = {
                "prompt": prompt,
                "hardware_id": hardware_id,
                "screenshot_base64": screenshot_base64,
                "interrupt_checker": request_data.get("interrupt_checker", lambda: False)
            }
            
            # Обрабатываем через модуль
            async for result in self.module.process(module_input):
                # Формируем ответ в стандартном формате
                yield {
                    "type": "text_chunk",
                    "content": result.get("text", ""),
                    "metadata": {
                        "module": "text_processing",
                        "timestamp": result.get("timestamp"),
                        "hardware_id": hardware_id
                    }
                }
                
        except Exception as e:
            logger.error(f"Error processing request in Text Processing Integration: {e}")
            yield {
                "type": "error",
                "content": f"Text processing error: {e}",
                "metadata": {
                    "module": "text_processing",
                    "error": True
                }
            }
    
    async def interrupt(self, hardware_id: str) -> bool:
        """Прерывание обработки Text Processing Module"""
        try:
            if self.module and hasattr(self.module, 'cancel_generation'):
                self.module.cancel_generation()
                logger.info(f"Text Processing interrupted for hardware_id: {hardware_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error interrupting Text Processing: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """Очистка ресурсов интеграции"""
        try:
            if self.module and hasattr(self.module, 'cleanup'):
                success = await self.module.cleanup()
                if success:
                    self.is_initialized = False
                    logger.info("Text Processing Integration cleaned up")
                return success
            return True
        except Exception as e:
            logger.error(f"Error cleaning up Text Processing Integration: {e}")
            return False
