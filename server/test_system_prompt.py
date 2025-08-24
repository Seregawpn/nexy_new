#!/usr/bin/env python3
"""
Тест для проверки корректности передачи System Prompt в LangChain
"""

import asyncio
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

async def test_system_prompt():
    """Тестирует передачу System Prompt в LangChain"""
    
    # Проверяем наличие API ключа
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY не найден в переменных окружения")
        return
    
    try:
        # Инициализируем LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=os.environ.get("GEMINI_API_KEY"),
            temperature=0.7,
            max_output_tokens=1024,
            streaming=False  # Отключаем стриминг для теста
        )
        
        print("✅ LLM инициализирован успешно")
        
        # Тест 1: Только текст
        print("\n🧪 Тест 1: Только текст")
        messages_text = [
            SystemMessage(content="You are a helpful assistant. Always respond in English and be very brief."),
            HumanMessage(content="Привет! Как дела?")
        ]
        
        response_text = await llm.ainvoke(messages_text)
        print(f"📝 Ответ: {response_text.content}")
        
        # Тест 2: Мультимодальный запрос (без изображения для простоты)
        print("\n🧪 Тест 2: Мультимодальный запрос")
        messages_multimodal = [
            SystemMessage(content="You are a helpful assistant. Always respond in English and be very brief."),
            HumanMessage(content=[
                {"type": "text", "text": "Describe what you see in this image"},
                {"type": "image_url", "image_url": {"url": "https://example.com/test.jpg"}}
            ])
        ]
        
        response_multimodal = await llm.ainvoke(messages_multimodal)
        print(f"🖼️ Ответ: {response_multimodal.content}")
        
        print("\n✅ Все тесты выполнены успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_system_prompt())
