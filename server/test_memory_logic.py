#!/usr/bin/env python3
"""
Тест логики извлечения памяти без реального API вызова
"""

import sys
sys.path.append('.')

from memory_analyzer import MemoryAnalyzer

def test_memory_extraction_logic():
    """Тестирует логику извлечения памяти из ответов"""
    
    print("🧪 Тестирую логику извлечения памяти...")
    
    # Создаем экземпляр MemoryAnalyzer без инициализации API
    analyzer = MemoryAnalyzer.__new__(MemoryAnalyzer)
    
    # Тестируем различные форматы ответов
    test_cases = [
        {
            "name": "Правильный формат SHORT/LONG MEMORY",
            "response": """SHORT MEMORY: User introduced themselves as Sergei, developer from Moscow
LONG MEMORY: User's name is Sergei, they are a developer from Moscow""",
            "expected_short": "User introduced themselves as Sergei, developer from Moscow",
            "expected_long": "User's name is Sergei, they are a developer from Moscow"
        },
        {
            "name": "Формат с двоеточием",
            "response": """SHORT MEMORY: Current conversation about user introduction
LONG MEMORY: Sergei is a developer from Moscow""",
            "expected_short": "Current conversation about user introduction",
            "expected_long": "Sergei is a developer from Moscow"
        },
        {
            "name": "Формат без двоеточия",
            "response": """SHORT MEMORY User mentioned their name and profession
LONG MEMORY User's name is Sergei""",
            "expected_short": "",
            "expected_long": ""
        },
        {
            "name": "Смешанный формат",
            "response": """Here's the analysis:
SHORT MEMORY: User introduced themselves
LONG MEMORY: User's name is Sergei""",
            "expected_short": "User introduced themselves",
            "expected_long": "User's name is Sergei"
        },
        {
            "name": "Пустой ответ",
            "response": "No memory updates needed",
            "expected_short": "",
            "expected_long": ""
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Тест {i}: {test_case['name']}")
        print(f"📝 Ответ: {test_case['response'][:100]}...")
        
        # Тестируем извлечение памяти
        short_memory, long_memory = analyzer._extract_memory_from_response(test_case['response'])
        
        print(f"📋 Извлеченная краткосрочная память: '{short_memory}'")
        print(f"📚 Извлеченная долгосрочная память: '{long_memory}'")
        
        # Проверяем ожидаемые результаты
        short_correct = short_memory == test_case['expected_short']
        long_correct = long_memory == test_case['expected_long']
        
        if short_correct and long_correct:
            print("✅ Тест пройден!")
        else:
            print("❌ Тест не пройден!")
            if not short_correct:
                print(f"   Ожидалось: '{test_case['expected_short']}'")
            if not long_correct:
                print(f"   Ожидалось: '{test_case['expected_long']}'")
    
    print("\n🔍 Анализ проблем:")
    print("1. MemoryAnalyzer ожидает ответ в формате 'SHORT MEMORY:' и 'LONG MEMORY:'")
    print("2. Если Gemini не возвращает ответ в этом формате, память не извлекается")
    print("3. Нужно либо изменить промпт, либо улучшить парсинг ответов")
    
    print("\n💡 Рекомендации:")
    print("1. Изменить промпт MemoryAnalyzer, чтобы Gemini возвращал ответ в нужном формате")
    print("2. Добавить fallback парсинг для других форматов ответов")
    print("3. Добавить логирование для понимания, в каком формате возвращает Gemini")

if __name__ == "__main__":
    test_memory_extraction_logic()
