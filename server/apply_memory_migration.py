#!/usr/bin/env python3
"""
Скрипт для применения миграции системы памяти к базе данных.

Этот скрипт добавляет поля для краткосрочной и долгосрочной памяти
в таблицу users и создает необходимые индексы и функции.
"""

import os
import sys
import logging
import psycopg2
from pathlib import Path

# Импортируем Config для получения URL базы данных
sys.path.append(os.path.dirname(__file__))
from config import Config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_migration_file():
    """Читает файл миграции"""
    # Сначала пробуем базовую версию
    migration_file = Path(__file__).parent / "database" / "migrate_memory_basic.sql"
    
    if not migration_file.exists():
        # Если базовой нет, пробуем упрощенную
        migration_file = Path(__file__).parent / "database" / "migrate_memory_simple.sql"
        
        if not migration_file.exists():
            # Если упрощенной нет, используем полную
            migration_file = Path(__file__).parent / "database" / "migrate_memory.sql"
    
    if not migration_file.exists():
        raise FileNotFoundError(f"Файл миграции не найден")
    
    logger.info(f"📄 Используется файл миграции: {migration_file.name}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        return f.read()

def apply_migration(db_url: str):
    """Применяет миграцию к базе данных"""
    try:
        logger.info("🔌 Подключение к базе данных...")
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        
        # Проверяем версию PostgreSQL
        with conn.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            logger.info(f"📊 PostgreSQL версия: {version}")
        
        # Читаем файл миграции
        migration_sql = read_migration_file()
        logger.info("📄 Файл миграции прочитан")
        
        # Применяем миграцию
        logger.info("🚀 Применение миграции...")
        with conn.cursor() as cursor:
            cursor.execute(migration_sql)
        
        # Проверяем результат
        with conn.cursor() as cursor:
            # Проверяем наличие новых полей
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('short_term_memory', 'long_term_memory', 'memory_updated_at')
                ORDER BY column_name
            """)
            
            new_columns = cursor.fetchall()
            if len(new_columns) == 3:
                logger.info("✅ Новые поля добавлены:")
                for col_name, col_type in new_columns:
                    logger.info(f"   - {col_name}: {col_type}")
            else:
                raise Exception(f"Ожидалось 3 новых поля, найдено: {len(new_columns)}")
            
            # Проверяем наличие индексов
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'users' 
                AND indexname IN ('idx_users_memory_updated', 'idx_users_active_memory')
                ORDER BY indexname
            """)
            
            new_indexes = cursor.fetchall()
            if len(new_indexes) == 2:
                logger.info("✅ Новые индексы созданы:")
                for (index_name,) in new_indexes:
                    logger.info(f"   - {index_name}")
            else:
                raise Exception(f"Ожидалось 2 новых индекса, найдено: {len(new_indexes)}")
            
            # Проверяем наличие функций
            cursor.execute("""
                SELECT proname 
                FROM pg_proc 
                WHERE proname IN ('cleanup_expired_short_term_memory')
                ORDER BY proname
            """)
            
            new_functions = cursor.fetchall()
            if len(new_functions) >= 1:
                logger.info("✅ Новые функции созданы:")
                for (func_name,) in new_functions:
                    logger.info(f"   - {func_name}")
            else:
                raise Exception(f"Ожидалось минимум 1 новая функция, найдено: {len(new_functions)}")
        
        # Фиксируем изменения
        conn.commit()
        logger.info("✅ Миграция успешно применена!")
        
        # Показываем статистику
        with conn.cursor() as cursor:
            try:
                cursor.execute("SELECT * FROM get_memory_stats()")
                stats = cursor.fetchone()
                if stats:
                    logger.info("📊 Статистика базы данных:")
                    logger.info(f"   - Всего пользователей: {stats[0]}")
                    logger.info(f"   - Пользователей с памятью: {stats[1]}")
                    logger.info(f"   - Краткосрочная память: {stats[2]}")
                    logger.info(f"   - Долгосрочная память: {stats[3]}")
            except Exception as e:
                logger.info("📊 Базовая статистика:")
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                logger.info(f"   - Всего пользователей: {total_users}")
                
                cursor.execute("SELECT COUNT(*) FROM users WHERE short_term_memory IS NOT NULL OR long_term_memory IS NOT NULL")
                users_with_memory = cursor.fetchone()[0]
                logger.info(f"   - Пользователей с памятью: {users_with_memory}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка применения миграции: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("🔌 Соединение с базой данных закрыто")


def main():
    """Основная функция"""
    logger.info("🚀 Запуск миграции системы памяти")
    
    try:
        # Получаем URL базы данных
        db_url = Config.get_database_url()
        logger.info(f"📊 База данных: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        
        # Применяем миграцию
        if apply_migration(db_url):
            logger.info("🎉 Миграция применена успешно!")
            
            # Тестируем систему
            if test_memory_system(db_url):
                logger.info("🎯 Система памяти готова к использованию!")
            else:
                logger.warning("⚠️ Тестирование не прошло, но миграция применена")
        else:
            logger.error("❌ Миграция не была применена")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
