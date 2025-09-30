"""
Интеграция для управления VoiceOver Ducking
Тонкая обертка над VoiceOverController для интеграции с EventBus
"""
import asyncio
import logging
from typing import Any, Dict, Optional

from integration.core.base_integration import BaseIntegration
from modules.voiceover_control.core.controller import VoiceOverController, VoiceOverControlSettings

logger = logging.getLogger(__name__)


class VoiceOverDuckingIntegration(BaseIntegration):
    """Интеграция для управления VoiceOver Ducking через EventBus."""

    def __init__(self, event_bus, state_manager, error_handler, config=None):
        super().__init__(event_bus, state_manager, error_handler, "voiceover_ducking")
        self.config = config or {}
        self.controller = None
        self._initialized = False

    async def _do_initialize(self) -> bool:
        """Инициализация интеграции VoiceOver Ducking."""
        try:
            logger.info("🔧 Инициализация VoiceOverDuckingIntegration...")
            
            # Создаем настройки из конфигурации
            settings = VoiceOverControlSettings(**self.config)
            
            # Создаем контроллер
            self.controller = VoiceOverController(settings)
            
            # Инициализируем контроллер
            if not await self.controller.initialize():
                logger.error("VoiceOverDuckingIntegration: Failed to initialize controller")
                return False
            
            # Подписываемся на события
            await self.event_bus.subscribe("app.mode_changed", self.handle_mode_change)
            await self.event_bus.subscribe("keyboard.press", self.handle_keyboard_press)
            await self.event_bus.subscribe("app.shutdown", self.handle_shutdown)
            
            self._initialized = True
            logger.info("✅ VoiceOverDuckingIntegration инициализирован")
            return True
            
        except Exception as exc:
            logger.error("Failed to initialize VoiceOverDuckingIntegration: %s", exc)
            return False

    async def _do_start(self) -> bool:
        """Запуск интеграции."""
        if not self._initialized:
            logger.error("VoiceOverDuckingIntegration: Not initialized")
            return False
        
        try:
            logger.info("🚀 VoiceOverDuckingIntegration запущен")
            return True
        except Exception as exc:
            logger.error("Failed to start VoiceOverDuckingIntegration: %s", exc)
            return False

    async def _do_stop(self) -> bool:
        """Остановка интеграции."""
        try:
            if self.controller:
                await self.controller.shutdown()
            logger.info("🛑 VoiceOverDuckingIntegration остановлен")
            return True
        except Exception as exc:
            logger.error("Failed to stop VoiceOverDuckingIntegration: %s", exc)
            return False

    async def handle_mode_change(self, event: Dict[str, Any]) -> None:
        """Обработка изменения режима приложения."""
        try:
            if not self.controller:
                return
            
            mode_data = event.get("data", {})
            mode = mode_data.get("mode")
            
            if not mode:
                logger.warning("VoiceOverDuckingIntegration: No mode in event data")
                return
            
            # Обновляем состояние VoiceOver перед применением режима
            await self.controller.update_voiceover_status()
            
            # Применяем режим к контроллеру
            await self.controller.apply_mode(mode.value)
            logger.debug("VoiceOverDuckingIntegration: Applied mode %s", mode.value)
            
        except Exception as exc:
            await self.error_handler.handle_error(exc, "handle_mode_change")

    async def handle_keyboard_press(self, event: Dict[str, Any]) -> None:
        """Обработка нажатия клавиши для ducking."""
        try:
            if not self.controller:
                return
            
            # Проверяем, нужно ли ducking при нажатии клавиши
            if self.controller.settings.engage_on_keyboard_events:
                # Обновляем состояние VoiceOver перед ducking
                await self.controller.update_voiceover_status()
                await self.controller.duck(reason="keyboard.press")
                logger.debug("VoiceOverDuckingIntegration: Ducking on keyboard press")
                
        except Exception as exc:
            await self.error_handler.handle_error(exc, "handle_keyboard_press")

    async def handle_shutdown(self, event: Dict[str, Any]) -> None:
        """Обработка завершения работы приложения."""
        try:
            if self.controller:
                await self.controller.shutdown()
                logger.info("VoiceOverDuckingIntegration: Shutdown completed")
                
        except Exception as exc:
            await self.error_handler.handle_error(exc, "handle_shutdown")

    async def manual_duck(self, reason: str = "manual") -> bool:
        """Ручное отключение VoiceOver."""
        try:
            if not self.controller:
                logger.error("VoiceOverDuckingIntegration: Controller not initialized")
                return False
            
            return await self.controller.duck(reason=reason)
            
        except Exception as exc:
            await self.error_handler.handle_error(exc, "manual_duck")
            return False

    async def manual_release(self, force: bool = False) -> bool:
        """Ручное восстановление VoiceOver."""
        try:
            if not self.controller:
                logger.error("VoiceOverDuckingIntegration: Controller not initialized")
                return False
            
            await self.controller.release(force=force)
            return True
            
        except Exception as exc:
            await self.error_handler.handle_error(exc, "manual_release")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Получить статус интеграции."""
        return {
            "initialized": self._initialized,
            "controller_available": self.controller is not None,
            "config": self.config,
            "enabled": self.config.get("enabled", True)
        }
