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
from integration.integrations.instance_manager_integration import InstanceManagerIntegration
from integration.integrations.autostart_manager_integration import AutostartManagerIntegration
from integration.integrations.tray_controller_integration import TrayControllerIntegration
from integration.integrations.mode_management_integration import ModeManagementIntegration
from integration.integrations.hardware_id_integration import HardwareIdIntegration, HardwareIdIntegrationConfig
from integration.integrations.grpc_client_integration import GrpcClientIntegration
from integration.integrations.speech_playback_integration import SpeechPlaybackIntegration
from modules.tray_controller.core.tray_types import TrayConfig
from integration.integrations.input_processing_integration import InputProcessingIntegration, InputProcessingConfig
from integration.integrations.voice_recognition_integration import VoiceRecognitionIntegration, VoiceRecognitionConfig
from integration.integrations.permissions_integration import PermissionsIntegration
from modules.permissions.core.types import PermissionConfig
from integration.integrations.updater_integration import UpdaterIntegration
from integration.integrations.network_manager_integration import NetworkManagerIntegration
from modules.network_manager.core.config import NetworkManagerConfig
from integration.integrations.audio_device_integration import AudioDeviceIntegration
from modules.audio_device_manager.core.types import AudioDeviceManagerConfig
from integration.integrations.interrupt_management_integration import InterruptManagementIntegration, InterruptManagementIntegrationConfig
from modules.input_processing.keyboard.types import KeyboardConfig
from integration.integrations.screenshot_capture_integration import ScreenshotCaptureIntegration
from integration.integrations.signal_integration import SignalIntegration
from modules.signals.config.types import PatternConfig
from integration.integrations.signal_integration import SignalsIntegrationConfig
from integration.integrations.welcome_message_integration import WelcomeMessageIntegration
from integration.integrations.voiceover_ducking_integration import VoiceOverDuckingIntegration

# Импорты core компонентов
from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory

# Импорт конфигурации
from config.unified_config_loader import UnifiedConfigLoader

# Импорт Workflows
from integration.workflows import ListeningWorkflow, ProcessingWorkflow

logger = logging.getLogger(__name__)

# Глобальная защита от множественного запуска
_app_running = False
_user_initiated_shutdown = False

