#!/usr/bin/env python3
"""
Тест для проверки работы системы памяти
"""

import asyncio
import os
import sys
sys.path.append('.')

from text_processor import TextProcessor
from database.database_manager import DatabaseManager

async def test_memory_system():
    """Тестирует систему памяти"""
    
    # Проверяем наличие API ключа
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY не найден в переменных окружения")
        return
    
    try:
        print("🧪 Тестирую систему памяти...")
        
        # Инициализируем компоненты
        text_processor = TextProcessor()
        db_manager = DatabaseManager()
        
        # 🔧 Подключаемся к базе данных
        await asyncio.to_thread(db_manager.connect)
        
        # Устанавливаем DatabaseManager в TextProcessor
        text_processor.set_database_manager(db_manager)
        
        print("✅ Компоненты инициализированы")
        
        # Тестовые данные
        test_hardware_id = "test_user_123"
        test_prompt = "Меня зовут Сергей, я разработчик из Москвы"
        test_response = "Привет, Сергей! Приятно познакомиться. Вы разработчик из Москвы, это интересно!"
        
        print(f"📝 Тестовый запрос: {test_prompt}")
        print(f"🤖 Тестовый ответ: {test_response}")
        
        # Тестируем анализ памяти
        if text_processor.memory_analyzer:
            print("🧠 Анализирую разговор для извлечения памяти...")
            
            # Создаем промпт для анализа
            analysis_prompt = text_processor.memory_analyzer._create_analysis_prompt(
                test_prompt, 
                test_response
            )
            print(f"📝 Промпт для анализа памяти:")
            print(f"   {analysis_prompt[:200]}...")
            
            short_memory, long_memory = await text_processor.memory_analyzer.analyze_conversation(
                test_prompt, 
                test_response
            )
            
            print(f"📋 Краткосрочная память: {short_memory}")
            print(f"📚 Долгосрочная память: {long_memory}")
            
            # Проверяем, что происходит в MemoryAnalyzer
            print("\n🔍 Детальная диагностика MemoryAnalyzer...")
            
            # Тестируем прямой вызов Gemini
            try:
                response = await asyncio.to_thread(
                    text_processor.memory_analyzer.model.generate_content,
                    analysis_prompt
                )
                
                if response and response.text:
                    print(f"🤖 Raw Gemini response:")
                    print(f"   {response.text[:500]}...")
                    
                    # Тестируем извлечение памяти
                    extracted_short, extracted_long = text_processor.memory_analyzer._extract_memory_from_response(response.text)
                    print(f"🔍 Извлеченная память:")
                    print(f"   Краткосрочная: '{extracted_short}'")
                    print(f"   Долгосрочная: '{extracted_long}'")
                else:
                    print("❌ Gemini вернул пустой ответ")
                    
            except Exception as e:
                print(f"❌ Ошибка прямого вызова Gemini: {e}")
            
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
                    
                    # Проверяем, что память сохранилась
                    memory_data = await asyncio.to_thread(
                        db_manager.get_user_memory, 
                        test_hardware_id
                    )
                    
                    print(f"🧠 Проверка сохраненной памяти:")
                    print(f"   Краткосрочная: {memory_data.get('short', 'Нет')}")
                    print(f"   Долгосрочная: {memory_data.get('long', 'Нет')}")
                else:
                    print("❌ Ошибка сохранения памяти")
            else:
                print("⚠️ Анализ памяти не выявил информации для сохранения")
        else:
            print("❌ MemoryAnalyzer недоступен")
        
        print("\n✅ Тест завершен!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_memory_system())
