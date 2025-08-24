#!/usr/bin/env python3
"""
Очистка тестовой памяти для чистого тестирования
"""

import asyncio
import sys
sys.path.append('.')

from database.database_manager import DatabaseManager

async def cleanup_test_memory():
    """Очищает тестовую память"""
    
    try:
        print("🧹 Очищаю тестовую память...")
        
        db_manager = DatabaseManager()
        await asyncio.to_thread(db_manager.connect)
        
        # Список тестовых пользователей для очистки
        test_users = [
            "test_user_memory_cycle_123",
            "test_user_123", 
            "clean_user_test_456"
        ]
        
        print(f"🎯 Найдено {len(test_users)} тестовых пользователей для очистки")
        
        cleaned_count = 0
        
        for hardware_id in test_users:
            print(f"\n🔍 Очищаю пользователя: {hardware_id}")
            
            try:
                # Очищаем память (устанавливаем в пустые строки)
                success = await asyncio.to_thread(
                    db_manager.update_user_memory,
                    hardware_id,
                    "",  # Пустая краткосрочная память
                    ""   # Пустая долгосрочная память
                )
                
                if success:
                    print(f"✅ Память пользователя {hardware_id} очищена")
                    cleaned_count += 1
                else:
                    print(f"⚠️ Не удалось очистить память пользователя {hardware_id}")
                    
            except Exception as e:
                print(f"❌ Ошибка при очистке {hardware_id}: {e}")
        
        print(f"\n📊 Результат очистки:")
        print(f"   Очищено пользователей: {cleaned_count}/{len(test_users)}")
        
        # Проверяем результат
        print("\n🧠 Проверяю результат очистки...")
        
        for hardware_id in test_users:
            memory_data = await asyncio.to_thread(
                db_manager.get_user_memory, 
                hardware_id
            )
            
            short_memory = memory_data.get('short', '')
            long_memory = memory_data.get('long', '')
            
            if not short_memory and not long_memory:
                print(f"✅ {hardware_id}: память пуста")
            else:
                print(f"⚠️ {hardware_id}: память не полностью очищена")
                print(f"   Краткосрочная: '{short_memory}'")
                print(f"   Долгосрочная: '{long_memory}'")
        
        print("\n🎉 Очистка завершена!")
        
        if cleaned_count == len(test_users):
            print("✅ Вся тестовая память успешно очищена")
        else:
            print("⚠️ Некоторые пользователи не были очищены полностью")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(cleanup_test_memory())
