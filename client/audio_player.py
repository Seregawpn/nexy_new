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

    def _playback_callback(self, outdata, frames, time, status):
        """Callback-функция для sounddevice, вызывается для заполнения буфера вывода."""
        if status:
            logger.warning(f"Sounddevice status: {status}")

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
                        while len(self.internal_buffer) < frames and not self.audio_queue.empty():
                            chunk = self.audio_queue.get_nowait()
                            if chunk is not None and len(chunk) > 0:
                                self.internal_buffer = np.concatenate([self.internal_buffer, chunk])
                            self.audio_queue.task_done()
                    except queue.Empty:
                        pass
                    
                    # Теперь проверяем снова
                    if len(self.internal_buffer) >= frames:
                        outdata[:frames] = self.internal_buffer[:frames].reshape(frames, self.channels)
                        self.internal_buffer = self.internal_buffer[frames:]
                    else:
                        # Все еще недостаточно данных, заполняем тишиной
                        available = len(self.internal_buffer)
                        if available > 0:
                            outdata[:available] = self.internal_buffer.reshape(-1, self.channels)
                            outdata[available:frames] = 0
                            self.internal_buffer = np.array([], dtype=np.int16)
                        else:
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
            
        # Добавляем небольшую задержку для синхронизации
        time.sleep(0.01)  # 10ms задержка между чанками
        
        self.audio_queue.put(audio_chunk)
        logger.debug(f"Аудио чанк размером {len(audio_chunk)} добавлен в очередь. Размер очереди: {self.audio_queue.qsize()}")

    def start_playback(self):
        """Запускает аудиопоток для воспроизведения."""
        if self.is_playing:
            logger.info("Воспроизведение уже запущено.")
            return

        logger.info("Запуск потокового воспроизведения аудио...")
        self.stop_event.clear()
        
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
        """Останавливает аудиопоток."""
        if not self.is_playing:
            return
            
        logger.info("Остановка потокового воспроизведения...")
        self.stop_event.set()
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            logger.info("Аудиопоток остановлен и закрыт.")
        
        # Очищаем очередь и буфер
        with self.buffer_lock:
            self.internal_buffer = np.array([], dtype=np.int16)
            
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()
            
        self.is_playing = False

    def wait_for_queue_empty(self):
        """Блокирует выполнение, пока очередь не опустеет."""
        # Ждем немного дольше для завершения воспроизведения
        time.sleep(0.5)
        self.audio_queue.join()
        logger.info("Воспроизведение всех аудио чанков в очереди завершено.")

    async def cleanup(self):
        """Очистка ресурсов плеера."""
        self.stop_playback()
        logger.info("Ресурсы AudioPlayer очищены.")