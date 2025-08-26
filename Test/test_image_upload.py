#!/usr/bin/env python3
"""
🧪 ТЕСТ ЗАГРУЗКИ ИЗОБРАЖЕНИЯ В TEST ПАПКЕ
Проверяем, работает ли types.Part.from_bytes в виртуальном окружении
"""

import os
import asyncio
import base64
from PIL import Image, ImageDraw
import io
from google import genai
from google.genai import types

async def test_image_upload():
    """Тест загрузки изображения"""
    print("🧪 ТЕСТ ЗАГРУЗКИ ИЗОБРАЖЕНИЯ В TEST ПАПКЕ")
    print("=" * 50)
    
    # Проверяем API ключ
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ ОШИБКА: Не установлен GEMINI_API_KEY")
        return
    
    print(f"✅ API ключ найден: {os.environ.get('GEMINI_API_KEY')[:10]}...")
    
    try:
        # Создаем клиент
        client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=os.environ.get("GEMINI_API_KEY"),
        )
        
        # Конфигурация
        config = types.LiveConnectConfig(
            response_modalities=["TEXT"],
            media_resolution="MEDIA_RESOLUTION_MEDIUM",
            tools=[
                types.Tool(
                    google_search=types.GoogleSearch()
                )
            ]
        )
        
        print("✅ Клиент и конфигурация созданы")
        
        # Создаем тестовое изображение
        print("\n🎨 Создаем тестовое изображение...")
        img = Image.new('RGB', (100, 100), color='red')
        draw = ImageDraw.Draw(img)
        
        # Рисуем что-то простое
        draw.ellipse([25, 25, 75, 75], fill='blue')
        draw.rectangle([10, 10, 30, 30], fill='green')
        
        print(f"✅ Изображение создано:")
        print(f"   - Размер: {img.width}x{img.height} пикселей")
        print(f"   - Цвета: красный фон, синий круг, зеленый квадрат")
        
        # Сохраняем в JPEG
        jpeg_buffer = io.BytesIO()
        img.save(jpeg_buffer, format='JPEG', quality=85)
        jpeg_buffer.seek(0)
        jpeg_data = jpeg_buffer.read()
        
        # Конвертируем в base64
        screenshot_base64 = base64.b64encode(jpeg_data).decode('utf-8')
        
        print(f"   - JPEG размер: {len(jpeg_data)} байт")
        print(f"   - Base64 длина: {len(screenshot_base64)} символов")
        
        # Сохраняем для проверки
        img.save("test_image.jpg", "JPEG", quality=95)
        print(f"💾 Изображение сохранено как 'test_image.jpg'")
        
        # Тест 1: Создание Part.from_bytes
        print("\n🧪 ТЕСТ 1: Создание Part.from_bytes")
        try:
            part = types.Part.from_bytes(
                data=jpeg_data,
                mime_type="image/jpeg"
            )
            print("✅ Part.from_bytes создан успешно!")
            print(f"   - Тип: {type(part)}")
            print(f"   - Атрибуты: {dir(part)}")
            
        except Exception as e:
            print(f"❌ Ошибка создания Part.from_bytes: {e}")
            return False
        
        # Тест 2: Отправка в Live API
        print("\n🧪 ТЕСТ 2: Отправка в Live API")
        try:
            async with client.aio.live.connect(model="models/gemini-2.5-flash-live-preview", config=config) as session:
                print("✅ Сессия создана")
                
                # Отправляем изображение и текст
                content_parts = [
                    types.Part.from_bytes(
                        data=jpeg_data,
                        mime_type="image/jpeg"
                    ),
                    types.Part.from_text(text="Опиши, что ты видишь на этом изображении")
                ]
                
                print("📤 Отправляем изображение через Part.from_bytes...")
                await session.send_client_content(
                    turns=types.Content(
                        role='user',
                        parts=content_parts
                    ),
                    turn_complete=True
                )
                print("✅ Изображение отправлено!")
                
                # Получаем ответ
                print("🔄 Получаем ответ...")
                turn = session.receive()
                async for response in turn:
                    if hasattr(response, 'text') and response.text:
                        print(f"🤖 Ответ: {response.text}")
                        break
                
                print("✅ ТЕСТ 2 УСПЕШЕН!")
                return True
                
        except Exception as e:
            print(f"❌ ТЕСТ 2 ПРОВАЛЕН: {e}")
            print(f"   - Тип ошибки: {type(e)}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Основная функция"""
    success = await test_image_upload()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ТЕСТ ЗАГРУЗКИ ИЗОБРАЖЕНИЯ ПРОШЕЛ УСПЕШНО!")
        print("📊 Проверьте файл 'test_image.jpg' и ответ Live API")
    else:
        print("❌ ТЕСТ ЗАГРУЗКИ ИЗОБРАЖЕНИЯ ПРОВАЛИЛСЯ")

if __name__ == "__main__":
    asyncio.run(main())
