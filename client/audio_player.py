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
        self.interrupt_flag = threading.Event()  # Флаг для мгновенного прерывания
        
        # Внутренний буфер для плавного воспроизведения
        self.internal_buffer = np.array([], dtype=np.int16)
        self.buffer_lock = threading.Lock()
        
        # Флаг для отслеживания ошибок аудио
        self.audio_error = False
        self.audio_error_message = ""
        
        # Проверяем доступность аудио устройств
        self._check_audio_devices()

    def _playback_callback(self, outdata, frames, time, status):
        """Callback-функция для sounddevice, вызывается для заполнения буфера вывода."""
        if status:
            logger.warning(f"Sounddevice status: {status}")

        # Проверяем флаг прерывания
        if self.interrupt_flag.is_set():
            outdata.fill(0)
            return

        try:
            with self.buffer_lock:
                # Проверяем внутренний буфер
                if len(self.internal_buffer) >= frames:
                    # Достаточно данных в буфере
                    outdata[:frames] = self.internal_buffer[:frames].reshape(frames, self.channels)
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
                        outdata[:frames] = self.internal_buffer[:frames].reshape(frames, self.channels)
                        self.internal_buffer = self.internal_buffer[frames:]
                        logger.debug(f"🎵 Отправлено в аудио: {frames} сэмплов. Осталось в буфере: {len(self.internal_buffer)}")
                    else:
                        # Все еще недостаточно данных, заполняем тишиной
                        available = len(self.internal_buffer)
                        if available > 0:
                            outdata[:available] = self.internal_buffer.reshape(-1, self.channels)
                            outdata[available:frames] = 0
                            self.internal_buffer = np.array([], dtype=np.int16)
                            logger.debug(f"🎵 Отправлено доступных: {available} сэмплов, остальное тишина")
                        else:
                            # Если нет данных, принудительно проверяем очередь еще раз
                            try:
                                while not self.audio_queue.empty():
                                    chunk = self.audio_queue.get_nowait()
                                    if chunk is not None and len(chunk) > 0:
                                        self.internal_buffer = np.concatenate([self.internal_buffer, chunk])
                                        logger.debug(f"🎵 Принудительно добавлен чанк в буфер: {len(chunk)} сэмплов")
                                    self.audio_queue.task_done()
                                    
                                if len(self.internal_buffer) > 0:
                                    # Теперь у нас есть данные
                                    available = min(len(self.internal_buffer), frames)
                                    outdata[:available] = self.internal_buffer[:available].reshape(available, self.channels)
                                    self.internal_buffer = self.internal_buffer[available:]
                                    outdata[available:frames] = 0
                                    logger.debug(f"🎵 Принудительно отправлено: {available} сэмплов")
                                else:
                                    outdata.fill(0)
                            except queue.Empty:
                                outdata.fill(0)
                            
        except Exception as e:
            logger.error(f"Ошибка в playback callback: {e}")
            outdata.fill(0)

    def add_chunk(self, audio_chunk: np.ndarray):
        """Добавляет фрагмент аудио (NumPy array) в очередь для воспроизведения."""
        if not isinstance(audio_chunk, np.ndarray):
            logger.error("В плеер был передан неверный формат аудио (ожидается NumPy array)")
            return
            
        # Проверяем размер чанка
        if len(audio_chunk) == 0:
            logger.warning("Получен пустой аудио чанк")
            return
            
        # Убираем задержку - она может замедлять обработку чанков
        # time.sleep(0.01)  # 10ms задержка между чанками
        
        self.audio_queue.put(audio_chunk)
        logger.info(f"🎵 Аудио чанк размером {len(audio_chunk)} добавлен в очередь. Размер очереди: {self.audio_queue.qsize()}")
        logger.info(f"📊 Общий размер внутреннего буфера: {len(self.internal_buffer)} сэмплов")

    def start_playback(self):
        """Запускает аудиопоток для воспроизведения."""
        if self.is_playing:
            logger.info("Воспроизведение уже запущено.")
            return

        logger.info("Запуск потокового воспроизведения аудио...")
        self.stop_event.clear()
        self.interrupt_flag.clear()  # Сбрасываем флаг перед началом нового воспроизведения
        self._clear_buffers()  # Очищаем буферы перед началом
        
        try:
            # Используем безопасную инициализацию
            self.stream = self._safe_init_stream()
            self.is_playing = True
            logger.info("Аудиопоток успешно запущен.")
        except Exception as e:
            logger.error(f"❌ Не удалось запустить аудиопоток: {e}")
            self.audio_error = True
            self.audio_error_message = str(e)
            # Не устанавливаем is_playing = True, так как поток не создан
            raise

    def stop_playback(self):
        """Останавливает аудиопоток и очищает ресурсы."""
        if not self.is_playing:
            return
            
        logger.info("Остановка потокового воспроизведения...")
        self.stop_event.set()
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            logger.info("Аудиопоток остановлен и закрыт.")
        
        self._clear_buffers()
        self.is_playing = False

    def interrupt(self):
        """
        Мгновенно прерывает воспроизведение и очищает все очереди.
        Используется для немедленной реакции на действия пользователя.
        """
        logger.info("🔇 Прерывание воспроизведения...")
        
        # Устанавливаем флаг прерывания
        self.interrupt_flag.set()
        
        # Немедленно останавливаем поток воспроизведения
        if self.stream and hasattr(self.stream, 'active') and self.stream.active:
            try:
                self.stream.stop()
                self.stream.close()
                self.stream = None
                logger.info("✅ Аудиопоток принудительно остановлен")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при принудительной остановке потока: {e}")
        
        # Немедленно очищаем все буферы и очереди
        self._clear_buffers()
        
        # Сбрасываем состояние
        self.is_playing = False
        self.stop_event.set()
        
        # Сбрасываем флаг прерывания для следующего использования
        self.interrupt_flag.clear()
        
        logger.info("✅ Воспроизведение прервано, очереди очищены.")

    def _safe_init_stream(self):
        """
        Безопасная инициализация аудио потока с обработкой ошибок PortAudio.
        """
        try:
            # Пробуем разные настройки для macOS
            device_settings = [
                {'device': None, 'channels': self.channels},  # Системный по умолчанию
                {'device': 'default', 'channels': self.channels},  # Явно указываем default
                {'device': sd.default.device[1], 'channels': self.channels},  # Только выход
            ]
            
            for settings in device_settings:
                try:
                    logger.info(f"🔄 Пробую инициализировать аудио с настройками: {settings}")
                    
                    # Создаем поток с дополнительными параметрами для macOS
                    stream = sd.OutputStream(
                        samplerate=self.sample_rate,
                        channels=settings['channels'],
                        dtype=self.dtype,
                        device=settings['device'],
                        callback=self._playback_callback,
                        blocksize=1024,  # Уменьшаем размер блока для лучшей совместимости
                        latency='low'     # Низкая задержка
                    )
                    
                    stream.start()
                    logger.info(f"✅ Аудио поток успешно инициализирован с настройками: {settings}")
                    return stream
                    
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось инициализировать с настройками {settings}: {e}")
                    continue
            
            # Если все попытки не удались, пробуем альтернативные настройки
            logger.info("🔄 Пробую альтернативные настройки для macOS...")
            
            # Пробуем с минимальными настройками
            try:
                stream = sd.OutputStream(
                    samplerate=44100,  # Стандартная частота
                    channels=1,        # Моно
                    dtype='int16',     # Стандартный тип
                    callback=self._playback_callback,
                    blocksize=512,     # Минимальный размер блока
                    latency='high'     # Высокая задержка для стабильности
                )
                stream.start()
                logger.info("✅ Аудио поток инициализирован с альтернативными настройками")
                return stream
            except Exception as e:
                logger.warning(f"⚠️ Альтернативные настройки не помогли: {e}")
            
            # Если все попытки не удались
            raise Exception("Не удалось инициализировать аудио поток ни с одним из доступных устройств")
            
        except Exception as e:
            self.audio_error = True
            self.audio_error_message = str(e)
            logger.error(f"❌ Критическая ошибка инициализации аудио: {e}")
            raise

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
        Неблокирующее ожидание завершения воспроизведения.
        Позволяет добавлять новые чанки во время ожидания.
        """
        if not self.is_playing:
            logger.info("Ожидание не требуется, плеер не активен.")
            return
            
        logger.info(f"⏳ Ожидание завершения воспроизведения. В очереди: {self.audio_queue.qsize()}, в буфере: {len(self.internal_buffer)} сэмплов")
        
        # 1. Ждем, пока очередь аудио не будет полностью передана во внутренний буфер
        timeout = 2.0  # Уменьшаем таймаут для более быстрой реакции
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            if self.interrupt_flag.is_set() or not self.is_playing:
                logger.info("🔇 Обнаружено прерывание, ожидание очереди остановлено.")
                return
                
            if self.audio_queue.empty():
                logger.info("✅ Очередь аудио пуста.")
                break
            
            logger.info(f"⏳ Ожидание опустошения очереди: {self.audio_queue.qsize()} чанков осталось...")
            time.sleep(0.05)  # Уменьшаем интервал для более быстрой реакции
        else:
            logger.warning(f"⚠️ Таймаут ожидания очереди! Осталось: {self.audio_queue.qsize()} чанков")
        
        # 2. Ждем, пока внутренний буфер не будет полностью воспроизведен
        timeout = 3.0  # Уменьшаем таймаут для более быстрой реакции
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            if self.interrupt_flag.is_set() or not self.is_playing:
                logger.info("🔇 Обнаружено прерывание, ожидание буфера остановлено.")
                return
                
            with self.buffer_lock:
                buffer_size = len(self.internal_buffer)
            
            # Дополнительная проверка, чтобы убедиться, что очередь все еще пуста
            if buffer_size == 0 and self.audio_queue.empty():
                logger.info("✅ Внутренний буфер пуст и очередь пуста.")
                break
            
            logger.info(f"⏳ Ожидание опустошения буфера: {buffer_size} сэмплов осталось...")
            time.sleep(0.05)  # Уменьшаем интервал для более быстрой реакции
        else:
            logger.warning(f"⚠️ Таймаут ожидания буфера! Осталось: {len(self.internal_buffer)} сэмплов")

        logger.info(f"✅ Воспроизведение завершено. Финальный размер очереди: {self.audio_queue.qsize()}, буфера: {len(self.internal_buffer)}")
        self.stop_playback()

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

    def force_stop(self):
        """
        Принудительная остановка воспроизведения в критических ситуациях.
        Используется когда обычные методы не работают.
        """
        logger.warning("🚨 Принудительная остановка воспроизведения...")
        
        # Устанавливаем все флаги остановки
        self.interrupt_flag.set()
        self.stop_event.set()
        
        # Принудительно останавливаем поток
        if self.stream:
            try:
                if hasattr(self.stream, 'stop'):
                    self.stream.stop()
                if hasattr(self.stream, 'close'):
                    self.stream.close()
                self.stream = None
                logger.info("✅ Поток принудительно остановлен")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при принудительной остановке: {e}")
        
        # Очищаем все буферы
        self._clear_buffers()
        
        # Сбрасываем состояние
        self.is_playing = False
        
        logger.warning("🚨 Воспроизведение принудительно остановлено")

    def _check_audio_devices(self):
        """Проверяет доступность аудио устройств."""
        try:
            sd.query_devices()
            logger.info("✅ Аудио устройства доступны.")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить список аудио устройств: {e}")
            self.audio_error = True
            self.audio_error_message = f"Не удалось получить список аудио устройств: {e}"