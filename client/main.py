import asyncio
import logging
import time
from rich.console import Console
from enum import Enum
import sys
from pathlib import Path

import os
import yaml
import fcntl
import atexit
import subprocess
import json
import signal

# Добавляем корневую директорию в путь для импорта
sys.path.append(str(Path(__file__).parent.parent))

from audio_player import AudioPlayer
from unified_audio_system import get_global_unified_audio_system
from audio_device_manager import initialize_global_audio_device_manager
from stt_recognizer import StreamRecognizer
from input_handler import InputHandler


 
from grpc_client import GrpcClient
from screen_capture import ScreenCapture                                                                              
from permissions import ensure_permissions
from utils.hardware_id import get_hardware_id, get_hardware_info
TrayController = None  # Используем helper-процесс вместо прямого UI в этом процессе

def _get_support_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "Nexy"

def _get_status_file_path() -> Path:
    support_dir = _get_support_dir()
    support_dir.mkdir(parents=True, exist_ok=True)
    return support_dir / "tray_status.json"

def _run_tray_helper_if_requested():
    """Если процесс запущен в режиме helper (`--tray-helper`), поднимаем rumps UI и выходим."""
    if "--tray-helper" not in sys.argv:
        return
    try:
        import rumps
    except Exception as e:
        print(f"Tray helper failed to import rumps: {e}")
        sys.exit(1)

    # Параметры
    status_file = None
    main_pid = None
    for i, arg in enumerate(sys.argv):
        if arg == "--status-file" and i + 1 < len(sys.argv):
            status_file = sys.argv[i + 1]
        if arg == "--pid" and i + 1 < len(sys.argv):
            try:
                main_pid = int(sys.argv[i + 1])
            except Exception:
                main_pid = None
    if not status_file:
        status_file = str(_get_status_file_path())

    STATUS_EMOJI = {"SLEEPING": "⚪️", "LISTENING": "🟢", "IN_PROCESS": "🔵"}

    class _TrayApp(rumps.App):
        def __init__(self):
            super().__init__("Nexy")
            self._current = "SLEEPING"
            self.title = f"{STATUS_EMOJI.get(self._current, '⚪️')} Nexy"
            self.quit_button = None
            self.menu = [rumps.MenuItem("Quit Nexy", callback=self._on_quit)]
            self._timer = rumps.Timer(self._tick, 0.5)
            self._timer.start()

        def _tick(self, _):
            # 1) если основной процесс завершился — закрываемся
            if main_pid:
                try:
                    os.kill(main_pid, 0)
                except Exception:
                    rumps.quit_application()
                    return
            # 2) читаем статус из файла
            try:
                with open(status_file, "r") as f:
                    data = json.load(f)
                st = data.get("state")
                if st and st != self._current:
                    self._current = st
                    self.title = f"{STATUS_EMOJI.get(self._current, '⚪️')} Nexy"
            except Exception:
                pass

        def _on_quit(self, _):
            # Пытаемся корректно завершить основной процесс
            if main_pid:
                try:
                    os.kill(main_pid, signal.SIGTERM)
                except Exception:
                    pass
            rumps.quit_application()

    _TrayApp().run()
    sys.exit(0)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()

SINGLE_INSTANCE_LOCK_FD = None
LOCK_FILE_PATH = None

def acquire_single_instance_lock():
    """
    Гарантирует единственный экземпляр приложения с помощью эксклюзивной блокировки файла.
    Возвращает True, если блокировка получена, иначе False.
    """
    global SINGLE_INSTANCE_LOCK_FD, LOCK_FILE_PATH
    try:
        support_dir = Path.home() / "Library" / "Application Support" / "Nexy"
        support_dir.mkdir(parents=True, exist_ok=True)
        LOCK_FILE_PATH = support_dir / "instance.lock"
        lock_file = open(LOCK_FILE_PATH, "w")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            try:
                lock_file.close()
            except Exception:
                pass
            return False
        # Сохраняем дескриптор, чтобы блокировка жила до завершения процесса
        SINGLE_INSTANCE_LOCK_FD = lock_file
        try:
            SINGLE_INSTANCE_LOCK_FD.truncate(0)
            SINGLE_INSTANCE_LOCK_FD.write(str(os.getpid()))
            SINGLE_INSTANCE_LOCK_FD.flush()
            os.fsync(SINGLE_INSTANCE_LOCK_FD.fileno())
        except Exception:
            pass
        return True
    except Exception:
        # При любой ошибке не мешаем запуску, но блокировка может не сработать
        return True