class SimpleModuleCoordinator:
    """Центральный координатор модулей для Nexy AI Assistant"""
    
    def __init__(self):
        # Core компоненты (центральные)
        self.event_bus: Optional[EventBus] = None
        self.state_manager: Optional[ApplicationStateManager] = None
        self.error_handler: Optional[ErrorHandler] = None
        
        # Интеграции (обертки для модулей)
        self.integrations: Dict[str, Any] = {}
        
        # Workflows (координаторы режимов)
        self.workflows: Dict[str, Any] = {}
        
        # Конфигурация
        self.config = UnifiedConfigLoader()
        
        # Состояние
        self.is_initialized = False
        self.is_running = False
        # Фоновый asyncio loop и поток для асинхронных интеграций
        self._bg_loop = None
        self._bg_thread = None
        
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
            
            # 1.1 Запускаем фоновый asyncio loop (для EventBus/интеграций)
            self._start_background_loop()

            # 2. Создаем интеграции
            print("🔧 Создание интеграций...")
            # Прикрепляем EventBus к StateManager, чтобы централизованно публиковать смену режимов
            try:
                self.state_manager.attach_event_bus(self.event_bus)
                # Фиксируем основной loop в EventBus
                self.event_bus.attach_loop(self._bg_loop)
            except Exception:
                pass
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
            # КРИТИЧНО: InstanceManagerIntegration должен быть ПЕРВЫМ и БЛОКИРУЮЩИМ
            config_data = self.config._load_config()
            instance_config = config_data.get('instance_manager', {})
            
            self.integrations['instance_manager'] = InstanceManagerIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=instance_config
            )

            # Hardware ID Integration — должен стартовать рано, чтобы ID был доступен всем
            self.integrations['hardware_id'] = HardwareIdIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=None  # берёт значения из unified_config.yaml при наличии
            )

            # TrayController Integration - используем конфигурацию модуля
            # Конфигурация будет загружена внутри TrayControllerIntegration
            tray_config = None  # Будет создана автоматически из unified_config.yaml
            
            self.integrations['tray'] = TrayControllerIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=tray_config
            )
            
            # InputProcessing Integration - загружаем из конфигурации
            config_data = self.config._load_config()
            integrations_cfg = (config_data.get('integrations') or {})
            kbd_cfg = integrations_cfg.get('keyboard')
            input_cfg = integrations_cfg.get('input_processing') or {}

            if kbd_cfg:
                keyboard_config = KeyboardConfig(
                    key_to_monitor=kbd_cfg.get('key_to_monitor', 'space'),
                    short_press_threshold=kbd_cfg.get('short_press_threshold', 0.1),
                    long_press_threshold=kbd_cfg.get('long_press_threshold', 0.3),
                    event_cooldown=kbd_cfg.get('event_cooldown', 0.15),
                    hold_check_interval=kbd_cfg.get('hold_check_interval', 0.03),
                    debounce_time=kbd_cfg.get('debounce_time', 0.02)
                )
                input_config = InputProcessingConfig(
                    keyboard_config=keyboard_config,
                    enable_keyboard_monitoring=input_cfg.get('enable_keyboard_monitoring', True),
                    auto_start=input_cfg.get('auto_start', True),
                    keyboard_backend=kbd_cfg.get('backend', 'auto')
                )
                self.integrations['input'] = InputProcessingIntegration(
                    event_bus=self.event_bus,
                    state_manager=self.state_manager,
                    error_handler=self.error_handler,
                    config=input_config
                )
            else:
                logger.warning("Keyboard integration config not found; skipping input integration")
            
            # Permissions Integration - используем конфигурацию модуля
            # Конфигурация будет загружена внутри PermissionsIntegration
            permissions_config = None  # Будет создана автоматически из unified_config.yaml
            
            self.integrations['permissions'] = PermissionsIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=permissions_config
            )
            
            # Updater Integration - новая система обновлений
            updater_cfg = config_data.get('updater', {})
            
            self.integrations['updater'] = UpdaterIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                config=updater_cfg
            )
            
            # Network Manager Integration - используем конфигурацию модуля
            # Конфигурация будет загружена внутри NetworkManagerIntegration
            network_config = None  # Будет создана автоматически из unified_config.yaml
            
            self.integrations['network'] = NetworkManagerIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=network_config
            )
            
            # Audio Device Integration - используем конфигурацию модуля
            # Конфигурация будет загружена внутри AudioDeviceIntegration
            audio_config = None  # Будет создана автоматически из unified_config.yaml
            
            self.integrations['audio'] = AudioDeviceIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=audio_config
            )
            
            # Interrupt Management Integration - загружаем из конфигурации
            int_cfg_all = (config_data.get('integrations') or {})
            int_cfg = int_cfg_all.get('interrupt_management') or {}
            interrupt_config = InterruptManagementIntegrationConfig(
                max_concurrent_interrupts=int_cfg.get('max_concurrent_interrupts', 1),
                interrupt_timeout=int_cfg.get('interrupt_timeout', 5.0),
                retry_attempts=int_cfg.get('retry_attempts', 3),
                retry_delay=int_cfg.get('retry_delay', 1.0),
                enable_speech_interrupts=int_cfg.get('enable_speech_interrupts', True),
                enable_recording_interrupts=int_cfg.get('enable_recording_interrupts', True),
                enable_session_interrupts=int_cfg.get('enable_session_interrupts', True),
                enable_full_reset=int_cfg.get('enable_full_reset', False)
            )
            
            self.integrations['interrupt'] = InterruptManagementIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=interrupt_config
            )

            # Screenshot Capture Integration (PROCESSING)
            self.integrations['screenshot_capture'] = ScreenshotCaptureIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
            )
            
            # Voice Recognition Integration - конфигурация по умолчанию/из unified_config
            try:
                vrec_cfg_raw = config_data['integrations'].get('voice_recognition', {})
                # Централизованный язык: берем из STT
                language = self.config.get_stt_language("en-US")
                vrec_config = VoiceRecognitionConfig(
                    timeout_sec=vrec_cfg_raw.get('timeout_sec', 10.0),
                    simulate=vrec_cfg_raw.get('simulate', True),
                    simulate_success_rate=vrec_cfg_raw.get('simulate_success_rate', 0.7),
                    simulate_min_delay_sec=vrec_cfg_raw.get('simulate_min_delay_sec', 1.0),
                    simulate_max_delay_sec=vrec_cfg_raw.get('simulate_max_delay_sec', 3.0),
                    language=language,
                )
            except Exception:
                # Fallback с централизованным языком
                vrec_config = VoiceRecognitionConfig(language=self.config.get_stt_language("en-US"))

            self.integrations['voice_recognition'] = VoiceRecognitionIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=vrec_config,
            )

            # Mode Management Integration (централизация режимов)
            self.integrations['mode_management'] = ModeManagementIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
            )

            # Grpc Client Integration
            self.integrations['grpc'] = GrpcClientIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
            )

            # Speech Playback Integration
            self.integrations['speech_playback'] = SpeechPlaybackIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
            )

            # Signals Integration (audio cues via EventBus -> playback)
            try:
                sig_raw = config_data.get('integrations', {}).get('signals', {})
                patterns_cfg = {}
                for name, p in sig_raw.get('patterns', {}).items():
                    patterns_cfg[name] = PatternConfig(
                        audio=p.get('audio', True),
                        visual=p.get('visual', False),
                        volume=p.get('volume', 0.2),
                        tone_hz=p.get('tone_hz', 880),
                        duration_ms=p.get('duration_ms', 120),
                        cooldown_ms=p.get('cooldown_ms', 300),
                    )
                sig_cfg = SignalsIntegrationConfig(
                    enabled=sig_raw.get('enabled', True),
                    sample_rate=sig_raw.get('sample_rate', 48_000),
                    default_volume=sig_raw.get('default_volume', 0.2),
                    patterns=patterns_cfg or None,
                )
            except Exception:
                sig_cfg = SignalsIntegrationConfig()

            self.integrations['signals'] = SignalIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=sig_cfg,
            )

            # AutostartManagerIntegration - мониторинг LaunchAgent
            autostart_config = config_data.get('autostart', {})
            
            self.integrations['autostart_manager'] = AutostartManagerIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=autostart_config
            )

            # Welcome Message Integration - приветствие при запуске
            self.integrations['welcome_message'] = WelcomeMessageIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
            )

            # VoiceOver Ducking Integration - управление VoiceOver
            config_data = self.config._load_config()
            voiceover_config = config_data.get("accessibility", {}).get("voiceover_control", {})
            self.integrations['voiceover_ducking'] = VoiceOverDuckingIntegration(
                event_bus=self.event_bus,
                state_manager=self.state_manager,
                error_handler=self.error_handler,
                config=voiceover_config
            )

            print("✅ Интеграции созданы: instance_manager, hardware_id, tray, input, permissions, updater, network, audio, interrupt, voice_recognition, screenshot_capture, grpc, speech_playback, signals, autostart_manager, welcome_message, voiceover_ducking")
            
            # 3. Создаем Workflows (координаторы режимов)
            print("🔧 Создание Workflows...")
            
            self.workflows['listening'] = ListeningWorkflow(
                event_bus=self.event_bus
            )
            print("✅ ListeningWorkflow создан")
            
            self.workflows['processing'] = ProcessingWorkflow(
                event_bus=self.event_bus
            )
            print("✅ ProcessingWorkflow создан")
            
            print("✅ Все Workflows созданы успешно")
            
        except Exception as e:
            print(f"❌ Ошибка создания интеграций: {e}")
            raise
    
    async def _initialize_integrations(self):
        """Инициализация всех интеграций"""
        try:
            # КРИТИЧНО: Сначала инициализируем PermissionsIntegration
            # чтобы централизованно запросить все разрешения
            if 'permissions' in self.integrations:
                print(f"🔧 Инициализация permissions (ПРИОРИТЕТ)...")
                success = await self.integrations['permissions'].initialize()
                if not success:
                    print(f"❌ Ошибка инициализации permissions")
                    raise Exception(f"Failed to initialize permissions")
                print(f"✅ permissions инициализирован")
                
                # Ждем завершения запроса разрешений
                print("⏳ Ожидание завершения запроса разрешений...")
                await asyncio.sleep(3)  # Даем время на обработку TCC запросов
            
            # Затем инициализируем остальные интеграции
            for name, integration in self.integrations.items():
                if name == 'permissions':  # Уже инициализирован
                    continue
                    
                print(f"🔧 Инициализация {name}...")
                success = await integration.initialize()
                if not success:
                    print(f"❌ Ошибка инициализации {name}")
                    raise Exception(f"Failed to initialize {name}")
                print(f"✅ {name} инициализирован")
            
            # Инициализируем Workflows
            print("🔧 Инициализация Workflows...")
            for name, workflow in self.workflows.items():
                print(f"🔧 Инициализация workflow {name}...")
                await workflow.initialize()
                print(f"✅ Workflow {name} инициализирован")
                
        except Exception as e:
            print(f"❌ Ошибка инициализации интеграций/workflows: {e}")
            raise
    
    async def _setup_coordination(self):
        """Настройка координации между модулями"""
        try:
            # Подписываемся на события приложения
            await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.HIGH)
            await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.HIGH)
            await self.event_bus.subscribe("app.mode_changed", self._on_mode_changed, EventPriority.MEDIUM)
            
            # Подписываемся на события пользовательского завершения
            await self.event_bus.subscribe("tray.quit_clicked", self._on_user_quit, EventPriority.HIGH)

            # Подписываемся на события клавиатуры
            await self.event_bus.subscribe("keyboard.long_press", self._on_keyboard_event, EventPriority.HIGH)
            await self.event_bus.subscribe("keyboard.release", self._on_keyboard_event, EventPriority.HIGH)
            await self.event_bus.subscribe("keyboard.short_press", self._on_keyboard_event, EventPriority.HIGH)

            # Подписываемся на события скриншота для логирования
            try:
                await self.event_bus.subscribe("screenshot.captured", self._on_screenshot_captured, EventPriority.MEDIUM)
                await self.event_bus.subscribe("screenshot.error", self._on_screenshot_error, EventPriority.MEDIUM)
            except Exception:
                pass

            # Подписываемся на события аудио для явного логирования
            try:
                await self.event_bus.subscribe("audio.device_switched", self._on_audio_device_switched, EventPriority.MEDIUM)
                await self.event_bus.subscribe("audio.device_snapshot", self._on_audio_device_snapshot, EventPriority.MEDIUM)
            except Exception:
                pass
            
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
            
            # Запускаем интеграции в правильном порядке (с учетом зависимостей)
            startup_order = [
                'permissions',        # 1. Сначала разрешения - КРИТИЧНО!
                'hardware_id',        # 2. Получить уникальный ID
                'tray',               # 3. GUI и меню-бар
                'voiceover_ducking',  # 4. VoiceOver Ducking (зависит от permissions)
                'audio',              # 5. Аудио система (после разрешений)
                'voice_recognition',  # 6. Распознавание речи (зависит от audio)
                'screenshot_capture', # 7. Захват экрана (зависит от permissions)
                'network',            # 8. Сетевая система
                'updater',            # 9. Система обновлений
                'interrupt',          # 10. Управление прерываниями
                'grpc',               # 11. gRPC клиент (зависит от hardware_id)
                'speech_playback',    # 12. Воспроизведение речи (зависит от grpc)
                'signals',            # 13. Аудио сигналы
                'welcome_message',    # 14. Приветственное сообщение (зависит от speech_playback)
                'autostart_manager',  # 15. Автозапуск
                'instance_manager',   # 16. Управление экземплярами (последний)
            ]
            
            # Запускаем в правильном порядке
            for name in startup_order:
                if name in self.integrations:
                    print(f"🚀 Запуск {name}...")
                    success = await self.integrations[name].start()
                    
                    # КРИТИЧНО: InstanceManagerIntegration может завершить приложение
                    if name == "instance_manager" and not success:
                        print("❌ Дублирование обнаружено - приложение завершено")
                        return False
                    
                    if not success:
                        print(f"❌ Ошибка запуска {name}")
                        return False
                    print(f"✅ {name} запущен")
            
            # Запускаем оставшиеся интеграции (если есть)
            for name, integration in self.integrations.items():
                if name not in startup_order:
                    print(f"🚀 Запуск {name}...")
                    success = await integration.start()
                    
                    if not success:
                        print(f"❌ Ошибка запуска {name}")
                        return False
                    print(f"✅ {name} запущен")
            
            # Запускаем все Workflows
            print("🚀 Запуск Workflows...")
            for name, workflow in self.workflows.items():
                print(f"🚀 Запуск workflow {name}...")
                await workflow.start()
                print(f"✅ Workflow {name} запущен")
            
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
            
            # Останавливаем все Workflows
            print("⏹️ Остановка Workflows...")
            for name, workflow in self.workflows.items():
                print(f"⏹️ Остановка workflow {name}...")
                await workflow.stop()
                print(f"✅ Workflow {name} остановлен")
            
            self.is_running = False
            print("✅ Все интеграции и workflows остановлены")
            # Останавливаем фоновый loop
            try:
                if self._bg_loop and self._bg_loop.is_running():
                    self._bg_loop.call_soon_threadsafe(self._bg_loop.stop)
                if self._bg_thread:
                    self._bg_thread.join(timeout=1.0)
            except Exception:
                pass
            return True
            
        except Exception as e:
            print(f"❌ Ошибка остановки интеграций: {e}")
            return False
    
    async def run(self):
        """Запуск приложения"""
        global _app_running
        try:
            # Проверяем, не запущено ли уже приложение
            if _app_running or self.is_running:
                print("⚠️ Приложение уже запущено")
                return
            
            _app_running = True
                
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
            
            # Запускаем UI-таймер ПОСЛЕ того как rumps приложение готово
            # Используем rumps.Timer для запуска таймера в UI-потоке (однократно)
            import rumps
            def start_timer_callback(_):
                try:
                    tray_integration.start_ui_timer()
                    logger.info("✅ UI-таймер запущен через rumps callback")
                    # Останавливаем startup_timer после первого запуска
                    startup_timer.stop()
                except Exception as e:
                    logger.error(f"❌ Ошибка запуска UI-таймера через callback: {e}")
            
            # Запускаем таймер через 1 секунду после старта приложения (однократно)
            # В rumps.Timer нет параметра repeat; останавливаем таймер внутри колбэка
            startup_timer = rumps.Timer(start_timer_callback, 1.0)
            startup_timer.start()
            
            # Запускаем приложение rumps (блокирующий вызов)
            app.run()
            
        except KeyboardInterrupt:
            print("\n⏹️ Приложение прервано пользователем")
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
        finally:
            _app_running = False
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
    
    async def _on_user_quit(self, event):
        """Обработка пользовательского завершения через Quit в меню"""
        global _user_initiated_shutdown
        try:
            print("👤 Пользователь инициировал завершение приложения через Quit")
            _user_initiated_shutdown = True
            
            # Публикуем событие завершения
            await self.event_bus.publish("app.shutdown", {
                "source": "user.quit",
                "user_initiated": True
            })
            
            # Останавливаем приложение
            await self.stop()
            
        except Exception as e:
            print(f"❌ Ошибка обработки пользовательского завершения: {e}")
    
    async def _on_mode_changed(self, event):
        """Обработка смены режима приложения"""
        try:
            from integration.core.event_utils import event_data
            data = event_data(event)
            new_mode = data.get("mode", None)
            printable_mode = getattr(new_mode, "value", None) or str(new_mode) if new_mode is not None else "unknown"
            print(f"🔄 Координация смены режима: {printable_mode}")
            
            # Делегируем обработку интеграциям
            # Координатор только координирует, не обрабатывает!
            
        except Exception as e:
            print(f"❌ Ошибка обработки смены режима: {e}")
    
    async def _on_keyboard_event(self, event):
        """Обработка событий клавиатуры"""
        try:
            from integration.core.event_utils import event_type as _etype
            event_type = _etype(event, "unknown")
            print(f"⌨️ Координация события клавиатуры: {event_type}")
            
            # Делегируем обработку интеграциям
            # Координатор только координирует, не обрабатывает!
            
        except Exception as e:
            print(f"❌ Ошибка обработки события клавиатуры: {e}")
            
    async def _on_screenshot_captured(self, event):
        """Логирование результата захвата скриншота"""
        try:
            data = (event or {}).get("data", {})
            path = data.get("image_path")
            width = data.get("width")
            height = data.get("height")
            size_bytes = data.get("size_bytes")
            session_id = data.get("session_id")
            print(f"🖼️ Screenshot captured: {path} ({width}x{height}, {size_bytes} bytes), session={session_id}")
            logger.info(f"Screenshot captured: path={path}, size={size_bytes}, dims={width}x{height}, session={session_id}")
        except Exception as e:
            logger.debug(f"Failed to log screenshot.captured: {e}")

    async def _on_screenshot_error(self, event):
        """Логирование ошибок захвата скриншота"""
        try:
            data = (event or {}).get("data", {})
            err = data.get("error")
            session_id = data.get("session_id")
            print(f"🖼️ Screenshot error: {err}, session={session_id}")
            logger.warning(f"Screenshot error: {err}, session={session_id}")
        except Exception as e:
            logger.debug(f"Failed to log screenshot.error: {e}")

    async def _on_audio_device_switched(self, event):
        """Логирование переключений аудио устройства."""
        try:
            data = (event or {}).get("data", {})
            from_device = data.get("from_device")
            to_device = data.get("to_device")
            device_type = data.get("device_type")
            print(f"🔊 Audio switched: {from_device} → {to_device} [{device_type}]")
            logger.info(f"Audio switched: {from_device} -> {to_device} type={device_type}")
        except Exception as e:
            logger.debug(f"Failed to log audio.device_switched: {e}")

    async def _on_audio_device_snapshot(self, event):
        """Логирование текущего устройства при запуске."""
        try:
            data = (event or {}).get("data", {})
            current = data.get("current_device")
            device_type = data.get("device_type")
            print(f"🔊 Audio device: {current} [{device_type}] (snapshot)")
            logger.info(f"Audio device snapshot: {current} type={device_type}")
        except Exception as e:
            logger.debug(f"Failed to log audio.device_snapshot: {e}")

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

    def _start_background_loop(self):
        """Запускает отдельный поток с asyncio loop, чтобы не блокироваться на app.run()."""
        import asyncio, threading
        if self._bg_loop and self._bg_thread:
            return
        self._bg_loop = asyncio.new_event_loop()
        def _runner():
            asyncio.set_event_loop(self._bg_loop)
            try:
                self._bg_loop.run_forever()
            finally:
                self._bg_loop.close()
        self._bg_thread = threading.Thread(target=_runner, name="nexy-bg-loop", daemon=True)
        self._bg_thread.start()
        print("🧵 Фоновый asyncio loop запущен для EventBus/интеграций")
