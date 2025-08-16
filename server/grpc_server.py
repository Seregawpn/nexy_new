import asyncio
import logging
import grpc
from concurrent.futures import ThreadPoolExecutor
import sys
import os
import numpy as np

# Добавляем корневую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streaming_pb2
import streaming_pb2_grpc
from config import Config
from text_processor import TextProcessor
from audio_generator import AudioGenerator

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StreamingServicer(streaming_pb2_grpc.StreamingServiceServicer):
    """gRPC сервис для стриминга аудио и текста"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.audio_generator = AudioGenerator()
    
    def StreamAudio(self, request, context):
        """Стриминг аудио и текста в ответ на промпт через LangChain streaming"""
        prompt = request.prompt
        screenshot_base64 = request.screenshot if request.HasField('screenshot') else None
        screen_width = request.screen_width if request.HasField('screen_width') else 0
        screen_height = request.screen_height if request.HasField('screen_height') else 0
        
        logger.info(f"Получен промпт: {prompt}")
        if screenshot_base64:
            logger.info(f"Получен скриншот: {screen_width}x{screen_height} пикселей, {len(screenshot_base64)} символов Base64")
        else:
            logger.info("Скриншот не предоставлен")
        
        try:
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

def serve():
    """Запуск gRPC сервера"""
    try:
        # Проверяем конфигурацию
        Config.validate()
        logger.info("Конфигурация успешно проверена.")
        
        # Создаем сервер
        server = grpc.server(
            ThreadPoolExecutor(max_workers=10),
            options=[
                ('grpc.max_send_message_length', 50 * 1024 * 1024),  # 50MB
                ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
                ('grpc.max_metadata_size', 1024 * 1024),  # 1MB
            ]
        )
        
        # Добавляем сервис
        streaming_pb2_grpc.add_StreamingServiceServicer_to_server(
            StreamingServicer(), server
        )
        
        # Запускаем сервер
        listen_addr = '[::]:50051'
        server.add_insecure_port(listen_addr)
        server.start()
        
        logger.info(f"gRPC сервер запущен на {listen_addr}")
        logger.info("Нажмите Ctrl+C для остановки...")
        
        # Ждем завершения
        server.wait_for_termination()
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"Ошибка запуска сервера: {e}")
    finally:
        if 'server' in locals():
            server.stop(0)
            logger.info("Сервер остановлен.")

if __name__ == "__main__":
    serve()
