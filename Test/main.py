"""
## Documentation
Quickstart: https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LiveAPI.py

## Setup

To install the dependencies for this script, run:

```
pip install -r requirements.txt
```

## Environment Variables
Set your Gemini API key:
export GEMINI_API_KEY="your_api_key_here"
"""

import os
import asyncio
import base64
import io
import traceback

import PIL.Image
import mss

import argparse

from google import genai
from google.genai import types

MODEL = "models/gemini-2.5-flash-live-preview"

DEFAULT_MODE = "screen"

client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)

CONFIG = types.LiveConnectConfig(
    response_modalities=[
        "TEXT",
    ],
    media_resolution="MEDIA_RESOLUTION_MEDIUM",  # Возвращаем среднее разрешение
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=25600,
        sliding_window=types.SlidingWindow(target_tokens=12800),
    ),
    # Включаем онлайн поиск
    tools=[
        types.Tool(
            google_search=types.GoogleSearch()
        )
    ]
)


class ScreenAssistant:
    def __init__(self, mode=DEFAULT_MODE):
        self.mode = mode
        self.session = None

    def _get_screen(self):
        """Делает скриншот экрана и возвращает в формате для Gemini"""
        try:
            sct = mss.mss()
            monitor = sct.monitors[0]
            
            # Захватываем скриншот
            screenshot = sct.grab(monitor)
            
            # Конвертируем в JPEG
            image_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)
            img = PIL.Image.open(io.BytesIO(image_bytes))
            
            # Сжимаем до разумного размера
            img.thumbnail([1024, 1024])
            
            # Сохраняем в JPEG
            image_io = io.BytesIO()
            img.save(image_io, format="jpeg", quality=85)
            image_io.seek(0)
            
            image_bytes = image_io.read()
            return {
                "mime_type": "image/jpeg", 
                "data": base64.b64encode(image_bytes).decode('utf-8'),
                "raw_bytes": image_bytes
            }
        except Exception as e:
            print(f"Ошибка при создании скриншота: {e}")
            return None

    async def send_message_with_screenshot(self, text):
        """Отправляет сообщение вместе со скриншотом экрана"""
        try:
            # Делаем скриншот
            print("Делаю скриншот экрана...")
            screenshot = self._get_screen()
            
            if screenshot is None:
                print("Не удалось создать скриншот, отправляю только текст")
                await self.session.send_client_content(
                    turns=types.Content(
                        role='user',
                        parts=[types.Part(text=text)]
                    ),
                    turn_complete=True
                )
            else:
                print("Скриншот создан, отправляю запрос...")
                # Отправляем скриншот и текст ВМЕСТЕ в одном Content объекте
                await self.session.send_client_content(
                    turns=types.Content(
                        role='user',
                        parts=[
                            types.Part.from_bytes(
                                data=screenshot["raw_bytes"],
                                mime_type=screenshot["mime_type"]
                            ),
                            types.Part.from_text(text=text)
                        ]
                    ),
                    turn_complete=True
                )
                
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")

    async def send_text_only(self, text):
        """Отправляет только текстовое сообщение для тестирования поиска"""
        try:
            await self.session.send_client_content(
                turns=types.Content(
                    role='user',
                    parts=[types.Part.from_text(text=text)]
                ),
                turn_complete=True
            )
        except Exception as e:
            print(f"Ошибка при отправке текста: {e}")

    async def receive_response(self):
        """Получает ответ от Gemini чанками с поддержкой инструментов"""
        try:
            turn = self.session.receive()
            async for response in turn:
                if hasattr(response, 'text') and response.text:
                    print(response.text, end="", flush=True)
                
                # Проверяем, есть ли вызовы инструментов
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    for tool_call in response.tool_calls:
                        print(f"\n🔍 Выполняю поиск: {tool_call.function.name}")
                        # Здесь можно добавить логику для обработки результатов поиска
                    
        except Exception as e:
            print(f"Ошибка при получении ответа: {e}")

    async def send_text(self):
        """Основной цикл для ввода текста и получения ответов"""
        print("Ассистент готов! Введите сообщение (или 'q' для выхода):")
        
        while True:
            try:
                text = await asyncio.to_thread(
                    input,
                    "\nСообщение > ",
                )
                
                if text.lower() == "q":
                    print("Завершение работы...")
                    break
                    
                if text.strip():
                    print(f"\nОтправляю: {text}")
                    # Выбираем режим: скриншот + текст или только текст
                    if "новости" in text.lower() or "поиск" in text.lower():
                        # Для новостей используем только текст (поиск)
                        await self.send_text_only(text)
                    else:
                        # Для других запросов используем скриншот
                        await self.send_message_with_screenshot(text)
                    await self.receive_response()
                    print("\n" + "="*50)
                else:
                    print("Введите непустое сообщение")
                    
            except KeyboardInterrupt:
                print("\nЗавершение работы...")
                break
            except Exception as e:
                print(f"Ошибка: {e}")

    async def run(self):
        """Основной метод запуска приложения"""
        # Проверяем API ключ
        if not os.environ.get("GEMINI_API_KEY"):
            print("ОШИБКА: Не установлен GEMINI_API_KEY")
            print("Установите переменную окружения: export GEMINI_API_KEY='your_key_here'")
            return

        try:
            async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
                self.session = session
                print(f"Подключение к Gemini Live API установлено (модель: {MODEL})")
                print(f"Режим: {self.mode}")
                
                await self.send_text()
                
        except Exception as e:
            print(f"Критическая ошибка: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini Live API - Ассистент со скриншотами")
    parser.add_argument(
        "--mode",
        type=str,
        default=DEFAULT_MODE,
        help="Режим работы (пока только screen)",
        choices=["screen"],
    )
    
    args = parser.parse_args()
    
    if args.mode != "screen":
        print("Предупреждение: Поддерживается только режим 'screen'")
        args.mode = "screen"
    
    main = ScreenAssistant(mode=args.mode)
    asyncio.run(main.run())
