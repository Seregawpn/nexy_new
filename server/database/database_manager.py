import psycopg2
import psycopg2.extras
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер базы данных PostgreSQL для голосового ассистента"""
    
    def __init__(self, connection_string: str = None):
        """
        Инициализация менеджера базы данных
        
        Args:
            connection_string: Строка подключения к PostgreSQL
        """
        self.connection_string = connection_string or "postgresql://localhost/voice_assistant_db"
        self.connection = None
        
    def connect(self) -> bool:
        """Подключение к базе данных"""
        try:
            self.connection = psycopg2.connect(self.connection_string)
            self.connection.autocommit = False
            logger.info("✅ Подключение к базе данных установлено")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            return False
    
    def disconnect(self):
        """Отключение от базы данных"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("🔌 Отключение от базы данных")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
    
    # =====================================================
    # УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
    # =====================================================
    
    def create_user(self, hardware_id_hash: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        Создание нового пользователя
        
        Args:
            hardware_id_hash: Хеш аппаратного ID
            metadata: Метаданные пользователя
            
        Returns:
            UUID пользователя или None при ошибке
        """
        try:
            with self.connection.cursor() as cursor:
                user_id = str(uuid.uuid4())
                logger.info(f"🆔 Создаю пользователя с ID: {user_id}")
                logger.info(f"🆔 Hardware ID hash: {hardware_id_hash}")
                
                cursor.execute("""
                    INSERT INTO users (id, hardware_id_hash, metadata)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (user_id, hardware_id_hash, json.dumps(metadata or {})))
                
                result = cursor.fetchone()
                self.connection.commit()
                
                if result and result[0]:
                    logger.info(f"✅ Пользователь создан успешно: {result[0]}")
                    return result[0]
                else:
                    logger.error(f"❌ create_user: result = {result}")
                    return None
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Ошибка создания пользователя: {e}")
            return None
    
    def get_user_by_hardware_id(self, hardware_id_hash: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по аппаратному ID"""
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM users WHERE hardware_id_hash = %s
                """, (hardware_id_hash,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователя: {e}")
            return None
    
    # =====================================================
    # УПРАВЛЕНИЕ СЕССИЯМИ
    # =====================================================
    
    def create_session(self, user_id: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Создание новой сессии"""
        try:
            if not user_id:
                logger.error(f"❌ create_session: user_id = {user_id}")
                return None
                
            with self.connection.cursor() as cursor:
                session_id = str(uuid.uuid4())
                logger.info(f"🆔 Создаю сессию с ID: {session_id}")
                logger.info(f"🆔 User ID: {user_id}")
                
                cursor.execute("""
                    INSERT INTO sessions (id, user_id, metadata)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (session_id, user_id, json.dumps(metadata or {})))
                
                result = cursor.fetchone()
                self.connection.commit()
                
                if result and result[0]:
                    logger.info(f"✅ Сессия создана успешно: {result[0]}")
                    return result[0]
                else:
                    logger.error(f"❌ create_session: result = {result}")
                    return None
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Ошибка создания сессии: {e}")
            return None
    
    def end_session(self, session_id: str) -> bool:
        """Завершение сессии"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE sessions 
                    SET end_time = NOW(), status = 'ended', updated_at = NOW()
                    WHERE id = %s
                """, (session_id,))
                
                self.connection.commit()
                logger.info(f"✅ Сессия завершена: {session_id}")
                return True
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Ошибка завершения сессии: {e}")
            return False
    
    # =====================================================
    # УПРАВЛЕНИЕ КОМАНДАМИ
    # =====================================================
    
    def create_command(self, session_id: str, prompt: str, metadata: Dict[str, Any] = None, language: str = 'en') -> Optional[str]:
        """Создание новой команды"""
        try:
            if not session_id:
                logger.error(f"❌ create_command: session_id = {session_id}")
                return None
                
            with self.connection.cursor() as cursor:
                command_id = str(uuid.uuid4())
                logger.info(f"🆔 Создаю команду с ID: {command_id}")
                logger.info(f"🆔 Session ID: {session_id}")
                
                cursor.execute("""
                    INSERT INTO commands (id, session_id, prompt, language, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (command_id, session_id, prompt, language, json.dumps(metadata or {})))
                
                result = cursor.fetchone()
                self.connection.commit()
                
                if result and result[0]:
                    logger.info(f"✅ Команда создана успешно: {result[0]}")
                    return result[0]
                else:
                    logger.error(f"❌ create_command: result = {result}")
                    return None
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Ошибка создания команды: {e}")
            return None
    
    # =====================================================
    # УПРАВЛЕНИЕ ОТВЕТАМИ LLM
    # =====================================================
    
    def create_llm_answer(self, command_id: str, prompt: str, response: str,
                         model_info: Dict[str, Any] = None,
                         performance_metrics: Dict[str, Any] = None) -> Optional[str]:
        """Создание ответа LLM"""
        try:
            with self.connection.cursor() as cursor:
                answer_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO llm_answers (id, command_id, prompt, response, model_info, performance_metrics)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (answer_id, command_id, prompt, response, 
                     json.dumps(model_info or {}), json.dumps(performance_metrics or {})))
                
                result = cursor.fetchone()
                self.connection.commit()
                
                logger.info(f"✅ Ответ LLM создан: {answer_id}")
                return result[0] if result else answer_id
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Ошибка создания ответа LLM: {e}")
            return None
    
    # =====================================================
    # УПРАВЛЕНИЕ СКРИНШОТАМИ
    # =====================================================
    
    def create_screenshot(self, session_id: str, file_path: str = None, file_url: str = None,
                         metadata: Dict[str, Any] = None) -> Optional[str]:
        """Создание записи о скриншоте"""
        try:
            if not session_id:
                logger.error(f"❌ create_screenshot: session_id = {session_id}")
                return None
                
            with self.connection.cursor() as cursor:
                screenshot_id = str(uuid.uuid4())
                logger.info(f"🆔 Создаю скриншот с ID: {screenshot_id}")
                logger.info(f"🆔 Session ID: {session_id}")
                
                cursor.execute("""
                    INSERT INTO screenshots (id, session_id, file_path, file_url, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (screenshot_id, session_id, file_path, file_url, json.dumps(metadata or {})))
                
                result = cursor.fetchone()
                self.connection.commit()
                
                if result and result[0]:
                    logger.info(f"✅ Скриншот создан успешно: {result[0]}")
                    return result[0]
                else:
                    logger.error(f"❌ create_screenshot: result = {result}")
                    return None
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Ошибка создания скриншота: {e}")
            return None
    
    # =====================================================
    # УПРАВЛЕНИЕ МЕТРИКАМИ
    # =====================================================
    
    def create_performance_metric(self, session_id: str, metric_type: str, 
                                metric_value: Dict[str, Any]) -> Optional[str]:
        """Создание метрики производительности"""
        try:
            with self.connection.cursor() as cursor:
                metric_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO performance_metrics (id, session_id, metric_type, metric_value)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (metric_id, session_id, metric_type, json.dumps(metric_value)))
                
                result = cursor.fetchone()
                self.connection.commit()
                
                logger.info(f"✅ Метрика создана: {metric_id}")
                return result[0] if result else metric_id
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Ошибка создания метрики: {e}")
            return None
    
    # =====================================================
    # АНАЛИТИЧЕСКИЕ ЗАПРОСЫ
    # =====================================================
    
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Получение статистики пользователя"""
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT s.id) as total_sessions,
                        COUNT(c.id) as total_commands,
                        COUNT(DISTINCT sc.id) as total_screenshots,
                        AVG(EXTRACT(EPOCH FROM (s.end_time - s.start_time))) as avg_session_duration_seconds
                    FROM users u
                    LEFT JOIN sessions s ON u.id = s.user_id
                    LEFT JOIN commands c ON s.id = c.session_id
                    LEFT JOIN screenshots sc ON s.id = sc.session_id
                    WHERE u.id = %s
                    GROUP BY u.id
                """, (user_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else {}
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики пользователя: {e}")
            return {}
    
    def get_session_commands(self, session_id: str) -> List[Dict[str, Any]]:
        """Получение всех команд сессии с ответами LLM"""
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        c.*,
                        la.response as llm_response,
                        la.model_info,
                        la.performance_metrics
                    FROM commands c
                    LEFT JOIN llm_answers la ON c.id = la.command_id
                    WHERE c.session_id = %s
                    ORDER BY c.created_at
                """, (session_id,))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения команд сессии: {e}")
            return []

# =====================================================
# УПРАВЛЕНИЕ ПАМЯТЬЮ ПОЛЬЗОВАТЕЛЯ
# =====================================================

    def get_user_memory(self, hardware_id_hash: str) -> Dict[str, str]:
        """
        Получает память пользователя по аппаратному ID.
        
        Args:
            hardware_id_hash: Хеш аппаратного ID пользователя
            
        Returns:
            Dict с ключами 'short' и 'long' для краткосрочной и долгосрочной памяти
        """
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT short_term_memory, long_term_memory
                    FROM users 
                    WHERE hardware_id_hash = %s
                """, (hardware_id_hash,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'short': result['short_term_memory'] or '',
                        'long': result['long_term_memory'] or ''
                    }
                else:
                    logger.warning(f"⚠️ Пользователь с hardware_id {hardware_id_hash} не найден")
                    return {'short': '', 'long': ''}
                    
        except Exception as e:
            logger.error(f"❌ Ошибка получения памяти пользователя: {e}")
            return {'short': '', 'long': ''}
    
    def update_user_memory(
        self, 
        hardware_id_hash: str, 
        short_memory: str, 
        long_memory: str
    ) -> bool:
        """
        Обновляет память пользователя.
        
        Args:
            hardware_id_hash: Хеш аппаратного ID пользователя
            short_memory: Краткосрочная память
            long_memory: Долгосрочная память
            
        Returns:
            True если обновление прошло успешно
        """
        try:
            with self.connection.cursor() as cursor:
                # Проверяем, существует ли пользователь
                cursor.execute("""
                    SELECT id FROM users WHERE hardware_id_hash = %s
                """, (hardware_id_hash,))
                
                user_exists = cursor.fetchone()
                
                if user_exists:
                    # Обновляем существующего пользователя
                    cursor.execute("""
                        UPDATE users 
                        SET short_term_memory = %s,
                            long_term_memory = %s,
                            memory_updated_at = NOW()
                        WHERE hardware_id_hash = %s
                    """, (short_memory, long_memory, hardware_id_hash))
                else:
                    # Создаем нового пользователя с памятью
                    cursor.execute("""
                        INSERT INTO users (hardware_id_hash, short_term_memory, long_term_memory)
                        VALUES (%s, %s, %s)
                    """, (hardware_id_hash, short_memory, long_memory))
                
                self.connection.commit()
                logger.info(f"✅ Память пользователя {hardware_id_hash} обновлена")
                return True
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Ошибка обновления памяти пользователя: {e}")
            return False
    
    def cleanup_expired_short_term_memory(self, hours: int = 24) -> int:
        """
        Очищает устаревшую краткосрочную память пользователей.
        
        Args:
            hours: Количество часов, после которых память считается устаревшей
            
        Returns:
            Количество очищенных записей
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT cleanup_expired_short_term_memory(%s)
                """, (hours,))
                
                result = cursor.fetchone()
                affected_rows = result[0] if result else 0
                
                self.connection.commit()
                logger.info(f"🧹 Очищено {affected_rows} записей краткосрочной памяти старше {hours} часов")
                return affected_rows
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"❌ Ошибка очистки устаревшей памяти: {e}")
            return 0
    
    def get_memory_statistics(self) -> Dict[str, any]:
        """
        Получает статистику использования системы памяти.
        
        Returns:
            Dict со статистикой памяти
        """
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM get_memory_stats()")
                result = cursor.fetchone()
                
                if result:
                    return dict(result)
                else:
                    logger.warning("⚠️ Не удалось получить статистику памяти")
                    return {}
                    
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики памяти: {e}")
            return {}
    
    def get_users_with_active_memory(self, limit: int = 100) -> List[Dict[str, any]]:
        """
        Получает список пользователей с активной памятью.
        
        Args:
            limit: Максимальное количество пользователей
            
        Returns:
            Список пользователей с памятью
        """
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT hardware_id_hash, memory_updated_at,
                           LENGTH(COALESCE(short_term_memory, '')) as short_memory_size,
                           LENGTH(COALESCE(long_term_memory, '')) as long_memory_size
                    FROM users 
                    WHERE short_term_memory IS NOT NULL OR long_term_memory IS NOT NULL
                    ORDER BY memory_updated_at DESC
                    LIMIT %s
                """, (limit,))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователей с памятью: {e}")
            return []

# =====================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# =====================================================

if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    # Тестирование менеджера базы данных
    with DatabaseManager() as db:
        # Создаем тестового пользователя
        hardware_id = "test_hardware_hash_123"
        user_metadata = {
            "hardware_info": {
                "mac_address": "00:11:22:33:44:55",
                "serial_number": "C02ABC123DEF",
                "volume_uuid": "12345678-1234-1234-1234-123456789abc"
            },
            "system_info": {
                "os_version": "macOS 14.0",
                "python_version": "3.12.7",
                "app_version": "1.0.0"
            }
        }
        
        user_id = db.create_user(hardware_id, user_metadata)
        if user_id:
            print(f"✅ Пользователь создан: {user_id}")
            
            # Создаем тестовую сессию
            session_metadata = {
                "app_version": "1.0.0",
                "start_method": "push_to_talk"
            }
            
            session_id = db.create_session(user_id, session_metadata)
            if session_id:
                print(f"✅ Сессия создана: {session_id}")
                
                # Создаем тестовую команду
                command_metadata = {
                    "input_method": "voice",
                    "duration_ms": 2500,
                    "confidence": 0.95
                }
                
                command_id = db.create_command(session_id, "Привет, как дела?", command_metadata)
                if command_id:
                    print(f"✅ Команда создана: {command_id}")
                    
                    # Создаем тестовый ответ LLM
                    model_info = {
                        "model_name": "gemini-2.0-flash-exp",
                        "provider": "google"
                    }
                    
                    performance_metrics = {
                        "response_time_ms": 1200,
                        "tokens_generated": 50
                    }
                    
                    answer_id = db.create_llm_answer(
                        command_id, 
                        "Привет, как дела?", 
                        "Привет! У меня все хорошо, спасибо что спросил. Как я могу тебе помочь?",
                        model_info,
                        performance_metrics
                    )
                    
                    if answer_id:
                        print(f"✅ Ответ LLM создан: {answer_id}")
                    
                    # Получаем статистику
                    stats = db.get_user_statistics(user_id)
                    print(f"📊 Статистика пользователя: {stats}")
                    
                    # Получаем команды сессии
                    commands = db.get_session_commands(session_id)
                    print(f"📝 Команды сессии: {len(commands)}")
                    
                    # Завершаем сессию
                    db.end_session(session_id)
                    print("✅ Сессия завершена")
        else:
            print("❌ Не удалось создать пользователя")
