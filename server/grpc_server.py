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
        """Стриминг аудио и текста в ответ на промпт"""
        prompt = request.prompt
        logger.info(f"Получен промпт: {prompt}")
        
        try:
            # Создаем простой генератор для текста (заглушка)
            def simple_text_generator(text):
                # Разбиваем текст на предложения
                sentences = self.text_processor.split_into_sentences(text)
                for sentence in sentences:
                    yield sentence
            
            # Запускаем стриминг текста
            text_stream = simple_text_generator(prompt)
            
            for sentence in text_stream:
                logger.info(f"Обработка предложения для озвучивания: {sentence}")
                
                # Отправляем текст клиенту
                text_response = streaming_pb2.StreamResponse(
                    text_chunk=sentence
                )
                yield text_response
                
                # Генерируем и отправляем аудио (синхронно)
                try:
                    # Генерируем реальное аудио через Edge TTS
                    audio_chunks = self.audio_generator.generate_audio_sync(sentence)
                    
                    if audio_chunks:
                        logger.info(f"Сгенерировано {len(audio_chunks)} аудио чанков для: {sentence}")
                        
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
                        logger.warning(f"Не удалось сгенерировать аудио для: {sentence}")
                    
                except Exception as audio_error:
                    logger.error(f"Ошибка генерации аудио: {audio_error}")
                    # Продолжаем без аудио
            
            # Отправляем сообщение о завершении
            end_response = streaming_pb2.StreamResponse(
                end_message="Стриминг завершен"
            )
            yield end_response
                
            logger.info("Стриминг завершен для данного промпта.")
            
        except Exception as e:
            logger.error(f"Произошла ошибка в стриминге: {e}")
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
