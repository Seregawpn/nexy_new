import asyncio
import base64
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import numpy as np

from config import Config
from text_processor import TextProcessor
from audio_generator import AudioGenerator

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Проверка конфигурации при старте"""
    try:
        Config.validate()
        logger.info("Конфигурация успешно проверена.")
    except ValueError as e:
        logger.critical(f"Ошибка конфигурации: {e}")
        # В реальном приложении здесь можно было бы остановить запуск
        # Но для простоты просто выводим критическую ошибку

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket эндпоинт для стриминга аудио"""
    await websocket.accept()
    logger.info("Клиент подключен по WebSocket.")

    try:
        # Инициализация компонентов для сессии
        text_processor = TextProcessor()
        audio_generator = AudioGenerator()

        while True:
            # Ожидаем промпт от клиента
            data = await websocket.receive_text()
            logger.info(f"Получен промпт: {data}")

            # Запускаем стриминг
            text_stream = text_processor.process_text_stream(data)

            async for sentence in text_stream:
                logger.info(f"Обработка предложения для озвучки: {sentence}")
                if websocket.client_state != WebSocketState.CONNECTED:
                    logger.warning("Клиент отключился, прерываю генерацию.")
                    break
                
                # Отправляем текст клиенту
                await websocket.send_json({"type": "text", "data": sentence})

                # Генерируем и отправляем аудио
                audio_stream = audio_generator.generate_audio_stream(sentence)
                async for audio_chunk in audio_stream:
                    if websocket.client_state != WebSocketState.CONNECTED:
                        logger.warning("Клиент отключился, прерываю отправку аудио.")
                        break
                    
                    # Кодируем NumPy массив в base64 для передачи по JSON
                    encoded_audio = base64.b64encode(audio_chunk.tobytes()).decode('utf-8')
                    await websocket.send_json({
                        "type": "audio",
                        "data": encoded_audio,
                        "dtype": str(audio_chunk.dtype),
                        "shape": audio_chunk.shape
                    })
            
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json({"type": "end", "data": "Стриминг завершен"})
            logger.info("Стриминг завершен для данного промпта.")

    except WebSocketDisconnect:
        logger.info("Клиент отключился.")
    except Exception as e:
        logger.error(f"Произошла ошибка в WebSocket: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({
                "type": "error",
                "data": f"Произошла внутренняя ошибка: {e}"
            })
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
        logger.info("WebSocket соединение закрыто.")

if __name__ == "__main__":
    import uvicorn
    logger.info("Запуск сервера...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
