#!/usr/bin/env python3
"""
Тест полного цикла работы памяти: сохранение и использование при генерации
"""

import asyncio
import os
import sys
sys.path.append('.')

from text_processor import TextProcessor
from database.database_manager import DatabaseManager

async def test_memory_full_cycle():
    """Тестирует полный цикл работы памяти"""
    
    # Проверяем наличие API ключа
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY не найден в переменных окружения")
        return
    
    try:
        print("🧪 Тестирую полный цикл работы памяти...")
        
        # Инициализируем компоненты
        text_processor = TextProcessor()
        db_manager = DatabaseManager()
        
        # Подключаемся к базе данных
        await asyncio.to_thread(db_manager.connect)
        
        # Устанавливаем DatabaseManager в TextProcessor
        text_processor.set_database_manager(db_manager)
        
        print("✅ Компоненты инициализированы")
        
        # Тестовый пользователь
        test_hardware_id = "test_user_memory_cycle_123"
        
        # 🔧 ТЕСТ 1: Сохранение памяти
        print("\n📝 ТЕСТ 1: Сохранение памяти")
        print("=" * 50)
        
        test_prompt_1 = "Меня зовут Сергей, я разработчик из Москвы, люблю программирование на Python"
        test_response_1 = "Привет, Сергей! Приятно познакомиться. Вы разработчик из Москвы, это интересно! Python - отличный язык программирования."
        
        print(f"📝 Запрос: {test_prompt_1}")
        print(f"🤖 Ответ: {test_response_1}")
        
        # Анализируем и сохраняем память
        if text_processor.memory_analyzer:
            print("🧠 Анализирую разговор для извлечения памяти...")
            
            short_memory, long_memory = await text_processor.memory_analyzer.analyze_conversation(
                test_prompt_1, 
                test_response_1
            )
            
            print(f"📋 Краткосрочная память: {short_memory}")
            print(f"📚 Долгосрочная память: {long_memory}")
            
            # Сохраняем в базу данных
            if short_memory or long_memory:
                success = await asyncio.to_thread(
                    db_manager.update_user_memory,
                    test_hardware_id,
                    short_memory,
                    long_memory
                )
                
                if success:
                    print("✅ Память сохранена в базе данных")
                else:
                    print("❌ Ошибка сохранения памяти")
            else:
                print("⚠️ Анализ памяти не выявил информации для сохранения")
        else:
            print("❌ MemoryAnalyzer недоступен")
            return
        
        # 🔧 ТЕСТ 2: Проверка сохраненной памяти
        print("\n🧠 ТЕСТ 2: Проверка сохраненной памяти")
        print("=" * 50)
        
        # Получаем сохраненную память
        memory_data = await asyncio.to_thread(
            db_manager.get_user_memory, 
            test_hardware_id
        )
        
        print(f"🧠 Сохраненная память:")
        print(f"   Краткосрочная: {memory_data.get('short', 'Нет')}")
        print(f"   Долгосрочная: {memory_data.get('long', 'Нет')}")
        
        # 🔧 ТЕСТ 3: Генерация ответа с использованием памяти
        print("\n🚀 ТЕСТ 3: Генерация ответа с использованием памяти")
        print("=" * 50)
        
        test_prompt_2 = "Как меня зовут и чем я занимаюсь?"
        
        print(f"📝 Новый запрос: {test_prompt_2}")
        print("🔄 Генерирую ответ с использованием сохраненной памяти...")
        
        # Генерируем ответ с использованием памяти
        response_chunks = []
        async for chunk in text_processor.generate_response_stream(
            prompt=test_prompt_2,
            hardware_id=test_hardware_id,
            screenshot_base64=None
        ):
            response_chunks.append(chunk)
            print(f"📦 Чанк: {chunk}")
        
        full_response = " ".join(response_chunks)
        print(f"\n🤖 Полный ответ: {full_response}")
        
        # 🔧 ТЕСТ 4: Проверка использования памяти
        print("\n🔍 ТЕСТ 4: Проверка использования памяти")
        print("=" * 50)
        
        # Проверяем, содержит ли ответ информацию из памяти
        memory_used = False
        if "Сергей" in full_response or "Sergei" in full_response:
            print("✅ Имя пользователя использовано в ответе")
            memory_used = True
        
        if "разработчик" in full_response.lower() or "developer" in full_response.lower():
            print("✅ Профессия пользователя использована в ответе")
            memory_used = True
        
        if "Москва" in full_response or "Moscow" in full_response:
            print("✅ Местоположение пользователя использовано в ответе")
            memory_used = True
        
        if "Python" in full_response:
            print("✅ Предпочтения пользователя использованы в ответе")
            memory_used = True
        
        if not memory_used:
            print("⚠️ Память не была использована в ответе")
        
        # 🔧 ТЕСТ 5: Обновление памяти после нового разговора
        print("\n🔄 ТЕСТ 5: Обновление памяти после нового разговора")
        print("=" * 50)
        
        test_prompt_3 = "Я также люблю путешествовать и играть на гитаре"
        test_response_3 = "Отлично! Путешествия и музыка - это замечательные увлечения. Гитара - прекрасный инструмент для творчества."
        
        print(f"📝 Новый запрос: {test_prompt_3}")
        print(f"🤖 Новый ответ: {test_response_3}")
        
        # Анализируем новый разговор
        short_memory_2, long_memory_2 = await text_processor.memory_analyzer.analyze_conversation(
            test_prompt_3, 
            test_response_3
        )
        
        print(f"📋 Новая краткосрочная память: {short_memory_2}")
        print(f"📚 Новая долгосрочная память: {long_memory_2}")
        
        # Обновляем память
        if short_memory_2 or long_memory_2:
            success = await asyncio.to_thread(
                db_manager.update_user_memory,
                test_hardware_id,
                short_memory_2,
                long_memory_2
            )
            
            if success:
                print("✅ Память обновлена")
                
                # Проверяем обновленную память
                updated_memory = await asyncio.to_thread(
                    db_manager.get_user_memory, 
                    test_hardware_id
                )
                
                print(f"🧠 Обновленная память:")
                print(f"   Краткосрочная: {updated_memory.get('short', 'Нет')}")
                print(f"   Долгосрочная: {updated_memory.get('long', 'Нет')}")
            else:
                print("❌ Ошибка обновления памяти")
        
        print("\n✅ Полный цикл тестирования завершен!")
        
        # Очищаем тестовые данные
        print("\n🧹 Очищаю тестовые данные...")
        # Здесь можно добавить очистку тестового пользователя
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_memory_full_cycle())
