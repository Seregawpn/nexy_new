"""
Интеграция Audio Generation Module с gRPC сервисом
"""

import logging
from typing import Dict, Any, AsyncGenerator

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from integrations.core.universal_grpc_integration import UniversalGrpcIntegration

logger = logging.getLogger(__name__)

class AudioGenerationIntegration(UniversalGrpcIntegration):
    """Интеграция Audio Generation Module с gRPC сервисом"""
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            if self.module and hasattr(self.module, 'initialize'):
                success = await self.module.initialize()
                if success:
                    self.is_initialized = True
                    logger.info(f"Audio Generation Integration initialized successfully")
                return success
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Audio Generation Integration: {e}")
            return False
    
    async def process_request(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Обработка запроса через Audio Generation Module"""
        try:
            if not self.is_initialized or not self.module:
                logger.error("Audio Generation Integration not initialized")
                return
            
            # Получаем текст для генерации аудио
            text = request_data.get("text", "")
            if not text:
                logger.warning("No text provided for audio generation")
                return
            
            # Создаем параметры для модуля
            module_input = {
                "text": text,
                "hardware_id": request_data.get("hardware_id", ""),
                "interrupt_checker": request_data.get("interrupt_checker", lambda: False)
            }
            
            # Обрабатываем через модуль
            async for result in self.module.process(module_input):
                # Формируем ответ в стандартном формате
                yield {
                    "type": "audio_chunk",
                    "content": {
                        "audio_data": result.get("audio_data"),
                        "dtype": result.get("dtype", "int16"),
                        "shape": result.get("shape", [])
                    },
                    "metadata": {
                        "module": "audio_generation",
                        "timestamp": result.get("timestamp"),
                        "hardware_id": request_data.get("hardware_id", "")
                    }
                }
                
        except Exception as e:
            logger.error(f"Error processing request in Audio Generation Integration: {e}")
            yield {
                "type": "error",
                "content": f"Audio generation error: {e}",
                "metadata": {
                    "module": "audio_generation",
                    "error": True
                }
            }
    
    async def interrupt(self, hardware_id: str) -> bool:
        """Прерывание обработки Audio Generation Module"""
        try:
            if self.module and hasattr(self.module, 'stop_generation'):
                self.module.stop_generation()
                logger.info(f"Audio Generation interrupted for hardware_id: {hardware_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error interrupting Audio Generation: {e}")
            return False
    
    async def cleanup(self) -> bool:
        """Очистка ресурсов интеграции"""
        try:
            if self.module and hasattr(self.module, 'cleanup'):
                success = await self.module.cleanup()
                if success:
                    self.is_initialized = False
                    logger.info("Audio Generation Integration cleaned up")
                return success
            return True
        except Exception as e:
            logger.error(f"Error cleaning up Audio Generation Integration: {e}")
            return False
