#!/usr/bin/env python3
"""
GrpcServiceIntegration - координирует все workflow интеграции
"""

import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GrpcServiceIntegration:
    """
    Координирует все workflow интеграции для обработки gRPC запросов
    """
    
    def __init__(self, 
                 streaming_workflow=None, 
                 memory_workflow=None, 
                 interrupt_workflow=None):
        """
        Инициализация GrpcServiceIntegration
        
        Args:
            streaming_workflow: StreamingWorkflowIntegration
            memory_workflow: MemoryWorkflowIntegration  
            interrupt_workflow: InterruptWorkflowIntegration
        """
        self.streaming_workflow = streaming_workflow
        self.memory_workflow = memory_workflow
        self.interrupt_workflow = interrupt_workflow
        self.is_initialized = False
        
        logger.info("GrpcServiceIntegration создан")
    
    async def initialize(self) -> bool:
        """
        Инициализация интеграции
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Инициализация GrpcServiceIntegration...")
            
            # Проверяем доступность workflow интеграций
            if not self.streaming_workflow:
                logger.warning("⚠️ StreamingWorkflowIntegration не предоставлен")
            
            if not self.memory_workflow:
                logger.warning("⚠️ MemoryWorkflowIntegration не предоставлен")
            
            if not self.interrupt_workflow:
                logger.warning("⚠️ InterruptWorkflowIntegration не предоставлен")
            
            # Инициализируем workflow интеграции если они доступны
            if self.streaming_workflow:
                await self.streaming_workflow.initialize()
                logger.info("✅ StreamingWorkflowIntegration инициализирован")
            
            if self.memory_workflow:
                await self.memory_workflow.initialize()
                logger.info("✅ MemoryWorkflowIntegration инициализирован")
            
            if self.interrupt_workflow:
                await self.interrupt_workflow.initialize()
                logger.info("✅ InterruptWorkflowIntegration инициализирован")
            
            self.is_initialized = True
            logger.info("✅ GrpcServiceIntegration инициализирован успешно")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации GrpcServiceIntegration: {e}")
            return False
    
    async def process_request_complete(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Полная обработка gRPC запроса через все workflow интеграции
        
        Args:
            request_data: Данные gRPC запроса
            
        Yields:
            Результаты обработки
        """
        if not self.is_initialized:
            logger.error("❌ GrpcServiceIntegration не инициализирован")
            yield {
                'success': False,
                'error': 'GrpcServiceIntegration not initialized',
                'text_response': '',
                'audio_chunks': []
            }
            return
        
        try:
            logger.info(f"🔄 Начало полной обработки запроса: {request_data.get('session_id', 'unknown')}")
            
            # Извлекаем данные из запроса
            hardware_id = request_data.get('hardware_id', 'unknown')
            session_id = request_data.get('session_id', f"session_{datetime.now().timestamp()}")
            text = request_data.get('text', '')
            screenshot = request_data.get('screenshot')
            
            # Используем InterruptWorkflowIntegration для безопасной обработки
            async def _process_full_workflow():
                async for item in self._process_full_workflow_internal(request_data, hardware_id, session_id):
                    yield item
            
            # Обрабатываем через InterruptWorkflowIntegration
            if self.interrupt_workflow:
                logger.debug("Используем InterruptWorkflowIntegration для безопасной обработки")
                try:
                    async for item in self.interrupt_workflow.process_with_interrupts(
                        _process_full_workflow, 
                        hardware_id, 
                        session_id
                    ):
                        yield item
                except Exception as e:
                    logger.error(f"Ошибка в InterruptWorkflowIntegration: {e}")
                    # Fallback к прямой обработке
                    async for item in self._process_full_workflow_internal(request_data, hardware_id, session_id):
                        yield item
            else:
                logger.debug("InterruptWorkflowIntegration не доступен, обрабатываем напрямую")
                async for result in self._process_full_workflow_internal(request_data, hardware_id, session_id):
                    yield result
            
            logger.info(f"✅ Полная обработка запроса завершена: {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка полной обработки запроса: {e}")
            yield {
                'success': False,
                'error': str(e),
                'text_response': '',
                'audio_chunks': []
            }
    
    async def _process_full_workflow_internal(self, request_data: Dict[str, Any], hardware_id: str, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Внутренняя обработка полного workflow
        
        Args:
            request_data: Данные запроса
            hardware_id: Идентификатор оборудования
            session_id: Идентификатор сессии
            
        Yields:
            Результаты обработки
        """
        try:
            logger.debug(f"Внутренняя обработка workflow для {session_id}")
            
            # 1. Параллельно получаем контекст памяти (неблокирующее)
            memory_context = None
            if self.memory_workflow:
                logger.debug("Получение контекста памяти параллельно")
                memory_context = await self.memory_workflow.get_memory_context_parallel(hardware_id)
            
            # 2. Обрабатываем через StreamingWorkflowIntegration
            collected_sentences: list[str] = []
            audio_delivered = False
            final_response_text = ''
            prompt_text = request_data.get('text', '')

            if self.streaming_workflow:
                logger.debug("Обработка через StreamingWorkflowIntegration")
                async for result in self.streaming_workflow.process_request_streaming(request_data):
                    try:
                        has_audio = 'audio_chunk' in result and isinstance(result.get('audio_chunk'), (bytes, bytearray))
                        sz = (len(result['audio_chunk']) if has_audio else 0)
                        txt = result.get('text_response')
                        logger.info(f'StreamingWorkflowIntegration → result: text_len={(len(txt) if txt else 0)}, audio_bytes={sz}')
                        if txt:
                            collected_sentences.append(txt)
                        if has_audio:
                            audio_delivered = True
                        if result.get('is_final'):
                            final_response_text = result.get('text_full_response', '') or " ".join(collected_sentences).strip()
                    except Exception:
                        pass
                    yield result
            else:
                logger.warning("⚠️ StreamingWorkflowIntegration не доступен, возвращаем базовый ответ")
                yield {
                    'success': True,
                    'text_response': request_data.get('text', ''),
                    'audio_chunks': []
                }
            
            # 3. Фоново сохраняем в память (неблокирующее)
            if self.memory_workflow:
                logger.debug("Фоновое сохранение в память")
                # Добавляем результат обработки к данным для сохранения
                save_data = request_data.copy()
                save_data['processed_text'] = final_response_text or " ".join(collected_sentences).strip()
                save_data['audio_generated'] = audio_delivered
                save_data['prompt'] = prompt_text
                save_data['response'] = final_response_text or save_data['processed_text']
                save_data['sentences'] = collected_sentences
                
                if save_data.get('prompt') and save_data.get('response'):
                    await self.memory_workflow.save_to_memory_background(save_data)
                    logger.debug("✅ Фоновое сохранение в память запущено")
                else:
                    logger.debug("⚠️ Фоновое сохранение пропущено: недостаточно данных (prompt/response)")
            
        except Exception as e:
            logger.error(f"❌ Ошибка внутренней обработки workflow: {e}")
            yield {
                'success': False,
                'error': str(e),
                'text_response': '',
                'audio_chunks': []
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса интеграции
        
        Returns:
            Словарь со статусом
        """
        try:
            status = {
                'initialized': self.is_initialized,
                'streaming_workflow': self.streaming_workflow is not None,
                'memory_workflow': self.memory_workflow is not None,
                'interrupt_workflow': self.interrupt_workflow is not None
            }
            
            # Получаем статус workflow интеграций если они доступны
            if self.streaming_workflow:
                status['streaming_workflow_initialized'] = getattr(self.streaming_workflow, 'is_initialized', False)
            
            if self.memory_workflow:
                status['memory_workflow_initialized'] = getattr(self.memory_workflow, 'is_initialized', False)
            
            if self.interrupt_workflow:
                status['interrupt_workflow_initialized'] = getattr(self.interrupt_workflow, 'is_initialized', False)
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса: {e}")
            return {
                'initialized': False,
                'error': str(e)
            }
    
    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            logger.info("Очистка GrpcServiceIntegration...")
            
            # Очищаем workflow интеграции если они доступны
            if self.streaming_workflow and hasattr(self.streaming_workflow, 'cleanup'):
                await self.streaming_workflow.cleanup()
                logger.debug("StreamingWorkflowIntegration очищен")
            
            if self.memory_workflow and hasattr(self.memory_workflow, 'cleanup'):
                await self.memory_workflow.cleanup()
                logger.debug("MemoryWorkflowIntegration очищен")
            
            if self.interrupt_workflow and hasattr(self.interrupt_workflow, 'cleanup'):
                await self.interrupt_workflow.cleanup()
                logger.debug("InterruptWorkflowIntegration очищен")
            
            self.is_initialized = False
            logger.info("✅ GrpcServiceIntegration очищен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки GrpcServiceIntegration: {e}")
