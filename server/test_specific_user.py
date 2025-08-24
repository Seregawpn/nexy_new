#!/usr/bin/env python3
"""
Тест памяти конкретного пользователя
"""

import asyncio
import sys
sys.path.append('.')

from database.database_manager import DatabaseManager

async def test_specific_user():
    """Тестирует память конкретного пользователя"""
    
    try:
        print("🧠 Тестирую память конкретного пользователя...")
        
        db_manager = DatabaseManager()
        await asyncio.to_thread(db_manager.connect)
        
        # Тестовый пользователь
        test_hardware_id = "test_user_memory_cycle_123"
        
        print(f"🔍 Проверяю пользователя: {test_hardware_id}")
        
        # Получаем память пользователя
        memory_data = await asyncio.to_thread(
            db_manager.get_user_memory, 
            test_hardware_id
        )
        
        print(f"📋 Память пользователя:")
        print(f"   Краткосрочная: '{memory_data.get('short', 'Нет')}'")
        print(f"   Долгосрочная: '{memory_data.get('long', 'Нет')}'")
        
        # Проверяем, есть ли пользователь в базе
        user_data = await asyncio.to_thread(
            db_manager.get_user_by_hardware_id, 
            test_hardware_id
        )
        
        if user_data:
            print(f"✅ Пользователь найден в базе:")
            print(f"   ID: {user_data.get('id', 'N/A')}")
            print(f"   Hardware ID Hash: {user_data.get('hardware_id_hash', 'N/A')}")
            print(f"   Short Term Memory: '{user_data.get('short_term_memory', 'Нет')}'")
            print(f"   Long Term Memory: '{user_data.get('long_term_memory', 'Нет')}'")
            print(f"   Memory Updated At: {user_data.get('memory_updated_at', 'N/A')}")
        else:
            print("❌ Пользователь не найден в базе")
        
        print("\n✅ Тест завершен!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_specific_user())
