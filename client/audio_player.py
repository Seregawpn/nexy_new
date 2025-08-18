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
        self.interrupt_flag.clear()  # Сбрасываем флаг прерывания
        
        try:
            # Используем больший буфер для плавности
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                callback=self._playback_callback,
                blocksize=4096,  # Увеличиваем размер блока
                latency='high'    # Используем высокую задержку для стабильности
            )
            self.stream.start()
            self.is_playing = True
            logger.info("Аудиопоток успешно запущен.")
        except Exception as e:
            logger.error(f"Не удалось запустить аудиопоток: {e}")
            # Попытка найти и использовать другое устройство
            try:
                logger.info("Попытка использовать устройство по умолчанию...")
                sd.default.device = None
                self.stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=self.dtype,
                    callback=self._playback_callback,
                    blocksize=4096,
                    latency='high'
                )
                self.stream.start()
                self.is_playing = True
                logger.info("Аудиопоток успешно запущен на устройстве по умолчанию.")
            except Exception as e_default:
                logger.critical(f"Не удалось запустить аудиопоток и на устройстве по умолчанию: {e_default}")

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
        
        # Очищаем очередь и буфер
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
        
        # Немедленно останавливаем stream, не дожидаясь завершения буфера
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                self.stream = None
                logger.info("✅ Аудиопоток остановлен")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при остановке потока: {e}")
        
        # Очищаем все буферы и очереди
        self._clear_buffers()
        
        # Сбрасываем состояние
        self.is_playing = False
        self.stop_event.set()  # Сигнализируем всем процессам остановку
        
        # Принудительно останавливаем поток воспроизведения
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=0.1)
            logger.info("✅ Поток воспроизведения остановлен")
        
        logger.info("✅ Воспроизведение прервано, очереди очищены.")

    def _clear_buffers(self):
        """Очищает внутренний буфер и очередь аудио."""
        with self.buffer_lock:
            self.internal_buffer = np.array([], dtype=np.int16)
            
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()
        
        # Сбрасываем счетчик join()
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.task_done()
            except queue.Empty:
                break

    def wait_for_queue_empty(self):
        """
        Блокирует выполнение до тех пор, пока все аудио из очереди и внутреннего буфера 
        не будет воспроизведено.
        """
        logger.info(f"⏳ Ожидание завершения воспроизведения. В очереди: {self.audio_queue.qsize()}, в буфере: {len(self.internal_buffer)} сэмплов")
        
        # 1. Ждем, пока очередь аудио не будет полностью передана во внутренний буфер
        self.audio_queue.join()
        logger.info("✅ Очередь аудио передана во внутренний буфер.")
        
        # 2. Ждем, пока внутренний буфер не будет полностью воспроизведен (опустошен)
        timeout = 10.0  # Максимум 10 секунд ожидания
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            # Проверяем флаг прерывания
            if self.interrupt_flag.is_set():
                logger.info("🔇 Прерывание обнаружено! Останавливаем ожидание.")
                break
                
            with self.buffer_lock:
                buffer_size = len(self.internal_buffer)
            
            if buffer_size == 0:
                logger.info("✅ Внутренний буфер полностью опустошен.")
                break
            
            # Логируем прогресс, но не слишком часто
            logger.info(f"⏳ Ожидание опустошения буфера: {buffer_size} сэмплов осталось...")
            time.sleep(0.1)  # Спим вне блокировки
        else:
            # Этот блок выполнится, если цикл завершился по таймауту
            logger.warning(f"⚠️ Таймаут ожидания! Воспроизведение остановлено. Осталось в буфере: {len(self.internal_buffer)} сэмплов")

        logger.info(f"✅ Воспроизведение завершено. Финальный размер очереди: {self.audio_queue.qsize()}, буфера: {len(self.internal_buffer)}")

    async def cleanup(self):
        """Очистка ресурсов плеера."""
        self.stop_playback()
        logger.info("Ресурсы AudioPlayer очищены.")