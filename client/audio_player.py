import asyncio
import sounddevice as sd
import numpy as np
import logging
import queue
import threading
import time

logger = logging.getLogger(__name__)

class AudioPlayer:
    """
    Воспроизводит аудиопоток в реальном времени с использованием sounddevice.
    Принимает аудиофрагменты (chunks) в виде NumPy массивов и воспроизводит их бесшовно.
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
        
        # Внутренний буфер для плавного воспроизведения
        self.internal_buffer = np.array([], dtype=np.int16)
        self.buffer_lock = threading.Lock()
        self.stream_lock = threading.Lock()
        self.current_output_device = None
        self.output_device_monitor_thread = None
        self.stop_output_monitor = threading.Event()
        # Дебаунс смены устройства вывода
        self._pending_output_device = None
        self._pending_output_count = 0
        # Конфиг по умолчанию (может быть переопределён из main.py)
        self.follow_system_default = True
        self.bluetooth_policy = 'prefer_quality'
        self.settle_ms = 400
        self.retries = 3
        # Строго следуем системному default: без резервов на другие устройства
        self.strict_follow_default = True
        # Дебаунс рестартов на текущем default
        self._last_restart_ts = 0.0
        self._restart_min_interval_sec = 0.2
        
        # Флаг для отслеживания ошибок аудио
        self.audio_error = False
        self.audio_error_message = ""
        
        # ПРОСТАЯ блокировка буфера после прерывания
        self.buffer_blocked_until = 0  # Время до которого буфер заблокирован
        self.buffer_block_duration = 0.5  # Длительность блокировки в секундах
        
        # Проверяем доступность аудио устройств
        self._check_audio_devices()
        
        # Флаг для временной приостановки переключения output-устройств (например, во время записи)
        self.suspend_output_switching = False

    def set_output_switching_suspended(self, suspended: bool):
        """Управляет приостановкой мониторинга и переключения выходных устройств."""
        try:
            self.suspend_output_switching = bool(suspended)
            logger.info(f"🔧 suspend_output_switching={'on' if self.suspend_output_switching else 'off'}")
        except Exception:
            self.suspend_output_switching = suspended

    def switch_to_system_default_output(self) -> bool:
        """Принудительно переключает поток вывода на текущее системное default-устройство CoreAudio."""
        try:
            new_device = self._resolve_output_device()
            # Диагностика: что именно выбрали
            try:
                info, name = self._get_device_info(new_device)
                logger.info(f"🎧 switch_to_system_default_output: target={name} (index={new_device})")
            except Exception:
                pass
            if new_device is None:
                logger.warning("⚠️ System default output не определён — пропускаю переключение")
                return False
            if new_device != self.current_output_device:
                if self._restart_output_stream(new_device):
                    self.current_output_device = new_device
                    logger.info(f"🔄 Принудительно переключил выход на системный default: {name} (index={new_device})")
                    return True
                return False
            # Уже на системном default
            return True
        except Exception as e:
            logger.warning(f"⚠️ Не удалось переключить на системный default output: {e}")
            return False

    def _get_device_info(self, device_index):
        """Безопасно возвращает info и name для устройства."""
        try:
            if device_index is None or device_index == -1:
                return None, 'System Default'
            info = sd.query_devices(device_index)
            return info, (info.get('name') or str(device_index))
        except Exception:
            return None, str(device_index)

    def _is_bt_hfp_active(self) -> bool:
        """
        Эвристика: активен ли BT HFP (телефонный) профиль на default input.
        Если да — вывод через те же AirPods часто невозможен (ошибки -10851/-9986),
        поэтому следует избегать выбор AirPods как output.
        """
        try:
            # 1) Получаем CoreAudio default input device
            hostapis = sd.query_hostapis()
            core_idx = None
            for i, api in enumerate(hostapis):
                if 'core' in (api.get('name', '').lower()):
                    core_idx = i
                    break
            if core_idx is None:
                core_idx = 0
            api = sd.query_hostapis(core_idx)
            d_in = api.get('default_input_device', -1)
            if d_in is None or d_in == -1:
                return False
            info_in = sd.query_devices(d_in)
            name_l = (info_in.get('name') or '').lower()
            max_in_ch = int(info_in.get('max_input_channels') or 0)
            def_sr_in = int(round(info_in.get('default_samplerate') or 0))
            # HFP признаки: airpods/hfp/hsp в имени, 1 канал и/или низкая частота 8k/16k
            if any(t in name_l for t in ['airpods', 'hands-free', 'handsfree', 'hfp', 'hsp']):
                return True
            if max_in_ch <= 1 and def_sr_in and def_sr_in <= 16000:
                return True
            return False
        except Exception:
            return False

    def _find_backup_output_device(self):
        """Возвращает индекс ближайшего доступного устройства вывода, избегая AirPods/HFP."""
        try:
            devices = sd.query_devices()
        except Exception:
            return None

        preferred_indices = []
        fallback_indices = []

        for idx, dev in enumerate(devices):
            try:
                if dev.get('max_output_channels', 0) <= 0:
                    continue
                name = (dev.get('name') or '').lower()
                if any(tag in name for tag in ['airpods', 'hands-free', 'handsfree', 'hfp', 'hsp']):
                    continue
                # Предпочтем встроенные динамики/внутренние устройства
                if any(tag in name for tag in ['built-in', 'macbook', 'internal', 'встро', 'system']):
                    preferred_indices.append(idx)
                else:
                    fallback_indices.append(idx)
            except Exception:
                continue

        if preferred_indices:
            return preferred_indices[0]
        if fallback_indices:
            return fallback_indices[0]
        return None

    def _playback_callback(self, outdata, frames, time, status):
        """Callback-функция для sounddevice, вызывается для заполнения буфера вывода."""
        if status:
            logger.warning(f"Sounddevice status: {status}")

        try:
            with self.buffer_lock:
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
                            outdata[:frames, :] = np.repeat(fs.reshape(frames, 1), self.channels, axis=1)
                    else:
                        if self.channels == 1:
                            outdata[:frames, 0] = mono_samples
                        else:
                            outdata[:frames, :] = np.repeat(mono_samples.reshape(frames, 1), self.channels, axis=1)
                    self.internal_buffer = self.internal_buffer[frames:]
                else:
                    # Недостаточно данных, пытаемся получить из очереди
                    try:
                        # Собираем ВСЕ доступные чанки в буфер
                        while not self.audio_queue.empty():
                            chunk = self.audio_queue.get_nowait()
                            if chunk is not None and len(chunk) > 0:
                                self.internal_buffer = np.concatenate([self.internal_buffer, chunk])
                                logger.debug(f"🎵 Добавлен чанк в буфер: {len(chunk)} сэмплов. Общий размер буфера: {len(self.internal_buffer)}")
                            self.audio_queue.task_done()
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
                                outdata[:frames, :] = np.repeat(fs.reshape(frames, 1), self.channels, axis=1)
                        else:
                            if self.channels == 1:
                                outdata[:frames, 0] = mono_samples
                            else:
                                outdata[:frames, :] = np.repeat(mono_samples.reshape(frames, 1), self.channels, axis=1)
                        self.internal_buffer = self.internal_buffer[frames:]
                        logger.debug(f"🎵 Отправлено в аудио: {frames} сэмплов. Осталось в буфере: {len(self.internal_buffer)}")
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
                                    outdata[:available, :] = np.repeat(fs.reshape(available, 1), self.channels, axis=1)
                                    outdata[available:frames, :] = 0.0
                            else:
                                if self.channels == 1:
                                    outdata[:available, 0] = mono_samples
                                    outdata[available:frames, 0] = 0
                                else:
                                    outdata[:available, :] = np.repeat(mono_samples.reshape(available, 1), self.channels, axis=1)
                                    outdata[available:frames, :] = 0
                            self.internal_buffer = np.array([], dtype=np.int16)
                            logger.debug(f"🎵 Отправлено доступных: {available} сэмплов, остальное тишина")
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
                                                outdata[:frames, :] = np.repeat(fs.reshape(frames, 1), self.channels, axis=1)
                                        else:
                                            if self.channels == 1:
                                                outdata[:frames, 0] = mono_samples
                                            else:
                                                outdata[:frames, :] = np.repeat(mono_samples.reshape(frames, 1), self.channels, axis=1)
                                        # Остаток чанка сохраняем в буфер
                                        if len(chunk) > frames:
                                            self.internal_buffer = chunk[frames:]
                                        logger.debug(f"🎵 Чанк обработан напрямую: {frames} сэмплов")
                                    else:
                                        # Чанк меньше frames, заполняем тишиной
                                        c = len(chunk)
                                        if outdata.dtype.kind == 'f':
                                            fs = chunk.astype(np.float32) / 32768.0
                                            if self.channels == 1:
                                                outdata[:c, 0] = fs
                                                outdata[c:frames, 0] = 0.0
                                            else:
                                                outdata[:c, :] = np.repeat(fs.reshape(c, 1), self.channels, axis=1)
                                                outdata[c:frames, :] = 0.0
                                        else:
                                            if self.channels == 1:
                                                outdata[:c, 0] = chunk
                                                outdata[c:frames, 0] = 0
                                            else:
                                                outdata[:c, :] = np.repeat(chunk.reshape(c, 1), self.channels, axis=1)
                                                outdata[c:frames, :] = 0
                                        logger.debug(f"🎵 Короткий чанк: {len(chunk)} сэмплов, остальное тишина")
                                else:
                                    # Нет данных, тишина
                                    outdata.fill(0)
                                    logger.debug("🔇 Нет данных - тишина")
                                self.audio_queue.task_done()
                            except queue.Empty:
                                # Очередь пуста, тишина
                                outdata.fill(0)
                                logger.debug("🔇 Очередь пуста - тишина")
        except Exception as e:
            logger.error(f"❌ Ошибка в playback callback: {e}")
            outdata.fill(0)  # В случае ошибки отправляем тишину

    def add_chunk(self, audio_chunk: np.ndarray):
        """Добавляет аудио чанк в очередь воспроизведения."""
        if audio_chunk is None or len(audio_chunk) == 0:
            logger.warning("⚠️ Попытка добавить пустой аудио чанк!")
            return
        
        # Автостарт воспроизведения при первом чанке
        try:
            if not self.is_playing or self.stream is None or not getattr(self.stream, 'active', False):
                logger.info("🎵 Автостарт воспроизведения перед добавлением первого чанка")
                self.start_playback()
        except Exception:
            pass

        chunk_size = len(audio_chunk)
        logger.debug(f"🎵 Добавляю аудио чанк размером {chunk_size} сэмплов")
        
        # Проверяем временную блокировку буфера
        if self.is_buffer_locked():
            logger.warning(f"🚨 БУФЕР ВРЕМЕННО ЗАБЛОКИРОВАН - пропускаю добавление аудио чанка размером {chunk_size}!")
            return
        
        try:
            # Добавляем чанк в очередь
            self.audio_queue.put(audio_chunk)
            logger.debug(f"✅ Аудио чанк добавлен в очередь. Размер очереди: {self.audio_queue.qsize()}")
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении аудио чанка: {e}")
            # Попытка восстановления
            try:
                if not self.audio_queue.full():
                    self.audio_queue.put(audio_chunk)
                    logger.info("✅ Аудио чанк добавлен после восстановления")
                else:
                    logger.warning("⚠️ Очередь переполнена, чанк отброшен")
            except Exception as e2:
                logger.error(f"❌ Критическая ошибка при восстановлении: {e2}")

    def start_playback(self):
        """Запускает потоковое воспроизведение аудио."""
        if self.is_playing:
            logger.warning("⚠️ Воспроизведение уже запущено!")
            return
        
        logger.info("Запуск потокового воспроизведения аудио...")
        self.stop_event.clear()
        self._clear_buffers()  # Очищаем буферы перед началом
        
        try:
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
            self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.playback_thread.start()
            
            # Безусловно читаем ТЕКУЩИЙ системный default напрямую (игнорируем возможный устаревший кэш listener)
            direct_device = self._resolve_output_device()
            # Снимок состояния устройств для диагностики
            try:
                import sounddevice as _sd
                devices = _sd.query_devices()
                hostapis = _sd.query_hostapis()
                core_idx = next((i for i,a in enumerate(hostapis) if 'core' in (a.get('name','').lower())), 0)
                api = _sd.query_hostapis(core_idx)
                din = api.get('default_input_device', -1)
                dout = api.get('default_output_device', -1)
                devs_count = sum(1 for d in devices if (d.get('max_input_channels',0)>0 or d.get('max_output_channels',0)>0))
                logger.info(f"🧪 Snapshot @start_playback: din={None if din==-1 else din} dout={None if dout==-1 else dout} devices={devs_count}")
            except Exception:
                pass
            # Диагностика: сравним с кэшем listener (если есть)
            try:
                ca_listener = getattr(self, 'default_listener', None)
                cached = ca_listener.get_default_output() if (ca_listener and hasattr(ca_listener, 'get_default_output')) else None
            except Exception:
                cached = None
            try:
                _, direct_name = self._get_device_info(direct_device)
                _, cached_name = self._get_device_info(cached)
                logger.info(f"🔊 Старт воспроизведения: system default now = {direct_name} (index={direct_device}); listener_cache = {cached_name} (index={cached})")
            except Exception:
                pass
            self.current_output_device = direct_device
            self.stream = self._safe_init_stream(preferred_device=direct_device)
            self.is_playing = True
            
            logger.info("✅ Потоковое воспроизведение аудио запущено!")
            
            # Мониторинг смены выходного устройства теперь в CoreAudio listener
            
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске воспроизведения: {e}")
            self.is_playing = False
            self.playback_thread = None
            self.stream = None

    def stop_playback(self):
        """Останавливает потоковое воспроизведение аудио."""
        if not self.is_playing:
            logger.warning("⚠️ Воспроизведение уже остановлено!")
            return
        
        logger.info("Остановка потокового воспроизведения аудио...")
        
        try:
            # Устанавливаем флаг остановки
            self.stop_event.set()
            
            # Останавливаем мониторинг смены устройства
            try:
                self.stop_output_monitor.set()
                if self.output_device_monitor_thread and self.output_device_monitor_thread.is_alive():
                    self.output_device_monitor_thread.join(timeout=0.5)
            except Exception:
                pass

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
            self.is_playing = False
            self.playback_thread = None
            
            # Очищаем буферы
            self._clear_buffers()
            
            logger.info("✅ Потоковое воспроизведение аудио остановлено!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке воспроизведения: {e}")
            # Принудительно сбрасываем состояние
            self.is_playing = False
            self.playback_thread = None
            self.stream = None



    def _playback_loop(self):
        """Фоновый поток для воспроизведения аудио"""
        logger.info("🔄 Фоновый поток воспроизведения запущен")
        
        try:
            while not self.stop_event.is_set():
                try:
                    # Если поток неожиданно стал неактивным — пробуем мягкий рестарт на текущем системном default
                    if self.is_playing and (self.stream is None or not getattr(self.stream, 'active', False)):
                        self._attempt_restart_on_current_default()
                except Exception:
                    pass
                # Проверяем, есть ли данные для воспроизведения
                if not self.audio_queue.empty() or len(self.internal_buffer) > 0:
                    # Небольшая пауза для снижения нагрузки на CPU
                    time.sleep(0.001)  # 1ms
                else:
                    # Если нет данных, ждем немного
                    time.sleep(0.01)  # 10ms
                    
        except Exception as e:
            logger.error(f"❌ Ошибка в фоновом потоке воспроизведения: {e}")
        finally:
            logger.info("🔄 Фоновый поток воспроизведения завершен")

    def _attempt_restart_on_current_default(self, retries: int = 2) -> bool:
        """Пробует перезапустить вывод на ТЕКУЩЕМ системном default (строгий режим).
        Не выбирает другие устройства. Возвращает True при успехе.
        """
        import time as _t
        now = _t.time()
        if (now - self._last_restart_ts) < self._restart_min_interval_sec:
            return False
        self._last_restart_ts = now

        for attempt in range(max(1, retries)):
            try:
                # Получаем предпочтительное устройство из listener (если есть), иначе None → CoreAudio default
                preferred_device = None
                try:
                    ca_listener = getattr(self, 'default_listener', None)
                    if ca_listener is not None and hasattr(ca_listener, 'get_default_output'):
                        preferred_device = ca_listener.get_default_output()
                except Exception:
                    preferred_device = None

                # Закрываем текущий поток (если есть)
                with self.stream_lock:
                    if self.stream:
                        try:
                            if hasattr(self.stream, 'active') and self.stream.active:
                                self.stream.stop()
                            self.stream.close()
                        except Exception:
                            pass
                        self.stream = None

                # Пытаемся запустить новый поток на текущем системном default
                self.stream = self._safe_init_stream(preferred_device=preferred_device)
                self.is_playing = True
                logger.info("✅ OutputStream перезапущен на текущем системном default")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Не удалось перезапустить OutputStream на текущем default (попытка {attempt+1}): {e}")
                _t.sleep(0.15)
        return False

    def _safe_init_stream(self, preferred_device=None):
        """
        Безопасная инициализация аудио потока с обработкой ошибок PortAudio.
        Учитывает режимы BT HFP/A2DP и свойства default-устройства.
        """
        try:
            # Текущий default output
            device_idx = preferred_device
            info = None
            try:
                info = sd.query_devices(device_idx) if device_idx is not None else None
                name = (info.get('name') if info else 'System Default')
            except Exception:
                name = str(device_idx)

            # Режим: строго следуем системному default, но если он в телефонном профиле (HFP) —
            # пробуем совместимые параметры (1 канал, 16k/8k) НА ЭТОМ ЖЕ устройстве.
            # Это не смена устройства, только параметры вывода.
            hfp_mode = False
            try:
                # Эвристика по текущему default input (если активен HFP на BT-микрофоне)
                if self._is_bt_hfp_active():
                    hfp_mode = True
                else:
                    # По самому output-устройству: ограниченные каналы/частота или имя
                    dev_name_l = (name or '').lower()
                    max_ch = (info.get('max_output_channels') if info else 2) or 2
                    def_sr = int(round((info.get('default_samplerate') if info else self.sample_rate)))
                    if any(t in dev_name_l for t in ['airpods', 'hands-free', 'handsfree', 'hfp', 'hsp']) or max_ch <= 1 or def_sr <= 16000:
                        hfp_mode = True
            except Exception:
                hfp_mode = False

            # Формируем набор параметров: сначала идеальные, затем совместимые
            samplerates = []
            channels_options = []

            try:
                if info and info.get('default_samplerate'):
                    samplerates.append(int(round(info.get('default_samplerate'))))
            except Exception:
                pass
            # Базовые популярные частоты
            for sr in [self.sample_rate, 48000, 44100, 32000, 22050, 16000, 12000, 11025, 8000]:
                if sr and sr not in samplerates:
                    samplerates.append(sr)

            try:
                max_out_ch = int(info.get('max_output_channels')) if info else 2
            except Exception:
                max_out_ch = 2

            if hfp_mode or max_out_ch <= 1:
                channels_options = [1, 2] if max_out_ch >= 2 else [1]
                # В HFP в приоритете 16000/8000
                for sr in [16000, 8000]:
                    if sr not in samplerates:
                        samplerates.insert(0, sr)
            else:
                # Всегда пробуем и стерео, и моно (на случай, если профиль меняется во время открытия)
                channels_options = [2, 1] if max_out_ch >= 2 else [1]

            # Несколько попыток с короткой задержкой — на случай переключения профиля BT
            attempts = max(1, getattr(self, 'retries', 3))
            for attempt in range(attempts):
                for ch in channels_options:
                    for sr in samplerates:
                        # Перебираем варианты dtype/blocksize/latency от мягких к строгим
                        for dtype in [self.dtype, 'float32', 'int16']:
                            for bs in [None, 1024, 2048]:
                                for lat in [None, 'high']:
                                    try:
                                        logger.info(f"🔄 Пробую default-вывод: device={name}, ch={ch}, sr={sr}, dtype={dtype}, bs={bs}, lat={lat}, attempt={attempt+1}")
                                        kwargs = dict(samplerate=sr, channels=ch, dtype=dtype, device=device_idx, callback=self._playback_callback)
                                        if bs is not None:
                                            kwargs['blocksize'] = bs
                                        if lat is not None:
                                            kwargs['latency'] = lat
                                        with self.stream_lock:
                                            stream = sd.OutputStream(**kwargs)
                                            stream.start()
                                        logger.info(f"✅ Поток инициализирован: device={name}, ch={ch}, sr={sr}, dtype={dtype}, bs={bs}, lat={lat}")
                                        self.channels = ch
                                        self.sample_rate = sr
                                        self.dtype = dtype
                                        # Фиксируем фактическое устройство вывода
                                        try:
                                            actual_idx = device_idx if device_idx is not None else self._resolve_output_device()
                                            self.current_output_device = actual_idx
                                        except Exception:
                                            pass
                                        return stream
                                    except Exception as e:
                                        logger.warning(f"⚠️ Не удалось: device={name}, ch={ch}, sr={sr}, dtype={dtype}, bs={bs}, lat={lat}: {e}")

                    # Попытка без явного девайса (пусть CoreAudio сам выберет default)
                    try:
                        logger.info(f"🔄 Пробую вывод с device=None, channels={ch}, samplerate={samplerates[0]}, attempt={attempt+1}")
                        with self.stream_lock:
                            stream = sd.OutputStream(
                                samplerate=samplerates[0],
                                channels=ch,
                                dtype=self.dtype,
                                device=None,
                                callback=self._playback_callback,
                                blocksize=2048,
                                latency='high'
                            )
                            stream.start()
                        logger.info("✅ Аудио поток инициализирован через CoreAudio default (device=None)")
                        self.channels = ch
                        self.sample_rate = samplerates[0]
                        # Фиксируем фактическое устройство вывода по текущему системному default
                        try:
                            self.current_output_device = self._resolve_output_device()
                        except Exception:
                            pass
                        return stream
                    except Exception as e:
                        logger.warning(f"⚠️ device=None тоже не сработал: {e}")

                # В строгом режиме НЕ выполняем резерв на другие устройства — следуем system default
                if not getattr(self, 'strict_follow_default', False):
                    try:
                        dev_lower = (name or '').lower()
                        if any(tag in dev_lower for tag in ['airpods', 'hands-free', 'handsfree', 'hfp', 'hsp']) or self._is_bt_hfp_active():
                            backup = self._find_backup_output_device()
                            if backup is not None and backup != device_idx:
                                try:
                                    info_b = sd.query_devices(backup)
                                    name_b = info_b.get('name')
                                except Exception:
                                    name_b = str(backup)
                                logger.info(f"🔄 Пробую резервный output: {name_b} (index={backup})")
                                device_idx = backup
                                # Пересчитаем info/name для последующих попыток
                                try:
                                    info = sd.query_devices(device_idx)
                                    name = info.get('name')
                                except Exception:
                                    name = str(device_idx)
                                # переходим к следующему циклу попыток (с новым device_idx)
                                continue
                    except Exception:
                        pass

                # Пауза и переопределение default
                try:
                    time.sleep(max(0.1, getattr(self, 'settle_ms', 400)/1000.0))
                    device_idx = preferred_device if preferred_device is not None else self._resolve_output_device()
                    try:
                        info = sd.query_devices(device_idx) if device_idx is not None else None
                        name = (info.get('name') if info else 'System Default')
                    except Exception:
                        name = str(device_idx)
                except Exception:
                    pass

            # Альтернативные консервативные настройки
            logger.info("🔄 Пробую альтернативные настройки для macOS...")
            try:
                stream = sd.OutputStream(
                    samplerate=44100,
                    channels=1,
                    dtype='int16',
                    callback=self._playback_callback,
                    blocksize=2048,
                    latency='high'
                )
                stream.start()
                logger.info("✅ Аудио поток инициализирован с альтернативными настройками")
                return stream
            except Exception as e:
                logger.warning(f"⚠️ Альтернативные настройки не помогли: {e}")

            # Если устройство вероятно в HFP и все попытки не удались — сообщаем мягко
            if hfp_mode:
                raise Exception("Выходное устройство в телефонном режиме (HFP). Воспроизведение недоступно во время записи через тот же BT девайс. Попробуйте остановить запись или дождаться переключения профиля.")

            raise Exception("Не удалось инициализировать аудио поток ни с одним из доступных устройств")

        except Exception as e:
            self.audio_error = True
            self.audio_error_message = str(e)
            logger.error(f"❌ Критическая ошибка инициализации аудио: {e}")
            raise

    def _resolve_output_device(self):
        """Возвращает индекс системного default output устройства CoreAudio или None.
        Предпочитаем CoreAudio host API (фактический системный выбор), затем пробуем sd.default.
        """
        try:
            # 1) CoreAudio host API — фактический системный дефолт
            try:
                hostapis = sd.query_hostapis()
                core_audio_idx = None
                for idx, api in enumerate(hostapis):
                    name = api.get('name', '')
                    if 'core' in name.lower():
                        core_audio_idx = idx
                        break
                if core_audio_idx is None:
                    core_audio_idx = 0  # fallback
                api = sd.query_hostapis(core_audio_idx)
                d = api.get('default_output_device', -1)
                if d is not None and d != -1:
                    try:
                        info = sd.query_devices(d)
                        if info.get('max_output_channels', 0) > 0:
                            logger.debug(f"🔊 Default output (CoreAudio): {info.get('name')} (index={d})")
                            return d
                    except Exception:
                        pass
            except Exception:
                pass

            # 2) sd.default.device как запасной вариант
            try:
                default = sd.default.device
                if isinstance(default, (list, tuple)) and len(default) >= 2:
                    default_out = default[1]
                    if default_out is not None and default_out != -1:
                        try:
                            info = sd.query_devices(default_out)
                            if info.get('max_output_channels', 0) > 0:
                                logger.debug(f"🔊 Default output (sd.default): {info.get('name')} (index={default_out})")
                                return default_out
                        except Exception:
                            pass
            except Exception:
                pass

            logger.warning("⚠️ Default output не определён — верну None (пусть PortAudio решит)")
            return None
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить default output: {e} — использую None")
            return None

    def _monitor_output_device_changes(self):
        """Следит за сменой выходного устройства и перезапускает поток при изменении."""
        try:
            while self.is_playing and not self.stop_output_monitor.is_set():
                try:
                    # Упрощенный режим: всегда следуем системному default без приостановок

                    new_device = self._resolve_output_device()
                    if new_device != self.current_output_device:
                        # Дебаунс: требуем два подряд одинаковых чтения default
                        if self._pending_output_device == new_device:
                            self._pending_output_count += 1
                        else:
                            self._pending_output_device = new_device
                            self._pending_output_count = 1

                        if self._pending_output_count >= 2:
                            old = self.current_output_device
                            if self._restart_output_stream(new_device):
                                self.current_output_device = new_device
                                logger.info(f"🔄 Переключил выходное устройство: {old} → {new_device}")
                            self._pending_output_device = None
                            self._pending_output_count = 0
                except Exception:
                    pass
                time.sleep(0.5)
        except Exception:
            pass

    def _restart_output_stream(self, new_device) -> bool:
        """Останавливает текущий OutputStream и запускает новый для нового устройства."""
        try:
            try:
                old_info, old_name = self._get_device_info(self.current_output_device)
                new_info, new_name = self._get_device_info(new_device)
                logger.info(f"🎛️ restart_output_stream: {old_name} → {new_name}")
            except Exception:
                pass
            with self.stream_lock:
                if self.stream:
                    try:
                        if hasattr(self.stream, 'active') and self.stream.active:
                            self.stream.stop()
                        self.stream.close()
                    except Exception:
                        pass
                    self.stream = None
            # Создаем новый поток с авто-подбором параметров
            self.stream = self._safe_init_stream(preferred_device=new_device)
            try:
                logger.info(f"✅ OutputStream restarted on device index={new_device}")
            except Exception:
                pass
            return True
        except Exception as e:
            logger.warning(f"⚠️ Не удалось переключить выходное устройство: {e}")
            return False

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
        
        # Сбрасываем счетчик join() для корректной работы
        try:
            self.audio_queue.join()
        except Exception:
            pass

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
            
        if queue_size == 0 and buffer_size == 0:
            logger.info("✅ Аудио уже завершено")
            return True
        else:
            logger.info(f"📊 Аудио еще воспроизводится: очередь={queue_size}, буфер={buffer_size}")
            return False

    def play_beep(self, frequency: float = 1000.0, duration_sec: float = 0.12, volume: float = 0.4):
        """
        Проигрывает короткий сигнал (beep) через текущую систему воспроизведения.
        - frequency: частота тона в Гц
        - duration_sec: длительность сигнала в секундах
        - volume: громкость [0.0..1.0]
        """
        try:
            # Гарантируем запуск воспроизведения
            if not self.is_playing:
                self.start_playback()

            # Генерируем синусоидальную волну
            num_samples = int(self.sample_rate * duration_sec)
            if num_samples <= 0:
                return

            t = np.linspace(0, duration_sec, num_samples, endpoint=False)
            waveform = np.sin(2 * np.pi * frequency * t)
            amplitude = int(32767 * max(0.0, min(volume, 1.0)))
            samples = (amplitude * waveform).astype(np.int16)

            # Добавляем в очередь для воспроизведения
            self.add_chunk(samples)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось воспроизвести сигнал: {e}")

    def start_audio_monitoring(self):
        """
        Запускает фоновый мониторинг завершения аудио.
        НЕ блокирует основной поток!
        """
        logger.info("🎵 Запускаю фоновый мониторинг аудио...")
        
        # Создаем фоновую задачу для мониторинга
        import threading
        
        def monitor_audio():
            """Фоновая функция мониторинга"""
            try:
                while self.is_playing:
                    time.sleep(0.5)  # Проверяем каждые 500ms
                    
                    # Проверяем статус
                    queue_size = self.audio_queue.qsize()
                    with self.buffer_lock:
                        buffer_size = len(self.internal_buffer)
                    
                    # Если все воспроизведено - останавливаем
                    if queue_size == 0 and buffer_size == 0:
                        logger.info("✅ Аудио завершено, останавливаю мониторинг")
                        self.is_playing = False
                        break
                        
                logger.info("✅ Мониторинг аудио завершен")
                
            except Exception as e:
                logger.error(f"❌ Ошибка в мониторинге аудио: {e}")
                self.is_playing = False
        
        # Запускаем мониторинг в отдельном потоке
        self.monitor_thread = threading.Thread(target=monitor_audio, daemon=True)
        self.monitor_thread.start()
        logger.info("✅ Мониторинг аудио запущен в фоне")

    async def cleanup(self):
        """Очистка ресурсов плеера."""
        self.stop_playback()
        logger.info("Ресурсы AudioPlayer очищены.")

    def get_audio_status(self):
        """
        Возвращает статус аудио системы и информацию об ошибках.
        """
        return {
            'is_playing': self.is_playing,
            'has_error': self.audio_error,
            'error_message': self.audio_error_message,
            'stream_active': self.stream is not None and hasattr(self.stream, 'active') and self.stream.active,
            'queue_size': self.audio_queue.qsize(),
            'buffer_size': len(self.internal_buffer)
        }

    def reset_audio_error(self):
        """
        Сбрасывает флаги ошибок аудио для повторной попытки инициализации.
        """
        self.audio_error = False
        self.audio_error_message = ""
        logger.info("🔄 Флаги ошибок аудио сброшены")

    def clear_all_audio_data(self):
        """ПРИНУДИТЕЛЬНО очищает ВСЕ аудио данные - включая очередь и активное воспроизведение"""
        clear_time = time.time()
        logger.warning(f"🚨 clear_all_audio_data() вызван в {clear_time:.3f}")
        
        try:
            # Логируем состояние ДО очистки
            queue_before = self.audio_queue.qsize()
            buffer_before = len(self.internal_buffer)
            stream_active = hasattr(self, 'stream') and self.stream and hasattr(self.stream, 'active') and self.stream.active
            logger.warning(f"   📊 Состояние ДО: queue={queue_before}, buffer={buffer_before}, stream_active={stream_active}")
            
            logger.warning("🚨 ПРИНУДИТЕЛЬНАЯ очистка ВСЕХ аудио данных...")
            
            # 1️⃣ ПРИНУДИТЕЛЬНО очищаем очередь чанков
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.task_done()
                except:
                    pass
            
            # 2️⃣ ДОПОЛНИТЕЛЬНАЯ очистка очереди через mutex
            try:
                with self.audio_queue.mutex:
                    self.audio_queue.queue.clear()
                logger.warning("🚨 Очередь ПРИНУДИТЕЛЬНО очищена через mutex!")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка очистки через mutex: {e}")
            
            # 3️⃣ ПРИНУДИТЕЛЬНО очищаем внутренний буфер
            with self.buffer_lock:
                self.internal_buffer = np.array([], dtype=np.int16)
            
            # 4️⃣ ПРИНУДИТЕЛЬНО останавливаем поток воспроизведения
            if hasattr(self, 'stream') and self.stream:
                try:
                    if hasattr(self.stream, 'active') and self.stream.active:
                        self.stream.abort()  # Агрессивная остановка
                        logger.warning("🚨 Аудио поток ПРИНУДИТЕЛЬНО остановлен через abort!")
                    self.stream.close()
                    self.stream = None
                    logger.warning("🚨 Аудио поток ПРИНУДИТЕЛЬНО закрыт!")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка остановки потока: {e}")
            
            # 5️⃣ Сбрасываем состояние
            self.is_playing = False
            
            # 6️⃣ ПРИНУДИТЕЛЬНО останавливаем все звуковые потоки
            try:
                sd.stop()  # Останавливает все звуковые потоки
                logger.warning("🚨 ВСЕ звуковые потоки ПРИНУДИТЕЛЬНО остановлены!")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка остановки всех потоков: {e}")
            
            # 7️⃣ ДОПОЛНИТЕЛЬНАЯ очистка через _clear_buffers
            try:
                self._clear_buffers()
                logger.warning("🚨 Дополнительная очистка буферов выполнена!")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка дополнительной очистки: {e}")
            
            # 8️⃣ Устанавливаем временную блокировку буфера
            try:
                self.set_buffer_lock()
                logger.warning("🚨 Временная блокировка буфера установлена!")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка установки временной блокировки: {e}")
            
            # Логируем состояние ПОСЛЕ очистки
            queue_after = self.audio_queue.qsize()
            buffer_after = len(self.internal_buffer)
            total_time = (time.time() - clear_time) * 1000
            logger.warning(f"   📊 Состояние ПОСЛЕ: queue={queue_after}, buffer={buffer_after}")
            logger.warning(f"   ⏱️ Общее время очистки: {total_time:.1f}ms")
            
            # Проверяем результат
            if queue_after == 0 and buffer_after == 0:
                logger.warning("   🎯 ОЧИСТКА УСПЕШНА - все буферы пусты!")
            else:
                logger.warning(f"   ⚠️ ОЧИСТКА НЕПОЛНАЯ - queue={queue_after}, buffer={buffer_after}")
            
            logger.warning("✅ ВСЕ аудио данные ПРИНУДИТЕЛЬНО очищены!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке всех аудио данных: {e}")
            import traceback
            logger.error(f"   🔍 Traceback: {traceback.format_exc()}")

    def interrupt_immediately(self):
        """МГНОВЕННОЕ прерывание без ожидания - для критических ситуаций"""
        try:
            logger.warning("🚨 МГНОВЕННОЕ прерывание аудио...")
            
            # 1️⃣ НЕМЕДЛЕННО устанавливаем флаги прерывания
            self.interrupt_flag.set()
            self.stop_event.set()
            
            # 2️⃣ ПРИНУДИТЕЛЬНО очищаем буферы
            with self.buffer_lock:
                self.internal_buffer = np.array([], dtype=np.int16)
            
            # 3️⃣ Очищаем очередь чанков
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.task_done()
                except:
                    pass
            
            # 4️⃣ Сбрасываем состояние
            self.is_playing = False
            
            logger.warning("✅ МГНОВЕННОЕ прерывание аудио выполнено!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при мгновенном прерывании: {e}")

    def force_stop(self, immediate=False):
        """Универсальный метод остановки аудио с опцией мгновенной остановки"""
        if immediate:
            logger.info("🚨 force_stop(immediate=True) вызван - МГНОВЕННАЯ остановка")
        else:
            logger.info("🚨 force_stop() вызван - обычная остановка")
        
        try:
            # 1️⃣ Устанавливаем флаг остановки
            self.stop_event.set()
            self.is_playing = False
            
            # 2️⃣ Останавливаем поток воспроизведения
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
                    timeout = 0.5
                
                self.playback_thread.join(timeout=timeout)
                if self.playback_thread.is_alive():
                    logger.warning(f"   ⚠️ Поток воспроизведения не остановился в таймаут {timeout}s")
                else:
                    logger.info("   ✅ Поток воспроизведения остановлен")
            
            # 3️⃣ Останавливаем аудио поток
            if self.stream and self.stream.active:
                if immediate:
                    logger.info("   🚨 МГНОВЕННО останавливаю аудио поток...")
                    try:
                        self.stream.stop()
                        self.stream.close()
                        self.stream = None
                        logger.info("   ✅ Аудио поток МГНОВЕННО остановлен")
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
            
            if immediate:
                logger.info("✅ force_stop(immediate=True) завершен")
            else:
                logger.info("✅ force_stop() завершен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в force_stop: {e}")
    
    def force_stop_playback(self):
        """МГНОВЕННО останавливает воспроизведение аудио (alias для force_stop(immediate=True))"""
        return self.force_stop(immediate=True)
    
    def stop_all_audio_threads(self):
        """Останавливает все аудио потоки"""
        logger.info("🚨 stop_all_audio_threads() вызван")
        
        try:
            # 1️⃣ Останавливаем основной поток воспроизведения
            if self.playback_thread and self.playback_thread.is_alive():
                logger.info("   🚨 Останавливаю основной поток воспроизведения...")
                self.stop_event.set()
                self.playback_thread.join(timeout=0.2)
                if self.playback_thread.is_alive():
                    logger.warning("   ⚠️ Основной поток не остановился в таймаут")
                else:
                    logger.info("   ✅ Основной поток остановлен")
            
            # 2️⃣ Останавливаем все дочерние потоки
            import threading
            current_thread = threading.current_thread()
            all_threads = threading.enumerate()
            
            audio_threads = []
            for thread in all_threads:
                if (thread != current_thread and 
                    thread != threading.main_thread() and 
                    thread.is_alive() and
                    'audio' in thread.name.lower()):
                    audio_threads.append(thread)
            
            if audio_threads:
                logger.info(f"   🚨 Найдено {len(audio_threads)} аудио потоков для остановки")
                for thread in audio_threads:
                    try:
                        logger.info(f"   🚨 Останавливаю поток: {thread.name}")
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
            else:
                logger.info("   ✅ Дополнительные аудио потоки не найдены")
            
            # 3️⃣ Останавливаем аудио поток
            if self.stream and self.stream.active:
                logger.info("   🚨 Останавливаю аудио поток...")
                try:
                    self.stream.stop()
                    self.stream.close()
                    self.stream = None
                    logger.info("   ✅ Аудио поток остановлен")
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка остановки аудио потока: {e}")
            
            logger.info("✅ stop_all_audio_threads завершен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в stop_all_audio_threads: {e}")
    
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
            self.audio_error = True
            self.audio_error_message = f"Не удалось получить список аудио устройств: {e}"
    
    def set_buffer_lock(self, duration=None):
        """Устанавливает временную блокировку буфера для предотвращения добавления новых чанков."""
        if duration is None:
            duration = self.buffer_block_duration
        
        self.buffer_blocked_until = time.time() + duration
        logger.warning(f"🚨 Временная блокировка буфера установлена на {duration:.1f} секунд")
    
    def is_buffer_locked(self):
        """Проверяет, заблокирован ли буфер временно."""
        return time.time() < self.buffer_blocked_until