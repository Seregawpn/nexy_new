import asyncio
import sounddevice as sd
import numpy as np
import logging
import queue
import threading
import time
from typing import List, Optional, Dict
# Импорты перенесены в методы для устранения циклических зависимостей
# from unified_audio_system import UnifiedAudioSystem, DeviceInfo, get_global_unified_audio_system
# from audio_device_manager import get_global_audio_device_manager
from utils.device_utils import is_headphones, is_virtual_device, get_device_type_keywords

logger = logging.getLogger(__name__)

class AudioPlayer:
    """
    Воспроизводит аудиопоток в реальном времени с использованием sounddevice.
    Принимает аудиофрагменты (chunks) в виде NumPy массивов и воспроизводит их бесшовно.
    Автоматически отслеживает изменения аудио устройств и переключается между ними.
    """
    def __init__(self, sample_rate=48000, channels=1, dtype='int16'):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        
        self.audio_queue = queue.Queue()
        self.playback_thread = None
        self.stop_event = threading.Event()
        self.stream = None
        self.is_playing = False
        
        # Централизованное управление состоянием воспроизведения
        self._state_lock = threading.Lock()
        
        # Внутренний буфер для плавного воспроизведения
        self.internal_buffer = np.array([], dtype=np.int16)
        self.buffer_lock = threading.Lock()
        self.stream_lock = threading.Lock()
        
        # Новая система управления аудио устройствами
        self.audio_manager = None
        self.current_device_info = None
        self._device_info_lock = threading.RLock()  # Thread-safe доступ к current_device_info
        self.device_switch_threshold = 1.0  # Минимальное время между переключениями
        self._last_device_switch = 0
        
        # Приоритеты устройств теперь управляются через UnifiedAudioSystem
        # Удалено дублирование - используем audio_manager.device_priorities
        
        # Настройки автоматического переключения на наушники
        self.auto_switch_to_headphones = True
        self.pause_on_disconnect = True
        self.resume_on_reconnect = True
        self._was_paused_for_disconnect = False
        
        # Проверяем доступность аудио устройств
        self._check_audio_devices()
        
        # Глобальный guard завершения/остановки, предотвращает гонки остановки/рестартов
        self._is_shutting_down = False
        self._shutdown_mutex = threading.Lock()
        
        # Защита от множественных запусков плеера
        self._is_starting = False
        
        # Кэширование аудио потоков для быстрого перезапуска
        self._cached_stream_config = None
        self._cached_device_info = None
        self._stream_cache_valid = False
        self._cache_lock = threading.Lock()

        # Инициализируем новую систему управления аудио устройствами
        self._init_audio_manager()
        
        # Запускаем мониторинг устройств через события
        self.start_device_monitoring()
        
        # Предварительная инициализация аудио системы в фоне
        self._preload_audio_system()

    def _cache_stream_config(self, config, device_info):
        """Кэширует конфигурацию потока для быстрого перезапуска"""
        with self._cache_lock:
            self._cached_stream_config = config.copy()
            # DeviceInfo - это объект, сохраняем его как есть
            self._cached_device_info = device_info
            self._stream_cache_valid = True
            logger.debug("💾 Конфигурация потока закэширована")
    
    def _get_cached_stream_config(self):
        """Получает закэшированную конфигурацию потока"""
        with self._cache_lock:
            if self._stream_cache_valid and self._cached_stream_config:
                logger.debug("💾 Использую закэшированную конфигурацию потока")
                return self._cached_stream_config.copy(), self._cached_device_info
            return None, None
    
    def _invalidate_stream_cache(self):
        """Инвалидирует кэш конфигурации потока"""
        with self._cache_lock:
            self._stream_cache_valid = False
            self._cached_stream_config = None
            self._cached_device_info = None
            logger.debug("🗑️ Кэш конфигурации потока очищен")
    
    def _preload_audio_system(self):
        """Предварительная загрузка аудио системы в фоне для быстрого запуска"""
        def preload_worker():
            try:
                logger.info("🔄 Предварительная инициализация аудио системы...")
                
                # Получаем информацию об устройствах
                all_devices, current_device, current_device_info = self._get_audio_manager_devices()
                
                if all_devices and current_device_info:
                    # Определяем оптимальные параметры для текущего устройства
                    device_type = getattr(current_device_info, 'type', 'unknown')
                    
                    # Базовые параметры для разных типов устройств
                    if device_type in ['airpods', 'beats', 'bluetooth_headphones']:
                        config = {
                            'channels': 2,
                            'samplerate': 44100,
                            'dtype': np.int16
                        }
                    else:
                        config = {
                            'channels': 2,
                            'samplerate': 48000,
                            'dtype': np.int16
                        }
                    
                    # Кэшируем конфигурацию
                    self._cache_stream_config(config, current_device_info)
                    logger.info("✅ Аудио система предварительно загружена и закэширована")
                else:
                    logger.warning("⚠️ Не удалось получить информацию об устройствах для предзагрузки")
                    
            except Exception as e:
                logger.warning(f"⚠️ Ошибка предварительной загрузки аудио системы: {e}")
        
        # Запускаем в отдельном потоке
        preload_thread = threading.Thread(target=preload_worker, daemon=True)
        preload_thread.start()

    def _set_playing_state(self, state: bool, reason: str = ""):
        """
        Централизованное управление состоянием воспроизведения.
        Предотвращает гонки условий и обеспечивает консистентность.
        """
        with self._state_lock:
            if self.is_playing != state:
                logger.info(f"🎵 [STATE] is_playing: {self.is_playing} → {state} ({reason})")
                self.is_playing = state
            else:
                logger.debug(f"🎵 [STATE] is_playing уже {state} ({reason})")

    def _get_playing_state(self) -> bool:
        """
        Безопасное получение состояния воспроизведения.
        """
        with self._state_lock:
            return self.is_playing


    def _init_audio_manager(self):
        """Инициализирует единую систему управления аудио устройствами"""
        try:
            logger.info("🔄 Инициализация UnifiedAudioSystem...")
            
            # Конфигурация для UnifiedAudioSystem
            config = {
                'switch_audio_path': '/opt/homebrew/bin/SwitchAudioSource',
                'device_priorities': {
                    'airpods': 95,
                    'beats': 90,
                    'bluetooth_headphones': 85,
                    'usb_headphones': 80,
                    'speakers': 70,
                    'microphone': 60,
                    'virtual': 1
                },
                'virtual_device_keywords': ['blackhole', 'loopback', 'virtual'],
                'exclude_virtual_devices': True
            }
            
            # Инициализируем и используем глобальный экземпляр UnifiedAudioSystem
            from unified_audio_system import initialize_global_unified_audio_system
            self.audio_manager = initialize_global_unified_audio_system(config)
            
            # Добавляем callback для уведомлений об изменениях устройств
            self.audio_manager.add_callback(self._on_device_change_callback)
            
            logger.info("✅ UnifiedAudioSystem инициализирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации UnifiedAudioSystem: {e}")
            self.audio_manager = None
    
    def _get_audio_manager_devices(self):
        """Получает актуальный список устройств из UnifiedAudioSystem"""
        if not self.audio_manager:
            return None, None, None

        try:
            # ИСПРАВЛЕНИЕ: Добавляем задержку для синхронизации с UnifiedAudioSystem
            time.sleep(0.3)  # 300ms для синхронизации

            # Получаем актуальный список устройств из UnifiedAudioSystem
            all_devices = self.audio_manager.get_available_devices()
            current_device = self.audio_manager.get_current_device()

            # Получаем информацию о текущем устройстве
            current_device_info = self.audio_manager.get_current_device_info()

            logger.info(f"🔄 Получен актуальный список из UnifiedAudioSystem: {len(all_devices)} устройств")
            logger.info(f"🎧 Текущее устройство: {current_device}")

            return all_devices, current_device, current_device_info

        except Exception as e:
            logger.error(f"❌ Ошибка получения устройств из UnifiedAudioSystem: {e}")
            return None, None, None

    def _on_device_change_callback(self, event_type: str, device_info: dict):
        """Callback для обработки изменений устройств от UnifiedAudioSystem"""
        try:
            logger.info(f"🔔 Получено событие от UnifiedAudioSystem: {event_type}")
            logger.info(f"   Устройство: {device_info.get('name', 'Unknown')}")
            logger.info(f"   Тип: {device_info.get('type', 'Unknown')}")
            logger.info(f"   Приоритет: {device_info.get('priority', 0)}")
            
            # ИСПРАВЛЕНИЕ: Принудительно обновляем список устройств при любом изменении
            logger.info("🔄 Принудительное обновление списка устройств после события...")
            self.force_device_refresh()
            
            # Инвалидируем кэш при изменении устройств
            self._invalidate_stream_cache()
            
            # Уведомляем STT об изменении устройств
            self.notify_device_changed()
            
            if event_type == 'device_added':
                # Если добавили высокоприоритетные наушники - переключаемся
                if device_info.get('priority', 0) >= 85:
                    logger.info("🎧 Обнаружены высокоприоритетные наушники - переключаемся автоматически")
                    # AudioManagerDaemon уже переключился, просто обновляем информацию
                    self._update_current_device_info()
            
            elif event_type == 'device_removed':
                # Если удалили текущее устройство - обновляем информацию
                current_device = self.audio_manager.get_current_device() if self.audio_manager else None
                if not current_device:
                    logger.info("🔄 Текущее устройство удалено - обновляем информацию")
                    self._update_current_device_info()
            
        except Exception as e:
            logger.error(f"❌ Ошибка в callback AudioManagerDaemon: {e}")

    def _update_current_device_info(self):
        """Обновляет информацию о текущем устройстве (thread-safe)"""
        try:
            if self.audio_manager:
                current_device = self.audio_manager.get_current_device()
                if current_device:
                    device_info = self.audio_manager.get_device_info(current_device)
                    with self._device_info_lock:
                        self.current_device_info = {
                            'name': device_info.name,
                            'type': device_info.device_type.value,
                            'priority': device_info.priority,
                            'is_headphones': device_info.device_type.value in ['airpods', 'beats', 'bluetooth_headphones', 'usb_headphones'],
                            'timestamp': time.time()
                        }
                    logger.info(f"📱 Обновлена информация об устройстве: {current_device}")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления информации об устройстве: {e}")
    
    def get_device_name_safe(self) -> str:
        """Безопасно получает имя текущего устройства (thread-safe)"""
        with self._device_info_lock:
            if self.current_device_info and 'name' in self.current_device_info:
                return self.current_device_info['name']
            return "Unknown"
    
    def get_device_index_safe(self) -> Optional[int]:
        """Безопасно получает индекс текущего устройства (thread-safe)"""
        with self._device_info_lock:
            if self.current_device_info and 'index' in self.current_device_info:
                return self.current_device_info['index']
            return None
    
    def is_current_device_headphones(self) -> bool:
        """Проверяет, является ли текущее устройство наушниками (thread-safe)"""
        with self._device_info_lock:
            if not self.current_device_info:
                return False
            device_name = self.current_device_info.get('name', '')
            return is_headphones(device_name)

    def start_device_monitoring(self):
        """Запускает улучшенный мониторинг изменений аудио устройств."""
        if self.audio_manager and self.audio_manager.running:
            logger.info("🔄 Мониторинг устройств уже запущен через AudioManagerDaemon")
            return
        
        logger.info("🔄 Запускаю улучшенный мониторинг аудио устройств...")
        
        # Мониторинг теперь управляется через AudioManagerDaemon
        if self.audio_manager:
            logger.info("✅ Мониторинг аудио устройств через AudioManagerDaemon активен")
        else:
            logger.warning("⚠️ AudioManagerDaemon недоступен, используем базовый мониторинг")

    def stop_device_monitoring(self):
        """Останавливает мониторинг аудио устройств."""
        if self.audio_manager:
            if hasattr(self.audio_manager, 'running') and self.audio_manager.running:
                logger.info("🔄 Остановка мониторинга через AudioManagerDaemon...")
                if hasattr(self.audio_manager, 'stop'):
                    self.audio_manager.stop()
                else:
                    logger.warning("⚠️ AudioManagerDaemon не имеет метода stop")
            else:
                logger.info("🔄 Мониторинг устройств не активен")
        else:
            logger.info("🔄 AudioManagerDaemon не инициализирован")
        
        logger.info("✅ Мониторинг аудио устройств остановлен")

    def _on_device_change_enhanced(self, old_device, new_device, source):
        """Улучшенный callback для обработки изменений аудио устройств."""
        try:
            logger.info(f"🔔 Получено событие изменения аудио устройства (источник: {source})!")
            logger.info(f"   Старое устройство: {old_device}")
            logger.info(f"   Новое устройство: {new_device}")
            
            # Определяем, является ли новое устройство наушниками
            if new_device and is_headphones(new_device['name']):
                logger.info(f"🎧 Обнаружены наушники: {new_device['name']}")
                self._handle_headphones_connection(new_device)
            elif old_device and is_headphones(old_device['name']):
                logger.info(f"🎧 Наушники отключены: {old_device['name']}")
                self._handle_headphones_disconnection()
            else:
                # Обычное переключение устройства
                self._handle_device_change()
                
        except Exception as e:
            logger.error(f"❌ Ошибка в улучшенном callback изменения устройств: {e}")

    def _on_device_change(self, added_devices, removed_devices):
        """Callback для обработки изменений аудио устройств (старая версия)."""
        try:
            logger.info("🔔 Получено событие изменения аудио устройств!")
            logger.info(f"   Добавлены: {added_devices}")
            logger.info(f"   Удалены: {removed_devices}")
            
            # Обрабатываем добавленные устройства
            for device_name in added_devices:
                if is_headphones(device_name):
                    logger.info(f"🎧 Обнаружены наушники: {device_name}")
                    # Находим устройство по имени и вызываем основной метод
                    devices = self.list_available_devices()
                    for device in devices:
                        if device['name'] == device_name and device['is_headphones']:
                            self._handle_headphones_connection(device)
                            break
                    return  # Выходим, так как уже обработали
            
            # Обрабатываем удаленные устройства
            for device_name in removed_devices:
                if is_headphones(device_name):
                    logger.info(f"🎧 Наушники отключены: {device_name}")
                    self._handle_headphones_disconnection()
                    return  # Выходим, так как уже обработали
            
            # Дополнительная проверка отключения наушников
            if self._was_headphones_disconnected():
                logger.info("🎧 Обнаружено отключение наушников через дополнительную проверку")
                self._handle_headphones_disconnection()
                return  # Выходим, так как уже обработали
            
        except Exception as e:
            logger.error(f"❌ Ошибка в callback изменения устройств: {e}")









    def _handle_device_change(self):
        """Обрабатывает изменение аудио устройства."""
        try:
            logger.info("🔄 Обрабатываю изменение аудио устройства...")
            
            # Проверяем, не слишком ли часто переключаемся
            current_time = time.time()
            if hasattr(self, '_last_device_switch') and current_time - self._last_device_switch < self.device_switch_threshold:
                logger.info("⏱️ Слишком частое переключение, пропускаю")
                return
            
            self._last_device_switch = current_time
            
            # Обновляем информацию об устройстве
            self._update_current_device_info()
            
            # Получаем информацию о новом устройстве
            new_device_info = self.get_current_device_info()
            
            # Проверяем, нужно ли автоматически переключиться на наушники
            if self.auto_switch_to_headphones:
                if self._should_auto_switch_to_headphones(new_device_info):
                    self._handle_headphones_connection(new_device_info)
                    return  # Выходим, так как уже обработали
                elif self._was_headphones_disconnected():
                    self._handle_headphones_disconnection()
                    return  # Выходим, так как уже обработали
            
            # Обычная обработка изменения устройства
            if self.is_playing and self.stream and self.stream.active:
                logger.info("🔄 Перезапускаю аудио поток для нового устройства...")
                
                # Обновляем информацию об устройстве перед перезапуском
                self._update_current_device_info()
                
                # Сохраняем текущее состояние
                was_playing = self.is_playing
                current_queue_size = self.audio_queue.qsize()
                
                # Останавливаем текущий поток
                self._safe_stop_stream()
                
                # Небольшая пауза для стабилизации
                time.sleep(0.2)
                
                # Перезапускаем с новыми параметрами
                self._restart_stream_with_new_device()
                
                # Безопасно получаем имя устройства
                device_name = self.get_device_name_safe()
                logger.info(f"✅ Поток перезапущен для устройства: {device_name}")
                
                # Восстанавливаем воспроизведение если было активно
                if was_playing and current_queue_size > 0:
                    logger.info("🔄 Восстанавливаю воспроизведение...")
                    self._set_playing_state(True, "восстановление после перезапуска потока")
                
            else:
                logger.info("📱 Устройство изменилось, но воспроизведение не активно")
                # Обновляем информацию об устройстве даже если воспроизведение не активно
                self._update_current_device_info()
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке изменения устройства: {e}")

    def _safe_stop_stream(self):
        """Безопасно останавливает аудио поток."""
        try:
            if self.stream and hasattr(self.stream, 'active') and self.stream.active:
                self.stream.stop()
                logger.info("✅ Аудио поток остановлен")
            
            if self.stream:
                self.stream.close()
                self.stream = None
                logger.info("✅ Аудио поток закрыт")
                
        except (OSError, IOError) as e:
            logger.warning(f"⚠️ Ошибка ввода-вывода при остановке потока: {e}")
        except AttributeError as e:
            logger.warning(f"⚠️ Ошибка атрибута при остановке потока: {e}")
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при остановке потока: {e}")
            # НЕ прерываем работу - только логируем

    def _restart_stream_with_new_device(self):
        """Перезапускает аудио поток с параметрами нового устройства."""
        try:
            logger.info("🔄 Перезапуск потока с новыми параметрами...")
            
            # Получаем адаптивные параметры для нового устройства
            devices = sd.query_devices()
            
            # Безопасно получаем текущее устройство вывода
            try:
                default_device = sd.default.device
                if isinstance(default_device, (list, tuple)):
                    current_output = default_device[1]  # output device
                else:
                    current_output = default_device
                
                # Проверяем корректность индекса и наличие устройств
                if not devices or not isinstance(current_output, int) or current_output == -1 or current_output >= len(devices):
                    logger.warning("⚠️ Не удалось определить текущее устройство")
                    return
                    
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения устройства по умолчанию: {e}")
                return
            
            device_info = devices[current_output]
            configs = self._get_adaptive_configs(devices, current_output)
            
            logger.info(f"🎯 Адаптивные параметры для нового устройства: {len(configs)} конфигураций")
            
            # Пробуем инициализировать с новыми параметрами
            for i, config in enumerate(configs):
                try:
                    logger.info(f"🔄 Попытка {i+1}: ch={config['channels']}, sr={config['samplerate']}")
                    
                    with self.stream_lock:
                        stream = sd.OutputStream(
                            device=None,  # Автоматический выбор
                            callback=self._playback_callback,
                            **config
                        )
                        self._safe_start_stream(stream, timeout=2.0)
                    
                    # Обновляем параметры
                    self.channels = config['channels']
                    self.sample_rate = config['samplerate']
                    self.dtype = config['dtype']
                    self.stream = stream
                    
                    logger.info(f"✅ Поток перезапущен: ch={config['channels']}, sr={config['samplerate']}")
                    return
                    
                except Exception as e:
                    logger.warning(f"⚠️ Попытка {i+1} не удалась: {e}")
                    if i < len(configs) - 1:
                        time.sleep(0.1)
            
            logger.error("❌ Не удалось перезапустить поток с новыми параметрами")
            
        except (OSError, IOError) as e:
            logger.error(f"❌ Ошибка ввода-вывода при перезапуске потока: {e}")
        except AttributeError as e:
            logger.error(f"❌ Ошибка атрибута при перезапуске потока: {e}")
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при перезапуске потока: {e}")

    def get_current_device_info(self):
        """Возвращает информацию о текущем аудио устройстве (использует кэшированную информацию)."""
        # Сначала обновляем информацию, если она устарела
        self._update_current_device_info()
        
        # Возвращаем кэшированную информацию
        with self._device_info_lock:
            return self.current_device_info.copy() if self.current_device_info else None

    def force_device_refresh(self):
        """Принудительно обновляет информацию об устройствах и перезапускает поток."""
        logger.info("🔄 Принудительное обновление аудио устройств...")
        
        try:
            # Информация об устройствах обновляется через систему событий
            
            # Если воспроизведение активно, перезапускаем
            if self.is_playing and self.stream and self.stream.active:
                self._handle_device_change()
            
            logger.info("✅ Обновление аудио устройств завершено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении устройств: {e}")

    def switch_to_device(self, device_name=None, device_index=None):
        """
        Принудительно переключается на указанное устройство.
        
        Args:
            device_name: Имя устройства (например, 'MacBook Air Speakers')
            device_index: Индекс устройства в системе
        """
        try:
            logger.info(f"🔄 [AudioPlayer] Переключение на устройство: {device_name or device_index}")
            
            # Сначала пробуем использовать централизованный AudioDeviceManager
            from audio_device_manager import get_global_audio_device_manager
            audio_manager = get_global_audio_device_manager()
            if audio_manager and device_name:
                logger.info("🎛️ [AudioPlayer] Используем централизованный AudioDeviceManager")
                success = audio_manager.switch_to_device(device_name)
                if success:
                    # Обновляем информацию об устройстве
                    self._update_current_device_info()
                    logger.info("✅ [AudioPlayer] Переключение через AudioDeviceManager успешно")
                    return True
                else:
                    logger.warning("⚠️ [AudioPlayer] AudioDeviceManager не смог переключиться, используем fallback")
            
            # Fallback на старый метод если AudioDeviceManager недоступен или не сработал
            logger.info("🔄 [AudioPlayer] Используем fallback метод переключения")
            
            devices = sd.query_devices()
            
            # Находим устройство
            target_device = None
            if device_name:
                for i, dev in enumerate(devices):
                    if device_name.lower() in dev.get('name', '').lower():
                        target_device = i
                        break
            elif device_index is not None:
                if 0 <= device_index < len(devices):
                    target_device = device_index
            
            if target_device is None or target_device >= len(devices):
                logger.warning(f"⚠️ [AudioPlayer] Устройство не найдено: {device_name or device_index}")
                return False
            
            device_info = devices[target_device]
            logger.info(f"📱 [AudioPlayer] Fallback переключение на: {device_info.get('name', 'Unknown')} (индекс: {target_device})")
            
            # Если воспроизведение активно, перезапускаем поток
            if self.is_playing and self.stream and self.stream.active:
                # Сохраняем текущее состояние
                was_playing = self.is_playing
                current_queue_size = self.audio_queue.qsize()
                
                # Останавливаем текущий поток
                self._safe_stop_stream()
                
                # Небольшая пауза для стабилизации
                time.sleep(0.2)
                
                # Перезапускаем с новым устройством
                self._restart_stream_with_specific_device(target_device)
                
                # Восстанавливаем воспроизведение если было активно
                if was_playing and current_queue_size > 0:
                    logger.info("🔄 [AudioPlayer] Восстанавливаю воспроизведение...")
                    self._set_playing_state(True, "восстановление после переключения устройства")
                
                logger.info(f"✅ [AudioPlayer] Переключение на {device_info.get('name', 'Unknown')} завершено")
                # Обновляем информацию об устройстве после успешного переключения
                self._update_current_device_info()
                return True
            else:
                logger.info("📱 [AudioPlayer] Воспроизведение не активно, обновляю информацию об устройстве")
                with self._device_info_lock:
                    self.current_device_info = {
                        'index': target_device,
                        'name': device_info.get('name', 'Unknown'),
                        'max_channels': device_info.get('max_output_channels', 0),
                        'default_samplerate': device_info.get('default_samplerate', 0),
                        'max_samplerate': device_info.get('max_samplerate', 0),
                        'timestamp': time.time()
                    }
                return True
            
        except Exception as e:
            logger.error(f"❌ [AudioPlayer] Ошибка при переключении устройства: {e}")
            return False

    def _restart_stream_with_specific_device(self, device_index):
        """Перезапускает аудио поток с указанным устройством."""
        try:
            logger.info(f"🔄 Перезапуск потока с устройством {device_index}...")
            
            devices = sd.query_devices()
            if not devices or device_index >= len(devices):
                logger.warning("⚠️ Некорректный индекс устройства или нет доступных устройств")
                return
            
            device_info = devices[device_index]
            configs = self._get_adaptive_configs(devices, device_index)
            
            logger.info(f"🎯 Адаптивные параметры для устройства {device_index}: {len(configs)} конфигураций")
            
            # Пробуем инициализировать с новыми параметрами
            for i, config in enumerate(configs):
                try:
                    logger.info(f"🔄 Попытка {i+1}: device={device_index}, ch={config['channels']}, sr={config['samplerate']}")
                    
                    with self.stream_lock:
                        stream = sd.OutputStream(
                            device=device_index,  # Конкретное устройство
                            callback=self._playback_callback,
                            **config
                        )
                        self._safe_start_stream(stream, timeout=2.0)
                    
                    # Обновляем параметры
                    self.channels = config['channels']
                    self.sample_rate = config['samplerate']
                    self.dtype = config['dtype']
                    self.stream = stream
                    
                    # Обновляем информацию об устройстве
                    self.current_device_info = {
                        'index': device_index,
                        'name': device_info.get('name', 'Unknown'),
                        'max_channels': config['channels'],
                        'default_samplerate': config['samplerate'],
                        'max_samplerate': device_info.get('max_samplerate', 0),
                        'timestamp': time.time()
                    }
                    
                    logger.info(f"✅ Поток перезапущен: {device_info.get('name', 'Unknown')} (ch={config['channels']}, sr={config['samplerate']})")
                    return
                    
                except Exception as e:
                    logger.warning(f"⚠️ Попытка {i+1} не удалась: {e}")
                    if i < len(configs) - 1:
                        time.sleep(0.1)
            
            logger.error("❌ Не удалось перезапустить поток с указанным устройством")
            
        except (OSError, IOError) as e:
            logger.error(f"❌ Ошибка ввода-вывода при перезапуске потока: {e}")
        except AttributeError as e:
            logger.error(f"❌ Ошибка атрибута при перезапуске потока: {e}")
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при перезапуске потока: {e}")

    def list_available_devices(self):
        """Возвращает список доступных аудио устройств."""
        try:
            devices = sd.query_devices()
            available_devices = []
            
            # Безопасно получаем текущее устройство по умолчанию
            try:
                default_device = sd.default.device
                if isinstance(default_device, (list, tuple)):
                    current_default = default_device[1]  # output device
                else:
                    current_default = default_device
            except Exception:
                current_default = -1
            
            for i, dev in enumerate(devices):
                if dev.get('max_output_channels', 0) > 0:  # Только устройства вывода
                    device_info = {
                        'index': i,
                        'name': dev.get('name', 'Unknown'),
                        'max_channels': dev.get('max_output_channels', 0),
                        'default_samplerate': dev.get('default_samplerate', 0),
                        'max_samplerate': dev.get('max_samplerate', 0),
                        'is_default': i == current_default,
                        'is_headphones': is_headphones(dev.get('name', '')),
                        'priority': self._get_device_priority(dev)
                    }
                    available_devices.append(device_info)
            
            return available_devices
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения списка устройств: {e}")
            return []




    def _playback_callback(self, outdata, frames, time, status):
        """Callback-функция для sounddevice, вызывается для заполнения буфера вывода."""
        if status:
            logger.warning(f"🎵 [CALLBACK] Sounddevice status: {status}")

        try:
            with self.buffer_lock:
                logger.debug(f"🎵 [CALLBACK] Запрос {frames} сэмплов, буфер={len(self.internal_buffer)}, очередь={self.audio_queue.qsize()}")
                
                # Проверяем внутренний буфер
                if len(self.internal_buffer) >= frames:
                    # Достаточно данных в буфере (моно → дублируем по каналам при необходимости)
                    mono_samples = self.internal_buffer[:frames]
                    if outdata.dtype.kind == 'f':
                        # float32/-64 ожидает значения [-1.0, 1.0]
                        fs = mono_samples.astype(np.float32) / 32768.0
                        if self.channels == 1:
                            outdata[:frames, 0] = fs
                        else:
                            # Стерео: дублируем моно сигнал на оба канала
                            for ch in range(self.channels):
                                outdata[:frames, ch] = fs
                    else:
                        if self.channels == 1:
                            outdata[:frames, 0] = mono_samples
                        else:
                            # Стерео: дублируем моно сигнал на оба канала
                            for ch in range(self.channels):
                                outdata[:frames, ch] = mono_samples
                    self.internal_buffer = self.internal_buffer[frames:]
                    logger.debug(f"🎵 [CALLBACK] Воспроизведено {frames} сэмплов, осталось в буфере: {len(self.internal_buffer)}")
                else:
                    # Недостаточно данных, пытаемся получить из очереди
                    try:
                        # Собираем ВСЕ доступные чанки в буфер (эффективно)
                        chunks_to_add = []
                        while not self.audio_queue.empty():
                            chunk = self.audio_queue.get_nowait()
                            if chunk is not None and len(chunk) > 0:
                                chunks_to_add.append(chunk)
                            self.audio_queue.task_done()
                        
                        if chunks_to_add:
                            # Эффективная конкатенация всех чанков сразу
                            self.internal_buffer = np.concatenate([self.internal_buffer] + chunks_to_add)
                            logger.debug(f"🎵 [CALLBACK] Добавлено {len(chunks_to_add)} чанков в буфер. Общий размер буфера: {len(self.internal_buffer)}")
                    except queue.Empty:
                        pass
                    
                    # Теперь проверяем снова
                    if len(self.internal_buffer) >= frames:
                        mono_samples = self.internal_buffer[:frames]
                        if outdata.dtype.kind == 'f':
                            fs = mono_samples.astype(np.float32) / 32768.0
                            if self.channels == 1:
                                outdata[:frames, 0] = fs
                            else:
                                for ch in range(self.channels):
                                    outdata[:frames, ch] = fs
                        else:
                            if self.channels == 1:
                                outdata[:frames, 0] = mono_samples
                            else:
                                for ch in range(self.channels):
                                    outdata[:frames, ch] = mono_samples
                        self.internal_buffer = self.internal_buffer[frames:]
                        logger.debug(f"🎵 [CALLBACK] Отправлено в аудио: {frames} сэмплов. Осталось в буфере: {len(self.internal_buffer)}")
                    else:
                        # Все еще недостаточно данных, заполняем тишиной
                        available = len(self.internal_buffer)
                        if available > 0:
                            # Пишем доступные сэмплы и дополняем тишиной
                            mono_samples = self.internal_buffer
                            if outdata.dtype.kind == 'f':
                                fs = mono_samples.astype(np.float32) / 32768.0
                                if self.channels == 1:
                                    outdata[:available, 0] = fs
                                    outdata[available:frames, 0] = 0.0
                                else:
                                    for ch in range(self.channels):
                                        outdata[:available, ch] = fs
                                    outdata[available:frames, :] = 0.0
                            else:
                                if self.channels == 1:
                                    outdata[:available, 0] = mono_samples
                                    outdata[available:frames, 0] = 0
                                else:
                                    for ch in range(self.channels):
                                        outdata[:available, ch] = mono_samples
                                    outdata[available:frames, :] = 0
                            self.internal_buffer = np.array([], dtype=np.int16)
                            logger.debug(f"🎵 [CALLBACK] Отправлено доступных: {available} сэмплов, остальное тишина")
                        else:
                            # Если нет данных, принудительно проверяем очередь еще раз
                            try:
                                chunk = self.audio_queue.get_nowait()
                                if chunk is not None and len(chunk) > 0:
                                    # Обрабатываем полученный чанк
                                    if len(chunk) >= frames:
                                        mono_samples = chunk[:frames]
                                        if outdata.dtype.kind == 'f':
                                            fs = mono_samples.astype(np.float32) / 32768.0
                                            if self.channels == 1:
                                                outdata[:frames, 0] = fs
                                            else:
                                                for ch in range(self.channels):
                                                    outdata[:frames, ch] = fs
                                        else:
                                            if self.channels == 1:
                                                outdata[:frames, 0] = mono_samples
                                            else:
                                                for ch in range(self.channels):
                                                    outdata[:frames, ch] = mono_samples
                                        # Остаток чанка сохраняем в буфер
                                        if len(chunk) > frames:
                                            self.internal_buffer = chunk[frames:]
                                        logger.debug(f"🎵 [CALLBACK] Чанк обработан напрямую: {frames} сэмплов")
                                    else:
                                        # Чанк меньше frames, заполняем тишиной
                                        c = len(chunk)
                                        if outdata.dtype.kind == 'f':
                                            fs = chunk.astype(np.float32) / 32768.0
                                            if self.channels == 1:
                                                outdata[:c, 0] = fs
                                                outdata[c:frames, 0] = 0.0
                                            else:
                                                for ch in range(self.channels):
                                                    outdata[:c, ch] = fs
                                                outdata[c:frames, :] = 0.0
                                        else:
                                            if self.channels == 1:
                                                outdata[:c, 0] = chunk
                                                outdata[c:frames, 0] = 0
                                            else:
                                                for ch in range(self.channels):
                                                    outdata[:c, ch] = chunk
                                                outdata[c:frames, :] = 0
                                        logger.debug(f"🎵 [CALLBACK] Короткий чанк: {len(chunk)} сэмплов, остальное тишина")
                                else:
                                    # Нет данных, тишина
                                    outdata.fill(0)
                                    logger.debug("🔇 [CALLBACK] Нет данных - тишина")
                                    
                                    # Проверяем, завершилось ли воспроизведение
                                    if (self.audio_queue.empty() and 
                                        len(self.internal_buffer) == 0 and
                                        not self.stop_event.is_set()):
                                        # ИСПРАВЛЕНИЕ: Убираем избыточное логирование и преждевременный сброс is_playing
                                        # logger.info("🎵 [CALLBACK] Воспроизведение естественно завершено - нет данных")
                                        # self.is_playing = False  # ← УБРАНО: Callback не должен управлять состоянием
                                        pass
                                        
                                self.audio_queue.task_done()
                            except queue.Empty:
                                # Очередь пуста, тишина
                                outdata.fill(0)
                                logger.debug("🔇 [CALLBACK] Очередь пуста - тишина")
                                
                                # Проверяем, завершилось ли воспроизведение
                                if (len(self.internal_buffer) == 0 and
                                    not self.stop_event.is_set()):
                                    # ИСПРАВЛЕНИЕ: Убираем избыточное логирование и преждевременный сброс is_playing
                                    # logger.info("🎵 [CALLBACK] Воспроизведение естественно завершено - очередь пуста")
                                    # self.is_playing = False  # ← УБРАНО: Callback не должен управлять состоянием
                                    pass
        except Exception as e:
            logger.error(f"❌ [CALLBACK] Ошибка в playback callback: {e}")
            outdata.fill(0)  # В случае ошибки отправляем тишину

    def add_chunk(self, audio_chunk: np.ndarray):
        """Добавляет аудио чанк в очередь воспроизведения."""
        logger.info(f"🎵 [AUDIO_PLAYER] add_chunk() вызван - размер чанка: {len(audio_chunk) if audio_chunk is not None else 'None'}")
        
        if getattr(self, '_is_shutting_down', False):
            logger.debug("🔒 [AUDIO_PLAYER] Shutdown в процессе — add_chunk пропущен")
            return
        if audio_chunk is None or len(audio_chunk) == 0:
            logger.warning("⚠️ [AUDIO_PLAYER] Попытка добавить пустой аудио чанк!")
            return
        
        # 🔍 ОТЛАДКА: Анализируем входящие аудио данные
        logger.info(f"🔍 [AUDIO_PLAYER] Входящий аудио чанк: shape={audio_chunk.shape}, dtype={audio_chunk.dtype}, min={audio_chunk.min()}, max={audio_chunk.max()}, mean={audio_chunk.mean():.2f}")
        logger.info(f"🔊 [AUDIO_PLAYER] Текущие настройки плеера: channels={self.channels}, sample_rate={self.sample_rate}")
        logger.info(f"🎵 [AUDIO_PLAYER] Состояние плеера: is_playing={self.is_playing}, очередь={self.audio_queue.qsize()}")
        
        # Нормализуем вход к формату int16 mono
        try:
            if isinstance(audio_chunk, np.ndarray):
                # Если стерео/многоканально → моно
                if audio_chunk.ndim == 2 and audio_chunk.shape[1] > 1:
                    try:
                        audio_chunk = np.mean(audio_chunk, axis=1)
                    except Exception:
                        audio_chunk = audio_chunk[:, 0]
                elif audio_chunk.ndim > 1:
                    audio_chunk = audio_chunk.reshape(-1)

                # Приводим к int16
                if audio_chunk.dtype.kind == 'f':
                    # Ожидаем диапазон [-1.0, 1.0]
                    audio_chunk = np.clip(audio_chunk, -1.0, 1.0)
                    audio_chunk = (audio_chunk * 32767.0).astype(np.int16)
                elif audio_chunk.dtype != np.int16:
                    # Консервативно приводим к int16 без масштабирования
                    try:
                        audio_chunk = np.clip(audio_chunk, -32768, 32767).astype(np.int16)
                    except Exception:
                        audio_chunk = audio_chunk.astype(np.int16, copy=False)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось нормализовать аудио чанк, продолжаю как есть: {e}")
        
        # Автостарт воспроизведения при первом чанке с защитой от множественных запусков
        try:
            # УМНАЯ проверка автостарта - только если действительно не играет и не запускается
            if not self.is_playing and not getattr(self, '_is_starting', False):
                logger.info("🎵 [AUDIO_PLAYER] Автостарт воспроизведения перед добавлением первого чанка")
                self._is_starting = True  # Защита от множественных запусков
                try:
                    logger.info("🎵 [AUDIO_PLAYER] Вызываю start_playback()...")
                    self.start_playback()
                    logger.info("🎵 [AUDIO_PLAYER] start_playback() завершен")
                finally:
                    self._is_starting = False
            elif self.is_playing:
                logger.debug("🎵 [AUDIO_PLAYER] Плеер уже активен, добавляю чанк")
            elif getattr(self, '_is_starting', False):
                logger.debug("🎵 [AUDIO_PLAYER] Плеер уже запускается, добавляю чанк в очередь")
        except Exception as e:
            logger.warning(f"⚠️ [AUDIO_PLAYER] Ошибка автостарта воспроизведения: {e}")
            # Сбрасываем флаг в случае ошибки
            self._is_starting = False

        chunk_size = len(audio_chunk)
        logger.debug(f"🎵 Добавляю аудио чанк размером {chunk_size} сэмплов")
        

        
        try:
            # Добавляем чанк в очередь
            logger.info(f"🎵 [AUDIO_PLAYER] Добавляю чанк в очередь (размер: {chunk_size} сэмплов)")
            self.audio_queue.put(audio_chunk)
            logger.info(f"✅ [AUDIO_PLAYER] Аудио чанк добавлен в очередь. Размер очереди: {self.audio_queue.qsize()}")
        except Exception as e:
            logger.error(f"❌ [AUDIO_PLAYER] Ошибка при добавлении аудио чанка: {e}")
            # Попытка восстановления
            try:
                if not self.audio_queue.full():
                    self.audio_queue.put(audio_chunk)
                    logger.info("✅ [AUDIO_PLAYER] Аудио чанк добавлен после восстановления")
                else:
                    logger.warning("⚠️ [AUDIO_PLAYER] Очередь переполнена, чанк отброшен")
            except Exception as e2:
                logger.error(f"❌ [AUDIO_PLAYER] Критическая ошибка при восстановлении: {e2}")

    def start_playback(self):
        """Запускает потоковое воспроизведение аудио с оптимизацией кэширования."""
        logger.info(f"🎵 [AUDIO_PLAYER] start_playback() вызван - is_playing={self.is_playing}, shutdown={getattr(self, '_is_shutting_down', False)}")
        
        if getattr(self, '_is_shutting_down', False):
            logger.info("🔒 [AUDIO_PLAYER] Shutdown в процессе — start_playback пропущен")
            return
        if self.is_playing:
            logger.debug("🎵 [AUDIO_PLAYER] Воспроизведение уже активно, пропускаю запуск")
            return
        
        logger.info("🎵 [AUDIO_PLAYER] Запуск потокового воспроизведения аудио...")
        self.stop_event.clear()
        self._clear_buffers()  # Очищаем буферы перед началом
        logger.info("🎵 [AUDIO_PLAYER] Буферы очищены")
        
        try:
            # Проверяем кэш для быстрого перезапуска
            cached_config, cached_device_info = self._get_cached_stream_config()
            
            if cached_config:
                logger.info("⚡ Использую закэшированную конфигурацию для быстрого запуска")
                try:
                    # Быстрая инициализация с кэшированными параметрами
                    logger.info("🎵 [AUDIO_PLAYER] Создаю поток воспроизведения с кэшированной конфигурацией...")
                    self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
                    self.playback_thread.start()
                    logger.info("🎵 [AUDIO_PLAYER] Поток воспроизведения запущен")
                    
                    # Создаем поток с кэшированными параметрами
                    with self.stream_lock:
                        logger.info("🎵 [AUDIO_PLAYER] Создаю sounddevice поток...")
                        self.stream = sd.OutputStream(
                            device=None,  # Автоматический выбор
                            callback=self._playback_callback,
                            **cached_config
                        )
                        # ВАЖНО: Запускаем поток с таймаутом!
                        logger.info("🎵 [AUDIO_PLAYER] Запускаю sounddevice поток...")
                        self._safe_start_stream(self.stream, timeout=2.0)
                    
                    self._set_playing_state(True, "запуск с кэшированной конфигурацией")
                    logger.info("⚡ [AUDIO_PLAYER] Потоковое воспроизведение запущено с кэшированной конфигурацией!")
                    return
                    
                except Exception as cache_e:
                    logger.warning(f"⚠️ Ошибка с кэшированной конфигурацией: {cache_e}")
                    logger.info("🔄 Переключаюсь на полную инициализацию...")
                    self._invalidate_stream_cache()
            
            # Предочистка для избежания гонок CoreAudio/BT
            try:
                if getattr(self, 'preflush_on_switch', True):
                    if self.stream and hasattr(self.stream, 'active') and self.stream.active:
                        self.stream.stop()
                        self.stream.close()
                        self.stream = None
                    sd.stop()
                    time.sleep(max(0.05, getattr(self, 'settle_ms', 400)/1000.0))
            except Exception:
                pass

            # Создаем новый поток воспроизведения
            logger.info("🎵 [AUDIO_PLAYER] Создаю новый поток воспроизведения...")
            self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.playback_thread.start()
            logger.info("🎵 [AUDIO_PLAYER] Новый поток воспроизведения запущен")
            
            # Полная инициализация с кэшированием результата
            logger.info("🔊 [AUDIO_PLAYER] Запуск в автоматическом режиме: macOS управляет устройствами")
            self.stream = self._safe_init_stream()
            logger.info("🎵 [AUDIO_PLAYER] sounddevice поток инициализирован")
            self._set_playing_state(True, "запуск воспроизведения")
            logger.info("🎵 [AUDIO_PLAYER] is_playing установлен в True")
            
            # Кэшируем успешную конфигурацию для следующего запуска
            if self.stream and hasattr(self.stream, 'channels') and hasattr(self.stream, 'samplerate'):
                config = {
                    'channels': self.stream.channels,
                    'samplerate': self.stream.samplerate,
                    'dtype': np.int16
                }
                self._cache_stream_config(config, self.current_device_info)
            
            logger.info("✅ Потоковое воспроизведение аудио запущено!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске воспроизведения: {e}")
            self._set_playing_state(False, "ошибка при запуске")
            self.playback_thread = None
            self.stream = None

    def stop_playback(self):
        """Останавливает потоковое воспроизведение аудио."""
        if getattr(self, '_is_shutting_down', False):
            logger.info("🔒 Shutdown уже идёт — stop_playback пропущен")
            return
        with self._shutdown_mutex:
            if self._is_shutting_down:
                logger.info("🔒 Shutdown уже идёт — stop_playback пропущен")
                return
            self._is_shutting_down = True
        if not self.is_playing:
            logger.warning("⚠️ Воспроизведение уже остановлено!")
            self._is_shutting_down = False
            return
        
        logger.info("Остановка потокового воспроизведения аудио...")
        
        try:
            # Устанавливаем флаг остановки
            self.stop_event.set()

            # Останавливаем звуковой поток
            if self.stream:
                with self.stream_lock:
                    if self.stream:
                        if hasattr(self.stream, 'active') and self.stream.active:
                            self.stream.stop()
                            logger.info("✅ Звуковой поток остановлен")
                        self.stream.close()
                        self.stream = None
                        logger.info("✅ Звуковой поток закрыт")
            
            # Ждем завершения потока воспроизведения
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=1.0)
                if self.playback_thread.is_alive():
                    logger.warning("⚠️ Поток воспроизведения не завершился за 1 секунду")
                else:
                    logger.info("✅ Поток воспроизведения завершен")
            
            # Сбрасываем состояние
            self._set_playing_state(False, "остановка воспроизведения")
            self.playback_thread = None
            self._is_starting = False  # Сбрасываем флаг запуска
            
            # Очищаем буферы
            self._clear_buffers()
            
            logger.info("✅ Потоковое воспроизведение аудио остановлено!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке воспроизведения: {e}")
            # Принудительно сбрасываем состояние
            self._set_playing_state(False, "ошибка при остановке")
            self.playback_thread = None
            self.stream = None
            self._is_starting = False  # Сбрасываем флаг запуска
        finally:
            self._is_shutting_down = False

    def pause_playback(self):
        """Приостанавливает воспроизведение аудио."""
        try:
            logger.info("⏸️ Приостановка воспроизведения...")
            
            # Останавливаем поток воспроизведения
            self.stop_event.set()
            
            # Ждем завершения потока
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=1.0)
            
            # Останавливаем поток
            self._safe_stop_stream()
            
            self._set_playing_state(False, "приостановка воспроизведения")
            logger.info("✅ Воспроизведение приостановлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при приостановке воспроизведения: {e}")

    def resume_playback(self):
        """Возобновляет воспроизведение аудио."""
        try:
            logger.info("▶️ Возобновление воспроизведения...")
            
            # Сбрасываем флаг остановки
            self.stop_event.clear()
            
            # Сбрасываем флаг завершения
            with self._shutdown_mutex:
                self._is_shutting_down = False
            
            # Запускаем поток воспроизведения
            self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.playback_thread.start()
            
            self._set_playing_state(True, "возобновление воспроизведения")
            logger.info("✅ Воспроизведение возобновлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при возобновлении воспроизведения: {e}")

    def _playback_loop(self):
        """Фоновый поток для воспроизведения аудио с безопасными таймаутами"""
        logger.info("🔄 Фоновый поток воспроизведения запущен")
        
        try:
            # Безопасный таймаут для предотвращения зависания цикла
            loop_timeout = 30.0  # 30 секунд - достаточно для длинных ответов
            start_time = time.time()
            
            while not self.stop_event.is_set():
                # Проверяем таймаут только для предотвращения зависания
                if time.time() - start_time > loop_timeout:
                    logger.warning("⚠️ Длительный цикл playback_loop - перезапуск")
                    # НЕ трогаем is_playing - только перезапускаем цикл
                    start_time = time.time()
                
                try:
                    # В автоматическом режиме система сама управляет — никаких рестартов
                    pass
                except Exception:
                    pass
                
                # Проверяем, есть ли данные для воспроизведения
                queue_empty = self.audio_queue.empty()
                with self.buffer_lock:
                    buffer_empty = len(self.internal_buffer) == 0
                
                if not queue_empty or not buffer_empty:
                    # Есть данные для воспроизведения
                    time.sleep(0.001)  # 1ms
                else:
                    # Нет данных - воспроизведение завершено
                    logger.info("🎵 Естественное завершение воспроизведения - нет данных")
                    self._set_playing_state(False, "естественное завершение - нет данных")
                    break
                    
        except Exception as e:
            logger.error(f"❌ Ошибка в фоновом потоке воспроизведения: {e}")
        finally:
            logger.info("🔄 Фоновый поток воспроизведения завершен")
            # Убеждаемся, что is_playing сброшен при завершении потока
            self._set_playing_state(False, "завершение фонового потока")



    def _safe_init_stream(self, preferred_device=None):
        """
        Простая инициализация аудио потока: пусть macOS сам управляет устройствами.
        Включает проверку доступности устройств и автоматический сброс при зависших устройствах.
        """
        try:
            # ПРИНУДИТЕЛЬНО обновляем список устройств перед инициализацией
            logger.info("🔄 Принудительно обновляю список аудио устройств...")
            try:
                # Останавливаем все потоки для "чистого" состояния
                sd.stop()
                time.sleep(0.1)
                
                # ПРИНУДИТЕЛЬНЫЙ СБРОС CoreAudio при ошибках
                logger.info("🔧 ПРИНУДИТЕЛЬНЫЙ СБРОС CoreAudio для устранения ошибок...")
                try:
                    # Останавливаем все потоки
                    sd.stop()
                    time.sleep(0.3)
                    
                    # Переинициализация CoreAudio
                    try:
                        # Безопасная переинициализация через sounddevice
                        if hasattr(sd, '_coreaudio'):
                            sd._coreaudio.reinitialize()
                            logger.info("✅ CoreAudio переинициализирован через API")
                        else:
                            logger.info("🔄 API недоступен, использую базовый сброс")
                            sd.stop()
                            time.sleep(0.5)
                    except Exception as ca_e:
                        logger.warning(f"⚠️ Ошибка переинициализации CoreAudio: {ca_e}")
                        logger.info("🔄 Использую базовый сброс")
                        sd.stop()
                        time.sleep(0.5)
                    
                    # Дополнительная очистка
                    logger.info("🔧 Дополнительная очистка аудио системы...")
                    sd.stop()
                    time.sleep(0.2)
                    
                    logger.info("✅ CoreAudio сброшен и очищен")
                    
                except Exception as reset_e:
                    logger.warning(f"⚠️ Ошибка сброса CoreAudio: {reset_e}")
                    logger.info("🔄 Продолжаю с базовым обновлением")
                
                # ИНТЕГРАЦИЯ: Используем актуальный список из UnifiedAudioSystem
                all_devices, current_device, current_device_info = self._get_audio_manager_devices()
                
                if all_devices is not None:
                    # Используем данные из UnifiedAudioSystem
                    logger.info(f"📱 Обновленный список устройств: {len(all_devices)} устройств")
                    logger.info(f"🎧 Текущее устройство: {current_device}")
                    
                    # Показываем все устройства из UnifiedAudioSystem
                    for device_info in all_devices:
                        logger.info(f"  📱 {device_info.name} (тип: {device_info.device_type.value}, приоритет: {device_info.priority})")
                    
                    # ИСПРАВЛЕНИЕ: Принудительно обновляем PortAudio перед получением устройств
                    logger.info("🔄 Принудительное обновление PortAudio...")
                    try:
                        sd._terminate()
                        time.sleep(0.2)
                        sd._initialize()
                        logger.info("✅ PortAudio обновлен")
                    except Exception as pa_e:
                        logger.warning(f"⚠️ Не удалось обновить PortAudio: {pa_e}")
                    
                    # Получаем РЕАЛЬНЫЕ PortAudio default устройства
                    devices = sd.query_devices()
                    current_default_out = sd.default.device[1]  # Реальный default output
                    current_default_in = sd.default.device[0]   # Реальный default input
                    
                    logger.info(f"🔊 Текущий default output: {current_default_out}")
                    logger.info(f"🎙️ Текущий default input: {current_default_in}")
                    
                    if current_default_out != -1:
                        default_out_name = devices[current_default_out].get('name', 'Unknown')
                        logger.info(f"🔊 Default output: {current_default_out} — {default_out_name}")
                        
                        # Определяем профиль AirPods
                        if 'airpods' in default_out_name.lower():
                            out_info = devices[current_default_out]
                else:
                    # Fallback к старому методу
                    logger.warning("⚠️ AudioManagerDaemon недоступен, использую fallback")
                    devices = sd.query_devices()
                    current_default_out = sd.default.device[1]  # Реальный default output
                    current_default_in = sd.default.device[0]   # Реальный default input
                    
                    logger.info(f"📱 Обновленный список устройств: {len(devices)} устройств")
                    logger.info(f"🔊 Текущий default output: {current_default_out}")
                    logger.info(f"🎙️ Текущий default input: {current_default_in}")
                    
                    # Показываем ВСЕ устройства (не только output)
                    for i, dev in enumerate(devices):
                        name = dev.get('name', 'Unknown')
                        in_ch = dev.get('max_input_channels', 0)
                        out_ch = dev.get('max_output_channels', 0)
                        if in_ch > 0 or out_ch > 0:
                            logger.info(f"  📱 {i}: {name} (in:{in_ch} out:{out_ch})")
                    
                    # Проверяем, что дефолты корректны
                    if current_default_out != -1 and current_default_out < len(devices):
                        default_out_name = devices[current_default_out].get('name', 'Unknown')
                        logger.info(f"🔊 Default output: {current_default_out} — {default_out_name}")
                        
                        # Определяем профиль AirPods
                        if 'airpods' in default_out_name.lower():
                            out_info = devices[current_default_out]
                            max_channels = out_info.get('max_output_channels', 0)
                            default_sr = out_info.get('default_samplerate', 0)
                            
                            if max_channels <= 1 or default_sr <= 16000:
                                logger.info(f"🎧 AirPods в HFP режиме (гарнитура): ch={max_channels}, sr={default_sr}")
                            else:
                                logger.info(f"🎧 AirPods в A2DP режиме (качество): ch={max_channels}, sr={default_sr}")
                    else:
                        logger.warning(f"⚠️ Некорректный default output: {current_default_out}")
                
                if current_default_in != -1 and current_default_in < len(devices):
                    default_in_name = devices[current_default_in].get('name', 'Unknown')
                    logger.info(f"🎙️ Default input: {current_default_in} — {default_in_name}")
                else:
                    logger.warning(f"⚠️ Некорректный default input: {current_default_in}")
                
            except Exception as e:
                logger.warning(f"⚠️ Не удалось обновить список устройств: {e}")
            
            # Универсальная адаптивная система параметров
            configs = self._get_adaptive_configs(devices, current_default_out)
            
            logger.info(f"🎯 Адаптивные параметры для устройства {current_default_out}: {len(configs)} конфигураций")
            
            # УМНАЯ ИНИЦИАЛИЗАЦИЯ с проверкой совместимости
            for i, config in enumerate(configs):
                try:
                    logger.info(f"🔄 Попытка {i+1}: device=None (автоматический), ch={config['channels']}, sr={config['samplerate']}")
                    
                    # ПРЕДВАРИТЕЛЬНАЯ ПРОВЕРКА СОВМЕСТИМОСТИ
                    if current_default_out != -1 and current_default_out < len(devices):
                        device_info = devices[current_default_out]
                        device_name = device_info.get('name', '').lower()
                        
                        # Проверяем Bluetooth устройства
                        if any(tag in device_name for tag in ['airpods', 'bluetooth', 'wireless']):
                            logger.info(f"🔍 Проверяю совместимость с {device_info.get('name', 'Unknown')}")
                            
                            # Тестируем совместимость
                            if self._test_device_compatibility(current_default_out, config):
                                logger.info(f"✅ Совместимость подтверждена для {config['channels']}ch/{config['samplerate']}Hz")
                            else:
                                logger.warning(f"⚠️ Несовместимость для {config['channels']}ch/{config['samplerate']}Hz")
                                # Пропускаем несовместимые параметры
                                continue
                    
                    # Инициализация потока
                        with self.stream_lock:
                            stream = sd.OutputStream(
                            device=None,  # Пусть macOS сам выбирает
                                callback=self._playback_callback,
                            **config
                            )
                            self._safe_start_stream(stream, timeout=2.0)
                    
                    logger.info(f"✅ Поток инициализирован: автоматический режим, ch={config['channels']}, sr={config['samplerate']}")
                    self.channels = config['channels']
                    self.sample_rate = config['samplerate']
                    self.dtype = config['dtype']
                    
                    # Сохраняем информацию об устройстве для мониторинга
                    self._last_device_info = {
                        'index': current_default_out,
                        'name': devices[current_default_out].get('name', 'Unknown') if current_default_out < len(devices) else 'Unknown',
                        'channels': config['channels'],
                        'samplerate': config['samplerate'],
                        'timestamp': time.time()
                    }
                    
                    logger.info(f"📱 Устройство: {self._last_device_info['name']} (индекс: {current_default_out})")
                    return stream
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"⚠️ Попытка {i+1} не удалась: {error_msg}")
                    
                    # Если это ошибка -10851/-9986, возможно зависшие устройства
                    if any(code in error_msg for code in ['-10851', '-9986', 'Invalid Property Value']):
                        if i == 0:  # Только при первой ошибке
                            logger.warning("🔧 Обнаружены зависшие устройства, пробую сброс CoreAudio...")
                            try:
                                # Останавливаем все аудио потоки
                                sd.stop()
                                time.sleep(0.5)
                                
                                # ПРИНУДИТЕЛЬНЫЙ СБРОС CoreAudio
                                logger.info("🔧 ПРИНУДИТЕЛЬНЫЙ СБРОС CoreAudio...")
                                try:
                                    # Безопасная переинициализация через sounddevice
                                    if hasattr(sd, '_coreaudio'):
                                        sd._coreaudio.reinitialize()
                                        logger.info("✅ CoreAudio переинициализирован")
                                    else:
                                        logger.info("🔄 API недоступен, базовый сброс")
                                        sd.stop()
                                        time.sleep(0.8)
                                except Exception as ca_e:
                                    logger.warning(f"⚠️ Ошибка переинициализации: {ca_e}")
                                    sd.stop()
                                    time.sleep(0.8)
                                
                                # Получаем обновленный список устройств
                                devices = sd.query_devices()
                                logger.info(f"📱 После сброса: {len(devices)} устройств")
                                
                                # Пробуем снова с теми же параметрами
                                logger.info("🔄 Пробую снова после сброса...")
                                try:
                                    with self.stream_lock:
                                        stream = sd.OutputStream(
                                            device=None,  # Автоматический выбор
                                            callback=self._playback_callback,
                                            **config
                                            )
                                        self._safe_start_stream(stream, timeout=2.0)
                                    
                                    logger.info(f"✅ Успех после сброса: ch={config['channels']}, sr={config['samplerate']}")
                                    self.channels = config['channels']
                                    self.sample_rate = config['samplerate']
                                    self.dtype = config['dtype']
                                    
                                    # Сохраняем информацию об устройстве для мониторинга
                                    self._last_device_info = {
                                        'index': current_default_out,
                                        'name': devices[current_default_out].get('name', 'Unknown') if current_default_out < len(devices) else 'Unknown',
                                        'channels': config['channels'],
                                        'samplerate': config['samplerate'],
                                        'timestamp': time.time()
                                    }
                                    
                                    logger.info(f"📱 Устройство после сброса: {self._last_device_info['name']} (индекс: {current_default_out})")
                                    return stream
                                    
                                except Exception as retry_e:
                                    logger.warning(f"⚠️ Повторная попытка не удалась: {retry_e}")
                                    
                                    # Fallback на встроенные устройства
                                    builtin_devices = self._find_builtin_devices()
                                    if builtin_devices:
                                        out_idx = builtin_devices.get('output')
                                        if out_idx is not None:
                                            logger.info(f"🔄 Принудительный fallback на встроенные: output={out_idx}")
                                            stream = sd.OutputStream(
                                                device=out_idx,
                                                channels=2,
                                                samplerate=48000,
                                                dtype=np.int16,
                                                callback=self._playback_callback
                                            )
                                            self._safe_start_stream(stream, timeout=2.0)
                                            logger.info("✅ Fallback на встроенные устройства успешен")
                                            
                                            # Сохраняем информацию об устройстве для мониторинга
                                            self._last_device_info = {
                                                'index': out_idx,
                                                'name': f'Built-in Device {out_idx} (fallback)',
                                                'channels': 2,
                                                'samplerate': 48000,
                                                'timestamp': time.time()
                                            }
                                            
                                            self.channels = 2
                                            self.sample_rate = 48000
                                            self.dtype = np.int16
                                            
                                            logger.info(f"📱 Fallback устройство: {self._last_device_info['name']} (индекс: {out_idx})")
                                            return stream
                            except Exception as fallback_e:
                                logger.warning(f"⚠️ Fallback тоже не удался: {fallback_e}")
                    
                    if i < len(configs) - 1:
                        time.sleep(0.1)  # Короткая пауза между попытками

            raise Exception("Не удалось инициализировать аудио поток в автоматическом режиме")

        except Exception as e:

            logger.error(f"❌ Критическая ошибка инициализации аудио: {e}")
            raise

    # _is_headphones удален - используется из utils.device_utils
    
    def _get_device_priority(self, device_info: dict) -> int:
        """Вычисляет приоритет устройства."""
        try:
            device_name = device_info.get('name', '').lower()
            
            # AirPods - высший приоритет
            if 'airpods' in device_name:
                return self.audio_manager.device_priorities['airpods'] if self.audio_manager else 100
                
            # Beats наушники
            elif 'beats' in device_name:
                return self.audio_manager.device_priorities['beats'] if self.audio_manager else 95
                
            # Bluetooth наушники
            elif 'bluetooth' in device_name and is_headphones(device_name):
                return self.audio_manager.device_priorities['bluetooth_headphones'] if self.audio_manager else 90
                
            # USB наушники
            elif 'usb' in device_name and is_headphones(device_name):
                return self.audio_manager.device_priorities['usb_headphones'] if self.audio_manager else 85
                
            # Bluetooth колонки
            elif 'bluetooth' in device_name:
                return self.audio_manager.device_priorities['bluetooth_speakers'] if self.audio_manager else 70
                
            # USB аудио
            elif 'usb' in device_name:
                return self.audio_manager.device_priorities['usb_audio'] if self.audio_manager else 60
                
            # Системные динамики
            elif any(tag in device_name for tag in ['macbook', 'built-in', 'internal', 'speakers']):
                return self.audio_manager.device_priorities['speakers'] if self.audio_manager else 40
                
            # Остальные устройства
            else:
                return self.audio_manager.device_priorities['unknown'] if self.audio_manager else 10
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка вычисления приоритета: {e}")
            return 0

    def _should_auto_switch_to_headphones(self, new_device_info: dict) -> bool:
        """Определяет, нужно ли автоматически переключиться на наушники."""
        try:
            if not self.auto_switch_to_headphones:
                return False
                
            # Если новое устройство - наушники, переключаемся
            if new_device_info and is_headphones(new_device_info['name']):
                logger.info("🎧 Обнаружены наушники - автоматическое переключение!")
                return True
                
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка определения необходимости переключения: {e}")
            return False

    def _handle_headphones_connection(self, device_info: dict):
        """Обрабатывает подключение наушников."""
        try:
            logger.info(f"🎧 НАУШНИКИ ПОДКЛЮЧЕНЫ: {device_info['name']}")
            
            # Принудительно переключаем системный default на наушники
            try:
                import sounddevice as sd
                current_default = sd.default.device
                if isinstance(current_default, (list, tuple)) and len(current_default) >= 2:
                    # Обновляем только output, оставляем input
                    new_default = (current_default[0], device_info['index'])
                else:
                    new_default = device_info['index']
                
                sd.default.device = new_default
                logger.info(f"🔄 Системный default переключен на наушники: {device_info['name']} (индекс: {device_info['index']})")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось переключить системный default на наушники: {e}")
            
            # Автоматически переключаемся на наушники
            self.switch_to_device(device_index=device_info['index'])
            
            # Восстанавливаем воспроизведение если было приостановлено
            if self.resume_on_reconnect and self._was_paused_for_disconnect:
                self.resume_playback()
                self._was_paused_for_disconnect = False
                logger.info("▶️ Воспроизведение возобновлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки подключения наушников: {e}")

    def _handle_headphones_disconnection(self):
        """Обрабатывает отключение наушников - УПРОЩЕННАЯ ЛОГИКА."""
        try:
            logger.info("🎧 НАУШНИКИ ОТКЛЮЧЕНЫ - УПРОЩЕННАЯ ОБРАБОТКА")
            
            # Пауза воспроизведения
            if self.pause_on_disconnect and self.is_playing:
                self.pause_playback()
                self._was_paused_for_disconnect = True
                logger.info("⏸️ Воспроизведение приостановлено")
            
            # УПРОЩЕНИЕ: Доверяем AudioDeviceManager для переключения
            # Не делаем никаких проверок и переключений - это делает AudioDeviceManager
            logger.info("🔄 Доверяем AudioDeviceManager для автоматического переключения")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки отключения наушников: {e}")

    def _was_headphones_disconnected(self) -> bool:
        """Проверяет, были ли отключены наушники - УПРОЩЕННАЯ ЛОГИКА."""
        try:
            # УПРОЩЕНИЕ: Простая проверка - если текущее устройство наушники
            # и они не найдены в списке доступных устройств
            with self._device_info_lock:
                if not self.current_device_info:
                    return False
                
            # Если текущее устройство - наушники, проверяем только одно условие
            if self.is_current_device_headphones():
                current_device_name = self.get_device_name_safe()
                
                # Простая проверка: есть ли наушники в списке доступных устройств
                available_devices = self.list_available_devices()
                headphones_found = False
                for device in available_devices:
                    if device['name'] == current_device_name:
                        headphones_found = True
                        break
                
                # Если наушники не найдены в списке, считаем их отключенными
                if not headphones_found:
                    logger.info(f"🎧 Наушники {current_device_name} не найдены в списке устройств")
                    return True
                
                return False
                
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки отключения наушников: {e}")
            return False

    def switch_to_system_device(self) -> bool:
        """Wrapper метод для переключения на системное устройство через централизованный AudioDeviceManager"""
        try:
            logger.info("🔄 [AudioPlayer] Переключение на системное устройство")
            
            # Сначала пробуем использовать централизованный AudioDeviceManager
            from audio_device_manager import get_global_audio_device_manager
            audio_manager = get_global_audio_device_manager()
            if audio_manager:
                logger.info("🎛️ [AudioPlayer] Используем централизованный AudioDeviceManager")
                success = audio_manager.switch_to_system_device()
                if success:
                    # Обновляем информацию об устройстве
                    self._update_current_device_info()
                    logger.info("✅ [AudioPlayer] Переключение на системное устройство через AudioDeviceManager успешно")
                    return True
                else:
                    logger.warning("⚠️ [AudioPlayer] AudioDeviceManager не смог переключиться, используем fallback")
            
            # Fallback на старый метод если AudioDeviceManager недоступен или не сработал
            logger.info("🔄 [AudioPlayer] Используем fallback метод переключения на системное устройство")
            
            # Используем AudioManagerDaemon если доступен
            if self.audio_manager:
                # Находим системное устройство через AudioManager
                devices = self.audio_manager.get_available_devices()
                system_device = None
                
                for device in devices:
                    if device.device_type.value == 'system_speakers':
                        system_device = device
                        break
                
                if system_device:
                    success = self.audio_manager.switch_to_device(system_device.name)
                    if success:
                        self._update_current_device_info()
                        logger.info(f"✅ [AudioPlayer] Переключились на системное устройство: {system_device.name}")
                        return True
                    else:
                        logger.warning(f"⚠️ [AudioPlayer] Не удалось переключиться на системное устройство: {system_device.name}")
                        return False
                else:
                    logger.warning("⚠️ [AudioPlayer] Системное устройство не найдено")
                    return False
            
            # Fallback на старый метод
            devices = self.list_available_devices()
            system_device = None
            
            for device in devices:
                if device['priority'] == (self.audio_manager.device_priorities['speakers'] if self.audio_manager else 40):
                    system_device = device
                    break
            
            if system_device:
                # Принудительно переключаем системный default
                try:
                    import sounddevice as sd
                    current_default = sd.default.device
                    if isinstance(current_default, (list, tuple)) and len(current_default) >= 2:
                        # Обновляем только output, оставляем input
                        new_default = (current_default[0], system_device['index'])
                    else:
                        new_default = system_device['index']
                    
                    sd.default.device = new_default
                    logger.info(f"🔄 Системный default переключен на: {system_device['name']} (индекс: {system_device['index']})")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось переключить системный default: {e}")
                
                return self.switch_to_device(device_index=system_device['index'])
            else:
                logger.warning("⚠️ Системное устройство не найдено")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка переключения на системное устройство: {e}")
            return False

    def _detect_bluetooth_profile(self, device_info):
        """
        Умно определяет текущий Bluetooth профиль устройства.
        Автоматически адаптирует параметры под реальные возможности.
        """
        try:
            device_name = device_info.get('name', '').lower()
            
            # Проверяем, является ли это Bluetooth устройством
            if not any(tag in device_name for tag in ['airpods', 'bluetooth', 'wireless']):
                return 'unknown', None
            
            logger.info(f"🔍 Определяю профиль Bluetooth для: {device_info.get('name', 'Unknown')}")
            
            # Получаем реальные возможности устройства
            max_channels = device_info.get('max_output_channels', 0)
            default_sr = device_info.get('default_samplerate', 0)
            max_sr = device_info.get('max_samplerate', 0)
            
            logger.info(f"📊 Возможности устройства:")
            logger.info(f"   Максимум каналов: {max_channels}")
            logger.info(f"   Дефолтная частота: {default_sr}")
            logger.info(f"   Максимальная частота: {max_sr}")
            
            # АВТОМАТИЧЕСКОЕ ОПРЕДЕЛЕНИЕ ПРОФИЛЯ
            if max_channels <= 1 and default_sr <= 16000:
                profile = 'hfp'  # Hands-Free Profile (гарнитура)
                logger.info("🎧 Определен профиль: HFP (гарнитура)")
                
                # HFP-совместимые параметры
                compatible_params = [
                    {'channels': 1, 'samplerate': 8000, 'dtype': np.int16},
                    {'channels': 1, 'samplerate': 16000, 'dtype': np.int16},
                    {'channels': 1, 'samplerate': 22050, 'dtype': np.int16},
                ]
                
            elif max_channels >= 2 and default_sr >= 44100:
                profile = 'a2dp'  # Advanced Audio Distribution Profile (качество)
                logger.info("🎧 Определен профиль: A2DP (качество)")
                
                # A2DP-совместимые параметры
                compatible_params = [
                    {'channels': 2, 'samplerate': 44100, 'dtype': np.int16},
                    {'channels': 2, 'samplerate': 48000, 'dtype': np.int16},
                    {'channels': 1, 'samplerate': 44100, 'dtype': np.int16},
                ]
                
            else:
                profile = 'mixed'  # Смешанный профиль
                logger.info("🎧 Определен профиль: MIXED (адаптивный)")
                
                # Адаптивные параметры
                compatible_params = [
                    {'channels': min(2, max_channels), 'samplerate': min(48000, default_sr), 'dtype': np.int16},
                    {'channels': 1, 'samplerate': min(44100, default_sr), 'dtype': np.int16},
                    {'channels': 1, 'samplerate': 16000, 'dtype': np.int16},
                ]
            
            # Проверяем совместимость параметров
            logger.info(f"🎯 Совместимые параметры для профиля {profile.upper()}:")
            for i, params in enumerate(compatible_params):
                logger.info(f"   {i+1}. ch={params['channels']}, sr={params['samplerate']}, dtype={params['dtype']}")
            
            return profile, compatible_params
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка определения профиля: {e}")
            return 'unknown', None
    
    def _test_device_compatibility(self, device_idx, params):
        """
        Тестирует совместимость устройства с заданными параметрами.
        Возвращает True если параметры работают.
        """
        try:
            logger.info(f"🧪 Тестирую совместимость: ch={params['channels']}, sr={params['samplerate']}")
            
            # Создаем тестовый поток
            test_stream = sd.OutputStream(
                device=device_idx,
                channels=params['channels'],
                samplerate=params['samplerate'],
                dtype=params['dtype']
            )
            
            # Запускаем поток с таймаутом
            self._safe_start_stream(test_stream, timeout=1.0)
            time.sleep(0.1)  # Даем потоку инициализироваться
            
            # Останавливаем и закрываем
            test_stream.stop()
            test_stream.close()
            
            logger.info(f"✅ Совместимость подтверждена: ch={params['channels']}, sr={params['samplerate']}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Несовместимость: {e}")
            return False
    
    def _get_adaptive_configs(self, devices, device_idx):
        """
        Умно определяет адаптивные параметры для устройства.
        Автоматически подбирает параметры под текущий профиль Bluetooth.
        """
        if device_idx == -1 or device_idx >= len(devices):
            # Fallback на универсальные параметры
            return [
                {'channels': 2, 'samplerate': 44100, 'dtype': np.int16},
                {'channels': 1, 'samplerate': 44100, 'dtype': np.int16},
                {'channels': 1, 'samplerate': 16000, 'dtype': np.int16},
            ]
        
        device = devices[device_idx]
        
        # АВТОМАТИЧЕСКОЕ ОПРЕДЕЛЕНИЕ ПРОФИЛЯ
        profile, compatible_params = self._detect_bluetooth_profile(device)
        
        if profile != 'unknown' and compatible_params:
            logger.info(f"🎯 Использую профиль {profile.upper()} для устройства {device_idx}")
            return compatible_params
        
        # Fallback на старую логику
        device_name = device.get('name', '').lower()
        
        # Определяем тип устройства и профиль
        if 'airpods' in device_name or 'bluetooth' in device_name:
            # Bluetooth устройство - адаптируемся под профиль
            max_channels = device.get('max_output_channels', 0)
            default_sr = device.get('default_samplerate', 0)
            
            logger.info(f"🎧 Bluetooth устройство: {device_name}")
            logger.info(f"   Максимум каналов: {max_channels}")
            logger.info(f"   Дефолтная частота: {default_sr}")
            
            if max_channels <= 1 or default_sr <= 16000:
                # HFP режим (гарнитура) - только низкое качество
                logger.info("🎧 Режим HFP (гарнитура) - используем низкое качество")
                return [
                    {'channels': 1, 'samplerate': 16000, 'dtype': np.int16},
                    {'channels': 1, 'samplerate': 8000, 'dtype': np.int16},
                    {'channels': 1, 'samplerate': 22050, 'dtype': np.int16},
                ]
            else:
                # A2DP режим (качество) - высокое качество
                logger.info("🎧 Режим A2DP (качество) - используем высокое качество")
                return [
                    {'channels': 2, 'samplerate': 44100, 'dtype': np.int16},
                    {'channels': 2, 'samplerate': 48000, 'dtype': np.int16},
                    {'channels': 1, 'samplerate': 44100, 'dtype': np.int16},
                ]
        
        elif any(tag in device_name for tag in ['macbook', 'built-in', 'internal']):
            # Встроенные устройства - стабильные параметры
            logger.info("💻 Встроенное устройство - используем стандартные параметры")
            return [
                {'channels': 2, 'samplerate': 48000, 'dtype': np.int16},
                {'channels': 2, 'samplerate': 44100, 'dtype': np.int16},
                {'channels': 1, 'samplerate': 48000, 'dtype': np.int16},
            ]
        
        else:
            # Неизвестное устройство - пробуем все варианты
            logger.info("❓ Неизвестное устройство - пробуем все варианты")
            return [
                {'channels': 2, 'samplerate': 44100, 'dtype': np.int16},
                {'channels': 1, 'samplerate': 44100, 'dtype': np.int16},
                {'channels': 2, 'samplerate': 48000, 'dtype': np.int16},
                {'channels': 1, 'samplerate': 16000, 'dtype': np.int16},
            ]

    def _find_builtin_devices(self):
        """Находит встроенные устройства MacBook для fallback."""
        try:
            devices = sd.query_devices()
            builtin = {'input': None, 'output': None}
            
            for idx, dev in enumerate(devices):
                try:
                    name = (dev.get('name') or '').lower()
                    if any(tag in name for tag in ['macbook', 'built-in', 'internal']):
                        if dev.get('max_input_channels', 0) > 0 and builtin['input'] is None:
                            builtin['input'] = idx
                        if dev.get('max_output_channels', 0) > 0 and builtin['output'] is None:
                            builtin['output'] = idx
                except Exception:
                    continue
            
            return builtin if any(builtin.values()) else None
        except Exception:
            return None





    def _safe_start_stream(self, stream, timeout=2.0):
        """
        Безопасно запускает sounddevice поток с таймаутом.
        Предотвращает зависание при stream.start().
        """
        import threading
        import time
        
        def start_stream_with_timeout():
            try:
                stream.start()
                logger.info("🎵 [AUDIO_PLAYER] sounddevice поток запущен")
                return True
            except Exception as e:
                logger.error(f"❌ Ошибка запуска потока: {e}")
                return False
        
        # Запускаем в отдельном потоке с таймаутом
        start_success = False
        start_thread = threading.Thread(target=lambda: setattr(self, '_stream_start_success', start_stream_with_timeout()), daemon=True)
        start_thread.start()
        start_thread.join(timeout=timeout)
        
        if start_thread.is_alive():
            logger.error(f"❌ ТАЙМАУТ: stream.start() завис - принудительно прерываю (таймаут {timeout}s)")
            # Принудительно останавливаем зависший поток
            try:
                if stream:
                    stream.stop()
                    stream.close()
            except:
                pass
            raise Exception(f"stream.start() завис - таймаут {timeout} секунд")
        
        if not getattr(self, '_stream_start_success', False):
            raise Exception("stream.start() завершился с ошибкой")
        
        logger.info("🎵 [AUDIO_PLAYER] sounddevice поток успешно запущен")
        return True

    def _clear_buffers(self):
        """Очищает внутренний буфер и очередь аудио."""
        # Очищаем внутренний буфер
        with self.buffer_lock:
            self.internal_buffer = np.array([], dtype=np.int16)
            logger.debug("✅ Внутренний буфер очищен")
        
        # Очищаем очередь аудио
        try:
            # Используем более эффективный способ очистки очереди
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.task_done()
                except queue.Empty:
                    break
            
            # Дополнительная очистка для гарантии
            with self.audio_queue.mutex:
                self.audio_queue.queue.clear()
            
            logger.debug("✅ Очередь аудио очищена")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при очистке очереди: {e}")
        
        # ИСПРАВЛЕНИЕ: убираем блокирующий join() - он блокирует поток
        # Вместо этого просто очищаем счетчики задач
        try:
            # Сбрасываем счетчики задач без блокировки
            with self.audio_queue.mutex:
                self.audio_queue.unfinished_tasks = 0
                self.audio_queue.all_tasks_done.notify_all()
        except Exception as e:
            logger.debug(f"Очистка счетчиков задач: {e}")

    def wait_for_queue_empty(self):
        """
        НЕБЛОКИРУЮЩЕЕ ожидание завершения воспроизведения.
        Возвращает управление НЕМЕДЛЕННО, не зависает!
        """
        logger.info("🎵 Проверяю статус воспроизведения (НЕБЛОКИРУЮЩЕЕ)...")
        
        # БЫСТРАЯ ПРОВЕРКА без ожидания
        queue_size = self.audio_queue.qsize()
        with self.buffer_lock:
            buffer_size = len(self.internal_buffer)
            
        # Простая логика: если нет данных - аудио завершено
        if queue_size == 0 and buffer_size == 0:
            logger.info("✅ Аудио завершено - нет данных в очереди и буфере")
            return True
        else:
            logger.info(f"📊 Аудио воспроизводится: очередь={queue_size}, буфер={buffer_size}")
            return False

    def play_beep(self, frequency: float = 1000.0, duration_sec: float = 0.12, volume: float = 0.4):
        """
        Проигрывает короткий сигнал (beep) БЕЗ запуска основного плеера.
        - frequency: частота тона в Гц
        - duration_sec: длительность сигнала в секундах
        - volume: громкость [0.0..1.0]
        """
        try:
            # Генерируем синусоидальную волну
            num_samples = int(self.sample_rate * duration_sec)
            if num_samples <= 0:
                return

            t = np.linspace(0, duration_sec, num_samples, endpoint=False)
            waveform = np.sin(2 * np.pi * frequency * t)
            amplitude = int(32767 * max(0.0, min(volume, 1.0)))
            samples = (amplitude * waveform).astype(np.int16)

            # ВАЖНО: НЕ используем add_chunk() - он запускает автостарт!
            if self.is_playing and self.stream and hasattr(self.stream, 'active') and self.stream.active:
                # Если плеер активен - добавляем beep в очередь БЕЗ автостарта
                logger.debug("🔊 Добавляю beep в активную очередь")
                self.audio_queue.put(samples)
            else:
                # Если плеер неактивен - воспроизводим beep напрямую
                logger.debug("🔊 Воспроизвожу beep напрямую")
                self._play_beep_directly(samples)
                
        except Exception as e:
            logger.warning(f"⚠️ Не удалось воспроизвести beep: {e}")

    def _play_beep_directly(self, samples):
        """Воспроизведение beep напрямую через sounddevice"""
        try:
            # Временный поток для beep
            def play_beep_thread():
                try:
                    # Исправляем параметры для sounddevice
                    sd.play(samples, samplerate=self.sample_rate, channels=1)  # Beep всегда моно
                    sd.wait()  # Ждем завершения
                    logger.debug("✅ Beep воспроизведен напрямую")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка прямого воспроизведения beep: {e}")
            
            threading.Thread(target=play_beep_thread, daemon=True).start()
        except Exception as e:
            logger.warning(f"⚠️ Не удалось запустить beep поток: {e}")



    async def cleanup(self):
        """Очистка ресурсов плеера с защитой от прерывания воспроизведения."""
        
        # КРИТИЧЕСКИ ВАЖНО: Не прерываем активное воспроизведение
        if self.is_playing and not self.stop_event.is_set():
            logger.info("🎵 Активное воспроизведение - ожидаю завершения...")
            # Ждем завершения воспроизведения естественным путем
            max_wait = 10.0  # 10 секунд максимум
            start_wait = time.time()
            
            while (self.is_playing and 
                   not self.stop_event.is_set() and 
                   time.time() - start_wait < max_wait):
                time.sleep(0.1)
            
            if self.is_playing:
                logger.warning("⚠️ Воспроизведение не завершилось за 10 секунд - принудительная остановка")
        
        # Только после завершения воспроизведения - очистка
        self.stop_playback()
        self.stop_device_monitoring()
        
        # Очистка потоков с таймаутом
        if hasattr(self, 'playback_thread') and self.playback_thread:
            if self.playback_thread.is_alive():
                logger.info("🔄 Ожидание завершения playback_thread...")
                self.playback_thread.join(timeout=2.0)
                if self.playback_thread.is_alive():
                    logger.warning("⚠️ playback_thread не завершился за 2 секунды")
        
        # НЕ останавливаем глобальный AudioManagerDaemon, так как он может использоваться другими экземплярами
        # Просто сбрасываем ссылку
        if self.audio_manager:
            try:
                # Удаляем callback, чтобы избежать утечек памяти
                # self.audio_manager.remove_callback(self._on_device_change_callback)  # Если будет метод
                self.audio_manager = None
                logger.info("✅ Ссылка на AudioManagerDaemon сброшена")
            except Exception as e:
                logger.error(f"❌ Ошибка очистки AudioManagerDaemon: {e}")
        
        logger.info("Ресурсы AudioPlayer очищены.")

    def get_audio_status(self):
        """
        Возвращает статус аудио системы и информацию об ошибках.
        """
        return {
            'is_playing': self.is_playing,

            'stream_active': self.stream is not None and hasattr(self.stream, 'active') and self.stream.active,
            'queue_size': self.audio_queue.qsize(),
            'buffer_size': len(self.internal_buffer)
        }



    def force_stop(self, immediate=False):
        """Универсальный метод остановки аудио с опцией мгновенной остановки"""
        if getattr(self, '_is_shutting_down', False):
            logger.info("🔒 Shutdown уже идёт — force_stop пропущен")
            return
        with self._shutdown_mutex:
            if self._is_shutting_down:
                logger.info("🔒 Shutdown уже идёт — force_stop пропущен")
                return
            self._is_shutting_down = True
        if immediate:
            logger.info("🚨 force_stop(immediate=True) вызван - МГНОВЕННАЯ остановка")
        else:
            logger.info("🚨 force_stop() вызван - обычная остановка")
        
        try:
            # 1️⃣ Устанавливаем флаг остановки
            self.stop_event.set()
            self._set_playing_state(False, "принудительная остановка")
            
            # 2️⃣ ПЕРВЫМ ДЕЛОМ останавливаем аудио поток (это останавливает звук!)
            if self.stream and hasattr(self.stream, 'active') and self.stream.active:
                if immediate:
                    logger.info("   🚨 МГНОВЕННО останавливаю аудио поток - ЗВУК ПРЕКРАТИТСЯ!")
                    try:
                        self.stream.stop()
                        self.stream.close()
                        self.stream = None
                        logger.info("   ✅ Аудио поток МГНОВЕННО остановлен - ЗВУК ПРЕКРАТИЛСЯ!")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Ошибка остановки аудио потока: {e}")
                else:
                    logger.info("   🚨 Останавливаю аудио поток...")
                    try:
                        self.stream.stop()
                        self.stream.close()
                        self.stream = None
                        logger.info("   ✅ Аудио поток остановлен")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Ошибка остановки аудио потока: {e}")
            
            # 3️⃣ Теперь останавливаем поток воспроизведения
            if self.playback_thread and self.playback_thread.is_alive():
                if immediate:
                    logger.info("   🚨 МГНОВЕННО останавливаю поток воспроизведения...")
                    
                    # Принудительно прерываем поток
                    import ctypes
                    thread_id = self.playback_thread.ident
                    if thread_id:
                        try:
                            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                                ctypes.c_long(thread_id), 
                                ctypes.py_object(SystemExit)
                            )
                            if res > 1:
                                ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
                                logger.warning("   ⚠️ Не удалось прервать поток воспроизведения")
                            else:
                                logger.info("   ✅ Поток воспроизведения принудительно прерван")
                        except Exception as e:
                            logger.warning(f"   ⚠️ Ошибка принудительного прерывания потока: {e}")
                    
                    # Ждем завершения с коротким таймаутом
                    timeout = 0.1
                else:
                    logger.info("   🚨 Останавливаю поток воспроизведения...")
                    timeout = 0.01
                
                self.playback_thread.join(timeout=timeout)
                if self.playback_thread.is_alive():
                    logger.warning(f"   ⚠️ Поток воспроизведения не остановился в таймаут {timeout}s")
                else:
                    logger.info("   ✅ Поток воспроизведения остановлен")
            
            # 4️⃣ Очищаем очередь
            if not self.audio_queue.empty():
                queue_size = self.audio_queue.qsize()
                if immediate:
                    logger.info(f"   🧹 МГНОВЕННО очищаю очередь: {queue_size} элементов")
                else:
                    logger.info(f"   🧹 Очищаю очередь: {queue_size} элементов")
                
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                    except:
                        break
                
                if immediate:
                    logger.info("   ✅ Очередь МГНОВЕННО очищена")
                else:
                    logger.info("   ✅ Очередь очищена")
            
            # 5️⃣ Очищаем внутренний буфер
            with self.buffer_lock:
                self.internal_buffer = np.array([], dtype=np.int16)
                if immediate:
                    logger.info("   ✅ Внутренний буфер МГНОВЕННО очищен")
                else:
                    logger.info("   ✅ Внутренний буфер очищен")
            
            # 6️⃣ Для мгновенной остановки - дополнительная очистка
            if immediate:
                # Принудительно останавливаем все звуковые потоки
                try:
                    import sounddevice as sd
                    sd.stop()  # Останавливает все звуковые потоки
                    logger.info("   ✅ Все звуковые потоки МГНОВЕННО остановлены")
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка остановки звуковых потоков: {e}")
                
                # Дополнительная проверка - если звук все еще играет, принудительно останавливаем
                try:
                    if self.stream and hasattr(self.stream, 'active') and self.stream.active:
                        logger.warning("   ⚠️ Аудио поток все еще активен - принудительная остановка!")
                        self.stream.stop()
                        self.stream.close()
                        self.stream = None
                        logger.info("   ✅ Аудио поток принудительно остановлен")
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка принудительной остановки: {e}")
            
            if immediate:
                logger.info("✅ force_stop(immediate=True) завершен")
            else:
                logger.info("✅ force_stop() завершен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в force_stop: {e}")
        finally:
            self._is_shutting_down = False
    

    

    
    def clear_audio_buffers(self):
        """Очищает все аудио буферы"""
        logger.info("🧹 clear_audio_buffers() вызван")
        
        try:
            # 1️⃣ Очищаем очередь
            if not self.audio_queue.empty():
                queue_size = self.audio_queue.qsize()
                logger.info(f"   🧹 Очищаю очередь: {queue_size} элементов")
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                    except:
                        break
                logger.info("   ✅ Очередь очищена")
            
            # 2️⃣ Очищаем внутренний буфер
            with self.buffer_lock:
                self.internal_buffer = np.array([], dtype=np.int16)
                logger.info("   ✅ Внутренний буфер очищен")
            
            # 3️⃣ Очищаем системные аудио буферы
            try:
                import sounddevice as sd
                sd.stop()
                logger.info("   ✅ Системные аудио буферы очищены")
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка очистки системных буферов: {e}")
            
            logger.info("✅ clear_audio_buffers завершен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в clear_audio_buffers: {e}")

    def _check_audio_devices(self):
        """Проверяет доступность аудио устройств."""
        try:
            sd.query_devices()
            logger.info("✅ Аудио устройства доступны.")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить список аудио устройств: {e}")
    
    # Новые методы для интеграции с AudioManagerDaemon
    
    def switch_to_headphones_via_manager(self) -> bool:
        """Переключается на наушники через AudioManagerDaemon"""
        try:
            if self.audio_manager:
                success = self.audio_manager.switch_to_headphones()
                if success:
                    self._update_current_device_info()
                    logger.info("✅ Переключились на наушники через AudioManagerDaemon")
                return success
            else:
                logger.warning("⚠️ AudioManagerDaemon недоступен")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка переключения на наушники: {e}")
            return False
    
    def auto_switch_to_best_device_via_manager(self) -> bool:
        """Автоматически переключается на лучшее устройство через AudioManagerDaemon"""
        try:
            if self.audio_manager:
                success = self.audio_manager.auto_switch_to_best()
                if success:
                    self._update_current_device_info()
                    logger.info("✅ Автоматически переключились на лучшее устройство через AudioManagerDaemon")
                return success
            else:
                logger.warning("⚠️ AudioManagerDaemon недоступен")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка автоматического переключения: {e}")
            return False
    
    def get_available_devices_via_manager(self) -> List[Dict]:
        """Получает список доступных устройств через AudioManagerDaemon"""
        try:
            if self.audio_manager:
                return self.audio_manager.get_available_devices()
            else:
                logger.warning("⚠️ AudioManagerDaemon недоступен")
                return []
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка устройств: {e}")
            return []
    
    def is_audio_manager_available(self) -> bool:
        """Проверяет доступность AudioManagerDaemon"""
        return self.audio_manager is not None
    
    def get_audio_manager_status(self) -> dict:
        """Возвращает статус AudioManagerDaemon"""
        if not self.audio_manager:
            return {'available': False, 'error': 'AudioManagerDaemon не инициализирован'}
        
        try:
            current_device = self.audio_manager.get_current_device()
            devices = self.audio_manager.get_available_devices()
            
            return {
                'available': True,
                'current_device': current_device,
                'total_devices': len(devices),
                'running': self.audio_manager.running
            }
        except Exception as e:
            return {'available': True, 'error': str(e)}
    
    def clear_all_audio_data(self):
        """МГНОВЕННО очищает ВСЕ аудио данные (очереди, буферы, потоки)"""
        logger.info("🚨 clear_all_audio_data() вызван - МГНОВЕННАЯ очистка всех аудио данных")
        
        try:
            # Используем существующий force_stop с immediate=True для мгновенной остановки
            self.force_stop(immediate=True)
            
            # Дополнительная очистка буферов для полной очистки
            self.clear_audio_buffers()
            
            logger.info("✅ clear_all_audio_data завершен - все аудио данные очищены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в clear_all_audio_data: {e}")
    
    def notify_device_changed(self):
        """Уведомляет STT об изменении устройств"""
        try:
            if hasattr(self, 'stt_recognizer') and self.stt_recognizer:
                logger.info("🔄 AudioPlayer: Уведомляю STT об изменении устройств...")
                self.stt_recognizer.invalidate_device_cache()
                logger.info("✅ AudioPlayer: STT уведомлен об изменении устройств")
            else:
                logger.debug("ℹ️ AudioPlayer: STT recognizer не подключен")
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления STT об изменении устройств: {e}")

                   