#!/usr/bin/env python3
"""
Тест с чистым пользователем для проверки памяти
"""

import asyncio
import os
import sys
sys.path.append('.')

from text_processor import TextProcessor
from database.database_manager import DatabaseManager

async def test_clean_user():
    """Тестирует память с чистым пользователем"""
    
    # Проверяем наличие API ключа
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY не найден в переменных окружения")
        return
    
    try:
        print("🧪 Тестирую память с чистым пользователем...")
        
        # Инициализируем компоненты
        text_processor = TextProcessor()
        db_manager = DatabaseManager()
        
        # Подключаемся к базе данных
        await asyncio.to_thread(db_manager.connect)
        
        # Устанавливаем DatabaseManager в TextProcessor
        text_processor.set_database_manager(db_manager)
        
        print("✅ Компоненты инициализированы")
        
        # Новый чистый пользователь
        clean_hardware_id = "clean_user_test_456"
        
        # 🔧 ТЕСТ 1: Создание памяти
        print("\n📝 ТЕСТ 1: Создание памяти")
        print("=" * 50)
        
        test_prompt = "Меня зовут Сергей, я разработчик из Москвы, люблю программирование на Python"
        test_response = "Привет, Сергей! Приятно познакомиться. Вы разработчик из Москвы, это интересно! Python - отличный язык программирования."
        
        print(f"📝 Запрос: {test_prompt}")
        print(f"🤖 Ответ: {test_response}")
        
        # Анализируем и сохраняем память
        if text_processor.memory_analyzer:
            print("🧠 Анализирую разговор для извлечения памяти...")
            
            short_memory, long_memory = await text_processor.memory_analyzer.analyze_conversation(
                test_prompt, 
                test_response
            )
            
            print(f"📋 Краткосрочная память: {short_memory}")
            print(f"📚 Долгосрочная память: {long_memory}")
            
            # Сохраняем в базу данных
            if short_memory or long_memory:
                success = await asyncio.to_thread(
                    db_manager.update_user_memory,
                    clean_hardware_id,
                    short_memory,
                    long_memory
                )
                
                if success:
                    print("✅ Память сохранена в базе данных")
                else:
                    print("❌ Ошибка сохранения памяти")
                    return
            else:
                print("⚠️ Анализ памяти не выявил информации для сохранения")
                return
        else:
            print("❌ MemoryAnalyzer недоступен")
            return
        
        # 🔧 ТЕСТ 2: Проверка сохраненной памяти
        print("\n🧠 ТЕСТ 2: Проверка сохраненной памяти")
        print("=" * 50)
        
        # Получаем сохраненную память
        memory_data = await asyncio.to_thread(
            db_manager.get_user_memory, 
            clean_hardware_id
        )
        
        print(f"🧠 Сохраненная память:")
        print(f"   Краткосрочная: {memory_data.get('short', 'Нет')}")
        print(f"   Долгосрочная: {memory_data.get('long', 'Нет')}")
        
        # 🔧 ТЕСТ 3: Вопрос "Как меня зовут?"
        print("\n📝 ТЕСТ 3: Как меня зовут?")
        print("=" * 50)
        
        question = "Как меня зовут?"
        print(f"❓ Вопрос: {question}")
        print("🔄 Генерирую ответ с использованием памяти...")
        
        # Генерируем ответ
        response_chunks = []
        async for chunk in text_processor.generate_response_stream(
            prompt=question,
            hardware_id=clean_hardware_id,
            screenshot_base64=None
        ):
            response_chunks.append(chunk)
            print(f"📦 Чанк: {chunk}")
        
        full_response = " ".join(response_chunks)
        print(f"\n🤖 Полный ответ: {full_response}")
        
        # 🔍 Анализируем ответ
        print("\n🔍 Анализ ответа:")
        print("=" * 50)
        
        # Проверяем, содержит ли ответ имя
        name_found = False
        if "Сергей" in full_response or "Sergei" in full_response:
            print("✅ Имя 'Сергей' найдено в ответе")
            name_found = True
        else:
            print("❌ Имя 'Сергей' НЕ найдено в ответе")
        
        # Проверяем, содержит ли ответ информацию о профессии
        profession_found = False
        if any(word in full_response.lower() for word in ["разработчик", "developer", "программист", "programmer"]):
            print("✅ Профессия найдена в ответе")
            profession_found = True
        else:
            print("❌ Профессия НЕ найдена в ответе")
        
        # Проверяем, содержит ли ответ информацию о местоположении
        location_found = False
        if any(word in full_response for word in ["Москва", "Moscow"]):
            print("✅ Местоположение найдено в ответе")
            location_found = True
        else:
            print("❌ Местоположение НЕ найдено в ответе")
        
        # Общая оценка
        print(f"\n📊 Оценка использования памяти:")
        if name_found and profession_found and location_found:
            print("🎉 ОТЛИЧНО! Память использована полностью")
        elif name_found:
            print("✅ ХОРОШО! Имя найдено, но можно лучше")
        else:
            print("⚠️ ТРЕБУЕТ ВНИМАНИЯ! Память не используется")
        
        print("\n✅ Тест завершен!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_clean_user())
