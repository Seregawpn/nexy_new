import asyncio
import logging
import grpc.aio
from concurrent.futures import ThreadPoolExecutor
import sys
import os
import numpy as np
from datetime import datetime

# Добавляем корневую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streaming_pb2
import streaming_pb2_grpc
from config import Config
from text_processor import TextProcessor
from audio_generator import AudioGenerator
from database.database_manager import DatabaseManager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StreamingServicer(streaming_pb2_grpc.StreamingServiceServicer):
    """gRPC сервис для стриминга аудио и текста (АСИНХРОННАЯ ВЕРСИЯ)"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.audio_generator = AudioGenerator()
        
        # Инициализируем менеджер базы данных
        try:
            db_url = Config.get_database_url()
            self.db_manager = DatabaseManager(db_url)
            if self.db_manager.connect():
                logger.info("✅ База данных подключена успешно")
            else:
                logger.warning("⚠️ Не удалось подключиться к базе данных")
                self.db_manager = None
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            self.db_manager = None

    async def StreamAudio(self, request, context):
        """
        АСИНХРОННЫЙ стриминг аудио и текста в ответ на промпт.
        Использует async for для обработки потоков текста и аудио.
        """
        prompt = request.prompt
        screenshot_base64 = request.screenshot if request.HasField('screenshot') else None
        screen_width = request.screen_width if request.HasField('screen_width') else 0
        screen_height = request.screen_height if request.HasField('screen_height') else 0
        hardware_id = request.hardware_id
        
        logger.info(f"Получен промпт: {prompt}")
        logger.info(f"Hardware ID: {hardware_id}")
        
        if screenshot_base64:
            logger.info(f"Получен скриншот: {screen_width}x{screen_height} пикселей, {len(screenshot_base64)} символов Base64")
        else:
            logger.info("Скриншот не предоставлен")
        
        try:
            # Асинхронная обработка БД (запускаем как фоновую задачу)
            if hardware_id and self.db_manager:
                screen_info_for_db = {'width': screen_width, 'height': screen_height} if screen_width > 0 else {}
                asyncio.create_task(self._process_hardware_id_async(hardware_id, prompt, screenshot_base64, screen_info_for_db))
            
            logger.info("Запускаю LangChain streaming через Gemini...")
            
            screen_info = {'width': screen_width, 'height': screen_height} if screen_width > 0 else {}
            
            # Получаем асинхронный генератор текста
            text_generator = self.text_processor.generate_response_stream(prompt)
            
            # Стримим текст и для каждого куска стримим аудио
            async for text_chunk in text_generator:
                if text_chunk and text_chunk.strip():
                    # 1. Отправляем текстовый чанк клиенту
                    yield streaming_pb2.StreamResponse(text_chunk=text_chunk)
                    
                    # 2. Асинхронно генерируем ПОЛНОЕ аудио для этого предложения
                    try:
                        # Вызываем новый метод, который возвращает один большой массив
                        audio_chunk_complete = await self.audio_generator.generate_complete_audio_for_sentence(text_chunk)
                        
                        if audio_chunk_complete is not None and len(audio_chunk_complete) > 0:
                            # Отправляем этот массив как один аудио-чанк
                            yield streaming_pb2.StreamResponse(
                                audio_chunk=streaming_pb2.AudioChunk(
                                    audio_data=audio_chunk_complete.tobytes(),
                                    dtype=str(audio_chunk_complete.dtype),
                                    shape=list(audio_chunk_complete.shape)
                                )
                            )
                    except Exception as audio_error:
                        logger.error(f"Ошибка генерации аудио для '{text_chunk[:30]}...': {audio_error}")

            logger.info("LangChain streaming завершен для данного промпта.")
                
        except Exception as e:
            logger.error(f"Произошла ошибка в StreamAudio: {e}", exc_info=True)
            yield streaming_pb2.StreamResponse(
                error_message=f"Произошла внутренняя ошибка: {e}"
            )

    async def _process_hardware_id_async(self, hardware_id: str, prompt: str, screenshot_base64: str = None, screen_info: dict = None):
        """Асинхронная обработка информации в базе данных."""
        # Эта функция теперь может быть нативной корутиной, если db_manager поддерживает async
        # Пока что оставляем запуск в executor'е для совместимости с синхронной библиотекой БД
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._process_hardware_id_sync, hardware_id, prompt, screenshot_base64, screen_info)

    def _process_hardware_id_sync(self, hardware_id: str, prompt: str, screenshot_base64: str = None, screen_info: dict = None):
        """Синхронный код для работы с БД, который будет выполняться в ThreadPoolExecutor."""
        try:
            if not self.db_manager:
                logger.warning("⚠️ База данных недоступна для обработки Hardware ID")
                return
            
            logger.info(f"🆔 Обработка Hardware ID в потоке: {hardware_id[:16]}...")
            
            user = self.db_manager.get_user_by_hardware_id(hardware_id)
            if not user:
                user_id = self.db_manager.create_user(hardware_id, {"created_via": "gRPC"})
                logger.info(f"✅ Создан новый пользователь: {user_id}")
            else:
                user_id = user['id']
                logger.info(f"✅ Найден существующий пользователь: {user_id}")

            session_id = self.db_manager.create_session(user_id, {"prompt": prompt})
            logger.info(f"✅ Создана сессия: {session_id}")

            command_metadata = {"has_screenshot": bool(screenshot_base64)}
            if screen_info:
                command_metadata['screen_info'] = screen_info
            self.db_manager.create_command(session_id, prompt, command_metadata)
            logger.info(f"✅ Команда сохранена")

            if screenshot_base64:
                import json
                screenshot_metadata = {
                    "base64_length": len(screenshot_base64),
                    "format": "webp_base64"
                }
                if screen_info:
                    screenshot_metadata["screen_resolution"] = f"{screen_info.get('width', 0)}x{screen_info.get('height', 0)}"
                
                # Преобразуем dict в JSON строку перед сохранением
                self.db_manager.create_screenshot(
                    session_id, 
                    f"/tmp/screenshot_{session_id}.webp", 
                    json.dumps(screenshot_metadata)
                )
                logger.info(f"✅ Скриншот сохранен")

        except Exception as e:
            logger.error(f"❌ Ошибка в потоке обработки Hardware ID: {e}", exc_info=True)


async def serve():
    """Запуск асинхронного gRPC сервера"""
    server = grpc.aio.server()
    streaming_pb2_grpc.add_StreamingServiceServicer_to_server(StreamingServicer(), server)
    
    server_address = f"{Config.GRPC_HOST}:{Config.GRPC_PORT}"
    server.add_insecure_port(server_address)
    
    logger.info(f"Асинхронный gRPC сервер запускается на {server_address}")
    await server.start()
    logger.info("Сервер запущен. Нажмите Ctrl+C для остановки.")
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки, останавливаю сервер...")
        await server.stop(0)
    finally:
        logger.info("Сервер остановлен.")

if __name__ == "__main__":
    # Проверяем конфигурацию перед запуском
    if not Config.validate():
        logger.error("❌ Конфигурация некорректна. Сервер не будет запущен.")
        sys.exit(1)
    
    asyncio.run(serve())
