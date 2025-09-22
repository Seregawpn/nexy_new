"""
ListeningWorkflow - Управление режимом LISTENING
Координирует дебаунс, таймауты и отмены для режима прослушивания
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .base_workflow import BaseWorkflow, WorkflowState, AppMode
from integration.core.event_bus import EventPriority

logger = logging.getLogger(__name__)

class ListeningWorkflow(BaseWorkflow):
    """
    Workflow для режима LISTENING.
    
    Функции:
    - Дебаунс защита от случайных нажатий
    - Умные таймауты (адаптивные)
    - Координированная отмена
    - Мониторинг качества записи
    """
    
    def __init__(self, event_bus):
        super().__init__(event_bus, "ListeningWorkflow")
        
        # Конфигурация
        self.debounce_threshold = 0.3  # секунд - минимальная длительность для валидного LISTENING
        self.max_listening_duration = 30.0  # секунд - максимальная длительность
        self.silence_timeout = 5.0  # секунд - таймаут тишины
        
        # Состояние
        self.listening_start_time: Optional[datetime] = None
        self.last_voice_activity: Optional[datetime] = None
        self.debounce_task: Optional[asyncio.Task] = None
        self.timeout_task: Optional[asyncio.Task] = None
        
    async def _setup_subscriptions(self):
        """Подписка на события режима LISTENING"""
        # Начало прослушивания
        await self.event_bus.subscribe(
            "voice.recording_start", 
            self._on_recording_start, 
            EventPriority.HIGH
        )
        
        # Завершение прослушивания
        await self.event_bus.subscribe(
            "voice.recording_stop", 
            self._on_recording_stop, 
            EventPriority.HIGH
        )
        
        # Прерывания
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
        
        # Мониторинг режимов
        await self.event_bus.subscribe(
            "app.mode_changed", 
            self._on_mode_changed, 
            EventPriority.MEDIUM
        )
        
        # Активность голоса (если доступно)
        await self.event_bus.subscribe(
            "voice.activity_detected", 
            self._on_voice_activity, 
            EventPriority.LOW
        )
    
    async def _on_start(self):
        """Запуск workflow'а"""
        logger.info("🎤 ListeningWorkflow: готов к координации прослушивания")
    
    async def _on_recording_start(self, event):
        """Обработка начала записи"""
        if not self.is_active():
            return
            
        try:
            data = event.get("data", {})
            session_id = data.get("session_id")
            
            logger.info(f"🎤 ListeningWorkflow: начало записи, session_id={session_id}")
            
            # Обновляем состояние
            self.current_session_id = session_id
            self.listening_start_time = datetime.now()
            self.last_voice_activity = datetime.now()
            self.state = WorkflowState.ACTIVE
            
            # Запускаем дебаунс проверку
            if self.debounce_task and not self.debounce_task.done():
                self.debounce_task.cancel()
            
            self.debounce_task = self._create_task(
                self._debounce_check(session_id), 
                "debounce_check"
            )
            
            # Запускаем таймаут мониторинг
            if self.timeout_task and not self.timeout_task.done():
                self.timeout_task.cancel()
                
            self.timeout_task = self._create_task(
                self._timeout_monitor(session_id), 
                "timeout_monitor"
            )
            
        except Exception as e:
            logger.error(f"❌ ListeningWorkflow: ошибка обработки recording_start - {e}")
    
    async def _on_recording_stop(self, event):
        """Обработка завершения записи"""
        try:
            data = event.get("data", {})
            session_id = data.get("session_id")
            
            logger.info(f"🎤 ListeningWorkflow: завершение записи, session_id={session_id}")
            
            # Проверяем сессию
            if self.current_session_id and session_id != self.current_session_id:
                logger.debug(f"🎤 ListeningWorkflow: игнорируем запись другой сессии")
                return
            
            # Отменяем таймауты
            await self._cancel_monitoring_tasks()
            
            # Проверяем длительность записи
            if self.listening_start_time:
                duration = (datetime.now() - self.listening_start_time).total_seconds()
                logger.info(f"🎤 ListeningWorkflow: длительность записи {duration:.2f}с")
                
                if duration < self.debounce_threshold:
                    logger.warning(f"🎤 ListeningWorkflow: запись слишком короткая ({duration:.2f}с), возможно случайное нажатие")
                    # Не переходим в PROCESSING для коротких записей
                    await self._return_to_sleeping("short_recording")
                    return
            
            # Переход в PROCESSING координируется InputProcessingIntegration
            # Мы только логируем успешное завершение
            logger.info(f"🎤 ListeningWorkflow: запись завершена успешно, ожидаем PROCESSING")
            
            # Сбрасываем состояние
            self._reset_state()
            
        except Exception as e:
            logger.error(f"❌ ListeningWorkflow: ошибка обработки recording_stop - {e}")
    
    async def _on_interrupt_request(self, event):
        """Обработка запроса прерывания"""
        if not self.is_active() or not self.current_session_id:
            return
            
        try:
            data = event.get("data", {})
            reason = data.get("reason", "user_interrupt")
            
            logger.info(f"🎤 ListeningWorkflow: получен запрос прерывания, reason={reason}")
            
            # Отменяем все мониторинговые задачи
            await self._cancel_monitoring_tasks()
            
            # Координированный возврат в SLEEPING
            await self._return_to_sleeping(reason)
            
        except Exception as e:
            logger.error(f"❌ ListeningWorkflow: ошибка обработки прерывания - {e}")
    
    async def _on_mode_changed(self, event):
        """Обработка смены режима"""
        try:
            data = event.get("data", {})
            new_mode = data.get("mode")
            
            if hasattr(new_mode, 'value'):
                mode_value = new_mode.value
            else:
                mode_value = str(new_mode).lower()
            
            logger.debug(f"🎤 ListeningWorkflow: режим изменен на {mode_value}")
            
            # Если вышли из LISTENING - сбрасываем состояние
            if mode_value != "listening" and self.state == WorkflowState.ACTIVE:
                logger.info(f"🎤 ListeningWorkflow: вышли из LISTENING, сбрасываем состояние")
                await self._cancel_monitoring_tasks()
                self._reset_state()
                
        except Exception as e:
            logger.error(f"❌ ListeningWorkflow: ошибка обработки mode_changed - {e}")
    
    async def _on_voice_activity(self, event):
        """Обработка активности голоса"""
        if self.state == WorkflowState.ACTIVE:
            self.last_voice_activity = datetime.now()
            logger.debug("🎤 ListeningWorkflow: зафиксирована голосовая активность")
    
    async def _debounce_check(self, session_id: str):
        """Проверка дебаунса - защита от случайных нажатий"""
        try:
            # Ждем минимальную длительность
            await asyncio.sleep(self.debounce_threshold)
            
            # Проверяем, что сессия еще активна
            if self.current_session_id != session_id:
                return
                
            logger.debug(f"🎤 ListeningWorkflow: дебаунс пройден для сессии {session_id}")
            
        except asyncio.CancelledError:
            logger.debug(f"🎤 ListeningWorkflow: дебаунс отменен для сессии {session_id}")
        except Exception as e:
            logger.error(f"❌ ListeningWorkflow: ошибка дебаунса - {e}")
    
    async def _timeout_monitor(self, session_id: str):
        """Мониторинг таймаутов"""
        try:
            # Максимальная длительность записи
            await asyncio.sleep(self.max_listening_duration)
            
            # Проверяем, что сессия еще активна
            if self.current_session_id != session_id:
                return
                
            logger.warning(f"🎤 ListeningWorkflow: достигнут максимальный таймаут ({self.max_listening_duration}с)")
            
            # Принудительно завершаем запись
            await self.event_bus.publish("voice.recording_stop", {
                "session_id": session_id,
                "reason": "max_duration_timeout"
            })
            
        except asyncio.CancelledError:
            logger.debug(f"🎤 ListeningWorkflow: мониторинг таймаута отменен для сессии {session_id}")
        except Exception as e:
            logger.error(f"❌ ListeningWorkflow: ошибка мониторинга таймаута - {e}")
    
    async def _cancel_monitoring_tasks(self):
        """Отмена всех мониторинговых задач"""
        if self.debounce_task and not self.debounce_task.done():
            self.debounce_task.cancel()
            
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()
    
    async def _return_to_sleeping(self, reason: str):
        """Координированный возврат в SLEEPING"""
        try:
            logger.info(f"🎤 ListeningWorkflow: возврат в SLEEPING, reason={reason}")
            
            await self._publish_mode_request(
                AppMode.SLEEPING, 
                f"listening_cancelled_{reason}",
                priority=80  # Высокий приоритет для отмен
            )
            
            self._reset_state()
            
        except Exception as e:
            logger.error(f"❌ ListeningWorkflow: ошибка возврата в SLEEPING - {e}")
    
    def _reset_state(self):
        """Сброс внутреннего состояния"""
        self.current_session_id = None
        self.listening_start_time = None
        self.last_voice_activity = None
        self.state = WorkflowState.IDLE
    
    def get_listening_duration(self) -> Optional[float]:
        """Получение длительности текущего прослушивания"""
        if self.listening_start_time:
            return (datetime.now() - self.listening_start_time).total_seconds()
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Расширенный статус workflow'а"""
        base_status = super().get_status()
        base_status.update({
            "listening_duration": self.get_listening_duration(),
            "last_voice_activity": self.last_voice_activity.isoformat() if self.last_voice_activity else None,
            "debounce_active": self.debounce_task is not None and not self.debounce_task.done(),
            "timeout_monitoring": self.timeout_task is not None and not self.timeout_task.done()
        })
        return base_status
