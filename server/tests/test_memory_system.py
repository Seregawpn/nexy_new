#!/usr/bin/env python3
"""
Тесты для системы памяти
"""

import sys
import os
import logging
import psycopg2
from pathlib import Path

# Добавляем путь к серверу для импорта
sys.path.append(str(Path(__file__).parent.parent))

from config import Config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_memory_system(db_url: str):
    """Тестирует систему памяти"""
    try:
        logger.info("🧪 Тестирование системы памяти...")
        conn = psycopg2.connect(db_url)
        
        # Тестируем создание пользователя с памятью
        with conn.cursor() as cursor:
            test_hardware_id = "test_memory_system_123"
            
            # Создаем тестового пользователя
            cursor.execute("""
                INSERT INTO users (hardware_id_hash, short_term_memory, long_term_memory)
                VALUES (%s, %s, %s)
                ON CONFLICT (hardware_id_hash) 
                DO UPDATE SET 
                    short_term_memory = EXCLUDED.short_term_memory,
                    long_term_memory = EXCLUDED.long_term_memory,
                    memory_updated_at = NOW()
            """, (test_hardware_id, "Тест краткосрочной памяти", "Тест долгосрочной памяти"))
            
            # Проверяем, что память сохранена
            cursor.execute("""
                SELECT short_term_memory, long_term_memory 
                FROM users 
                WHERE hardware_id_hash = %s
            """, (test_hardware_id,))
            
            result = cursor.fetchone()
            if result and result[0] and result[1]:
                logger.info("✅ Тест создания памяти прошел успешно")
            else:
                raise Exception("Память не была сохранена")
            
            # Очищаем тестовые данные
            cursor.execute("DELETE FROM users WHERE hardware_id_hash = %s", (test_hardware_id,))
            logger.info("🧹 Тестовые данные очищены")
        
        conn.commit()
        logger.info("✅ Тестирование системы памяти завершено успешно")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования системы памяти: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("🔌 Соединение с базой данных закрыто")


if __name__ == "__main__":
    # Получаем URL базы данных из конфигурации
    db_url = Config.get_database_url()
    logger.info(f"📊 База данных: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    
    # Запускаем тест
    success = test_memory_system(db_url)
    if success:
        print("🎉 Тест системы памяти прошел успешно!")
    else:
        print("❌ Тест системы памяти провален!")
        sys.exit(1)
