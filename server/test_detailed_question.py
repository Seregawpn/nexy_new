#!/usr/bin/env python3
"""
Тест с детальным вопросом для проверки использования всей памяти
"""

import asyncio
import os
import sys
sys.path.append('.')

from text_processor import TextProcessor
from database.database_manager import DatabaseManager

async def test_detailed_question():
    """Тестирует ответ на детальный вопрос с использованием всей памяти"""
    
    # Проверяем наличие API ключа
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY не найден в переменных окружения")
        return
    
    try:
        print("🧪 Тестирую ответ на детальный вопрос...")
        
        # Инициализируем компоненты
        text_processor = TextProcessor()
        db_manager = DatabaseManager()
        
        # Подключаемся к базе данных
        await asyncio.to_thread(db_manager.connect)
        
        # Устанавливаем DatabaseManager в TextProcessor
        text_processor.set_database_manager(db_manager)
        
        print("✅ Компоненты инициализированы")
        
        # Используем пользователя с уже созданной памятью
        test_hardware_id = "clean_user_test_456"
        
        # Проверяем память
        print("\n🧠 Проверяю память пользователя...")
        memory_data = await asyncio.to_thread(
            db_manager.get_user_memory, 
            test_hardware_id
        )
        
        print(f"🧠 Доступная память:")
        print(f"   Краткосрочная: {memory_data.get('short', 'Нет')}")
        print(f"   Долгосрочная: {memory_data.get('long', 'Нет')}")
        
        # 🔧 ТЕСТ: Детальный вопрос
        print("\n📝 ТЕСТ: Детальный вопрос о пользователе")
        print("=" * 50)
        
        question = "Расскажи обо мне: как меня зовут, чем я занимаюсь, откуда я и что я люблю?"
        print(f"❓ Вопрос: {question}")
        print("🔄 Генерирую ответ с использованием памяти...")
        
        # Генерируем ответ
        response_chunks = []
        async for chunk in text_processor.generate_response_stream(
            prompt=question,
            hardware_id=test_hardware_id,
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
        
        # Проверяем, содержит ли ответ информацию о предпочтениях
        preferences_found = False
        if "Python" in full_response:
            print("✅ Предпочтения (Python) найдены в ответе")
            preferences_found = True
        else:
            print("❌ Предпочтения НЕ найдены в ответе")
        
        # Общая оценка
        print(f"\n📊 Оценка использования памяти:")
        total_found = sum([name_found, profession_found, location_found, preferences_found])
        
        if total_found == 4:
            print("🎉 ОТЛИЧНО! Вся память использована полностью")
        elif total_found >= 3:
            print("✅ ХОРОШО! Большая часть памяти использована")
        elif total_found >= 2:
            print("⚠️ УДОВЛЕТВОРИТЕЛЬНО! Часть памяти использована")
        else:
            print("❌ ТРЕБУЕТ ВНИМАНИЯ! Память практически не используется")
        
        print(f"📈 Использовано элементов памяти: {total_found}/4")
        
        print("\n✅ Тест завершен!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_detailed_question())
