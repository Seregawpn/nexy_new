#!/usr/bin/env python3
"""
Проверка всей памяти в базе данных
"""

import asyncio
import sys
sys.path.append('.')

from database.database_manager import DatabaseManager

async def check_all_memory():
    """Проверяет всю память в базе данных"""
    
    try:
        print("🧠 Проверяю всю память в базе данных...")
        
        db_manager = DatabaseManager()
        await asyncio.to_thread(db_manager.connect)
        
        # Получаем все записи памяти
        all_memory = await asyncio.to_thread(db_manager.get_users_with_active_memory, 100)
        
        if all_memory:
            print(f"✅ Найдено {len(all_memory)} записей памяти:")
            print("=" * 60)
            
            for i, record in enumerate(all_memory, 1):
                print(f"\n📋 Запись {i}:")
                print(f"   Hardware ID: {record.get('hardware_id_hash', 'N/A')}")
                print(f"   Размер краткосрочной памяти: {record.get('short_memory_size', 'Нет')} символов")
                print(f"   Размер долгосрочной памяти: {record.get('long_memory_size', 'Нет')} символов")
                print(f"   Обновлено: {record.get('updated_at', 'N/A')}")
                print("-" * 40)
        else:
            print("⚠️ Память в базе данных не найдена")
        
        print("\n✅ Проверка завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_all_memory())
