"""
SimpleModuleCoordinator - Центральный координатор модулей
Управляет инициализацией, запуском и остановкой всех модулей приложения
Четкое разделение ответственности без дублирования
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent))

# Импорты интеграций (НЕ модулей напрямую!)
from integrations.tray_controller_integration import TrayControllerIntegration, TrayControllerConfig
from integrations.input_processing_integration import InputProcessingIntegration, InputProcessingConfig
from integrations.permissions_integration import PermissionsIntegration, PermissionsIntegrationConfig
from integrations.update_manager_integration import UpdateManagerIntegration, UpdateManagerIntegrationConfig
from integrations.network_manager_integration import NetworkManagerIntegration, NetworkManagerIntegrationConfig
from integrations.audio_device_integration import AudioDeviceIntegration, AudioDeviceIntegrationConfig
from integrations.interrupt_management_integration import InterruptManagementIntegration, InterruptManagementIntegrationConfig
from modules.input_processing.keyboard.types import KeyboardConfig

# Импорты core компонентов
from .event_bus import EventBus, EventPriority
from .state_manager import ApplicationStateManager, AppMode
from .error_handler import ErrorHandler, ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)

class SimpleModuleCoordinator:
    """Центральный координатор модулей для Nexy AI Assistant"""
    
    def __init__(self):
        # Core компоненты (центральные)
        self.event_bus: Optional[EventBus] = None
        self.state_manager: Optional[ApplicationStateManager] = None
        self.error_handler: Optional[ErrorHandler] = None
        
        # Интеграции (обертки для модулей)
        self.integrations: Dict[str, Any] = {}
        
        # Состояние
        self.is_initialized = False
        self.is_running = False
        
    async def initialize(self) -> bool:
        """Инициализация всех компонентов и интеграций"""
        try:
            print("\n" + "="*60)
            print("🚀 SIMPLE MODULE COORDINATOR - ИНИЦИАЛИЗАЦИЯ")
            print("="*60)
            print("Инициализация core компонентов и интеграций...")
            print("="*60 + "\n")
            
            # 1. Создаем core компоненты
            print("🔧 Создание core компонентов...")
            self.event_bus = EventBus()
            self.state_manager = ApplicationStateManager()
            self.error_handler = ErrorHandler(self.event_bus)
            print("✅ Core компоненты созданы")
            
            # 2. Создаем интеграции
            print("🔧 Создание интеграций...")
            await self._create_integrations()
            print("✅ Интеграции созданы")
            
            # 3. Инициализируем интеграции
            print("🔧 Инициализация интеграций...")
            await self._initialize_integrations()
            print("✅ Интеграции инициализированы")
            
            # 4. Настраиваем координацию
            print("🔧 Настройка координации...")
            await self._setup_coordination()
            print("✅ Координация настроена")
            
            self.is_initialized = True
            
            print("\n" + "="*60)
            print("✅ ВСЕ КОМПОНЕНТЫ ИНИЦИАЛИЗИРОВАНЫ!")
            print("="*60)
            print("🎯 Иконка должна появиться в меню-баре macOS")
            print("🖱️ Кликните по иконке, чтобы увидеть меню")
            print("⌨️ Нажмите ПРОБЕЛ для тестирования клавиатуры")
            print("⌨️ Нажмите Ctrl+C для выхода")
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            print(f"❌ Критическая ошибка инициализации: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _create_integrations(self):
        """Создание всех интеграций"""
        try:
            # TrayController Integration
            tray_config = TrayControllerConfig(
                icon_size=16,
                show_status_in_menu=True,
                enable_notifications=True,
                auto_update_status=True,
                debug_mode=True
            )
            
            self.integrations['tray'] = TrayControllerIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=tray_config
            )
            
            # InputProcessing Integration
            keyboard_config = KeyboardConfig(
                key_to_monitor="space",
                short_press_threshold=0.6,
                long_press_threshold=2.0,
                event_cooldown=0.1,
                hold_check_interval=0.05,
                debounce_time=0.1
            )
            
            input_config = InputProcessingConfig(
                keyboard_config=keyboard_config,
                enable_keyboard_monitoring=True,
                auto_start=True
            )
            
            self.integrations['input'] = InputProcessingIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=input_config
            )
            
            # Permissions Integration
            permissions_config = PermissionsIntegrationConfig(
                check_interval=30,
                auto_request_required=True,
                show_instructions=True,
                open_preferences=True,
                debug_mode=True
            )
            
            self.integrations['permissions'] = PermissionsIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=permissions_config
            )
            
            # Update Manager Integration
            update_config = UpdateManagerIntegrationConfig(
                enabled=True,
                check_interval=24,
                check_time="02:00",
                auto_install=True,
                announce_updates=False,  # Тихий режим
                check_on_startup=True,
                appcast_url="https://api.nexy.ai/updates/appcast.xml",
                retry_attempts=3,
                retry_delay=300,
                silent_mode=True,  # Полностью тихий режим
                log_updates=True
            )
            
            self.integrations['update_manager'] = UpdateManagerIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=update_config
            )
            
            # Network Manager Integration
            network_config = NetworkManagerIntegrationConfig(
                check_interval=30.0,
                ping_timeout=5.0,
                ping_hosts=["8.8.8.8", "1.1.1.1", "google.com"]
            )
            
            self.integrations['network'] = NetworkManagerIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=network_config
            )
            
            # Audio Device Integration
            audio_config = AudioDeviceIntegrationConfig(
                auto_switch_enabled=True,
                monitoring_interval=3.0,
                switch_delay=0.5,
                enable_microphone_on_listening=True,
                disable_microphone_on_sleeping=True,
                disable_microphone_on_processing=True
            )
            
            self.integrations['audio'] = AudioDeviceIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=audio_config
            )
            
            # Interrupt Management Integration
            interrupt_config = InterruptManagementIntegrationConfig(
                max_concurrent_interrupts=5,
                interrupt_timeout=10.0,
                retry_attempts=3,
                retry_delay=1.0,
                enable_speech_interrupts=True,
                enable_recording_interrupts=True,
                enable_session_interrupts=True,
                enable_full_reset=True
            )
            
            self.integrations['interrupt'] = InterruptManagementIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=interrupt_config
            )
            
            print("✅ Интеграции созданы: tray, input, permissions, update_manager, network, audio, interrupt")
            
        except Exception as e:
            print(f"❌ Ошибка создания интеграций: {e}")
            raise
    
    async def _initialize_integrations(self):
        """Инициализация всех интеграций"""
        try:
            for name, integration in self.integrations.items():
                print(f"🔧 Инициализация {name}...")
                success = await integration.initialize()
                if not success:
                    print(f"❌ Ошибка инициализации {name}")
                    raise Exception(f"Failed to initialize {name}")
                print(f"✅ {name} инициализирован")
                
        except Exception as e:
            print(f"❌ Ошибка инициализации интеграций: {e}")
            raise
    
    async def _setup_coordination(self):
        """Настройка координации между модулями"""
        try:
            # Подписываемся на события приложения
            await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.HIGH)
            await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.HIGH)
            await self.event_bus.subscribe("app.mode_changed", self._on_mode_changed, EventPriority.MEDIUM)
            
            # Подписываемся на события клавиатуры
            await self.event_bus.subscribe("keyboard.long_press", self._on_keyboard_event, EventPriority.HIGH)
            await self.event_bus.subscribe("keyboard.release", self._on_keyboard_event, EventPriority.HIGH)
            await self.event_bus.subscribe("keyboard.short_press", self._on_keyboard_event, EventPriority.HIGH)
            
            print("✅ Координация настроена")
            
        except Exception as e:
            print(f"❌ Ошибка настройки координации: {e}")
            raise
    
    async def start(self) -> bool:
        """Запуск всех интеграций"""
        try:
            if not self.is_initialized:
                print("❌ Компоненты не инициализированы")
                return False
            
            if self.is_running:
                print("⚠️ Компоненты уже запущены")
                return True
            
            print("🚀 Запуск всех интеграций...")
            
            # Запускаем все интеграции
            for name, integration in self.integrations.items():
                print(f"🚀 Запуск {name}...")
                success = await integration.start()
                if not success:
                    print(f"❌ Ошибка запуска {name}")
                    return False
                print(f"✅ {name} запущен")
            
            self.is_running = True
            
            # Публикуем событие запуска
            await self.event_bus.publish("app.startup", {
                "coordinator": "simple_module_coordinator",
                "integrations": list(self.integrations.keys())
            })
            
            print("✅ Все интеграции запущены")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка запуска интеграций: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка всех интеграций"""
        try:
            if not self.is_running:
                print("⚠️ Компоненты не запущены")
                return True
            
            print("⏹️ Остановка всех интеграций...")
            
            # Публикуем событие остановки
            await self.event_bus.publish("app.shutdown", {
                "coordinator": "simple_module_coordinator"
            })
            
            # Останавливаем все интеграции
            for name, integration in self.integrations.items():
                print(f"⏹️ Остановка {name}...")
                success = await integration.stop()
                if not success:
                    print(f"⚠️ Ошибка остановки {name}")
                else:
                    print(f"✅ {name} остановлен")
            
            self.is_running = False
            print("✅ Все интеграции остановлены")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка остановки интеграций: {e}")
            return False
    
    async def run(self):
        """Запуск приложения"""
        try:
            # Инициализируем
            success = await self.initialize()
            if not success:
                print("❌ Не удалось инициализировать компоненты")
                return
            
            # Запускаем
            success = await self.start()
            if not success:
                print("❌ Не удалось запустить компоненты")
                return
            
            # Получаем приложение rumps для отображения иконки
            tray_integration = self.integrations.get('tray')
            if not tray_integration:
                print("❌ TrayController интеграция не найдена")
                return
            
            app = tray_integration.get_app()
            if not app:
                print("❌ Не удалось получить приложение трея")
                return
            
            print("🎯 Запуск приложения с иконкой в меню-баре...")
            
            # Запускаем приложение rumps (блокирующий вызов)
            app.run()
            
        except KeyboardInterrupt:
            print("\n⏹️ Приложение прервано пользователем")
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.stop()
    
    # Обработчики событий (только координация, не дублирование логики)
    
    async def _on_app_startup(self, event):
        """Обработка запуска приложения"""
        try:
            print("🚀 Обработка запуска приложения в координаторе")
            # Делегируем обработку интеграциям через EventBus
            # Координатор не делает работу модулей!
            
        except Exception as e:
            print(f"❌ Ошибка обработки запуска приложения: {e}")
    
    async def _on_app_shutdown(self, event):
        """Обработка завершения приложения"""
        try:
            print("⏹️ Обработка завершения приложения в координаторе")
            # Делегируем обработку интеграциям через EventBus
            
        except Exception as e:
            print(f"❌ Ошибка обработки завершения приложения: {e}")
    
    async def _on_mode_changed(self, event):
        """Обработка смены режима приложения"""
        try:
            new_mode = event.data.get("mode")
            print(f"🔄 Координация смены режима: {new_mode.value if new_mode else 'unknown'}")
            
            # Делегируем обработку интеграциям
            # Координатор только координирует, не обрабатывает!
            
        except Exception as e:
            print(f"❌ Ошибка обработки смены режима: {e}")
    
    async def _on_keyboard_event(self, event):
        """Обработка событий клавиатуры"""
        try:
            event_type = event.event_type
            print(f"⌨️ Координация события клавиатуры: {event_type}")
            
            # Делегируем обработку интеграциям
            # Координатор только координирует, не обрабатывает!
            
        except Exception as e:
            print(f"❌ Ошибка обработки события клавиатуры: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус всех компонентов"""
        return {
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "core_components": {
                "event_bus": self.event_bus is not None,
                "state_manager": self.state_manager is not None,
                "error_handler": self.error_handler is not None
            },
            "integrations": {
                name: integration.get_status() 
                for name, integration in self.integrations.items()
            }
        }
