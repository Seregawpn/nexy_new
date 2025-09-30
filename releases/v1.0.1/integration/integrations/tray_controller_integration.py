"""
TrayController Integration
Обертка для TrayController с интеграцией в EventBus
Четкое разделение ответственности без дублирования
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Импорты модулей (НЕ дублируем логику!)
from modules.tray_controller import TrayController, TrayStatus, TrayConfig
from modules.tray_controller.core.tray_types import TrayEvent

# Импорт конфигурации
from config.unified_config_loader import UnifiedConfigLoader

# Импорты интеграции
from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory
from PyObjCTools import AppHelper
import rumps

logger = logging.getLogger(__name__)

# Убираем дублированную конфигурацию - используем TrayConfig из модуля

class TrayControllerIntegration:
    """Интеграция TrayController с EventBus и ApplicationStateManager"""
    
    def __init__(self, event_bus: EventBus, state_manager: ApplicationStateManager, 
                 error_handler: ErrorHandler, config: Optional[TrayConfig] = None):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        # Загружаем конфигурацию из unified_config.yaml
        unified_config = UnifiedConfigLoader()
        if config is None:
            # Создаем конфигурацию модуля из unified_config (с безопасными дефолтами)
            config_data = unified_config._load_config()
            integrations_cfg = (config_data.get('integrations') or {})
            tray_cfg = (integrations_cfg.get('tray_controller') or {})
            tray_basic = (config_data.get('tray') or {})

            icon_size = tray_cfg.get('icon_size', tray_basic.get('icon_size', 18))
            show_status_in_menu = tray_cfg.get('show_status_in_menu', True)
            enable_notifications = tray_cfg.get('enable_notifications', tray_basic.get('show_notifications', True))
            debug_mode = tray_cfg.get('debug_mode', (config_data.get('app') or {}).get('debug', False))

            config = TrayConfig(
                icon_size=icon_size,
                show_status=show_status_in_menu,  # Правильное поле
                show_menu=True,  # Из модуля
                enable_click_events=True,  # Из модуля
                enable_right_click=True,  # Из модуля
                auto_hide=False,  # Из модуля
                animation_speed=0.5,  # Из модуля
                menu_font_size=13,  # Из модуля
                enable_sound=enable_notifications,  # Маппинг
                debug_mode=debug_mode
            )
        
        self.config = config
        
        # TrayController (обертываем существующий модуль)
        self.tray_controller: Optional[TrayController] = None
        
        # Состояние интеграции
        self.is_initialized = False
        self.is_running = False
        # Желаемый статус трея (прямое применение в UI-треде при смене режима)
        self._desired_status: Optional[TrayStatus] = None
        self._ui_timer: Optional[rumps.Timer] = None
        self._ui_timer_started: bool = False
        self._ui_dirty: bool = False
        
        # Маппинг режимов приложения на статусы трея
        self.mode_to_status = {
            AppMode.SLEEPING: TrayStatus.SLEEPING,
            AppMode.LISTENING: TrayStatus.LISTENING,
            AppMode.PROCESSING: TrayStatus.PROCESSING,
        }
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            logger.info("🔧 Инициализация TrayControllerIntegration...")
            
            # Создаем TrayController (обертываем существующий модуль)
            self.tray_controller = TrayController()
            
            # Инициализируем TrayController
            success = await self.tray_controller.initialize()
            if not success:
                logger.error("❌ Ошибка инициализации TrayController")
                return False
            
            # Настраиваем обработчики событий
            await self._setup_event_handlers()
            
            self.is_initialized = True
            logger.info("✅ TrayControllerIntegration инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации TrayControllerIntegration: {e}")
            return False
    
    async def start(self) -> bool:
        """Запуск интеграции"""
        try:
            if not self.is_initialized:
                logger.error("TrayControllerIntegration не инициализирован")
                return False
            
            if self.is_running:
                logger.warning("TrayControllerIntegration уже запущен")
                return True
            
            logger.info("🚀 Запуск TrayControllerIntegration...")
            
            # Запускаем TrayController
            success = await self.tray_controller.start()
            if not success:
                logger.error("❌ Ошибка запуска TrayController")
                return False
            
            # Синхронизируем статус с текущим режимом приложения
            await self._sync_with_app_mode()
            
            self.is_running = True
            
            # Больше не используем периодический таймер для критичных обновлений иконки
            self._ui_timer = None

            # Публикуем событие готовности
            await self.event_bus.publish("tray.integration_ready", {
                "integration": "tray_controller",
                "status": "running"
            })
            
            logger.info("✅ TrayControllerIntegration запущен")

            # Обработчик клика по пункту Quit
            try:
                if self.tray_controller and hasattr(self.tray_controller, 'set_event_callback'):
                    self.tray_controller.set_event_callback("quit_clicked", self._on_tray_quit)
            except Exception:
                pass
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска TrayControllerIntegration: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка интеграции"""
        try:
            if not self.is_running:
                logger.warning("TrayControllerIntegration не запущен")
                return True
            
            logger.info("⏹️ Остановка TrayControllerIntegration...")
            
            # Останавливаем UI-таймер
            self.stop_ui_timer()
            
            # Останавливаем TrayController
            if self.tray_controller:
                success = await self.tray_controller.stop()
                if not success:
                    logger.warning("Ошибка остановки TrayController")
            
            self.is_running = False
            
            logger.info("✅ TrayControllerIntegration остановлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки TrayControllerIntegration: {e}")
            return False
    
    async def _setup_event_handlers(self):
        """Настройка обработчиков событий"""
        try:
            # Подписываемся на события приложения
            logger.info(f"🎯 TRAY DEBUG: Подписываемся на app.mode_changed событие")
            await self.event_bus.subscribe("app.mode_changed", self._on_mode_changed, EventPriority.HIGH)
            logger.info(f"🎯 TRAY DEBUG: Подписка на app.mode_changed успешна")
            await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.HIGH)
            await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.HIGH)
            
            # Подписываемся на события клавиатуры
            await self.event_bus.subscribe("keyboard.long_press", self._on_keyboard_event, EventPriority.MEDIUM)
            await self.event_bus.subscribe("keyboard.release", self._on_keyboard_event, EventPriority.MEDIUM)
            await self.event_bus.subscribe("keyboard.short_press", self._on_keyboard_event, EventPriority.MEDIUM)

            # Подписываемся на события микрофона/распознавания для точной индикации
            await self.event_bus.subscribe("voice.mic_opened", self._on_voice_mic_opened, EventPriority.HIGH)
            await self.event_bus.subscribe("voice.mic_closed", self._on_voice_mic_closed, EventPriority.HIGH)
            # Подписываемся на переключение аудиоустройств
            await self.event_bus.subscribe("audio.device_switched", self._on_audio_device_switched, EventPriority.MEDIUM)
            # Подписываемся на снапшот устройства для первичного заполнения
            await self.event_bus.subscribe("audio.device_snapshot", self._on_audio_device_snapshot, EventPriority.MEDIUM)
            
            logger.info("✅ Обработчики событий TrayControllerIntegration настроены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки обработчиков событий: {e}")

    async def _on_tray_quit(self, event_type: str, data: Dict[str, Any]):
        """Корректное завершение приложения по пункту меню Quit."""
        try:
            # Публикуем событие пользовательского завершения
            await self.event_bus.publish("tray.quit_clicked", {"source": "tray.quit"})
        except Exception:
            pass
        # Завершение приложения выполняет модуль TrayController (см. _on_quit_clicked)
    
    async def _sync_with_app_mode(self):
        """Синхронизация с текущим режимом приложения"""
        try:
            current_mode = self.state_manager.get_current_mode()
            if current_mode in self.mode_to_status:
                target_status = self.mode_to_status[current_mode]
                self._desired_status = target_status
                
                logger.info(f"🔄 Синхронизация с режимом приложения: {current_mode.value} → {target_status.value}")
        
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации с режимом приложения: {e}")
    
    async def _update_tray_status(self, status: TrayStatus):
        """Обновление статуса трея"""
        try:
            if not self.tray_controller or not self.is_running:
                return
            
            success = await self.tray_controller.update_status(status)
            if success:
                logger.info(f"🔄 Статус трея обновлен: {status.value}")
                # Обновляем текст статуса в меню для наглядности
                human = {
                    TrayStatus.SLEEPING: "Sleeping",
                    TrayStatus.LISTENING: "Listening",
                    TrayStatus.PROCESSING: "Processing",
                }.get(status, status.value.title())
                await self.tray_controller.update_menu_status_text(human)
            else:
                logger.warning(f"⚠️ Не удалось обновить статус трея: {status.value}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса трея: {e}")
    
    # Обработчики событий EventBus (НЕ дублируем логику модуля!)
    
    async def _on_mode_changed(self, event):
        """Обработка смены режима приложения"""
        try:
            # 🎯 TRAY DEBUG: Детальное логирование
            logger.info(f"🎯 TRAY DEBUG: _on_mode_changed ВЫЗВАН!")
            logger.info(f"🎯 TRAY DEBUG: event type={type(event)}, event={event}")
            
            data = (event.get("data") or {}) if isinstance(event, dict) else {}
            new_mode = data.get("mode")
            logger.info(f"🎯 TRAY DEBUG: data={data}")
            logger.info(f"🎯 TRAY DEBUG: new_mode={new_mode} (type: {type(new_mode)})")
            logger.info(f"🎯 TRAY DEBUG: mode_to_status={self.mode_to_status}")
            logger.info(f"🎯 TRAY DEBUG: new_mode in mapping? {new_mode in self.mode_to_status}")
            
            # Проверяем каждый ключ отдельно
            for key in self.mode_to_status.keys():
                logger.info(f"🎯 TRAY DEBUG: key={key} (type: {type(key)}), equals new_mode? {key == new_mode}")
            
            if new_mode in self.mode_to_status:
                target_status = self.mode_to_status[new_mode]
                logger.debug(f"TrayIntegration: mapping mode -> status: {new_mode} -> {target_status}")
                # Фиксируем желаемый статус и применяем немедленно в UI-потоке
                self._desired_status = target_status
                self._ui_dirty = True
                
                # Публикуем событие обновления статуса
                await self.event_bus.publish("tray.status_updated", {
                    "status": target_status.value,
                    "mode": new_mode.value,
                    "integration": "tray_controller"
                })
                
                logger.info(f"🔄 Режим приложения изменен: {new_mode.value} → {target_status.value}")
                # Применяем на главном UI-потоке через AppHelper.callAfter
                try:
                    AppHelper.callAfter(self._apply_status_ui, target_status)
                except Exception:
                    pass
        
        except Exception as e:
            logger.error(f"❌ Ошибка обработки смены режима: {e}")
    
    async def _on_keyboard_event(self, event):
        """Обработка событий клавиатуры"""
        try:
            # Безопасное получение типа события
            if isinstance(event, dict):
                event_type = event.get("type", "unknown")
            else:
                event_type = getattr(event, 'event_type', 'unknown')
            
            logger.info(f"⌨️ Обработка события клавиатуры в TrayControllerIntegration: {event_type}")
            
            # Push-to-talk: режимы меняются в InputProcessingIntegration
            # Здесь только логируем/можно обновлять UI, если нужно
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки события клавиатуры: {e}")
            import traceback
            logger.debug(f"Стектрейс: {traceback.format_exc()}")

    async def _on_voice_mic_opened(self, event):
        """Не меняем цвет иконки напрямую: источником истины остаётся app.mode_changed"""
        try:
            await self.event_bus.publish("tray.status_updated", {
                "status": getattr(self._desired_status, 'value', None),
                "reason": "voice.mic_opened",
                "integration": "tray_controller"
            })
        except Exception as e:
            logger.error(f"❌ Ошибка обработки voice.mic_opened: {e}")

    async def _on_voice_mic_closed(self, event):
        """Не меняем цвет иконки напрямую: всё через app.mode_changed"""
        try:
            mode = self.state_manager.get_current_mode()
            await self.event_bus.publish("tray.status_updated", {
                "status": getattr(self._desired_status, 'value', None),
                "mode": getattr(mode, 'value', str(mode)),
                "reason": "voice.mic_closed",
                "integration": "tray_controller"
            })
        except Exception as e:
            logger.error(f"❌ Ошибка обработки voice.mic_closed: {e}")

    def _apply_status_ui(self, status: TrayStatus):
        """Применение статуса в UI на главном потоке (через AppHelper.callAfter)."""
        try:
            # Вызов фактического обновления в UI-потоке
            AppHelper.callAfter(self._apply_status_ui_sync, status)
        except Exception as e:
            logger.error(f"❌ Ошибка планирования UI-обновления: {e}")

    def _apply_status_ui_sync(self, status: TrayStatus):
        """Фактическое обновление UI. ДОЛЖНО выполняться в главном UI-потоке."""
        logger.info(f"🎯 TRAY DEBUG: _apply_status_ui_sync ВЫЗВАН! status={status} (type: {type(status)})")
        if not self.tray_controller or not self.tray_controller.tray_menu or not self.tray_controller.tray_icon:
            logger.error(
                "🎯 TRAY DEBUG: UI компоненты не готовы! tray_controller=%s, tray_menu=%s, tray_icon=%s",
                bool(self.tray_controller),
                bool(self.tray_controller.tray_menu if self.tray_controller else False),
                bool(self.tray_controller.tray_icon if self.tray_controller else False),
            )
            return
        try:
            icon_path = self.tray_controller.tray_icon.create_icon_file(status)
            if not icon_path:
                logger.error("_apply_status_ui_sync: не удалось создать иконку")
                return
            self.tray_controller.tray_menu.update_icon(icon_path)
            human_names = {
                TrayStatus.SLEEPING: "Sleeping",
                TrayStatus.LISTENING: "Listening",
                TrayStatus.PROCESSING: "Processing",
            }
            human = human_names.get(status, status.value.title())
            self.tray_controller.tray_menu.update_status_text(human)
            prev_status = getattr(self.tray_controller, 'current_status', None)
            self.tray_controller.current_status = status
            self._ui_dirty = False
            prev_value = getattr(prev_status, 'value', str(prev_status)) if prev_status else 'None'
            logger.info(f"✅ Tray UI applied: {prev_value} -> {status.value}")
        except Exception as e:
            logger.error(f"❌ Ошибка _apply_status_ui_sync: {e}")

    async def _on_audio_device_switched(self, event):
        """Отображение устройства, на которое произошло переключение."""
        try:
            data = (event or {}).get("data", {})
            to_device = data.get("to_device") or data.get("device") or "Unknown"
            device_type = data.get("device_type", "output")
            # Обновляем пункт меню "Output: ..."
            if self.tray_controller:
                await self.tray_controller.update_menu_output_device(to_device)
                # Ненавязчивая нотификация (без звука)
                await self.tray_controller.show_notification(
                    title="Audio device switched",
                    message=f"Now using: {to_device}",
                    subtitle=device_type
                )
        except Exception as e:
            logger.error(f"❌ Ошибка обработки audio.device_switched: {e}")

    async def _on_audio_device_snapshot(self, event):
        """Первичное отображение текущего устройства в меню на старте."""
        try:
            data = (event or {}).get("data", {})
            cur = data.get("current_device") or "Unknown"
            if self.tray_controller:
                await self.tray_controller.update_menu_output_device(cur)
        except Exception as e:
            logger.debug(f"Failed to handle audio.device_snapshot in tray: {e}")

    # ---------- UI helper (runs in main rumps thread via Timer) ----------
    def _ui_tick(self, _timer):
        """UI-таймер: применяет изменения статуса иконки в главном потоке rumps"""
        try:
            # Проверяем базовые условия
            if not self.tray_controller:
                logger.debug("UI tick: tray_controller не инициализирован")
                return
            if not self.tray_controller.tray_menu:
                logger.debug("UI tick: tray_menu не инициализирован")
                return
            if not self.tray_controller.tray_icon:
                logger.debug("UI tick: tray_icon не инициализирован")
                return
            
            # Получаем желаемый статус
            desired = self._desired_status
            if not desired:
                logger.debug("UI tick: _desired_status не установлен")
                return
            
            # Получаем текущий статус
            current = getattr(self.tray_controller, 'current_status', None)
            try:
                logger.debug(f"UI tick: current={getattr(current,'value','None')}, desired={getattr(desired,'value','None')}")
            except Exception:
                pass
            
            # Проверяем, нужно ли обновление
            dirty = getattr(self, '_ui_dirty', False)
            if (current == desired) and (not dirty):
                # Логируем только первые несколько раз для отладки
                if not hasattr(self, '_ui_tick_debug_count'):
                    self._ui_tick_debug_count = 0
                if self._ui_tick_debug_count < 3:
                    logger.debug(f"UI tick: статус уже актуален ({desired.value}), dirty={dirty}")
                    self._ui_tick_debug_count += 1
                return
            
            logger.debug(f"UI tick: обновление иконки {getattr(current,'value','None')} -> {desired.value}")
            
            # Генерируем новую иконку
            try:
                icon_path = self.tray_controller.tray_icon.create_icon_file(desired)
                if not icon_path:
                    logger.error("❌ UI tick: не удалось создать иконку")
                    return
                
                # Применяем иконку в UI
                self.tray_controller.tray_menu.update_icon(icon_path)
                
                # Обновляем текст статуса в меню
                human_names = {
                    TrayStatus.SLEEPING: "Sleeping",
                    TrayStatus.LISTENING: "Listening", 
                    TrayStatus.PROCESSING: "Processing",
                }
                human = human_names.get(desired, desired.value.title())
                self.tray_controller.tray_menu.update_status_text(human)
                
                # Обновляем текущее состояние контроллера
                prev_status = getattr(self.tray_controller, 'current_status', None)
                self.tray_controller.current_status = desired
                self._ui_dirty = False
                
                # Логируем успешное обновление
                prev_value = getattr(prev_status, 'value', str(prev_status)) if prev_status else 'None'
                logger.info(f"✅ Tray UI applied: {prev_value} -> {desired.value}")
                
                # Сбрасываем счетчик отладки при успешном обновлении
                if hasattr(self, '_ui_tick_debug_count'):
                    self._ui_tick_debug_count = 0
                
            except Exception as e:
                logger.error(f"❌ UI tick: ошибка применения изменений: {e}")
                import traceback
                logger.debug(f"UI tick stacktrace: {traceback.format_exc()}")
                
        except Exception as e:
            logger.error(f"❌ UI tick: критическая ошибка: {e}")
            import traceback
            logger.debug(f"UI tick critical stacktrace: {traceback.format_exc()}")
    
    async def _on_app_startup(self, event):
        """Обработка запуска приложения"""
        try:
            logger.info("🚀 Обработка запуска приложения в TrayControllerIntegration")
            await self._sync_with_app_mode()
            # Применяем текущий режим на главном UI-потоке
            try:
                mode = self.state_manager.get_current_mode()
                status = self.mode_to_status.get(mode)
                if status:
                    AppHelper.callAfter(self._apply_status_ui, status)
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки запуска приложения: {e}")
    
    async def _on_app_shutdown(self, event):
        """Обработка завершения приложения"""
        try:
            logger.info("⏹️ Обработка завершения приложения в TrayControllerIntegration")
            await self.stop()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки завершения приложения: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус интеграции"""
        return {
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "tray_controller": {
                "initialized": self.tray_controller is not None,
                "running": self.tray_controller.is_running if self.tray_controller else False,
                "current_status": self.tray_controller.current_status.value if self.tray_controller else None
            },
            "config": {
                "icon_size": self.config.icon_size,
                "show_status_in_menu": self.config.show_status_in_menu,
                "enable_notifications": self.config.enable_notifications,
                "auto_update_status": self.config.auto_update_status,
                "debug_mode": self.config.debug_mode
            }
        }
    
    def get_app(self):
        """Получить приложение rumps для запуска в главном потоке"""
        if self.tray_controller:
            return self.tray_controller.get_app()
        return None
    
    def start_ui_timer(self):
        """Запустить UI-таймер после app.run() - вызывается из главного потока rumps"""
        try:
            # Периодический таймер больше не требуется — молча игнорируем вызов
            if self._ui_timer and not self._ui_timer_started:
                try:
                    self._ui_timer.start()
                    self._ui_timer_started = True
                except Exception:
                    pass
            # Если таймера нет — ничего не делаем (без логирования)
        except Exception as e:
            logger.error(f"❌ Ошибка запуска UI-таймера: {e}")
    
    def stop_ui_timer(self):
        """Остановить UI-таймер"""
        try:
            if self._ui_timer and getattr(self._ui_timer, 'is_alive', lambda: False)():
                self._ui_timer.stop()
                self._ui_timer_started = False
                logger.info("⏹️ UI-таймер остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки UI-таймера: {e}")
