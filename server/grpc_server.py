import asyncio
import logging
import grpc
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
    """gRPC сервис для стриминга аудио и текста"""
    
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

    def StreamAudio(self, request, context):
        """Стриминг аудио и текста в ответ на промпт через LangChain streaming"""
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
            # АСИНХРОННО: Обрабатываем Hardware ID в базе данных (не блокируем основной поток)
            if hardware_id and self.db_manager:
                # Формируем информацию об экране для передачи в метод
                screen_info_for_db = {}
                if screen_width > 0 and screen_height > 0:
                    screen_info_for_db = {
                        'width': screen_width,
                        'height': screen_height
                    }
                self._process_hardware_id_async(hardware_id, prompt, screenshot_base64, screen_info_for_db)
            
            # Запускаем LangChain streaming для получения токенов в реальном времени
            logger.info("Запускаю LangChain streaming через Gemini...")
            
            # Создаем новый event loop для асинхронных операций
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Формируем информацию об экране
                screen_info = {}
                if screen_width > 0 and screen_height > 0:
                    screen_info = {
                        'width': screen_width,
                        'height': screen_height
                    }
                
                # Собираем все токены из асинхронного генератора
                async def collect_tokens():
                    tokens = []
                    async for token in self.text_processor.generate_response_stream(
                        prompt, 
                        screenshot_base64, 
                        screen_info
                    ):
                        if token and token.strip():
                            tokens.append(token)
                    return tokens
                
                # Запускаем асинхронную функцию
                tokens = loop.run_until_complete(collect_tokens())
                
                if not tokens:
                    logger.error("LangChain не вернул токены")
                    error_response = streaming_pb2.StreamResponse(
                        error_message="Не удалось сгенерировать ответ"
                    )
                    yield error_response
                    return
                
                logger.info(f"Получено {len(tokens)} токенов от LangChain Gemini")
                
                # Обрабатываем каждый токен
                for token in tokens:
                    if token and token.strip():
                        # Отправляем токен клиенту
                        text_response = streaming_pb2.StreamResponse(
                            text_chunk=token
                        )
                        yield text_response
                        
                        # Генерируем аудио для этого токена
                        try:
                            audio_chunks = self.audio_generator.generate_audio_sync(token)
                            
                            if audio_chunks:
                                logger.debug(f"Сгенерировано {len(audio_chunks)} аудио чанков для токена: {token[:30]}...")
                                
                                # Отправляем каждый аудио чанк
                                for audio_chunk in audio_chunks:
                                    audio_response = streaming_pb2.StreamResponse(
                                        audio_chunk=streaming_pb2.AudioChunk(
                                            audio_data=audio_chunk.tobytes(),
                                            dtype=str(audio_chunk.dtype),
                                            shape=list(audio_chunk.shape)
                                        )
                                    )
                                    yield audio_response
                            else:
                                logger.warning(f"Не удалось сгенерировать аудио для токена: {token[:30]}...")
                                
                        except Exception as audio_error:
                            logger.error(f"Ошибка генерации аудио для токена: {audio_error}")
                            # Продолжаем без аудио
                
                # Отправляем сообщение о завершении
                end_response = streaming_pb2.StreamResponse(
                    end_message="Стриминг завершен"
                )
                yield end_response
                    
                logger.info("LangChain streaming завершен для данного промпта.")
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Произошла ошибка в LangChain streaming: {e}")
            error_response = streaming_pb2.StreamResponse(
                error_message=f"Произошла внутренняя ошибка: {e}"
            )
            yield error_response
    
    def _process_hardware_id_async(self, hardware_id: str, prompt: str, screenshot_base64: str = None, screen_info: dict = None):
        """Асинхронная обработка Hardware ID в базе данных (не блокирует основной поток)"""
        try:
            # Запускаем в отдельном потоке для неблокирующей обработки
            import threading
            
            def process_in_thread():
                try:
                    if not self.db_manager:
                        logger.warning("⚠️ База данных недоступна для обработки Hardware ID")
                        return
                    
                    logger.info(f"🆔 Асинхронная обработка Hardware ID: {hardware_id[:16]}...")
                    logger.info(f"📝 Команда: {prompt[:50]}...")
                    
                    # 1. Получаем или создаем пользователя
                    user = self.db_manager.get_user_by_hardware_id(hardware_id)
                    if not user:
                        # Создаем нового пользователя
                        user_metadata = {
                            "hardware_id": hardware_id,
                            "first_command": prompt,
                            "created_via": "gRPC"
                        }
                        user_id = self.db_manager.create_user(hardware_id, user_metadata)
                        if user_id:
                            logger.info(f"✅ Создан новый пользователь: {user_id}")
                        else:
                            logger.error("❌ Не удалось создать пользователя")
                            return
                    else:
                        user_id = user['id']
                        logger.info(f"✅ Найден существующий пользователь: {user_id}")
                    
                    # 2. Создаем новую сессию
                    session_metadata = {
                        "prompt": prompt,
                        "has_screenshot": bool(screenshot_base64),
                        "screen_resolution": f"{screen_info.get('width', 0)}x{screen_info.get('height', 0)}" if screen_info else "unknown"
                    }
                    session_id = self.db_manager.create_session(user_id, session_metadata)
                    if not session_id:
                        logger.error("❌ Не удалось создать сессию")
                        return
                    
                    logger.info(f"✅ Создана сессия: {session_id}")
                    
                    # 3. Сохраняем команду
                    command_metadata = {
                        "prompt_length": len(prompt),
                        "has_screenshot": bool(screenshot_base64),
                        "screen_info": screen_info or {}
                    }
                    command_id = self.db_manager.create_command(session_id, prompt, command_metadata)
                    if not command_id:
                        logger.error("❌ Не удалось сохранить команду")
                        return
                    
                    logger.info(f"✅ Команда сохранена: {command_id}")
                    
                    # 4. Сохраняем скриншот (если есть)
                    if screenshot_base64:
                        screenshot_metadata = {
                            "base64_length": len(screenshot_base64),
                            "screen_resolution": f"{screen_info.get('width', 0)}x{screen_info.get('height', 0)}" if screen_info else "unknown",
                            "format": "webp_base64"
                        }
                        screenshot_id = self.db_manager.create_screenshot(session_id, screenshot_metadata)
                        if screenshot_id:
                            logger.info(f"✅ Скриншот сохранен: {screenshot_id}")
                        else:
                            logger.warning("⚠️ Не удалось сохранить скриншот")
                    
                    # 5. Сохраняем метрики производительности
                    performance_metadata = {
                        "command_processing": {
                            "prompt_length": len(prompt),
                            "has_screenshot": bool(screenshot_base64),
                            "timestamp": str(datetime.now())
                        }
                    }
                    metric_id = self.db_manager.create_performance_metric(session_id, "command_processing", performance_metadata)
                    if metric_id:
                        logger.info(f"✅ Метрики сохранены: {metric_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка асинхронной обработки Hardware ID: {e}")
                    # Логируем ошибку в базу данных
                    if self.db_manager:
                        try:
                            self.db_manager.create_error_log(
                                session_id=None,
                                error_type="hardware_id_processing",
                                error_message=str(e),
                                metadata={"hardware_id": hardware_id[:16]}
                            )
                        except:
                            pass
            
            # Запускаем в отдельном потоке
            thread = threading.Thread(target=process_in_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска асинхронной обработки Hardware ID: {e}")

def serve():
    """Запуск gRPC сервера"""
    try:
        # Проверяем конфигурацию
        if not Config.validate():
            logger.error("❌ Конфигурация некорректна")
            return
        
        logger.info("Конфигурация успешно проверена.")
        
        # Создаем gRPC сервер
        server = grpc.server(ThreadPoolExecutor(max_workers=Config.MAX_WORKERS))
        streaming_pb2_grpc.add_StreamingServiceServicer_to_server(StreamingServicer(), server)
        
        # Запускаем сервер
        server_address = f"{Config.GRPC_HOST}:{Config.GRPC_PORT}"
        server.add_insecure_port(server_address)
        server.start()
        
        logger.info(f"gRPC сервер запущен на {server_address}")
        logger.info("Нажмите Ctrl+C для остановки...")
        
        # Ждем завершения
        server.wait_for_termination()
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"Ошибка запуска сервера: {e}")
    finally:
        logger.info("Сервер остановлен")

if __name__ == "__main__":
    serve()
