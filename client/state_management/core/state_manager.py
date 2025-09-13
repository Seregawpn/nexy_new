"""
Основной менеджер состояний приложения
"""

import asyncio
import threading
import time
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

from .types import (
    AppState, StateTransition, StateConfig, StateMetrics, StateInfo,
    StateChangedCallback, ErrorCallback, RecoveryCallback
)
from .state_validator import StateValidator
from ..monitoring.state_monitor import StateMonitor
from ..recovery.state_recovery import StateRecovery

logger = logging.getLogger(__name__)


class StateManager:
    """Основной менеджер состояний приложения"""
    
    def __init__(self, config: Optional[StateConfig] = None):
        self.config = config or StateConfig()
        
        # Состояние приложения
        self._state = AppState.SLEEPING
        self._state_lock = threading.RLock()
        self._state_start_time = time.time()
        
        # Компоненты
        self.validator = StateValidator()
        self.monitor = StateMonitor(self.config.max_history_size)
        self.recovery = StateRecovery(self)
        
        # Callbacks
        self.on_state_changed: Optional[StateChangedCallback] = None
        self.on_error: Optional[ErrorCallback] = None
        self.on_recovery: Optional[RecoveryCallback] = None
        
        # Активные задачи
        self.active_tasks: List[asyncio.Task] = []
        self._task_lock = threading.RLock()
        
        # Флаги
        self._shutdown_requested = False
        self._shutdown_lock = threading.RLock()
        
        logger.info("🔄 State Manager инициализирован")
    
    @property
    def state(self) -> AppState:
        """Возвращает текущее состояние"""
        with self._state_lock:
            return self._state
    
    @state.setter
    def state(self, new_state: AppState):
        """Устанавливает новое состояние (только для внутреннего использования)"""
        with self._state_lock:
            self._state = new_state
    
    async def _transition_to_state(self, new_state: AppState, reason: str = "") -> bool:
        """
        Выполняет переход к новому состоянию
        
        Args:
            new_state: Новое состояние
            reason: Причина перехода
            
        Returns:
            bool: True если переход успешен
        """
        try:
            with self._state_lock:
                current_state = self._state
                
                # Проверяем, можно ли выполнить переход
                if not self.validator.can_transition(current_state, new_state):
                    logger.warning(f"Невозможен переход: {current_state.value} → {new_state.value}")
                    return False
                
                # Валидируем новое состояние
                if not self.validator.validate_state(new_state):
                    logger.warning(f"Некорректное состояние: {new_state.value}")
                    return False
                
                # Выполняем переход
                start_time = time.time()
                success = await self._execute_transition(current_state, new_state, reason)
                duration = time.time() - start_time
                
                if success:
                    # Обновляем состояние
                    self._state = new_state
                    self._state_start_time = time.time()
                    
                    # Записываем переход
                    self.monitor.record_transition(current_state, new_state, duration, True, reason)
                    
                    # Логируем переход
                    self._log_state_transition(current_state, new_state, reason)
                    
                    # Уведомляем callback
                    if self.on_state_changed:
                        try:
                            self.on_state_changed(current_state, new_state, reason)
                        except Exception as e:
                            logger.error(f"Ошибка callback состояния: {e}")
                    
                    return True
                else:
                    # Записываем неудачный переход
                    self.monitor.record_transition(current_state, new_state, duration, False, reason)
                    return False
                    
        except Exception as e:
            logger.error(f"Ошибка перехода к состоянию: {e}")
            return False
    
    async def _execute_transition(self, from_state: AppState, to_state: AppState, reason: str) -> bool:
        """
        Выполняет логику перехода между состояниями
        
        Args:
            from_state: Исходное состояние
            to_state: Целевое состояние
            reason: Причина перехода
            
        Returns:
            bool: True если переход успешен
        """
        try:
            # Определяем тип перехода
            transition_type = self.validator.get_transition_type(from_state, to_state)
            
            if transition_type == StateTransition.SLEEP_TO_LISTEN:
                return await self._execute_sleep_to_listen()
            elif transition_type == StateTransition.LISTEN_TO_PROCESS:
                return await self._execute_listen_to_process()
            elif transition_type == StateTransition.PROCESS_TO_SLEEP:
                return await self._execute_process_to_sleep()
            elif transition_type == StateTransition.ANY_TO_ERROR:
                return await self._execute_any_to_error()
            elif transition_type == StateTransition.ERROR_TO_SLEEP:
                return await self._execute_error_to_sleep()
            elif transition_type == StateTransition.ANY_TO_SHUTDOWN:
                return await self._execute_any_to_shutdown()
            else:
                # Остаемся в том же состоянии
                return True
                
        except Exception as e:
            logger.error(f"Ошибка выполнения перехода: {e}")
            return False
    
    async def _execute_sleep_to_listen(self) -> bool:
        """Выполняет переход от сна к прослушиванию"""
        try:
            logger.info("Переход: SLEEPING → LISTENING")
            # Здесь должна быть логика активации микрофона
            return True
        except Exception as e:
            logger.error(f"Ошибка перехода к прослушиванию: {e}")
            return False
    
    async def _execute_listen_to_process(self) -> bool:
        """Выполняет переход от прослушивания к обработке"""
        try:
            logger.info("Переход: LISTENING → PROCESSING")
            # Здесь должна быть логика остановки записи и получения текста
            return True
        except Exception as e:
            logger.error(f"Ошибка перехода к обработке: {e}")
            return False
    
    async def _execute_process_to_sleep(self) -> bool:
        """Выполняет переход от обработки ко сну"""
        try:
            logger.info("Переход: PROCESSING → SLEEPING")
            # Останавливаем активные задачи
            await self._cancel_active_tasks()
            return True
        except Exception as e:
            logger.error(f"Ошибка перехода ко сну: {e}")
            return False
    
    async def _execute_any_to_error(self) -> bool:
        """Выполняет переход в состояние ошибки"""
        try:
            logger.warning("Переход: ANY → ERROR")
            # Останавливаем все активные операции
            await self._cancel_active_tasks()
            return True
        except Exception as e:
            logger.error(f"Ошибка перехода к ошибке: {e}")
            return False
    
    async def _execute_error_to_sleep(self) -> bool:
        """Выполняет переход от ошибки ко сну"""
        try:
            logger.info("Переход: ERROR → SLEEPING")
            # Сбрасываем состояние
            self.monitor.record_recovery()
            
            # Уведомляем callback
            if self.on_recovery:
                try:
                    self.on_recovery(AppState.SLEEPING)
                except Exception as e:
                    logger.error(f"Ошибка callback восстановления: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка перехода от ошибки: {e}")
            return False
    
    async def _execute_any_to_shutdown(self) -> bool:
        """Выполняет переход к завершению"""
        try:
            logger.info("Переход: ANY → SHUTDOWN")
            # Останавливаем все активные операции
            await self._cancel_active_tasks()
            return True
        except Exception as e:
            logger.error(f"Ошибка перехода к завершению: {e}")
            return False
    
    async def _cancel_active_tasks(self):
        """Отменяет активные задачи"""
        try:
            with self._task_lock:
                for task in self.active_tasks:
                    if not task.done():
                        task.cancel()
                
                # Ждем завершения задач
                if self.active_tasks:
                    await asyncio.gather(*self.active_tasks, return_exceptions=True)
                
                self.active_tasks.clear()
        except Exception as e:
            logger.error(f"Ошибка отмены активных задач: {e}")
    
    def _log_state_transition(self, from_state: AppState, to_state: AppState, reason: str):
        """Логирует переход между состояниями"""
        try:
            logger.info(f"🔄 {from_state.value} → {to_state.value} ({reason})")
        except Exception as e:
            logger.error(f"Ошибка логирования перехода: {e}")
    
    # Публичные методы для управления состояниями
    
    async def start_listening(self) -> bool:
        """Начинает прослушивание команд"""
        return await self._transition_to_state(AppState.LISTENING, "пользователь нажал кнопку")
    
    async def stop_listening(self) -> bool:
        """Останавливает прослушивание команд"""
        return await self._transition_to_state(AppState.SLEEPING, "пользователь отпустил кнопку")
    
    async def start_processing(self) -> bool:
        """Начинает обработку команды"""
        return await self._transition_to_state(AppState.PROCESSING, "команда распознана")
    
    async def stop_processing(self) -> bool:
        """Завершает обработку команды"""
        return await self._transition_to_state(AppState.SLEEPING, "обработка завершена")
    
    async def sleep(self) -> bool:
        """Переводит приложение в режим сна"""
        return await self._transition_to_state(AppState.SLEEPING, "принудительный сон")
    
    async def error(self, error: Exception, context: str = "") -> bool:
        """Переводит приложение в состояние ошибки"""
        try:
            # Записываем ошибку
            self.monitor.record_error(error, context)
            
            # Уведомляем callback
            if self.on_error:
                try:
                    self.on_error(error, context)
                except Exception as e:
                    logger.error(f"Ошибка callback ошибки: {e}")
            
            return await self._transition_to_state(AppState.ERROR, f"ошибка: {context}")
        except Exception as e:
            logger.error(f"Ошибка перехода к ошибке: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Завершает работу приложения"""
        try:
            with self._shutdown_lock:
                if self._shutdown_requested:
                    return True
                self._shutdown_requested = True
            
            return await self._transition_to_state(AppState.SHUTDOWN, "завершение работы")
        except Exception as e:
            logger.error(f"Ошибка завершения работы: {e}")
            return False
    
    # Методы проверки состояний
    
    def is_listening(self) -> bool:
        """Проверяет, находится ли приложение в режиме прослушивания"""
        return self.state == AppState.LISTENING
    
    def is_processing(self) -> bool:
        """Проверяет, находится ли приложение в режиме обработки"""
        return self.state == AppState.PROCESSING
    
    def is_sleeping(self) -> bool:
        """Проверяет, находится ли приложение в режиме сна"""
        return self.state == AppState.SLEEPING
    
    def is_error(self) -> bool:
        """Проверяет, находится ли приложение в состоянии ошибки"""
        return self.state == AppState.ERROR
    
    def is_shutdown(self) -> bool:
        """Проверяет, завершается ли приложение"""
        return self.state == AppState.SHUTDOWN
    
    def get_state_name(self) -> str:
        """Возвращает название текущего состояния"""
        return self.state.value
    
    # Методы для мониторинга
    
    def get_metrics(self) -> StateMetrics:
        """Возвращает метрики состояний"""
        return self.monitor.get_metrics()
    
    def get_state_history(self, limit: int = 10) -> List[StateInfo]:
        """Возвращает историю состояний"""
        return self.monitor.get_state_history(limit)
    
    # Callback методы
    
    def set_state_changed_callback(self, callback: StateChangedCallback):
        """Устанавливает callback для изменений состояния"""
        self.on_state_changed = callback
    
    def set_error_callback(self, callback: ErrorCallback):
        """Устанавливает callback для ошибок"""
        self.on_error = callback
    
    def set_recovery_callback(self, callback: RecoveryCallback):
        """Устанавливает callback для восстановления"""
        self.on_recovery = callback
    
    # Cleanup
    
    async def cleanup(self):
        """Очистка ресурсов при выходе"""
        try:
            # Останавливаем активные задачи
            await self._cancel_active_tasks()
            
            logger.info("🧹 Ресурсы очищены")
        except Exception as e:
            logger.error(f"Ошибка очистки ресурсов: {e}")