@atexit.register
def _release_single_instance_lock():
    global SINGLE_INSTANCE_LOCK_FD
    try:
        if SINGLE_INSTANCE_LOCK_FD:
            try:
                fcntl.flock(SINGLE_INSTANCE_LOCK_FD.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                SINGLE_INSTANCE_LOCK_FD.close()
            except Exception:
                pass
    except Exception:
        pass
    
    # ДОБАВЛЕНО: Очистка глобальных ресурсов при завершении приложения
    try:
        from unified_audio_system import stop_global_unified_audio_system
        from realtime_device_monitor import stop_global_realtime_monitor
        stop_global_unified_audio_system()
        stop_global_realtime_monitor()
        logger.info("🧹 Глобальные ресурсы очищены при завершении")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка очистки глобальных ресурсов: {e}")

class AppState(Enum):
    LISTENING = 1     # Ассистент слушает команды (микрофон активен)
    IN_PROCESS = 2    # Ассистент работает (обрабатывает команду или говорит)
    SLEEPING = 3      # Ассистент спит, ждет команды (микрофон неактивен)

class StateManager:
    """
    Управляет переходами между состояниями приложения.
    Каждое состояние знает, как реагировать на каждое событие.
    """
    
    def __init__(self, console, audio_player, stt_recognizer, screen_capture, grpc_client, hardware_id, input_handler=None, tray_controller=None):
        self.console = console
        self.audio_player = audio_player
        self.stt_recognizer = stt_recognizer
        self.screen_capture = screen_capture
        self.grpc_client = grpc_client
        self.hardware_id = hardware_id
        self.input_handler = input_handler  # Ссылка на InputHandler для синхронизации
        self.tray_controller = tray_controller
        
        # Состояние приложения
        self.state = AppState.SLEEPING
        self.active_call = None
        self.streaming_task = None
        self.current_screenshot = None
        self.current_screen_info = None
        
        # Флаг для fade-in первого аудио чанка
        self._first_tts_chunk = True
        
        # Время начала прерывания для логирования
        self.interrupt_start_time = time.time()
        
        # Защита от дублирования команд
        self._last_command_time = 0
        self._command_debounce = 0.5  # 500ms защита от дублирования команд
        
        # Централизованное управление состоянием микрофона
        import threading
        self._microphone_state = {
            'is_recording': False,
            'last_start_time': 0,
            'last_stop_time': 0,
            'state_lock': threading.Lock()
        }
    
    def _write_tray_status_file(self, state_name: str):
        try:
            path = _get_status_file_path()
            with open(path, "w") as f:
                json.dump({"state": state_name, "ts": time.time()}, f)
        except Exception:
            pass
        
    def get_state(self):
        """Возвращает текущее состояние"""
        return self.state
    
    def get_microphone_state(self) -> dict:
        """Централизованное получение состояния микрофона"""
        with self._microphone_state['state_lock']:
            return {
                'is_recording': self._microphone_state['is_recording'],
                'last_start_time': self._microphone_state['last_start_time'],
                'last_stop_time': self._microphone_state['last_stop_time']
            }
    
    def set_microphone_recording(self, is_recording: bool):
        """Централизованное управление состоянием записи"""
        with self._microphone_state['state_lock']:
            current_time = time.time()
            self._microphone_state['is_recording'] = is_recording
            if is_recording:
                self._microphone_state['last_start_time'] = current_time
            else:
                self._microphone_state['last_stop_time'] = current_time
            
            # Обратная синхронизация убрана - STT recognizer управляется через activate_microphone/deactivate_microphone
    
    def activate_microphone(self) -> bool:
        """ПРОСТОЙ метод: активация микрофона с проверками"""
        if not self.can_start_recording():
            current_state = self.get_microphone_state()
            logger.warning(f"   ⚠️ Невозможно активировать микрофон: состояние={self.state.name}, микрофон={current_state['is_recording']}")
            return False
        
        self.set_microphone_recording(True)
        logger.info(f"   🎤 Микрофон активирован в состоянии {self.state.name}")
        return True
    
    def deactivate_microphone(self) -> bool:
        """ПРОСТОЙ метод: деактивация микрофона"""
        self.set_microphone_recording(False)
        logger.info(f"   🔇 Микрофон деактивирован в состоянии {self.state.name}")
        return True
    
    def _sync_microphone_with_state(self, old_state: AppState, new_state: AppState):
        """ИДЕАЛЬНАЯ СИНХРОНИЗАЦИЯ: автоматически синхронизирует состояние микрофона с состоянием приложения"""
        
        # Правила синхронизации микрофона с состоянием приложения
        if new_state == AppState.SLEEPING:
            # SLEEPING = микрофон всегда выключен
            self.set_microphone_recording(False)
            logger.info(f"   🔇 Микрофон выключен при переходе в SLEEPING")
            
        elif new_state == AppState.IN_PROCESS:
            # IN_PROCESS = микрофон всегда выключен
            self.set_microphone_recording(False)
            logger.info(f"   🔇 Микрофон выключен при переходе в IN_PROCESS")
            
        elif new_state == AppState.LISTENING:
            # LISTENING = микрофон включается только при явной активации
            # НЕ включаем автоматически - только при вызове start_recording
            logger.info(f"   🎤 LISTENING: микрофон будет включен при активации")
    
    def can_start_recording(self) -> bool:
        """Проверка возможности активации микрофона"""
        # Микрофон можно активировать в SLEEPING (новая запись) или LISTENING (перезапуск)
        if self.state not in [AppState.SLEEPING, AppState.LISTENING]:
            return False
        
        # Нельзя активировать уже активный микрофон
        if self.is_microphone_recording():
            return False
            
        return True
    
    def is_microphone_recording(self) -> bool:
        """Проверяет, активна ли запись микрофона"""
        with self._microphone_state['state_lock']:
            return self._microphone_state['is_recording']
    
    def _check_interrupt_status(self) -> bool:
        """
        Централизованная проверка статуса прерывания.
        Возвращает True если обнаружено прерывание.
        """
        try:
            if hasattr(self, 'input_handler') and self.input_handler:
                return self.input_handler.get_interrupt_status()
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке статуса прерывания: {e}")
            return False
    
    def set_state(self, new_state: AppState):
        """ИДЕАЛЬНЫЙ метод: установка состояния с автоматической синхронизацией микрофона"""
        old_state = self.state
        self.state = new_state
        
        # 🔥 АВТОМАТИЧЕСКАЯ СИНХРОНИЗАЦИЯ МИКРОФОНА
        self._sync_microphone_with_state(old_state, new_state)
        
        # Синхронизируем с треем
        try:
            self._write_tray_status_file(new_state.name)
        except Exception:
            pass
        try:
            if self.tray_controller:
                self.tray_controller.update_status(new_state.name)
                # Синхронизируем _current в трее
                if hasattr(self.tray_controller, '_current'):
                    self.tray_controller._current = new_state.name
        except Exception:
            pass
        return old_state, new_state
    
    def handle_start_recording(self):
        """ПРОБЕЛ ЗАЖАТ - включаем микрофон (БЕЗ прерывания)"""
        
        # 🛡️ ЗАЩИТА: проверяем возможность начала записи
        if not self.can_start_recording():
            current_state = self.get_microphone_state()
            logger.warning(f"   ⚠️ Невозможно начать запись: микрофон={current_state['is_recording']}, состояние={self.state.name}")
            self.console.print(f"[yellow]⚠️ Невозможно начать запись: микрофон={current_state['is_recording']}, состояние={self.state.name}[/yellow]")
            return
        
        if self.state == AppState.SLEEPING:
            # Начинаем запись через централизованную систему
            logger.info("   🎤 Активация микрофона из состояния SLEEPING")
            self.set_state(AppState.LISTENING)
            # Используем централизованную активацию микрофона
            if not self.activate_microphone():
                logger.error("   ❌ Не удалось активировать микрофон")
                self.set_state(AppState.SLEEPING)
                return
            
            # Подготовка устройств: выставляем системные дефолты и переключаем вывод ДО бипа
            try:
                if hasattr(self.stt_recognizer, 'prepare_for_recording'):
                    self.stt_recognizer.prepare_for_recording()
                    logger.info("   🎤 STT подготовлен для записи")
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка подготовки STT: {e}")
            
            # Сигнал включения микрофона (короткий beep)
            try:
                if self.audio_player and hasattr(self.audio_player, 'play_beep'):
                    self.audio_player.play_beep()
                    logger.info("   🔊 Beep воспроизведен")
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка воспроизведения beep: {e}")
            
            # Запускаем запись сразу - beep воспроизводится в отдельном потоке
            try:
                # Микрофон уже активирован, запускаем STT без повторной активации
                self.stt_recognizer.start_recording_without_activation()
                logger.info("   ⚡ Запись запущена мгновенно")
            except Exception as e:
                logger.error(f"   ❌ Ошибка запуска записи: {e}")
                # При ошибке переходим в SLEEPING (микрофон автоматически выключится)
                self.set_state(AppState.SLEEPING)
            
            self.console.print("[green]🎤 Микрофон включен - говорите команду[/green]")
            logger.info("   🎤 Микрофон активирован из состояния SLEEPING")
            
        elif self.state == AppState.IN_PROCESS:
            # 🚨 КРИТИЧНО: НЕ прерываем здесь! Только переходим в LISTENING
            logger.info("   🎤 Переход в LISTENING из IN_PROCESS (БЕЗ прерывания)")
            self.console.print("[blue]🎤 Переход в LISTENING - микрофон будет включен[/blue]")
            
            # Переходим в LISTENING
            self.set_state(AppState.LISTENING)
            
            # Активируем микрофон для LISTENING
            if not self.activate_microphone():
                logger.error("   ❌ Не удалось активировать микрофон")
                self.set_state(AppState.SLEEPING)
                return
            
            # Подготовка устройств
            try:
                if hasattr(self.stt_recognizer, 'prepare_for_recording'):
                    self.stt_recognizer.prepare_for_recording()
                    logger.info("   🎤 STT подготовлен для записи")
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка подготовки STT: {e}")
            
            # Сигнал включения микрофона
            try:
                if hasattr(self.audio_player, 'play_beep'):
                    self.audio_player.play_beep()
            except Exception:
                pass
            
            # Запускаем запись
            try:
                # Микрофон уже активирован, запускаем STT без повторной активации
                self.stt_recognizer.start_recording_without_activation()
                logger.info("   ⚡ Запись запущена мгновенно")
            except Exception as e:
                logger.error(f"   ❌ Ошибка запуска записи: {e}")
                self.set_state(AppState.SLEEPING)
            
            self.console.print("[green]🎤 Микрофон включен - говорите команду[/green]")
            logger.info("   🎤 Микрофон активирован из IN_PROCESS")
            
        elif self.state == AppState.LISTENING:
            # Уже слушаем → перезапускаем запись для надежности
            self.console.print("[blue]🔄 Уже слушаю - перезапускаю запись для надежности[/blue]")
            logger.info("   🔄 Перезапуск записи в состоянии LISTENING")
            
            # 🚨 ЗАЩИТА: проверяем, не активен ли уже микрофон
            if self.is_microphone_recording():
                logger.info("   ℹ️ Микрофон уже активен - дублирование активации предотвращено")
                self.console.print("[blue]ℹ️ Микрофон уже активен - дублирование предотвращено[/blue]")
                return  # Выходим без повторной активации
            
            # Активируем микрофон для LISTENING
            if not self.activate_microphone():
                logger.warning("   ⚠️ Микрофон уже активен или недоступен")
                return
            
            # Останавливаем текущую запись и начинаем новую
            try:
                self.stt_recognizer.stop_recording_and_recognize()
                logger.info("   ✅ Текущая запись остановлена")
            except:
                pass
            
            # Начинаем новую запись (с сигналом о готовности)
            try:
                if hasattr(self.audio_player, 'play_beep'):
                    self.audio_player.play_beep()
            except Exception:
                pass
            
            try:
                import threading
                threading.Timer(0.12, self.stt_recognizer.start_recording).start()
            except Exception:
                self.stt_recognizer.start_recording()
            logger.info("   ✅ Новая запись запущена")
            self.console.print("[green]🎤 Запись перезапущена - говорите команду[/green]")
            
        else:
            # Неизвестное состояние → переходим в LISTENING
            self.console.print(f"[yellow]⚠️ Неизвестное состояние {self.state.name}, перехожу в LISTENING[/yellow]")
            self.set_state(AppState.LISTENING)
            
            # Активируем микрофон
            if not self.activate_microphone():
                logger.error("   ❌ Не удалось активировать микрофон")
                self.set_state(AppState.SLEEPING)
                return
            
            try:
                if hasattr(self.audio_player, 'play_beep'):
                    self.audio_player.play_beep()
            except Exception:
                pass
            
            try:
                # Микрофон уже активирован, запускаем STT без повторной активации
                self.stt_recognizer.start_recording_without_activation()
                logger.info("   ⚡ Запись запущена мгновенно")
            except Exception as e:
                logger.error(f"   ❌ Ошибка запуска записи: {e}")
                self.set_state(AppState.SLEEPING)
            
            self.console.print("[green]🎤 Микрофон включен - говорите команду[/green]")
            logger.info("   🎤 Микрофон активирован из неизвестного состояния")
    
    
    def handle_stop_recording(self):
        """ПРОБЕЛ ОТПУЩЕН - выключаем микрофон и обрабатываем команду"""
        
        # 🚨 ИСПРАВЛЕНИЕ: Обрабатываем stop_recording из любого состояния
        
        if self.state == AppState.LISTENING:
            # Нормальная остановка записи
            command = self.stt_recognizer.stop_recording_and_recognize()
            logger.info("   ✅ Запись остановлена, микрофон выключен")
            
            if command and command.strip():
                # КОМАНДА ПРИНЯТА → переходим в IN_PROCESS
                self.console.print(f"[bold green]📝 Команда принята: {command}[/bold green]")
                self.set_state(AppState.IN_PROCESS)
                self.console.print("[blue]🔄 Переход в IN_PROCESS - обрабатываю команду...[/blue]")
                
                # Захватываем актуальный скриншот ПЕРЕД отправкой на сервер
                try:
                    self._capture_screen()
                    logger.info("   ✅ Актуальный скриншот захвачен перед отправкой")
                except Exception as e:
                    logger.warning(f"   ⚠️ Не удалось захватить скриншот: {e}")
                self._process_command(command)
            else:
                # КОМАНДА НЕ ПРИНЯТА → возвращаемся в SLEEPING
                self.console.print("[yellow]⚠️ Команда не распознана[/yellow]")
                self.set_state(AppState.SLEEPING)
                self.console.print("[blue]✅ Возврат в SLEEPING - готов к новым командам[/blue]")
                
        elif self.state == AppState.IN_PROCESS:
            # Ассистент работает → прерываем и переходим в LISTENING
            self.console.print("[bold yellow]🔇 Ассистент работает - ПРЕРЫВАЮ и перехожу в LISTENING![/bold yellow]")
            
            # Прерываем работу
            success = self.force_stop_everything()
            if success:
                logger.info("   ✅ Универсальная остановка успешна")
                self.console.print("[bold green]✅ ВСЕ ПРИНУДИТЕЛЬНО ОСТАНОВЛЕНО![/bold green]")
            
            # Переходим в LISTENING и включаем микрофон
            self.set_state(AppState.LISTENING)
            self.stt_recognizer.start_recording()
            self.console.print("[bold green]✅ Переход в LISTENING - микрофон включен![/bold green]")
            
        elif self.state == AppState.SLEEPING:
            # Ассистент спит → активируем микрофон
            self.console.print("[blue]🎤 Активирую микрофон из состояния SLEEPING[/blue]")
            self.set_state(AppState.LISTENING)
            self.stt_recognizer.start_recording()
            self.console.print("[green]🎤 Микрофон включен - говорите команду[/green]")
            
        else:
            # Неизвестное состояние → возвращаемся в SLEEPING
            self.console.print(f"[yellow]⚠️ Неизвестное состояние {self.state.name}, возвращаюсь в SLEEPING[/yellow]")
            self.set_state(AppState.SLEEPING)
    
    def handle_deactivate_microphone(self):
        """ПРОБЕЛ ОТПУЩЕН - деактивируем микрофон и возвращаемся в SLEEPING"""
        logger.info("   🔇 handle_deactivate_microphone() вызван")
        
        # 🛡️ ЗАЩИТА: проверяем состояние приложения
        if self.state != AppState.LISTENING:
            logger.info(f"   ℹ️ Неправильное состояние для deactivate_microphone: {self.state.name}")
            self.console.print(f"[blue]ℹ️ Неправильное состояние: {self.state.name}[/blue]")
            return
        
        if self.state == AppState.LISTENING:
            # Останавливаем запись и РАСПОЗНАЕМ КОМАНДУ
            command = None
            try:
                if hasattr(self, 'stt_recognizer') and self.stt_recognizer:
                    command = self.stt_recognizer.stop_recording_and_recognize()
                    logger.info("   ✅ Запись остановлена")
                    # Состояние микрофона будет сброшено автоматически при переходе в SLEEPING
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка остановки записи: {e}")
                # Состояние микрофона будет сброшено автоматически при переходе в SLEEPING
            
            # Если команда распознана - ОБРАБАТЫВАЕМ ЕЕ
            if command and command.strip():
                self.console.print(f"[bold green]📝 Команда распознана: {command}[/bold green]")
                logger.info(f"   📝 Команда распознана: {command}")
                
                # Переходим в IN_PROCESS для обработки команды
                self.set_state(AppState.IN_PROCESS)
                logger.info("   🔄 Переход в IN_PROCESS для обработки команды")
                
                # Захватываем актуальный скриншот ПЕРЕД отправкой на сервер
                try:
                    self._capture_screen()
                    logger.info("   ✅ Актуальный скриншот захвачен перед отправкой")
                except Exception as e:
                    logger.warning(f"   ⚠️ Не удалось захватить скриншот: {e}")
                
                # Обрабатываем команду
                self._process_command(command)
            else:
                # Команда не распознана - переходим в SLEEPING
                self.console.print("[yellow]⚠️ Команда не распознана[/yellow]")
                logger.info("   ⚠️ Команда не распознана")
                
                # Переходим в SLEEPING
                self.set_state(AppState.SLEEPING)
                self.console.print("[blue]🔇 Микрофон деактивирован - возврат в SLEEPING[/blue]")
                logger.info("   🔄 Переход в SLEEPING после деактивации микрофона")
            
        elif self.state == AppState.IN_PROCESS:
            # Ассистент работает → ничего не делаем
            self.console.print("[blue]ℹ️ Ассистент работает - микрофон неактивен[/blue]")
            logger.info("   ℹ️ Ассистент работает - микрофон неактивен")
            
        elif self.state == AppState.SLEEPING:
            # Уже спим → ничего не делаем
            self.console.print("[blue]ℹ️ Уже в состоянии SLEEPING[/blue]")
            logger.info("   ℹ️ Уже в состоянии SLEEPING")
    
    async def handle_interrupt_or_cancel(self):
        """ПРОБЕЛ НАЖАТ - прерываем работу (ЕДИНСТВЕННОЕ место прерывания)"""
        # Обновляем время начала прерывания
        self.interrupt_start_time = time.time()
        
        logger.info(f"🚨 handle_interrupt_or_cancel() начат в {self.interrupt_start_time:.3f}")
        
        current_state = self.state
        logger.info(f"   📊 Текущее состояние: {current_state.name}")
        
        # 🛡️ ЗАЩИТА: проверяем, не обрабатывается ли уже прерывание
        if hasattr(self, '_processing_interrupt') and self._processing_interrupt:
            logger.info("   ℹ️ Прерывание уже обрабатывается - дублирование предотвращено")
            return
        
        # 🛡️ ЗАЩИТА: проверяем, есть ли что прерывать
        if current_state == AppState.SLEEPING:
            logger.info("   ℹ️ Ассистент спит - проверяю аудио")
            self.console.print("[blue]ℹ️ Ассистент спит - проверяю аудио[/blue]")
            
            # ОСТАВЛЯЕМ: останавливаем аудио если оно воспроизводится
            if (self.audio_player and 
                hasattr(self.audio_player, 'is_playing') and 
                self.audio_player.is_playing):
                
                logger.info("   🎵 Аудио воспроизводится в фоне - останавливаю")
                self.console.print("[bold red]🎵 Останавливаю фоновое аудио![/bold red]")
                self.force_stop_everything()
                return
            else:
                logger.info("   ℹ️ Аудио не воспроизводится - нечего останавливать")
                self.console.print("[blue]ℹ️ Аудио не воспроизводится[/blue]")
                return
        
        # Устанавливаем флаг обработки прерывания
        self._processing_interrupt = True
        
        try:
            if current_state == AppState.IN_PROCESS:
                # Ассистент работает → ПРИНУДИТЕЛЬНО прерываем работу!
                logger.info(f"   🚨 Прерывание работы (состояние: {current_state.name})")
                self.console.print("[bold red]🚨 ПРИНУДИТЕЛЬНО прерывание работы![/bold red]")
                
                # 🚨 ИСПОЛЬЗУЕМ УНИВЕРСАЛЬНЫЙ МЕТОД!
                success = self.force_stop_everything()
                
                if success:
                    logger.info("   ✅ Универсальная остановка успешна")
                    self.console.print("[bold green]✅ ВСЕ ПРИНУДИТЕЛЬНО ОСТАНОВЛЕНО![/bold green]")
                else:
                    logger.warning("   ⚠️ Универсальная остановка неполная")
                    self.console.print("[yellow]⚠️ Остановка неполная[/yellow]")
                
                # 🚨 КРИТИЧНО: После прерывания ВСЕГДА переходим в SLEEPING!
                self.set_state(AppState.SLEEPING)
                logger.info("   🔄 Переход в SLEEPING после прерывания IN_PROCESS")
                
                try:
                    # Чистим экран/ресурсы при необходимости
                    pass
                except Exception as e:
                    logger.error(f"   ❌ Ошибка обработки прерывания: {e}")
                
                # СБРАСЫВАЕМ ФЛАГ ПРЕРЫВАНИЯ В INPUT_HANDLER
                if self.input_handler and hasattr(self.input_handler, 'reset_interrupt_flag'):
                    self.input_handler.reset_interrupt_flag()
                    logger.info(f"   🔄 Флаг прерывания сброшен в InputHandler")
                
            elif current_state == AppState.LISTENING:
                # Ассистент слушает → прерываем запись и возвращаемся в SLEEPING
                logger.info(f"   🎤 Прерывание записи (состояние: {current_state.name})")
                self.console.print("[bold red]🔇 Прерывание записи команды[/bold red]")
            
                # Останавливаем запись и распознаем речь
                if hasattr(self, 'stt_recognizer') and self.stt_recognizer:
                    command = self.stt_recognizer.stop_recording_and_recognize()
                    if command and command.strip():
                        self.console.print(f"[bold green]📝 Команда распознана: {command}[/bold green]")
                        logger.info(f"   📝 Команда распознана: {command}")
                    else:
                        self.console.print("[yellow]⚠️ Команда не распознана[/yellow]")
                        logger.info("   ⚠️ Команда не распознана")
                else:
                    logger.warning("   ⚠️ STT recognizer недоступен")
                    self.console.print("[yellow]⚠️ STT recognizer недоступен[/yellow]")
                
                # Переходим в SLEEPING
                self.set_state(AppState.SLEEPING)
                logger.info("   🔄 Переход в SLEEPING - STT недоступен")
                
                # СБРАСЫВАЕМ ФЛАГ ПРЕРЫВАНИЯ В INPUT_HANDLER
                if self.input_handler and hasattr(self.input_handler, 'reset_interrupt_flag'):
                    self.input_handler.reset_interrupt_flag()
                    logger.info(f"   🔄 Флаг прерывания сброшен в InputHandler после прерывания записи")
                    
            elif current_state == AppState.SLEEPING:
                # Ассистент спит → при прерывании ничего не активируем автоматически
                logger.info(f"   🌙 Ассистент спит - обрабатываю прерывание без автоактивации (состояние: {current_state.name})")
                self.console.print("[blue]🌙 Ассистент спит - никаких действий, ждём нажатия для записи[/blue]")
                
                # Чистим ресурсы, но микрофон не включаем
                try:
                    success = self.force_stop_everything()
                    if success:
                        self.console.print("[green]✅ Очистка завершена[/green]")
                    else:
                        self.console.print("[yellow]⚠️ Очистка неполная[/yellow]")
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка очистки при SLEEPING: {e}")
                
                # Остаёмся в SLEEPING
                self.set_state(AppState.SLEEPING)
                
                # Сбрасываем флаг прерывания
                if self.input_handler and hasattr(self.input_handler, 'reset_interrupt_flag'):
                    self.input_handler.reset_interrupt_flag()
                    logger.info(f"   🔄 Флаг прерывания сброшен в InputHandler (SLEEPING)")
        
        except Exception as e:
            logger.error(f"   ❌ Ошибка в handle_interrupt_or_cancel: {e}")
            self.console.print(f"[red]❌ Ошибка обработки прерывания: {e}[/red]")
        
        finally:
            # ИСПРАВЛЕНИЕ: ВСЕГДА сбрасываем флаг обработки прерывания
            self._processing_interrupt = False
            logger.info("   🔄 Флаг _processing_interrupt сброшен в finally")
            
            # Логируем время выполнения
            end_time = time.time()
            execution_time = (end_time - self.interrupt_start_time) * 1000
            logger.info(f"   ⏱️ handle_interrupt_or_cancel завершен за {execution_time:.1f}ms")
            
            # Логируем финальное состояние
            logger.info(f"   📊 Финальное состояние: {self.state.name}")
    
    async def handle_event(self, event):
        """Маршрутизирует события к соответствующим обработчикам"""
        start_time = time.time()
        logger.info(f"   🎯 handle_event() начат для события: {event} в {start_time:.3f}")
        
        try:
            if event == "start_recording":
                logger.info(f"   🎤 Маршрутизация события start_recording")
                
                # Проверяем флаг прерывания - если есть, игнорируем start_recording
                if hasattr(self.input_handler, 'interrupting') and self.input_handler.interrupting:
                    logger.info(f"   ⚠️ Игнорирую start_recording - активен флаг прерывания")
                    return
                self.handle_start_recording()
            elif event == "interrupt_or_cancel":
                logger.info(f"   🔇 Маршрутизация события interrupt_or_cancel")
                await self.handle_interrupt_or_cancel()  # 🚨 ДОБАВЛЯЕМ await!
            elif event == "stop_recording":
                logger.info(f"   ⏹️ Маршрутизация события stop_recording")
                self.handle_stop_recording()
            elif event == "deactivate_microphone":
                logger.info(f"   🔇 Маршрутизация события deactivate_microphone")
                self.handle_deactivate_microphone()
            elif event == "process_command":
                logger.info(f"   ⚙️ Маршрутизация события process_command")
                self.handle_process_command()
            else:
                logger.warning(f"   ⚠️ Неизвестное событие: {event}")
                self.console.print(f"[yellow]⚠️ Неизвестное событие: {event}[/yellow]")
                
        except Exception as e:
            logger.error(f"   ❌ Ошибка в handle_event для {event}: {e}")
            self.console.print(f"[bold red]❌ Ошибка обработки события {event}: {e}[/bold red]")
            # Восстанавливаемся в SLEEPING при ошибке
            self.set_state(AppState.SLEEPING)
            self.console.print("[blue]🔄 Восстановление в SLEEPING при ошибке[/blue]")
        
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000
        logger.info(f"   ⏱️ handle_event завершен за {processing_time:.1f}ms")
        logger.info(f"   📊 Финальное состояние: {self.state.name}")
    
    def _process_command(self, command):
        """Обрабатывает команду через gRPC"""
        try:
            # Защита от дублирования команд
            current_time = time.time()
            if current_time - self._last_command_time < self._command_debounce:
                logger.info("   ⚠️ Игнорирую дублированную команду")
                self.console.print("[yellow]⚠️ Дублированная команда проигнорирована[/yellow]")
                return
            self._last_command_time = current_time
            
            # Сбрасываем флаг отмены для новой команды
            self._cancelled = False
            self.console.print("[blue]🔄 Сброшен флаг отмены для новой команды[/blue]")
            
            # 🚨 КРИТИЧНО: Проверяем и восстанавливаем gRPC соединение!
            if not self.grpc_client.stub or not self.grpc_client.channel:
                self.console.print("[yellow]⚠️ gRPC соединение разорвано, восстанавливаю...[/yellow]")
                logger.info("   🔌 Восстанавливаю gRPC соединение...")
                
                try:
                    # ИСПРАВЛЕНИЕ: используем синхронное восстановление для надежности
                    if self.grpc_client.connect_sync():
                        self.console.print("[green]✅ gRPC соединение восстановлено синхронно![/green]")
                        logger.info("   ✅ gRPC соединение восстановлено синхронно")
                    else:
                        self.console.print("[red]❌ Не удалось восстановить gRPC соединение синхронно[/red]")
                        logger.error("   ❌ Не удалось восстановить gRPC соединение синхронно")
                        raise Exception("gRPC соединение не восстановлено синхронно")
                
                except Exception as e:
                    self.console.print(f"[bold red]❌ Ошибка восстановления gRPC соединения: {e}[/bold red]")
                    logger.error(f"   ❌ Ошибка восстановления gRPC соединения: {e}")
                    raise Exception(f"gRPC соединение не восстановлено: {e}")
            
            # Просто создаем gRPC стрим
            # 🔧 ОПТИМИЗАЦИЯ: скриншот уже Base64 строка
            screenshot_base64 = self.current_screenshot if self.current_screenshot else ""
            if screenshot_base64:
                self.console.print(f"[blue]📸 Отправляю Base64 скриншот: {len(screenshot_base64)} символов[/blue]")
            
            stream_generator = self.grpc_client.stream_audio(
                command,
                screenshot_base64,
                self.current_screen_info,
                self.hardware_id
            )
            
            # ИСПРАВЛЕНИЕ: сбрасываем предыдущую задачу перед созданием новой
            if self.streaming_task and not self.streaming_task.done():
                self.streaming_task.cancel()
                logger.info("   🔄 Предыдущая streaming_task отменена")
            
            # Создаем задачу для обработки стрима
            self.streaming_task = asyncio.create_task(self._consume_stream(stream_generator))
            
        except Exception as e:
            self.console.print(f"[bold red]❌ Ошибка выполнения команды: {e}[/bold red]")
            logger.error(f"   ❌ Ошибка выполнения команды: {e}")
            self.set_state(AppState.SLEEPING)
    
    async def _consume_stream(self, stream_generator):
        """Обрабатывает gRPC стрим в фоне"""
        logger.info(f"🚨 _consume_stream() начат в {time.time():.3f}")
        
        try:
            self.set_state(AppState.IN_PROCESS)
            logger.info(f"   📊 Состояние установлено: {self.state.name}")
            
            # Сбрасываем флаг для fade-in первого чанка
            self._first_tts_chunk = True
            
            # Потребляем генератор до конца
            chunk_count = 0
            self.console.print("[bold red]🚨 НАЧАЛО ОБРАБОТКИ gRPC СТРИМА![/bold red]")
            logger.info("   🚀 Начало обработки gRPC стрима")
            
            try:
                # ДИАГНОСТИКА: добавляем периодическое логирование
                last_diagnostic = time.time()
                
                async for chunk in stream_generator:
                    # ДИАГНОСТИКА: логируем каждые 5 секунд
                    current_time = time.time()
                    if current_time - last_diagnostic > 5.0:
                        logger.info(f"🔍 ДИАГНОСТИКА _consume_stream: обработано {chunk_count} чанков, состояние={self.state.name}")
                        last_diagnostic = current_time
                    
                    # 🚨 КРИТИЧНО: ПРОВЕРЯЕМ ПРЕРЫВАНИЕ ПЕРЕД КАЖДЫМ ЧАНКОМ
                    if self._check_interrupt_status():
                        logger.warning(f"   🚨 ОБНАРУЖЕНО ПРЕРЫВАНИЕ! Останавливаю обработку чанков")
                        self.console.print("[bold red]🚨 ОБНАРУЖЕНО ПРЕРЫВАНИЕ! Останавливаю обработку чанков![/bold red]")
                        
                        # Принудительно очищаем аудио буферы при прерывании
                        try:
                            if hasattr(self.audio_player, 'clear_all_audio_data'):
                                self.audio_player.clear_all_audio_data()
                                logger.info(f"   🚨 Аудио буферы очищены при прерывании")
                                self.console.print("[green]✅ Аудио буферы очищены при прерывании[/green]")
                            elif hasattr(self.audio_player, 'force_stop'):
                                self.audio_player.force_stop(immediate=True)
                                logger.info(f"   🚨 Аудио принудительно остановлено при прерывании")
                                self.console.print("[green]✅ Аудио принудительно остановлено при прерывании[/green]")
                            else:
                                logger.warning(f"   ⚠️ Не найден метод очистки аудио")
                                self.console.print("[yellow]⚠️ Не найден метод очистки аудио[/yellow]")
                        except Exception as e:
                            logger.error(f"   ❌ Ошибка очистки аудио при прерывании: {e}")
                            self.console.print(f"[red]❌ Ошибка очистки аудио при прерывании: {e}[/red]")
                        
                        # Выходим из цикла обработки чанков
                        logger.info(f"   🚨 Выход из цикла обработки чанков при прерывании")
                        self.console.print("[bold red]🚨 Выход из цикла обработки чанков при прерывании![/bold red]")
                        break
                    
                    chunk_count += 1
                    logger.info(f"   📦 Получен чанк {chunk_count} в {time.time():.3f}")
                    
                    self.console.print(f"[blue]🔍 Обрабатываю чанк {chunk_count}...[/blue]")
                    
                    # Обрабатываем каждый чанк!
                    if hasattr(chunk, 'text_chunk') and chunk.text_chunk:
                        self.console.print(f"[green]📄 Текст: {chunk.text_chunk[:100]}...[/green]")
                    
                    if hasattr(chunk, 'audio_chunk') and chunk.audio_chunk:
                        audio_data = chunk.audio_chunk.audio_data
                        # 🔧 ИСПРАВЛЕНИЕ: правильно вычисляем количество сэмплов
                        # audio_data - это bytes, поэтому делим на размер одного сэмпла (2 байта для int16)
                        audio_samples = len(audio_data) // 2
                        logger.info(f"   🎵 [CLIENT] Аудио чанк {chunk_count}: {audio_samples} сэмплов")
                        self.console.print(f"[green]🎵 Аудио чанк получен: {audio_samples} сэмплов[/green]")
                        
                        # КРИТИЧНО: Проверяем, что аудио чанк не пустой
                        if audio_samples > 0:
                            logger.info(f"   🎵 [CLIENT] Обрабатываю непустой аудио чанк {chunk_count}")
                            # Добавляем аудио в плеер!
                            try:
                                import numpy as np
                                # 🔧 ИСПРАВЛЕНИЕ: используем правильный dtype из protobuf
                                dtype_str = chunk.audio_chunk.dtype
                                if dtype_str == 'int16':
                                    dtype = np.int16
                                elif dtype_str == 'float32':
                                    dtype = np.float32
                                elif dtype_str == 'float64':
                                    dtype = np.float64
                                else:
                                    # Fallback на int16 если dtype не распознан
                                    dtype = np.int16
                                    logger.warning(f"   ⚠️ Неизвестный dtype '{dtype_str}', использую int16")
                                
                                audio_array = np.frombuffer(audio_data, dtype=dtype)
                                
                                # Делаем копию массива для возможности изменения
                                audio_array = audio_array.copy()

                                # Короткий fade-in для первого чанка чтобы убрать щелчок на старте
                                try:
                                    if getattr(self, '_first_tts_chunk', True):
                                        fade_len = min(512, audio_array.size)
                                        if fade_len > 0:
                                            if audio_array.dtype.kind == 'f':
                                                window = np.linspace(0.0, 1.0, num=fade_len, endpoint=False)
                                                audio_array[:fade_len] *= window
                                            else:
                                                window = np.linspace(0.0, 1.0, num=fade_len, endpoint=False).astype(np.float32)
                                                tmp = audio_array[:fade_len].astype(np.float32)
                                                audio_array[:fade_len] = (tmp * window).astype(np.int16)
                                        self._first_tts_chunk = False
                                except Exception as fade_e:
                                    logger.warning(f"   ⚠️ Fade-in не выполнен: {fade_e}")
                                
                                # Логируем состояние очереди ДО добавления
                                if self.audio_player and hasattr(self.audio_player, 'audio_queue'):
                                    queue_before = self.audio_player.audio_queue.qsize()
                                    logger.info(f"   📊 [CLIENT] Очередь ДО добавления: {queue_before}")
                                
                                # КРИТИЧНО: используем правильное имя метода!
                                logger.info(f"   🎵 [CLIENT] Вызываю audio_player.add_chunk() для чанка {chunk_count}")
                                if self.audio_player:
                                    self.audio_player.add_chunk(audio_array)
                                else:
                                    logger.warning("   ⚠️ AudioPlayer недоступен - пропускаю аудио чанк")
                                
                                # Логируем состояние очереди ПОСЛЕ добавления
                                if self.audio_player and hasattr(self.audio_player, 'audio_queue'):
                                    queue_after = self.audio_player.audio_queue.qsize()
                                    logger.info(f"   📊 [CLIENT] Очередь ПОСЛЕ добавления: {queue_after}")
                                
                                self.console.print(f"[green]✅ Аудио добавлено в плеер[/green]")
                            except Exception as e:
                                logger.error(f"   ❌ Ошибка добавления аудио: {e}")
                                self.console.print(f"[red]❌ Ошибка добавления аудио: {e}[/red]")
                        else:
                            logger.debug(f"   🔇 [CLIENT] Пропускаю пустой аудио чанк {chunk_count}")
                            self.console.print(f"[yellow]🔇 Пропускаю пустой аудио чанк[/yellow]")
                    
                    if hasattr(chunk, 'error_message') and chunk.error_message:
                        self.console.print(f"[red]❌ Ошибка сервера: {chunk.error_message}[/red]")
                    
                    if hasattr(chunk, 'end_message') and chunk.end_message:
                        self.console.print(f"[green]✅ Получен сигнал завершения: {chunk.end_message}[/green]")
                        break
                        
            except Exception as stream_error:
                self.console.print(f"[red]❌ Ошибка в async for: {stream_error}[/red]")
                
        except Exception as e:
            logger.error(f"   ❌ Ошибка в _consume_stream: {e}")
            self.console.print(f"[red]❌ Ошибка в _consume_stream: {e}[/red]")
        finally:
            # ИСПРАВЛЕНИЕ: сбрасываем streaming_task в None для предотвращения повторного использования
            if self.streaming_task:
                self.streaming_task = None
                logger.info("   🔄 streaming_task сброшен в None в finally")
            
            # КРИТИЧНО: всегда сбрасываем состояние в SLEEPING после завершения
            final_time = time.time()
            logger.info(f"   🏁 _consume_stream завершен в {final_time:.3f}")
            
            # 🚨 ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: если было прерывание, принудительно очищаем аудио
            if self._check_interrupt_status():
                logger.warning(f"   🚨 В finally: обнаружено прерывание, принудительно очищаю аудио")
                self.console.print("[bold red]🚨 В finally: обнаружено прерывание, принудительно очищаю аудио![/bold red]")
                
                try:
                    if hasattr(self.audio_player, 'clear_all_audio_data'):
                        self.audio_player.clear_all_audio_data()
                        logger.info(f"   🚨 Аудио буферы очищены в finally при прерывании")
                    elif hasattr(self.audio_player, 'force_stop'):
                        self.audio_player.force_stop(immediate=True)
                        logger.info(f"   🚨 Аудио принудительно остановлено в finally при прерывании")
                except Exception as e:
                    logger.error(f"   ❌ Ошибка очистки аудио в finally: {e}")
                
                # При прерывании НЕ запускаем ожидание завершения аудио
                logger.info(f"   🚨 Прерывание обнаружено - пропускаю ожидание завершения аудио")
                self.console.print("[bold red]🚨 Прерывание обнаружено - пропускаю ожидание завершения аудио![/bold red]")
                
                # Сразу переходим в SLEEPING
                self.set_state(AppState.SLEEPING)
                logger.info(f"   📊 Финальное состояние при прерывании: {self.state.name}")
                self.console.print(f"[blue]✅ _consume_stream завершен при прерывании, переход в SLEEPING[/blue]")
                self.console.print(f"[green]🌙 Ассистент прерван, перешел в режим ожидания[/green]")
                return  # Выходим из finally
            
            # ИСПРАВЛЕНИЕ: используем существующий НЕБЛОКИРУЮЩИЙ метод
            try:
                if self.audio_player and hasattr(self.audio_player, 'is_playing') and self.audio_player.is_playing:
                    # Проверяем статус аудио НЕБЛОКИРУЮЩИМ способом
                    if self.audio_player.wait_for_queue_empty():
                        logger.info("   🎵 Аудио завершено - переход в SLEEPING")
                        self.console.print("[green]🎵 Аудио завершено - переход в SLEEPING[/green]")
                    else:
                        # Аудио еще воспроизводится - переходим в SLEEPING, аудио в фоне
                        logger.info("   🎵 Аудио в фоне - переход в SLEEPING")
                        self.console.print("[blue]🎵 Аудио в фоне - переход в SLEEPING[/blue]")
                else:
                    logger.info("   ℹ️ Аудио не воспроизводится - переход в SLEEPING")
                    self.console.print("[blue]ℹ️ Аудио не воспроизводится - переход в SLEEPING[/blue]")
                    
            except Exception as e:
                logger.error(f"   ❌ Ошибка проверки статуса аудио: {e}")
                self.console.print(f"[red]❌ Ошибка проверки статуса аудио: {e}[/red]")
            
            # 🚨 ИСПРАВЛЕНИЕ: переходим в SLEEPING ТОЛЬКО после завершения аудио
            # Теперь это происходит ПОСЛЕ реального завершения воспроизведения
            self.set_state(AppState.SLEEPING)
            logger.info(f"   📊 Финальное состояние: {self.state.name}")
            self.console.print(f"[blue]✅ _consume_stream завершен, переход в SLEEPING[/blue]")
            self.console.print(f"[green]🌙 Ассистент завершил работу, перешел в режим ожидания[/green]")
    
                      
    
    def _force_stop_grpc_stream(self):
        """ПРИНУДИТЕЛЬНО останавливает gRPC стрим на уровне соединения"""
        logger.info(f"   🚨 _force_stop_grpc_stream() вызван в {time.time():.3f}")
        
        try:
            # 1️⃣ Принудительно закрываем gRPC соединение
            if hasattr(self, 'grpc_client') and self.grpc_client:
                logger.info(f"   🚨 Принудительно закрываю gRPC соединение...")
                
                # Закрываем соединение
                if hasattr(self.grpc_client, 'close_connection'):
                    self.grpc_client.close_connection()
                    logger.info(f"   ✅ gRPC соединение принудительно закрыто")
                elif hasattr(self.grpc_client, 'channel'):
                    # Закрываем канал
                    try:
                        self.grpc_client.channel.close()
                        logger.info(f"   ✅ gRPC канал принудительно закрыт")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Ошибка закрытия gRPC канала: {e}")
                
                # Сбрасываем состояние клиента
                if hasattr(self.grpc_client, 'reset_state'):
                    self.grpc_client.reset_state()
                    logger.info(f"   ✅ Состояние gRPC клиента сброшено")
                
            # 2️⃣ Принудительно очищаем все буферы
            if hasattr(self, 'audio_player') and self.audio_player:
                logger.info(f"   🚨 Принудительно очищаю все аудио буферы...")
                
                # Очищаем очередь
                if hasattr(self.audio_player, 'audio_queue'):
                    queue_size = self.audio_player.audio_queue.qsize()
                    logger.info(f"   📊 Очищаю очередь: {queue_size} элементов")
                    
                    # Принудительно очищаем очередь
                    while not self.audio_player.audio_queue.empty():
                        try:
                            self.audio_player.audio_queue.get_nowait()
                        except:
                            break
                    
                    logger.info(f"   ✅ Очередь принудительно очищена")
                
                # Останавливаем воспроизведение
                if hasattr(self.audio_player, 'force_stop'):
                    self.audio_player.force_stop(immediate=True)
                    logger.info(f"   ✅ Аудио принудительно остановлено")
                elif hasattr(self.audio_player, 'stop'):
                    self.audio_player.stop()
                    logger.info(f"   ✅ Аудио остановлено")
                
                # Очищаем буферы
                if hasattr(self.audio_player, 'clear_all_audio_data'):
                    self.audio_player.clear_all_audio_data()
                    logger.info(f"   ✅ Все аудио буферы очищены")
            
            # 3️⃣ Принудительно прерываем все потоки
            import threading
            current_thread = threading.current_thread()
            all_threads = threading.enumerate()
            
            logger.info(f"   🚨 Проверяю активные потоки: {len(all_threads)}")
            
            for thread in all_threads:
                if (thread != current_thread and 
                    thread != threading.main_thread() and 
                    thread.is_alive() and
                    'grpc' in thread.name.lower()):
                    
                    logger.info(f"   🚨 Прерываю gRPC поток: {thread.name}")
                    try:
                        # Принудительно прерываем поток
                        import ctypes
                        thread_id = thread.ident
                        if thread_id:
                            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                                ctypes.c_long(thread_id), 
                                ctypes.py_object(SystemExit)
                            )
                            if res > 1:
                                ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
                                logger.warning(f"   ⚠️ Не удалось прервать поток: {thread.name}")
                            else:
                                logger.info(f"   ✅ Поток прерван: {thread.name}")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Ошибка прерывания потока {thread.name}: {e}")
            
            logger.info(f"   ✅ _force_stop_grpc_stream завершен")
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка в _force_stop_grpc_stream: {e}")
    
    async def _wait_for_task_cancellation(self, task):
        """Ожидает завершения отмены задачи"""
        try:
            if not task.done():
                # Ждем завершения с таймаутом
                await asyncio.wait_for(task, timeout=0.1)
        except asyncio.TimeoutError:
            logger.warning(f"   ⚠️ Таймаут ожидания отмены задачи")
        except asyncio.CancelledError:
            logger.info(f"   ✅ Задача успешно отменена")
        except Exception as e:
            logger.warning(f"   ⚠️ Ошибка ожидания отмены: {e}")
    
    def cleanup(self):
        """Очищает ресурсы"""
        if self.streaming_task and not self.streaming_task.done():
            self.streaming_task.cancel()
        if self.active_call and not self.active_call.done():
            self.active_call.cancel()

    def _capture_screen(self):
        """Захватывает экран"""
        self.console.print("[bold blue]📸 Захватываю экран в JPEG Base64...[/bold blue]")
        try:
            if not getattr(self, 'screen_capture', None):
                self.console.print("[bold yellow]⚠️ Захват экрана недоступен[/bold yellow]")
                self.current_screenshot = None
                return
            self.current_screenshot = self.screen_capture.capture_screen(quality=75, max_size=1024)
            if self.current_screenshot:
                self.console.print(f"[bold green]✅ Base64 скриншот захвачен: {len(self.current_screenshot)} символов[/bold green]")
            else:
                self.console.print("[bold yellow]⚠️ Не удалось захватить скриншот[/bold yellow]")
        except Exception as e:
            logger.warning(f"   ⚠️ Ошибка захвата экрана: {e}")
            self.current_screenshot = None
    
    def force_stop_everything(self):
        """🚨 УНИВЕРСАЛЬНЫЙ МЕТОД: мгновенно останавливает ВСЕ при нажатии пробела!"""
        logger.info(f"🚨 force_stop_everything() вызван в {time.time():.3f}")
        self.console.print("[bold red]🚨 УНИВЕРСАЛЬНАЯ ОСТАНОВКА ВСЕГО![/bold red]")
        
        try:
            # 1️⃣ Останавливаем аудио воспроизведение
            if hasattr(self.audio_player, 'force_stop'):
                self.audio_player.force_stop(immediate=True)
                logger.info("   ✅ Аудио принудительно остановлено")
            
            # 2️⃣ Закрываем gRPC соединение
            if hasattr(self.grpc_client, 'close_connection'):
                self.grpc_client.close_connection()
                logger.info("   ✅ gRPC соединение закрыто")
            
            # 3️⃣ Очищаем аудио буферы
            if hasattr(self.audio_player, 'clear_all_audio_data'):
                self.audio_player.clear_all_audio_data()
                logger.info("   ✅ Аудио буферы очищены")
            
            # 4️⃣ Отменяем активные задачи
            if self.streaming_task and not self.streaming_task.done():
                self.streaming_task.cancel()
                logger.info("   ✅ Streaming задача отменена")
                
                # ИСПРАВЛЕНИЕ: ждем завершения отмены и сбрасываем в None
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Создаем задачу для ожидания отмены
                        wait_task = loop.create_task(self._wait_for_task_cancellation(self.streaming_task))
                        # Даем немного времени на отмену
                        import threading
                        threading.Timer(0.1, lambda: wait_task.cancel() if not wait_task.done() else None).start()
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка ожидания отмены streaming_task: {e}")
                
                # Сбрасываем в None для предотвращения повторного использования
                self.streaming_task = None
                logger.info("   ✅ Streaming задача сброшена в None")
            
            if self.active_call and not self.active_call.done():
                self.active_call.cancel()
                logger.info("   ✅ Active call отменен")
                self.active_call = None
            
            logger.info("   🎯 УНИВЕРСАЛЬНАЯ ОСТАНОВКА УСПЕШНА!")
            self.console.print("[bold green]✅ ВСЕ ПРИНУДИТЕЛЬНО ОСТАНОВЛЕНО![/bold green]")
            return True
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка в force_stop_everything: {e}")
            self.console.print(f"[red]❌ Ошибка универсальной остановки: {e}[/red]")
            return False
    
    def _force_stop_audio_playback(self):
        """МГНОВЕННО останавливает воспроизведение аудио"""
        logger.info(f"   🚨 _force_stop_audio_playback() вызван")
        
        try:
            if hasattr(self, 'audio_player') and self.audio_player:
                # 1️⃣ Принудительно останавливаем воспроизведение
                if hasattr(self.audio_player, 'force_stop'):
                    self.audio_player.force_stop(immediate=True)
                
                # 2️⃣ Принудительно очищаем все аудио буферы (включая очереди и потоки)
                if hasattr(self.audio_player, 'clear_all_audio_data'):
                    self.audio_player.clear_all_audio_data()
                
                logger.info("   ✅ _force_stop_audio_playback завершен")
                
        except Exception as e:
            logger.error(f"   ❌ Ошибка в _force_stop_audio_playback: {e}")
    
    def _force_cancel_all_tasks(self):
        """МГНОВЕННО отменяет все asyncio задачи"""
        logger.info(f"   🚨 _force_cancel_all_tasks() вызван")
        
        try:
            # 1️⃣ Отменяем streaming_task
            if self.streaming_task and not self.streaming_task.done():
                logger.info(f"   🚨 Принудительно отменяю streaming_task: {self.streaming_task}")
                self.streaming_task.cancel()
                
                # Ждем завершения отмены с таймаутом
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Создаем задачу для ожидания отмены
                        wait_task = loop.create_task(self._wait_for_task_cancellation(self.streaming_task))
                        # Даем немного времени на отмену
                        import threading
                        def wait_in_thread():
                            try:
                                import asyncio
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(asyncio.sleep(0.1))
                            except:
                                pass
                        
                        wait_thread = threading.Thread(target=wait_in_thread, daemon=True)
                        wait_thread.start()
                        wait_thread.join(timeout=0.2)
                        
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка ожидания отмены streaming_task: {e}")
            
            # 2️⃣ Отменяем active_call
            if self.active_call and not self.active_call.done():
                logger.info(f"   🚨 Принудительно отменяю active_call: {self.active_call}")
                self.active_call.cancel()
                
                # Ждем завершения отмены с таймаутом
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Создаем задачу для ожидания отмены
                        wait_task = loop.create_task(self._wait_for_task_cancellation(self.active_call))
                        # Даем немного времени на отмену
                        import threading
                        def wait_in_thread():
                            try:
                                import asyncio
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(asyncio.sleep(0.1))
                            except:
                                pass
                        
                        wait_thread = threading.Thread(target=wait_in_thread, daemon=True)
                        wait_thread.start()
                        wait_thread.join(timeout=0.2)
                        
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка ожидания отмены active_call: {e}")
            
            # 3️⃣ Очищаем ссылки на задачи
            self.streaming_task = None
            self.active_call = None
            logger.info("   ✅ Все ссылки на задачи очищены")
            
            logger.info("   ✅ _force_cancel_all_tasks завершен")
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка в _force_cancel_all_tasks: {e}")
    
    def _force_clear_all_buffers(self):
        """МГНОВЕННО очищает все буферы"""
        logger.info(f"   🚨 _force_clear_all_buffers() вызван")
        
        try:
            # 1️⃣ Очищаем все аудио буферы
            if hasattr(self, 'audio_player') and self.audio_player:
                if hasattr(self.audio_player, 'clear_all_audio_data'):
                    self.audio_player.clear_all_audio_data()
                    logger.info("   ✅ Все аудио буферы очищены")
                
                if hasattr(self.audio_player, 'clear_audio_buffers'):
                    self.audio_player.clear_audio_buffers()
                    logger.info("   ✅ Аудио буферы очищены")
            
            # 2️⃣ Очищаем все gRPC буферы
            if hasattr(self, 'grpc_client') and self.grpc_client:
                if hasattr(self.grpc_client, 'clear_buffers'):
                    self.grpc_client.clear_buffers()
                    logger.info("   ✅ gRPC буферы очищены")
            
            # 3️⃣ Очищаем все системные буферы
            import gc
            gc.collect()
            logger.info("   ✅ Системные буферы очищены")
            
            logger.info("   ✅ _force_clear_all_buffers завершен")
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка в _force_clear_all_buffers: {e}")
    
    def _force_interrupt_server(self):
        """МГНОВЕННО отправляет команду прерывания на сервер"""
        logger.info(f"   🚨 _force_interrupt_server() вызван")
        
        try:
            if hasattr(self, 'grpc_client') and self.grpc_client:
                # 1️⃣ Отправляем команду прерывания на сервер
                if hasattr(self.grpc_client, 'force_interrupt_server'):
                    self.grpc_client.force_interrupt_server()
                    logger.info("   ✅ Команда прерывания отправлена на сервер")
                
                # 2️⃣ Принудительно закрываем соединение
                if hasattr(self.grpc_client, 'close_connection'):
                    self.grpc_client.close_connection()
                    logger.info("   ✅ gRPC соединение принудительно закрыто")
                
                # 3️⃣ Сбрасываем состояние клиента
                if hasattr(self.grpc_client, 'reset_state'):
                    self.grpc_client.reset_state()
                    logger.info("   ✅ Состояние gRPC клиента сброшено")
                
                logger.info("   ✅ _force_interrupt_server завершен")
            else:
                logger.warning("   ⚠️ gRPC клиент недоступен")
                
        except Exception as e:
            logger.error(f"   ❌ Ошибка в _force_interrupt_server: {e}")

