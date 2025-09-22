"""
ProcessingWorkflow - Управление режимом PROCESSING
Координирует цепочку: capture → grpc → playback → sleeping
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum

from .base_workflow import BaseWorkflow, WorkflowState, AppMode
from integration.core.event_bus import EventPriority

logger = logging.getLogger(__name__)

class ProcessingStage(Enum):
    """Этапы обработки в режиме PROCESSING"""
    STARTING = "starting"
    CAPTURING = "capturing"
    SENDING_GRPC = "sending_grpc"
    PLAYING_AUDIO = "playing_audio"
    COMPLETING = "completing"

class ProcessingWorkflow(BaseWorkflow):
    """
    Workflow для режима PROCESSING.
    
    Координирует полную цепочку обработки:
    1. Захват скриншота (ScreenshotCaptureIntegration)
    2. Отправка на gRPC сервер (GrpcClientIntegration) 
    3. Воспроизведение ответа (SpeechPlaybackIntegration)
    4. Возврат в SLEEPING
    
    КЛЮЧЕВАЯ ОСОБЕННОСТЬ: Ждет РЕАЛЬНЫХ событий вместо таймаутов!
    """
    
    def __init__(self, event_bus):
        super().__init__(event_bus, "ProcessingWorkflow")
        
        # Конфигурация
        self.stage_timeout = 30.0  # секунд на каждый этап
        self.total_timeout = 300.0  # секунд общий таймаут (5 минут)
        
        # Состояние цепочки
        self.current_stage = ProcessingStage.STARTING
        self.stage_start_time: Optional[datetime] = None
        self.processing_start_time: Optional[datetime] = None
        self.completed_stages: Set[ProcessingStage] = set()
        
        # Мониторинг
        self.stage_timeout_task: Optional[asyncio.Task] = None
        self.total_timeout_task: Optional[asyncio.Task] = None
        
        # Флаги завершения
        self.screenshot_captured = False
        self.grpc_completed = False
        self.playback_completed = False
        self.interrupted = False
    
    async def _setup_subscriptions(self):
        """Подписка на события цепочки PROCESSING"""
        
        # === ВХОД В PROCESSING ===
        await self.event_bus.subscribe(
            "app.mode_changed", 
            self._on_mode_changed, 
            EventPriority.HIGH
        )
        
        # === ЭТАП 1: ЗАХВАТ СКРИНШОТА ===
        await self.event_bus.subscribe(
            "screenshot.captured", 
            self._on_screenshot_captured, 
            EventPriority.HIGH
        )
        
        await self.event_bus.subscribe(
            "screenshot.error", 
            self._on_screenshot_error, 
            EventPriority.HIGH
        )
        
        # === ЭТАП 2: GRPC ЗАПРОС ===
        await self.event_bus.subscribe(
            "grpc.request_started", 
            self._on_grpc_started, 
            EventPriority.HIGH
        )
        
        await self.event_bus.subscribe(
            "grpc.request_completed", 
            self._on_grpc_completed, 
            EventPriority.HIGH
        )
        
        await self.event_bus.subscribe(
            "grpc.request_failed", 
            self._on_grpc_failed, 
            EventPriority.HIGH
        )
        
        # === ЭТАП 3: ВОСПРОИЗВЕДЕНИЕ ===
        await self.event_bus.subscribe(
            "playback.started", 
            self._on_playback_started, 
            EventPriority.HIGH
        )
        
        await self.event_bus.subscribe(
            "playback.completed", 
            self._on_playback_completed, 
            EventPriority.HIGH
        )
        
        await self.event_bus.subscribe(
            "playback.failed", 
            self._on_playback_failed, 
            EventPriority.HIGH
        )
        
        # === ПРЕРЫВАНИЯ ===
        await self.event_bus.subscribe(
            "keyboard.short_press", 
            self._on_interrupt_request, 
            EventPriority.CRITICAL
        )
        
        await self.event_bus.subscribe(
            "interrupt.request", 
            self._on_interrupt_request, 
            EventPriority.CRITICAL
        )
    
    async def _on_start(self):
        """Запуск workflow'а"""
        logger.info("⚙️ ProcessingWorkflow: готов к координации обработки")
    
    async def _on_mode_changed(self, event):
        """Обработка смены режима"""
        try:
            data = event.get("data", {})
            new_mode = data.get("mode")
            session_id = data.get("session_id")
            
            if hasattr(new_mode, 'value'):
                mode_value = new_mode.value
            else:
                mode_value = str(new_mode).lower()
            
            logger.debug(f"⚙️ ProcessingWorkflow: режим изменен на {mode_value}")
            
            if mode_value == "processing":
                # НАЧИНАЕМ координацию цепочки PROCESSING
                await self._start_processing_chain(session_id)
                
            elif self.state == WorkflowState.ACTIVE and mode_value != "processing":
                # Вышли из PROCESSING - завершаем координацию
                logger.info(f"⚙️ ProcessingWorkflow: вышли из PROCESSING, завершаем координацию")
                await self._cleanup_processing()
                
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка обработки mode_changed - {e}")
    
    async def _start_processing_chain(self, session_id: Optional[str]):
        """Начало координации цепочки PROCESSING"""
        try:
            logger.info(f"⚙️ ProcessingWorkflow: НАЧАЛО цепочки обработки, session_id={session_id}")
            
            # Инициализация состояния
            self.current_session_id = session_id
            self.current_stage = ProcessingStage.STARTING
            self.processing_start_time = datetime.now()
            self.stage_start_time = datetime.now()
            self.state = WorkflowState.ACTIVE
            
            # Сброс флагов
            self.completed_stages.clear()
            self.screenshot_captured = False
            self.grpc_completed = False
            self.playback_completed = False
            self.interrupted = False
            
            # Запуск общего таймаута
            if self.total_timeout_task and not self.total_timeout_task.done():
                self.total_timeout_task.cancel()
                
            self.total_timeout_task = self._create_task(
                self._total_timeout_monitor(session_id), 
                "total_timeout"
            )
            
            # Переходим к этапу захвата
            await self._transition_to_stage(ProcessingStage.CAPTURING)
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка начала цепочки - {e}")
            await self._handle_error("start_chain_error")
    
    async def _transition_to_stage(self, new_stage: ProcessingStage):
        """Переход к новому этапу обработки"""
        try:
            old_stage = self.current_stage
            self.current_stage = new_stage
            self.stage_start_time = datetime.now()
            
            logger.info(f"⚙️ ProcessingWorkflow: переход {old_stage.value} → {new_stage.value}")
            
            # Отменяем предыдущий stage timeout
            if self.stage_timeout_task and not self.stage_timeout_task.done():
                self.stage_timeout_task.cancel()
            
            # Запускаем новый stage timeout
            self.stage_timeout_task = self._create_task(
                self._stage_timeout_monitor(new_stage), 
                f"stage_timeout_{new_stage.value}"
            )
            
            # Отмечаем предыдущий этап как завершенный
            if old_stage != ProcessingStage.STARTING:
                self.completed_stages.add(old_stage)
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка перехода к этапу {new_stage.value} - {e}")
    
    # === ОБРАБОТЧИКИ ЭТАПА 1: СКРИНШОТ ===
    
    async def _on_screenshot_captured(self, event):
        """Скриншот захвачен успешно"""
        if not self._is_relevant_event(event):
            return
            
        try:
            data = event.get("data", {})
            session_id = data.get("session_id")
            screenshot_path = data.get("path")
            
            logger.info(f"📸 ProcessingWorkflow: скриншот захвачен, path={screenshot_path}")
            
            self.screenshot_captured = True
            
            if self.current_stage == ProcessingStage.CAPTURING:
                # Переходим к отправке gRPC
                await self._transition_to_stage(ProcessingStage.SENDING_GRPC)
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка обработки screenshot.captured - {e}")
    
    async def _on_screenshot_error(self, event):
        """Ошибка захвата скриншота"""
        if not self._is_relevant_event(event):
            return
            
        try:
            data = event.get("data", {})
            error = data.get("error", "unknown")
            
            logger.error(f"📸 ProcessingWorkflow: ошибка захвата скриншота - {error}")
            
            # Продолжаем без скриншота (graceful degradation)
            self.screenshot_captured = False
            
            if self.current_stage == ProcessingStage.CAPTURING:
                logger.info("📸 ProcessingWorkflow: продолжаем без скриншота")
                await self._transition_to_stage(ProcessingStage.SENDING_GRPC)
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка обработки screenshot.error - {e}")
    
    # === ОБРАБОТЧИКИ ЭТАПА 2: GRPC ===
    
    async def _on_grpc_started(self, event):
        """gRPC запрос начат"""
        if not self._is_relevant_event(event):
            return
            
        try:
            logger.info("🌐 ProcessingWorkflow: gRPC запрос начат")
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка обработки grpc.request_started - {e}")
    
    async def _on_grpc_completed(self, event):
        """gRPC запрос завершен успешно"""
        if not self._is_relevant_event(event):
            return
            
        try:
            logger.info("🌐 ProcessingWorkflow: gRPC запрос завершен успешно")
            
            self.grpc_completed = True
            
            if self.current_stage == ProcessingStage.SENDING_GRPC:
                # Переходим к воспроизведению (если оно еще не началось)
                if not self.playback_completed:
                    await self._transition_to_stage(ProcessingStage.PLAYING_AUDIO)
                else:
                    # Воспроизведение уже завершено - завершаем цепочку
                    await self._complete_processing_chain()
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка обработки grpc.request_completed - {e}")
    
    async def _on_grpc_failed(self, event):
        """gRPC запрос завершился ошибкой"""
        if not self._is_relevant_event(event):
            return
            
        try:
            data = event.get("data", {})
            error = data.get("error", "unknown")
            
            logger.error(f"🌐 ProcessingWorkflow: gRPC запрос завершился ошибкой - {error}")
            
            self.grpc_completed = False
            await self._handle_error(f"grpc_error_{error}")
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка обработки grpc.request_failed - {e}")
    
    # === ОБРАБОТЧИКИ ЭТАПА 3: ВОСПРОИЗВЕДЕНИЕ ===
    
    async def _on_playback_started(self, event):
        """Воспроизведение началось"""
        if not self._is_relevant_event(event):
            return
            
        try:
            logger.info("🔊 ProcessingWorkflow: воспроизведение началось")
            
            if self.current_stage != ProcessingStage.PLAYING_AUDIO:
                await self._transition_to_stage(ProcessingStage.PLAYING_AUDIO)
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка обработки playback.started - {e}")
    
    async def _on_playback_completed(self, event):
        """Воспроизведение завершено - КЛЮЧЕВОЕ СОБЫТИЕ!"""
        if not self._is_relevant_event(event):
            return
            
        try:
            logger.info("🔊 ProcessingWorkflow: воспроизведение ЗАВЕРШЕНО - готовы к SLEEPING!")
            
            self.playback_completed = True
            
            # Если gRPC тоже завершен - завершаем всю цепочку
            if self.grpc_completed:
                await self._complete_processing_chain()
            else:
                logger.info("🔊 ProcessingWorkflow: ждем завершения gRPC...")
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка обработки playback.completed - {e}")
    
    async def _on_playback_failed(self, event):
        """Ошибка воспроизведения"""
        if not self._is_relevant_event(event):
            return
            
        try:
            data = event.get("data", {})
            error = data.get("error", "unknown")
            
            logger.error(f"🔊 ProcessingWorkflow: ошибка воспроизведения - {error}")
            
            self.playback_completed = False
            await self._handle_error(f"playback_error_{error}")
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка обработки playback.failed - {e}")
    
    # === ПРЕРЫВАНИЯ ===
    
    async def _on_interrupt_request(self, event):
        """Обработка запроса прерывания"""
        if not self.is_active() or self.interrupted:
            return
            
        try:
            data = event.get("data", {})
            reason = data.get("reason", "user_interrupt")
            
            logger.info(f"⚙️ ProcessingWorkflow: получен запрос ПРЕРЫВАНИЯ, reason={reason}, stage={self.current_stage.value}")
            
            self.interrupted = True
            
            # Отменяем все таймауты
            await self._cancel_timeout_tasks()
            
            # Публикуем события отмены для всех активных процессов
            await self._cancel_active_processes()
            
            # Немедленный возврат в SLEEPING
            await self._return_to_sleeping("interrupted")
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка обработки прерывания - {e}")
    
    async def _cancel_active_processes(self):
        """Отмена всех активных процессов через ЕДИНЫЙ канал прерывания"""
        try:
            session_id = self.current_session_id
            
            # Отменяем gRPC запрос
            if not self.grpc_completed:
                logger.info("⚙️ ProcessingWorkflow: отменяем gRPC запрос")
                await self.event_bus.publish("grpc.request_cancel", {
                    "session_id": session_id,
                    "reason": "user_interrupt"
                })
            
            # ЕДИНЫЙ канал прерывания аудио - публикуем playback.cancelled
            if not self.playback_completed:
                logger.info("⚙️ ProcessingWorkflow: останавливаем воспроизведение через ЕДИНЫЙ канал")
                await self.event_bus.publish("playback.cancelled", {
                    "session_id": session_id,
                    "reason": "user_interrupt",
                    "source": "processing_workflow"
                })
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка отмены процессов - {e}")
    
    # === ЗАВЕРШЕНИЕ ЦЕПОЧКИ ===
    
    async def _complete_processing_chain(self):
        """Успешное завершение всей цепочки обработки"""
        try:
            duration = (datetime.now() - self.processing_start_time).total_seconds() if self.processing_start_time else 0
            
            logger.info(f"✅ ProcessingWorkflow: цепочка ЗАВЕРШЕНА успешно за {duration:.2f}с")
            logger.info(f"📊 ProcessingWorkflow: скриншот={self.screenshot_captured}, gRPC={self.grpc_completed}, воспроизведение={self.playback_completed}")
            
            await self._transition_to_stage(ProcessingStage.COMPLETING)
            
            # Возвращаемся в SLEEPING
            await self._return_to_sleeping("completed")
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка завершения цепочки - {e}")
    
    async def _handle_error(self, error_type: str):
        """Обработка ошибки в цепочке"""
        try:
            logger.error(f"❌ ProcessingWorkflow: обработка ошибки {error_type} на этапе {self.current_stage.value}")
            
            # Отменяем таймауты
            await self._cancel_timeout_tasks()
            
            # Возвращаемся в SLEEPING
            await self._return_to_sleeping(f"error_{error_type}")
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка обработки ошибки - {e}")
    
    async def _return_to_sleeping(self, reason: str):
        """Координированный возврат в SLEEPING"""
        try:
            logger.info(f"⚙️ ProcessingWorkflow: возврат в SLEEPING, reason={reason}")
            
            await self._publish_mode_request(
                AppMode.SLEEPING, 
                f"processing_{reason}",
                priority=90  # Очень высокий приоритет для завершения
            )
            
            await self._cleanup_processing()
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка возврата в SLEEPING - {e}")
    
    async def _cleanup_processing(self):
        """Очистка состояния после завершения обработки"""
        try:
            # Отменяем все таймауты
            await self._cancel_timeout_tasks()
            
            # Сбрасываем состояние
            self.current_session_id = None
            self.current_stage = ProcessingStage.STARTING
            self.processing_start_time = None
            self.stage_start_time = None
            self.completed_stages.clear()
            self.state = WorkflowState.IDLE
            
            # Сбрасываем флаги
            self.screenshot_captured = False
            self.grpc_completed = False
            self.playback_completed = False
            self.interrupted = False
            
            logger.debug("⚙️ ProcessingWorkflow: состояние очищено")
            
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка очистки - {e}")
    
    # === МОНИТОРИНГ И ТАЙМАУТЫ ===
    
    async def _stage_timeout_monitor(self, stage: ProcessingStage):
        """Мониторинг таймаута этапа"""
        try:
            await asyncio.sleep(self.stage_timeout)
            
            if self.current_stage == stage and not self.interrupted:
                logger.warning(f"⏰ ProcessingWorkflow: таймаут этапа {stage.value} ({self.stage_timeout}с)")
                await self._handle_error(f"stage_timeout_{stage.value}")
                
        except asyncio.CancelledError:
            logger.debug(f"⚙️ ProcessingWorkflow: мониторинг этапа {stage.value} отменен")
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка мониторинга этапа - {e}")
    
    async def _total_timeout_monitor(self, session_id: str):
        """Мониторинг общего таймаута"""
        try:
            await asyncio.sleep(self.total_timeout)
            
            if self.current_session_id == session_id and not self.interrupted:
                logger.warning(f"⏰ ProcessingWorkflow: общий таймаут ({self.total_timeout}с)")
                await self._handle_error("total_timeout")
                
        except asyncio.CancelledError:
            logger.debug(f"⚙️ ProcessingWorkflow: общий мониторинг отменен")
        except Exception as e:
            logger.error(f"❌ ProcessingWorkflow: ошибка общего мониторинга - {e}")
    
    async def _cancel_timeout_tasks(self):
        """Отмена всех таймаутов"""
        if self.stage_timeout_task and not self.stage_timeout_task.done():
            self.stage_timeout_task.cancel()
            
        if self.total_timeout_task and not self.total_timeout_task.done():
            self.total_timeout_task.cancel()
    
    # === УТИЛИТЫ ===
    
    def _is_relevant_event(self, event) -> bool:
        """Проверка релевантности события"""
        if not self.is_active():
            return False
            
        # Фильтрация по сессии
        data = event.get("data", {})
        event_session = data.get("session_id")
        
        if self.current_session_id and event_session:
            return event_session == self.current_session_id
            
        return True
    
    def get_processing_duration(self) -> Optional[float]:
        """Получение длительности обработки"""
        if self.processing_start_time:
            return (datetime.now() - self.processing_start_time).total_seconds()
        return None
    
    def get_stage_duration(self) -> Optional[float]:
        """Получение длительности текущего этапа"""
        if self.stage_start_time:
            return (datetime.now() - self.stage_start_time).total_seconds()
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Расширенный статус workflow'а"""
        base_status = super().get_status()
        base_status.update({
            "current_stage": self.current_stage.value,
            "processing_duration": self.get_processing_duration(),
            "stage_duration": self.get_stage_duration(),
            "completed_stages": [stage.value for stage in self.completed_stages],
            "screenshot_captured": self.screenshot_captured,
            "grpc_completed": self.grpc_completed,
            "playback_completed": self.playback_completed,
            "interrupted": self.interrupted
        })
        return base_status
