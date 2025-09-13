"""
Контроллер режимов - управляет переходами между состояниями приложения
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

from .types import (
    AppMode, ModeTransition, ModeTransitionType, ModeStatus, ModeEvent,
    ModeConfig, ModeMetrics
)

logger = logging.getLogger(__name__)

class ModeController:
    """Контроллер режимов приложения"""
    
    def __init__(self, config: ModeConfig = None):
        self.config = config or ModeConfig()
        self.current_mode = self.config.default_mode
        self.previous_mode = None
        self.mode_start_time = time.time()
        
        # Переходы между режимами
        self.transitions: Dict[AppMode, List[ModeTransition]] = {}
        
        # Обработчики режимов
        self.mode_handlers: Dict[AppMode, Callable] = {}
        
        # Callbacks для уведомлений
        self.mode_change_callbacks: List[Callable] = []
        
        # Метрики
        self.metrics = ModeMetrics()
        
        # Блокировка для thread-safety
        self._lock = asyncio.Lock()
        
    def register_transition(self, transition: ModeTransition):
        """Регистрирует переход между режимами"""
        if transition.from_mode not in self.transitions:
            self.transitions[transition.from_mode] = []
        
        # Сортируем по приоритету (высший приоритет = меньшее число)
        self.transitions[transition.from_mode].append(transition)
        self.transitions[transition.from_mode].sort(key=lambda x: x.priority)
        
        logger.debug(f"📝 Зарегистрирован переход: {transition.from_mode.value} → {transition.to_mode.value}")
        
    def register_mode_handler(self, mode: AppMode, handler: Callable):
        """Регистрирует обработчик режима"""
        self.mode_handlers[mode] = handler
        logger.debug(f"📝 Зарегистрирован обработчик для режима {mode.value}")
        
    def register_mode_change_callback(self, callback: Callable):
        """Регистрирует callback для смены режима"""
        self.mode_change_callbacks.append(callback)
        logger.debug("📝 Зарегистрирован callback смены режима")
        
    async def switch_mode(self, new_mode: AppMode, force: bool = False, 
                         transition_type: ModeTransitionType = ModeTransitionType.MANUAL,
                         data: Dict[str, Any] = None) -> bool:
        """Переключает режим приложения"""
        async with self._lock:
            try:
                # Проверяем, можно ли переключиться
                if not force and not self.can_switch_to(new_mode):
                    logger.warning(f"⚠️ Нельзя переключиться из {self.current_mode.value} в {new_mode.value}")
                    return False
                
                # Если уже в нужном режиме
                if self.current_mode == new_mode:
                    logger.debug(f"ℹ️ Уже в режиме {new_mode.value}")
                    return True
                
                # Обновляем метрики времени в текущем режиме
                current_time = time.time()
                time_in_current_mode = current_time - self.mode_start_time
                self.metrics.time_in_modes[self.current_mode] += time_in_current_mode
                
                # Сохраняем предыдущий режим
                self.previous_mode = self.current_mode
                
                # Находим переход
                transition = self._find_transition(self.current_mode, new_mode)
                
                # Выполняем переход
                if transition and transition.action:
                    logger.info(f"🔄 Выполнение перехода: {transition.from_mode.value} → {transition.to_mode.value}")
                    await transition.action()
                
                # Переключаем режим
                old_mode = self.current_mode
                self.current_mode = new_mode
                self.mode_start_time = current_time
                
                # Выполняем обработчик режима
                handler = self.mode_handlers.get(new_mode)
                if handler:
                    try:
                        await handler()
                    except Exception as e:
                        logger.error(f"❌ Ошибка в обработчике режима {new_mode.value}: {e}")
                
                # Уведомляем о смене режима
                await self._notify_mode_change(old_mode, new_mode, transition_type, data)
                
                # Обновляем метрики
                self.metrics.total_transitions += 1
                self.metrics.successful_transitions += 1
                self.metrics.transitions_by_type[transition_type] += 1
                
                logger.info(f"✅ Режим изменен: {old_mode.value} → {new_mode.value}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Ошибка переключения режима: {e}")
                self.metrics.failed_transitions += 1
                return False
                
    def can_switch_to(self, mode: AppMode) -> bool:
        """Проверяет, можно ли переключиться в режим"""
        transitions = self.transitions.get(self.current_mode, [])
        return any(t.to_mode == mode for t in transitions)
        
    def _find_transition(self, from_mode: AppMode, to_mode: AppMode) -> Optional[ModeTransition]:
        """Находит переход между режимами"""
        transitions = self.transitions.get(from_mode, [])
        for transition in transitions:
            if transition.to_mode == to_mode:
                return transition
        return None
        
    async def _notify_mode_change(self, from_mode: AppMode, to_mode: AppMode, 
                                 transition_type: ModeTransitionType, data: Dict[str, Any] = None):
        """Уведомляет о смене режима"""
        try:
            event = ModeEvent(
                mode=to_mode,
                status=ModeStatus.ACTIVE,
                timestamp=time.time(),
                transition_type=transition_type,
                data=data
            )
            
            for callback in self.mode_change_callbacks:
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"❌ Ошибка в callback смены режима: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления о смене режима: {e}")
            
    def get_current_mode(self) -> AppMode:
        """Возвращает текущий режим"""
        return self.current_mode
        
    def get_previous_mode(self) -> Optional[AppMode]:
        """Возвращает предыдущий режим"""
        return self.previous_mode
        
    def get_available_transitions(self) -> List[AppMode]:
        """Возвращает доступные переходы из текущего режима"""
        transitions = self.transitions.get(self.current_mode, [])
        return [t.to_mode for t in transitions]
        
    def get_metrics(self) -> ModeMetrics:
        """Возвращает метрики режимов"""
        return self.metrics
        
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус контроллера режимов"""
        current_time = time.time()
        time_in_current_mode = current_time - self.mode_start_time
        
        return {
            "current_mode": self.current_mode.value,
            "previous_mode": self.previous_mode.value if self.previous_mode else None,
            "time_in_current_mode": time_in_current_mode,
            "available_transitions": [m.value for m in self.get_available_transitions()],
            "total_transitions": self.metrics.total_transitions,
            "successful_transitions": self.metrics.successful_transitions,
            "failed_transitions": self.metrics.failed_transitions,
            "success_rate": (
                self.metrics.successful_transitions / max(self.metrics.total_transitions, 1) * 100
            ),
            "handlers_registered": len(self.mode_handlers),
            "callbacks_registered": len(self.mode_change_callbacks),
            "config": {
                "default_mode": self.config.default_mode.value,
                "enable_automatic_transitions": self.config.enable_automatic_transitions,
                "transition_timeout": self.config.transition_timeout,
            }
        }