async def check_audio_completion(state_manager, audio_player):
    """
    Проверяет завершение аудио и переводит в SLEEPING.
    Вызывается периодически из основного цикла.
    """
    try:
        # Проверяем, нужно ли переводить в SLEEPING
        if (state_manager.state == AppState.IN_PROCESS and 
            audio_player and 
            hasattr(audio_player, 'is_playing') and 
            not audio_player.is_playing and
            audio_player.wait_for_queue_empty()):
            
            logger.info("   🎵 Аудио завершено - переход в SLEEPING")
            state_manager.console.print("[green]🎵 Аудио завершено - переход в SLEEPING[/green]")
            state_manager.set_state(AppState.SLEEPING)
            return True
        return False
    except Exception as e:
        logger.error(f"   ❌ Ошибка в check_audio_completion: {e}")
        return False

async def main():
    """Основная функция клиента с push-to-talk логикой, захватом экрана и Hardware ID"""
    
    # Инициализируем компоненты в правильном порядке
    console.print("[bold blue]🔧 Инициализация компонентов...[/bold blue]")
    
    # 0. Сначала инициируем запросы системных разрешений (Screen, Mic, Accessibility, Apple Events)
    try:
        ensure_permissions()
    except Exception:
        pass
    
    # Загружаем конфиг
    config_path = Path(__file__).parent / 'config' / 'app_config.yaml'
    config = {}
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        console.print(f"[yellow]⚠️ Не удалось загрузить конфиг: {e}[/yellow]")

    audio_cfg = (config.get('audio') or {})
    audio_follow_default = bool(audio_cfg.get('follow_system_default', True))
    bt_policy = (audio_cfg.get('bluetooth_policy') or 'prefer_quality')
    settle_ms = int(audio_cfg.get('settle_ms', 400))
    retries = int(audio_cfg.get('retries', 3))
    preflush = bool(audio_cfg.get('preflush_on_switch', True))
    use_coreaudio_listeners = bool(audio_cfg.get('use_coreaudio_listeners', False))
    
    # Новая конфигурация AudioManagerDaemon
    device_manager_cfg = audio_cfg.get('device_manager', {})
    device_manager_enabled = bool(device_manager_cfg.get('enabled', True))
    device_manager_config = {
        'monitoring_interval': float(device_manager_cfg.get('monitoring_interval', 3.0)),
        'switch_cooldown': float(device_manager_cfg.get('switch_cooldown', 2.0)),
        'cache_timeout': float(device_manager_cfg.get('cache_timeout', 5.0))
    }
                                                                      
    # 1. STT будет инициализирован после создания StateManager
    
    # 2. Инициализируем захват экрана
    console.print("[blue]📸 Инициализация захвата экрана...[/blue]")
    try:
        screen_capture = ScreenCapture()
        console.print("[bold green]✅ Захват экрана инициализирован[/bold green]")
    except Exception as e:
        console.print(f"[bold yellow]⚠️ Захват экрана недоступен: {e}[/bold yellow]")
        screen_capture = None
    
    # 3. Инициализируем аудио плеер
    console.print("[blue]🔊 Инициализация аудио плеера...[/blue]")
    try:
        audio_player = AudioPlayer(sample_rate=48000, channels=2)
        # Применяем настройки воспроизведения
        if hasattr(audio_player, '__dict__'):
            audio_player.follow_system_default = audio_follow_default
            audio_player.bluetooth_policy = bt_policy
            audio_player.settle_ms = settle_ms
            audio_player.retries = retries
            audio_player.preflush_on_switch = preflush
            # Переводим в режим централизованного управления: без авто-рестартов внутри плеера
            try:
                audio_player.external_controlled = True
            except Exception:
                pass
            
            # Передаем конфигурацию AudioManagerDaemon
            if device_manager_enabled and hasattr(audio_player, 'audio_manager') and audio_player.audio_manager:
                try:
                    # Конфигурация уже применена при инициализации AudioManagerDaemon
                    # audio_player.audio_manager._apply_config(device_manager_config)
                    console.print("[bold green]✅ Конфигурация AudioManagerDaemon применена[/bold green]")
                except Exception as e:
                    console.print(f"[yellow]⚠️ Не удалось применить конфигурацию AudioManagerDaemon: {e}[/yellow]")
        
        console.print("[bold green]✅ Аудио плеер инициализирован[/bold green]")
        
        # Проверяем, что новая система событий активна
        if hasattr(audio_player, 'device_events') and audio_player.device_events:
            console.print("[bold green]🎧 Система автоматического переключения наушников активна[/bold green]")
            console.print("[green]   ⚡ Реакция на изменения: 0.5 секунды[/green]")
            console.print("[green]   🔄 Автоматическое переключение: включено[/green]")
            console.print("[green]   ⏸️ Пауза при отключении: включена[/green]")
            console.print("[green]   ▶️ Возобновление при подключении: включено[/green]")
        
        # Проверяем AudioManagerDaemon
        if hasattr(audio_player, 'audio_manager') and audio_player.audio_manager:
            console.print("[bold green]🎛️ AudioManagerDaemon активен[/bold green]")
            console.print("[green]   🔄 Мониторинг устройств: включен[/green]")
            console.print("[green]   🎯 Автоматическое переключение: включено[/green]")
            console.print("[green]   ⚡ SwitchAudioSource: интегрирован[/green]")
            
            # Показываем статус AudioManagerDaemon
            try:
                manager_status = audio_player.get_audio_manager_status()
                if manager_status.get('available', False):
                    console.print(f"[green]   📱 Устройств обнаружено: {manager_status.get('total_devices', 0)}[/green]")
                    console.print(f"[green]   🎧 Текущее устройство: {manager_status.get('current_device', 'Unknown')}[/green]")
                else:
                    console.print(f"[yellow]   ⚠️ AudioManagerDaemon недоступен: {manager_status.get('error', 'Unknown error')}[/yellow]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Не удалось получить статус AudioManagerDaemon: {e}[/yellow]")
            
            # Показываем текущее аудио устройство
            try:
                current_device = audio_player.get_current_device_info()
                if current_device:
                    device_type = "🎧 НАУШНИКИ" if current_device.get('is_headphones', False) else "🔊 ДИНАМИКИ"
                    console.print(f"[blue]📱 Текущее аудио устройство: {current_device['name']} - {device_type}[/blue]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Не удалось получить информацию об устройстве: {e}[/yellow]")
        
        # Автоматический режим: отключаем старый CoreAudio мониторинг
        # Теперь используем новую систему событий в AudioPlayer
        ca_listener = None
        if False:  # Отключаем старую систему CoreAudio мониторинга
            try:
                from coreaudio_default_listener import CoreAudioDefaultListener
                ca_listener = CoreAudioDefaultListener()
                # Установим начальные значения из CoreAudio
                import sounddevice as sd
                hostapis = sd.query_hostapis()
                core_idx = next((i for i,a in enumerate(hostapis) if 'core' in (a.get('name','').lower())), 0)
                api = sd.query_hostapis(core_idx)
                din = api.get('default_input_device', -1)
                dout = api.get('default_output_device', -1)
                ca_listener.set_defaults(din if din != -1 else None, dout if dout != -1 else None)
                # Привязываем output-change к плееру (индекс из события игнорируем, используем HostAPI + имя)
                def _on_output_changed(new_idx):
                    try:
                        if getattr(audio_player, '_is_shutting_down', False):
                            return
                        import time as _t
                        import sounddevice as _sd
                        # Короткий settle на случай задержки CoreAudio
                        _t.sleep(max(0.05, settle_ms/1000.0))
                        # Повторно считываем hostapi defaults (и имена)
                        try:
                            hostapis = _sd.query_hostapis()
                            core_idx2 = next((i for i,a in enumerate(hostapis) if 'core' in (a.get('name','').lower())), 0)
                            api2 = _sd.query_hostapis(core_idx2)
                            din2 = api2.get('default_input_device', -1)
                            dout2 = api2.get('default_output_device', -1)
                        except Exception:
                            din2 = None
                            dout2 = None

                        # Резолвим актуальный индекс вывода по имени системного дефолта (если доступен)
                        resolved_out = None
                        try:
                            if dout2 not in (None, -1):
                                target_name = _sd.query_devices(dout2).get('name')
                                try:
                                    devs = _sd.query_devices()
                                    for i, d in enumerate(devs):
                                        try:
                                            if d.get('name') == target_name and int(d.get('max_output_channels') or 0) > 0:
                                                resolved_out = i
                                                break
                                        except Exception:
                                            continue
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        # Если не смогли резолвить по имени — используем hostapi индекс
                        if resolved_out in (None, -1):
                            resolved_out = dout2 if dout2 not in (None, -1) else None

                        # Синхронизируем sd.default.device
                        try:
                            curr = _sd.default.device
                            if isinstance(curr, (list, tuple)) and len(curr) >= 2:
                                _sd.default.device = (curr[0] if curr[0] not in (None, -1) else din2, resolved_out)
                            else:
                                _sd.default.device = (din2, resolved_out)
                        except Exception:
                            pass
                        # Если идёт воспроизведение — мягко перестроимся на целевой индекс
                        if getattr(audio_player, 'is_playing', False):
                            try:
                                if resolved_out not in (None, -1):
                                    audio_player._restart_output_stream(resolved_out)
                            except Exception:
                                # Fallback на текущий системный default
                                try:
                                    audio_player._attempt_restart_on_current_default(retries=2)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                ca_listener.on_output_changed(_on_output_changed)
                # Реакция на смену input: с settle и синхронизацией sd.default.device
                def _on_input_changed(new_idx):
                    try:
                        import time as _t
                        import sounddevice as _sd
                        # Короткий settle
                        _t.sleep(max(0.05, settle_ms/1000.0))
                        # Повторная проверка hostapi
                        try:
                            hostapis = _sd.query_hostapis()
                            core_idx2 = next((i for i,a in enumerate(hostapis) if 'core' in (a.get('name','').lower())), 0)
                            api2 = _sd.query_hostapis(core_idx2)
                            din2 = api2.get('default_input_device', -1)
                            dout2 = api2.get('default_output_device', -1)
                        except Exception:
                            din2 = new_idx
                            dout2 = None

                        # Резолвим актуальный индекс входа по имени системного дефолта (если доступен)
                        resolved_in = None
                        try:
                            if din2 not in (None, -1):
                                target_name = _sd.query_devices(din2).get('name')
                                try:
                                    devs = _sd.query_devices()
                                    for i, d in enumerate(devs):
                                        try:
                                            if d.get('name') == target_name and int(d.get('max_input_channels') or 0) > 0:
                                                resolved_in = i
                                                break
                                        except Exception:
                                            continue
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        if resolved_in in (None, -1):
                            resolved_in = new_idx if new_idx not in (None, -1) else din2
                        # Синхронизация sd.default.device
                        try:
                            curr = _sd.default.device
                            in_idx = (resolved_in if resolved_in not in (None, -1) else din2)
                            if isinstance(curr, (list, tuple)) and len(curr) >= 2:
                                _sd.default.device = (in_idx, curr[1] if curr[1] not in (None, -1) else dout2)
                            else:
                                _sd.default.device = (in_idx, dout2)
                        except Exception:
                            pass
                        # Перезапуск записи на новом устройстве, если запись активна
                        if hasattr(state_manager, 'stt_recognizer') and state_manager.stt_recognizer and state_manager.is_microphone_recording():
                            target = in_idx
                            try:
                                if hasattr(state_manager.stt_recognizer, '_restart_input_stream'):
                                    state_manager.stt_recognizer._restart_input_stream(target)
                                    logger.info(f"🎙️ Перезапустил InputStream на новом устройстве (index={target})")
                            except Exception as e:
                                logger.warning(f"⚠️ Не удалось перезапустить InputStream: {e}")

                        # Диагностика
                        try:
                            name = None
                            if new_idx not in (None, -1):
                                name = _sd.query_devices(new_idx).get('name')
                            logger.info(f"🎙️ Default input device changed → {name} (index={new_idx})")
                        except Exception:
                            pass
                    except Exception:
                        pass
                if hasattr(ca_listener, 'on_input_changed'):
                    ca_listener.on_input_changed(_on_input_changed)
                # Прокинем провайдер активности, чтобы монитор работал только при активности аудио
                try:
                    ca_listener.set_activity_provider(
                        lambda: bool(getattr(audio_player, 'is_playing', False) or state_manager.is_microphone_recording())
                    )
                except Exception:
                    pass
                # Инжектируем listener в плеер и STT
                try:
                    setattr(audio_player, 'default_listener', ca_listener)
                except Exception:
                    pass
                try:
                    if hasattr(state_manager, 'stt_recognizer') and state_manager.stt_recognizer:
                        setattr(state_manager.stt_recognizer, 'default_listener', ca_listener)
                except Exception:
                    pass
                ca_listener.start()
            except Exception as e:
                logger.warning(f"⚠️ CoreAudio listener недоступен: {e}")
        else:
            logger.info("🤖 Автоматический режим: macOS сам управляет аудио устройствами")
        # Инжектируем плеер в STT для корректной координации переключений
        try:
            if hasattr(state_manager, 'stt_recognizer') and state_manager.stt_recognizer and hasattr(state_manager.stt_recognizer, 'set_audio_player'):
                state_manager.stt_recognizer.set_audio_player(audio_player)
        except Exception:
            pass
        
        # Связываем компоненты для координации изменений устройств
        try:
            if audio_player and hasattr(state_manager, 'stt_recognizer') and state_manager.stt_recognizer:
                audio_player.stt_recognizer = state_manager.stt_recognizer
                logger.info("✅ Компоненты связаны для координации изменений устройств")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось связать компоненты: {e}")
    except Exception as e:
        console.print(f"[bold red]❌ Ошибка инициализации аудио плеера: {e}[/bold red]")
        console.print("[yellow]⚠️ Ассистент будет работать без звука[/yellow]")
        # Используем None вместо заглушки - код будет проверять на None
        audio_player = None
    
    # 4. Инициализируем gRPC клиент (последним)
    console.print("[blue]🌐 Инициализация gRPC клиента...[/blue]")
    grpc_client = GrpcClient()
    
    # 5. Получаем Hardware ID (один раз при запуске, с кэшированием)
    console.print("[blue]🆔 Получение Hardware ID...[/blue]")
    
    # Проверяем аргументы командной строки для управления кэшем
    import sys
    force_regenerate = "--force-regenerate" in sys.argv
    clear_cache = "--clear-cache" in sys.argv
    
    if clear_cache:
        from utils.hardware_id import clear_hardware_id_cache
        clear_hardware_id_cache()
        console.print("[yellow]🗑️ Кэш Hardware ID очищен[/yellow]")
    
    hardware_id = get_hardware_id(force_regenerate=force_regenerate)  # Автоматически использует кэш если доступен
    hardware_info = get_hardware_info()
    
    console.print(f"[bold green]✅ Hardware ID получен: {hardware_id[:16]}...[/bold green]")
    uuid = hardware_info.get('hardware_uuid')
    serial = hardware_info.get('serial_number')
    uuid_preview = f"{uuid[:16]}..." if isinstance(uuid, str) and uuid else "недоступен"
    serial_text = serial if isinstance(serial, str) and serial else "недоступен"
    console.print(f"[blue]📱 UUID: {uuid_preview}[/blue]")
    console.print(f"[blue]🔢 Serial: {serial_text}[/blue]")
    
    # Показываем информацию о кэше
    from utils.hardware_id import get_cache_info
    cache_info = get_cache_info()
    if cache_info['exists']:
        console.print(f"[green]💾 Hardware ID загружен из кэша[/green]")
    else:
        console.print(f"[yellow]🔄 Hardware ID сгенерирован заново[/yellow]")
    
    # Показываем справку по управлению кэшем
    if "--help" in sys.argv:
        console.print("\n[yellow]📋 Управление кэшем Hardware ID:[/yellow]")
        console.print("[yellow]  • --clear-cache      - очистить кэш[/yellow]")
        console.print("[yellow]  • --force-regenerate - принудительно пересоздать ID[/yellow]")
        console.print("[yellow]  • --help            - показать эту справку[/yellow]")
        console.print("[yellow]  • Без аргументов    - использовать кэш если доступен[/yellow]")
    
    # Инициализируем централизованный AudioDeviceManager
    console.print("[blue]🎛️ Инициализация AudioDeviceManager...[/blue]")
    unified_system = get_global_unified_audio_system()
    audio_device_manager = initialize_global_audio_device_manager(unified_system=unified_system)
    if audio_device_manager:
        console.print("[bold green]✅ AudioDeviceManager инициализирован[/bold green]")
    else:
        console.print("[bold red]❌ Ошибка инициализации AudioDeviceManager[/bold red]")
    
    # Создаем StateManager с временными None для циклических зависимостей
    console.print("[blue]🎛️ Инициализация StateManager...[/blue]")
    state_manager = StateManager(
        console=console,
        audio_player=audio_player,
        stt_recognizer=None,  # Временно None, обновим позже
        screen_capture=screen_capture,
        grpc_client=grpc_client,
        hardware_id=hardware_id,
        input_handler=None,  # Временно None, обновим позже
        tray_controller=None  # Временно None, обновим позже
    )
    console.print("[bold green]✅ StateManager создан[/bold green]")
    
    # Теперь создаем STT с правильным state_manager
    console.print("[blue]🎤 Инициализация STT...[/blue]")
    try:
        stt_recognizer = StreamRecognizer(state_manager=state_manager)
        # Применяем настройки записи
        if hasattr(stt_recognizer, 'config'):             
            stt_recognizer.config = {
                'follow_system_default': audio_follow_default,
                'bluetooth_policy': bt_policy,
                'settle_ms': settle_ms,
                'retries': retries,
                'preflush_on_switch': preflush,
            }
        # Обновляем ссылку в StateManager
        state_manager.stt_recognizer = stt_recognizer
        console.print("[bold green]✅ STT инициализирован[/bold green]")
    except Exception as e:
        console.print(f"[bold red]❌ STT недоступен: {e}[/bold red]")
        stt_recognizer = None
        state_manager.stt_recognizer = None
    
    # Очередь для событий от клавиатуры
    event_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    input_handler = InputHandler(loop, event_queue, state_manager)
    
    # КРИТИЧНО: ждем инициализации InputHandler
    console.print("[blue]⏳ Инициализация InputHandler...[/blue]")
    await asyncio.sleep(0.5)  # Даем время на инициализацию
    console.print("[blue]✅ InputHandler инициализирован[/blue]")
    
    # Обновляем ссылку на input_handler в StateManager
    state_manager.input_handler = input_handler
    
    # Получаем информацию об экране (с учетом возможного отсутствия screen_capture)
    try:
        if screen_capture:
            screen_info = screen_capture.get_screen_info()
        else:
            screen_info = {'width': 0, 'height': 0}
    except Exception as e:
        console.print(f"[bold yellow]⚠️ Не удалось получить информацию об экране: {e}[/bold yellow]")
        screen_info = {'width': 0, 'height': 0}
    console.print(f"[bold blue]📱 Экран: {screen_info.get('width', 0)}x{screen_info.get('height', 0)} пикселей[/bold blue]")
    
    # Создаём и запускаем иконку в меню-баре (helper-процесс)
    tray = None
    try:
        # Запускаем helper через отдельный процесс rumps
        status_file = str(_get_status_file_path())
        main_pid = os.getpid()
        is_frozen = getattr(sys, 'frozen', False)
        if is_frozen:
            # Запущено из PyInstaller .app → можно вызвать тот же бинарник с флагом
            helper_cmd = [sys.executable, "--tray-helper", "--status-file", status_file, "--pid", str(main_pid)]
        else:
            # Запуск из исходников → вызываем python main.py --tray-helper ...
            helper_cmd = [sys.executable, str(Path(__file__).resolve()), "--tray-helper", "--status-file", status_file, "--pid", str(main_pid)]
        try:
            subprocess.Popen(helper_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    except Exception:
        pass
    
    # Обновляем ссылку на tray_controller в StateManager
    state_manager.tray_controller = tray
    
    # Настраиваем StateManager
    state_manager.current_screen_info = screen_info
    state_manager._write_tray_status_file(state_manager.state.name)
    
    # КРИТИЧНО: передаем hardware_id в grpc_client для прерывания на сервере
    grpc_client.hardware_id = hardware_id
    console.print(f"[blue]🔧 Hardware ID {hardware_id[:16]}... передан в gRPC клиент[/blue]")
    
    # Подключаемся к gRPC серверу
    console.print("[blue]🔌 Подключение к серверу...[/blue]")
    if not await grpc_client.connect():
        console.print("[bold red]❌ Не удалось подключиться к серверу[/bold red]")
        return
        
    console.print("[bold green]✅ Подключено к серверу[/bold green]")
    
    # 🔹 Автоприветствие при запуске (через общий поток с маркером)
    try:
        greeting_text = "Hi! Nexy is here. How can I help you?"
        greeting_generator = grpc_client.stream_audio(
            f"__GREETING__:{greeting_text}",
            "",  # без скриншота
            state_manager.current_screen_info,
            hardware_id
        )
        asyncio.create_task(state_manager._consume_stream(greeting_generator))
    except Exception as e:
        console.print(f"[yellow]⚠️ Не удалось воспроизвести приветствие: {e}[/yellow]")
    
    # Показываем справку по управлению
    console.print("[bold green]✅ Ассистент готов![/bold green]")
    console.print("[yellow]📋 Управление (3 состояния):[/yellow]")
    console.print("[yellow]  • Нажмите пробел → прерывание работы ассистента[/yellow]")
    console.print("[yellow]  • Удерживайте пробел → запись команды[/yellow]")
    console.print("[yellow]  • Отпустите пробел → отправка команды[/yellow]")
    console.print("[yellow]  • Три состояния:[/yellow]")
    console.print("[yellow]    - SLEEPING: спит, ждет команды[/yellow]")
    console.print("[yellow]    - LISTENING: слушает команды[/yellow]")
    console.print("[yellow]    - IN_PROCESS: работает (обрабатывает/говорит)[/yellow]")
    console.print("[yellow]  • При активации автоматически захватывается экран[/yellow]")
    console.print("[yellow]  • Hardware ID отправляется с каждой командой[/yellow]")
    console.print("[blue]🌐 Автопереключение серверов:[/blue]")
    console.print("[blue]  • Локальный сервер (127.0.0.1:50051) - приоритет 1[/blue]")
    console.print("[blue]  • Продакшн сервер (20.151.51.172:50051) - fallback[/blue]")
    console.print("[blue]  • Автоматическое переподключение при ошибках[/blue]")
    console.print("[blue]  • Мониторинг соединения каждые 30 секунд[/blue]")

    # Основной цикл обработки событий
    console.print("🔄 Запуск основного цикла обработки событий...")
    
    # Запускаем фоновую задачу для проверки состояния соединения
    async def connection_monitor():
        """Мониторинг состояния gRPC соединения"""
        while True:
            try:
                await asyncio.sleep(30)  # Проверяем каждые 30 секунд
                if hasattr(grpc_client, 'check_connection_health'):
                    await grpc_client.check_connection_health()
            except Exception as e:
                logger.warning(f"⚠️ Ошибка в мониторинге соединения: {e}")
    
    # Автоматический режим: периодически обновляем список устройств
    async def device_refresh_monitor():
        """Периодически обновляет список аудио устройств для предотвращения кеширования"""
        while True:
            try:
                await asyncio.sleep(10)  # Каждые 10 секунд
                try:
                    import sounddevice as sd
                    # Принудительно обновляем список устройств
                    devices = sd.query_devices()
                    hostapis = sd.query_hostapis()
                    core_idx = next((i for i, a in enumerate(hostapis) if 'core' in (a.get('name','').lower())), 0)
                    api = sd.query_hostapis(core_idx)
                    current_default_out = api.get('default_output_device', -1)
                    current_default_in = api.get('default_input_device', -1)
                    
                    logger.debug(f"🔄 Периодическое обновление устройств: {len(devices)} устройств, out={current_default_out}, in={current_default_in}")
                except Exception as e:
                    logger.debug(f"⚠️ Не удалось обновить список устройств: {e}")
            except Exception:
                pass

    # Запускаем мониторинг соединения в фоне
    connection_monitor_task = asyncio.create_task(connection_monitor())
    # Запускаем обновление списка устройств в фоне
    device_refresh_task = asyncio.create_task(device_refresh_monitor())
    
    # Переменная для периодической проверки аудио
    last_audio_check = 0
    
    try:
        while True:
            try:
                # Проверяем завершение аудио каждые 0.5 секунды
                current_time = time.time()
                if current_time - last_audio_check > 0.5:
                    await check_audio_completion(state_manager, audio_player)
                    last_audio_check = current_time
                
                # ДИАГНОСТИКА: логируем состояние очереди
                queue_size = event_queue.qsize()
                if queue_size > 0:
                    logger.info(f"🔍 ДИАГНОСТИКА: В очереди {queue_size} событий, состояние={state_manager.state.name}")
                
                # Получаем событие из очереди с таймаутом
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    event_time = time.time()
                    logger.info(f"🔍 ДИАГНОСТИКА: Получено событие {event} в {event_time:.3f}")
                except asyncio.TimeoutError:
                    # Таймаут - продолжаем цикл для проверки аудио
                    continue
                
                # Логируем получение события
                logger.info(f"📡 СОБЫТИЕ ПОЛУЧЕНО: {event} в {event_time:.3f}")
                console.print(f"[dim]📡 Событие получено: {event}[/dim]")
                
                # Получаем текущее состояние
                current_state = state_manager.get_state()
                logger.info(f"   📊 Текущее состояние: {current_state.name}")
                
                # Обрабатываем событие
                start_time = time.time()
                logger.info(f"   🎯 ОБРАБАТЫВАЮ СОБЫТИЕ: {event}")
                console.print(f"[blue]🔍 Текущее состояние: {current_state.name}, событие: {event}[/blue]")
                
                # Обрабатываем событие через StateManager
                await state_manager.handle_event(event)
                
                # Логируем завершение обработки
                end_time = time.time()
                processing_time = (end_time - start_time) * 1000
                logger.info(f"   ⏱️ Время обработки события: {processing_time:.1f}ms")
                
                # Получаем новое состояние
                new_state = state_manager.get_state()
                logger.info(f"   📊 Новое состояние: {new_state.name}")
                
                # Проверяем изменение состояния
                if current_state != new_state:
                    logger.info(f"   🔄 ИЗМЕНЕНИЕ СОСТОЯНИЯ: {current_state.name} → {new_state.name}")
                    console.print(f"[green]✅ СОБЫТИЕ {event} ОБРАБОТАНО! Новое состояние: {new_state.name}[/green]")
                else:
                    logger.info(f"   🔄 Состояние не изменилось: {current_state.name}")
                    console.print(f"[green]✅ СОБЫТИЕ {event} ОБРАБОТАНО! Новое состояние: {new_state.name}[/green]")
                
                # Показываем статус аудио
                audio_status = audio_player.get_audio_status()
                if audio_status.get('is_playing', False):
                    console.print("🔊 Аудио статус: ВОСПРОИЗВОДИТСЯ")
                else:
                    console.print("🔇 Аудио статус: ОСТАНОВЛЕНО")
                        
            except asyncio.CancelledError:
                logger.info("   🚨 Основной цикл отменен")
                break
            except Exception as e:
                logger.error(f"   ❌ Ошибка в основном цикле: {e}")
                console.print(f"[bold red]❌ Критическая ошибка в основном цикле: {e}[/bold red]")
                # Восстанавливаемся в SLEEPING
                state_manager.set_state(AppState.SLEEPING)
                console.print("[blue]🔄 Восстановление в SLEEPING[/blue]")
                
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Выход...[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]❌ Критическая ошибка: {e}[/bold red]")
    finally:
        # Отменяем задачу мониторинга соединения
        if 'connection_monitor_task' in locals():
            connection_monitor_task.cancel()
            try:
                await connection_monitor_task
            except asyncio.CancelledError:
                pass
        # Отменяем задачу обновления устройств
        if 'device_refresh_task' in locals():
            device_refresh_task.cancel()
            try:
                await device_refresh_task
            except asyncio.CancelledError:
                pass
        
        state_manager.cleanup()
        if audio_player.is_playing:
            audio_player.stop_playback()
        logger.info("Клиент завершил работу.")

if __name__ == "__main__":
    # Режим helper-процесса для меню-бара
    try:
        _run_tray_helper_if_requested()
    except Exception:
        pass

    # Жёсткая блокировка единственного экземпляра
    if not acquire_single_instance_lock():
        try:
            console.print("[bold yellow]ℹ️ Nexy уже запущен — второй экземпляр не будет стартовать[/bold yellow]")
        except Exception:
            pass
        sys.exit(0)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Выход...[/bold yellow]")

                 