"""
PostgreSQL Provider для работы с базой данных
"""

import asyncio
import logging
import json
import uuid
import time
from typing import AsyncGenerator, Dict, Any, Optional, List, Union
from datetime import datetime, timezone
import psycopg2
import psycopg2.extras
import psycopg2.pool
from integration.core.universal_provider_interface import UniversalProviderInterface

logger = logging.getLogger(__name__)

class PostgreSQLProvider(UniversalProviderInterface):
    """
    Провайдер для работы с PostgreSQL базой данных
    
    Обеспечивает все CRUD операции для таблиц:
    - users, sessions, commands, llm_answers, screenshots, performance_metrics
    - Управление памятью (short_term_memory, long_term_memory)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация PostgreSQL провайдера
        
        Args:
            config: Конфигурация провайдера
        """
        super().__init__(
            name="postgresql",
            priority=1,  # Основной провайдер
            config=config
        )
        
        # Настройки подключения
        self.connection_string = config.get('connection_string', 'postgresql://localhost/voice_assistant_db')
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5432)
        self.database = config.get('database', 'voice_assistant_db')
        self.username = config.get('username', 'postgres')
        self.password = config.get('password', '')
        
        # Настройки пула соединений
        self.min_connections = config.get('min_connections', 1)
        self.max_connections = config.get('max_connections', 10)
        self.connection_timeout = config.get('connection_timeout', 30)
        self.command_timeout = config.get('command_timeout', 60)
        
        # Настройки retry
        self.retry_attempts = config.get('retry_attempts', 3)
        self.retry_delay = config.get('retry_delay', 1)
        self.retry_backoff = config.get('retry_backoff', 2)
        
        # Настройки производительности
        self.fetch_size = config.get('fetch_size', 1000)
        self.batch_size = config.get('batch_size', 100)
        self.enable_prepared_statements = config.get('enable_prepared_statements', True)
        
        # Настройки логирования
        self.log_queries = config.get('log_queries', False)
        self.log_slow_queries = config.get('log_slow_queries', True)
        self.slow_query_threshold = config.get('slow_query_threshold', 1000)
        
        # Настройки мониторинга
        self.enable_metrics = config.get('enable_metrics', True)
        self.health_check_interval = config.get('health_check_interval', 300)
        
        # Пулы соединений
        self.connection_pool = None
        self.connection = None
        
        logger.info(f"PostgreSQL Provider initialized with host: {self.host}:{self.port}")
    
    async def initialize(self) -> bool:
        """
        Инициализация PostgreSQL провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing PostgreSQL Provider...")
            
            # Создаем пул соединений
            await self._create_connection_pool()
            
            # Тестируем подключение
            if await self._test_connection():
                self.is_initialized = True
                logger.info("PostgreSQL Provider initialized successfully")
                return True
            else:
                logger.error("PostgreSQL Provider connection test failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL Provider: {e}")
            return False
    
    async def process(self, input_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Обработка запроса к базе данных
        
        Args:
            input_data: Данные запроса (operation, table, data и т.д.)
            
        Yields:
            Результат операции
        """
        try:
            if not self.is_initialized:
                raise Exception("PostgreSQL Provider not initialized")
            
            # Извлекаем данные запроса
            operation = input_data.get('operation')
            table = input_data.get('table')
            data = input_data.get('data', {})
            filters = input_data.get('filters', {})
            
            if not operation or not table:
                raise Exception("Operation and table are required")
            
            # Выполняем операцию
            result = await self._execute_operation(operation, table, data, filters)
            
            # Обновляем метрики
            self.total_requests += 1
            self.report_success()
            
            yield result
            logger.debug(f"Database operation completed: {operation} on {table}")
            
        except Exception as e:
            logger.error(f"PostgreSQL Provider processing error: {e}")
            self.report_error(str(e))
            raise e
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов PostgreSQL провайдера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up PostgreSQL Provider...")
            
            # Закрываем пул соединений
            if self.connection_pool:
                self.connection_pool.closeall()
                self.connection_pool = None
            
            # Закрываем основное соединение
            if self.connection:
                self.connection.close()
                self.connection = None
            
            self.is_initialized = False
            logger.info("PostgreSQL Provider cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up PostgreSQL Provider: {e}")
            return False
    
    async def _create_connection_pool(self):
        """Создание пула соединений"""
        try:
            # Создаем пул соединений
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.min_connections,
                maxconn=self.max_connections,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                connect_timeout=self.connection_timeout
            )
            
            logger.info(f"Connection pool created: {self.min_connections}-{self.max_connections} connections")
            
        except Exception as e:
            logger.error(f"Error creating connection pool: {e}")
            raise e
    
    async def _test_connection(self) -> bool:
        """Тестирование подключения к БД"""
        try:
            # Получаем соединение из пула
            conn = self.connection_pool.getconn()
            
            try:
                # Выполняем простой запрос
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    
                if result and result[0] == 1:
                    logger.info("Database connection test successful")
                    return True
                else:
                    logger.error("Database connection test failed")
                    return False
                    
            finally:
                # Возвращаем соединение в пул
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Database connection test error: {e}")
            return False
    
    async def _execute_operation(self, operation: str, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнение операции с базой данных
        
        Args:
            operation: Тип операции (create, read, update, delete)
            table: Название таблицы
            data: Данные для операции
            filters: Фильтры для операции
            
        Returns:
            Результат операции
        """
        start_time = time.time()
        
        try:
            if operation == 'create':
                return await self._create_record(table, data)
            elif operation == 'read':
                return await self._read_records(table, filters)
            elif operation == 'update':
                return await self._update_record(table, data, filters)
            elif operation == 'delete':
                return await self._delete_record(table, filters)
            else:
                raise Exception(f"Unknown operation: {operation}")
                
        finally:
            # Логируем медленные запросы
            execution_time = (time.time() - start_time) * 1000
            if self.log_slow_queries and execution_time > self.slow_query_threshold:
                logger.warning(f"Slow query detected: {operation} on {table} took {execution_time:.2f}ms")
            
            if self.log_queries:
                logger.info(f"Query executed: {operation} on {table} in {execution_time:.2f}ms")
    
    async def _create_record(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание записи в таблице"""
        try:
            # Получаем соединение из пула
            conn = self.connection_pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    # Генерируем ID если не указан
                    if 'id' not in data:
                        data['id'] = str(uuid.uuid4())
                    
                    # Подготавливаем данные
                    prepared_data = self._prepare_data_for_db(data)
                    
                    # Формируем SQL запрос
                    columns = list(prepared_data.keys())
                    values = list(prepared_data.values())
                    placeholders = ['%s'] * len(values)
                    
                    sql = f"""
                        INSERT INTO {table} ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                        RETURNING *
                    """
                    
                    # Выполняем запрос
                    cursor.execute(sql, values)
                    result = cursor.fetchone()
                    
                    # Коммитим транзакцию
                    conn.commit()
                    
                    # Преобразуем результат
                    if result:
                        column_names = [desc[0] for desc in cursor.description]
                        result_dict = dict(zip(column_names, result))
                        return {
                            'success': True,
                            'data': result_dict,
                            'operation': 'create',
                            'table': table
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'No data returned',
                            'operation': 'create',
                            'table': table
                        }
                        
            finally:
                # Возвращаем соединение в пул
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error creating record in {table}: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation': 'create',
                'table': table
            }
    
    async def _read_records(self, table: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Чтение записей из таблицы"""
        try:
            # Получаем соединение из пула
            conn = self.connection_pool.getconn()
            
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Формируем SQL запрос
                    sql = f"SELECT * FROM {table}"
                    values = []
                    
                    if filters:
                        where_conditions = []
                        for key, value in filters.items():
                            if isinstance(value, dict):
                                # Поддержка операторов (gt, lt, like и т.д.)
                                for op, val in value.items():
                                    if op == 'gt':
                                        where_conditions.append(f"{key} > %s")
                                        values.append(val)
                                    elif op == 'lt':
                                        where_conditions.append(f"{key} < %s")
                                        values.append(val)
                                    elif op == 'like':
                                        where_conditions.append(f"{key} LIKE %s")
                                        values.append(val)
                                    elif op == 'in':
                                        placeholders = ['%s'] * len(val)
                                        where_conditions.append(f"{key} IN ({', '.join(placeholders)})")
                                        values.extend(val)
                            else:
                                where_conditions.append(f"{key} = %s")
                                values.append(value)
                        
                        if where_conditions:
                            sql += " WHERE " + " AND ".join(where_conditions)
                    
                    # Выполняем запрос
                    cursor.execute(sql, values)
                    results = cursor.fetchall()
                    
                    # Преобразуем результаты
                    records = [dict(row) for row in results]
                    
                    return {
                        'success': True,
                        'data': records,
                        'count': len(records),
                        'operation': 'read',
                        'table': table
                    }
                    
            finally:
                # Возвращаем соединение в пул
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error reading records from {table}: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation': 'read',
                'table': table
            }
    
    async def _update_record(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление записи в таблице"""
        try:
            # Получаем соединение из пула
            conn = self.connection_pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    # Подготавливаем данные
                    prepared_data = self._prepare_data_for_db(data)
                    
                    # Формируем SQL запрос
                    set_clauses = []
                    values = []
                    
                    for key, value in prepared_data.items():
                        set_clauses.append(f"{key} = %s")
                        values.append(value)
                    
                    # Добавляем условия WHERE
                    where_conditions = []
                    for key, value in filters.items():
                        where_conditions.append(f"{key} = %s")
                        values.append(value)
                    
                    if not where_conditions:
                        raise Exception("Update operation requires filters")
                    
                    sql = f"""
                        UPDATE {table}
                        SET {', '.join(set_clauses)}
                        WHERE {' AND '.join(where_conditions)}
                        RETURNING *
                    """
                    
                    # Выполняем запрос
                    cursor.execute(sql, values)
                    result = cursor.fetchone()
                    
                    # Коммитим транзакцию
                    conn.commit()
                    
                    # Преобразуем результат
                    if result:
                        column_names = [desc[0] for desc in cursor.description]
                        result_dict = dict(zip(column_names, result))
                        return {
                            'success': True,
                            'data': result_dict,
                            'operation': 'update',
                            'table': table
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'No records updated',
                            'operation': 'update',
                            'table': table
                        }
                        
            finally:
                # Возвращаем соединение в пул
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error updating record in {table}: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation': 'update',
                'table': table
            }
    
    async def _delete_record(self, table: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Удаление записи из таблицы"""
        try:
            # Получаем соединение из пула
            conn = self.connection_pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    # Формируем SQL запрос
                    where_conditions = []
                    values = []
                    
                    for key, value in filters.items():
                        where_conditions.append(f"{key} = %s")
                        values.append(value)
                    
                    if not where_conditions:
                        raise Exception("Delete operation requires filters")
                    
                    sql = f"""
                        DELETE FROM {table}
                        WHERE {' AND '.join(where_conditions)}
                        RETURNING *
                    """
                    
                    # Выполняем запрос
                    cursor.execute(sql, values)
                    result = cursor.fetchone()
                    
                    # Коммитим транзакцию
                    conn.commit()
                    
                    # Преобразуем результат
                    if result:
                        column_names = [desc[0] for desc in cursor.description]
                        result_dict = dict(zip(column_names, result))
                        return {
                            'success': True,
                            'data': result_dict,
                            'operation': 'delete',
                            'table': table
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'No records deleted',
                            'operation': 'delete',
                            'table': table
                        }
                        
            finally:
                # Возвращаем соединение в пул
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error deleting record from {table}: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation': 'delete',
                'table': table
            }
    
    def _prepare_data_for_db(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Подготовка данных для записи в БД
        
        Args:
            data: Исходные данные
            
        Returns:
            Подготовленные данные
        """
        prepared = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                # JSONB поля
                prepared[key] = json.dumps(value)
            elif isinstance(value, datetime):
                # Timestamp поля
                prepared[key] = value
            elif value is None:
                # NULL значения
                prepared[key] = None
            else:
                # Обычные значения
                prepared[key] = value
        
        return prepared
    
    async def _custom_health_check(self) -> bool:
        """
        Кастомная проверка здоровья PostgreSQL провайдера
        
        Returns:
            True если провайдер здоров, False иначе
        """
        try:
            # Проверяем пул соединений
            if not self.connection_pool:
                return False
            
            # Проверяем подключение к БД
            return await self._test_connection()
            
        except Exception as e:
            logger.warning(f"PostgreSQL Provider health check failed: {e}")
            return False
    
    # =====================================================
    # СПЕЦИАЛИЗИРОВАННЫЕ МЕТОДЫ ДЛЯ КАЖДОЙ ТАБЛИЦЫ
    # =====================================================
    
    async def create_user(self, hardware_id_hash: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Создание нового пользователя"""
        data = {
            'hardware_id_hash': hardware_id_hash,
            'metadata': metadata or {}
        }
        
        result = await self._execute_operation('create', 'users', data, {})
        
        if result['success']:
            return result['data']['id']
        else:
            logger.error(f"Failed to create user: {result['error']}")
            return None
    
    async def get_user_by_hardware_id(self, hardware_id_hash: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по аппаратному ID"""
        filters = {'hardware_id_hash': hardware_id_hash}
        
        result = await self._execute_operation('read', 'users', {}, filters)
        
        if result['success'] and result['data']:
            return result['data'][0]
        else:
            return None
    
    async def create_session(self, user_id: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Создание новой сессии"""
        data = {
            'user_id': user_id,
            'metadata': metadata or {},
            'status': 'active'
        }
        
        result = await self._execute_operation('create', 'sessions', data, {})
        
        if result['success']:
            return result['data']['id']
        else:
            logger.error(f"Failed to create session: {result['error']}")
            return None
    
    async def end_session(self, session_id: str) -> bool:
        """Завершение сессии"""
        data = {
            'status': 'ended',
            'end_time': datetime.now(timezone.utc)
        }
        filters = {'id': session_id}
        
        result = await self._execute_operation('update', 'sessions', data, filters)
        
        return result['success']
    
    async def create_command(self, session_id: str, prompt: str, metadata: Dict[str, Any] = None, language: str = 'en') -> Optional[str]:
        """Создание новой команды"""
        data = {
            'session_id': session_id,
            'prompt': prompt,
            'language': language,
            'metadata': metadata or {}
        }
        
        result = await self._execute_operation('create', 'commands', data, {})
        
        if result['success']:
            return result['data']['id']
        else:
            logger.error(f"Failed to create command: {result['error']}")
            return None
    
    async def create_llm_answer(self, command_id: str, prompt: str, response: str,
                               model_info: Dict[str, Any] = None,
                               performance_metrics: Dict[str, Any] = None) -> Optional[str]:
        """Создание ответа LLM"""
        data = {
            'command_id': command_id,
            'prompt': prompt,
            'response': response,
            'model_info': model_info or {},
            'performance_metrics': performance_metrics or {}
        }
        
        result = await self._execute_operation('create', 'llm_answers', data, {})
        
        if result['success']:
            return result['data']['id']
        else:
            logger.error(f"Failed to create LLM answer: {result['error']}")
            return None
    
    async def create_screenshot(self, session_id: str, file_path: str = None, file_url: str = None,
                               metadata: Dict[str, Any] = None) -> Optional[str]:
        """Создание записи о скриншоте"""
        data = {
            'session_id': session_id,
            'file_path': file_path,
            'file_url': file_url,
            'metadata': metadata or {}
        }
        
        result = await self._execute_operation('create', 'screenshots', data, {})
        
        if result['success']:
            return result['data']['id']
        else:
            logger.error(f"Failed to create screenshot: {result['error']}")
            return None
    
    async def create_performance_metric(self, session_id: str, metric_type: str, 
                                       metric_value: Dict[str, Any]) -> Optional[str]:
        """Создание метрики производительности"""
        data = {
            'session_id': session_id,
            'metric_type': metric_type,
            'metric_value': metric_value
        }
        
        result = await self._execute_operation('create', 'performance_metrics', data, {})
        
        if result['success']:
            return result['data']['id']
        else:
            logger.error(f"Failed to create performance metric: {result['error']}")
            return None
    
    # =====================================================
    # МЕТОДЫ УПРАВЛЕНИЯ ПАМЯТЬЮ (БЕЗ ЛОГИКИ)
    # =====================================================
    
    async def get_user_memory(self, hardware_id_hash: str) -> Dict[str, str]:
        """Получение памяти пользователя"""
        filters = {'hardware_id_hash': hardware_id_hash}
        
        result = await self._execute_operation('read', 'users', {}, filters)
        
        if result['success'] and result['data']:
            user_data = result['data'][0]
            return {
                'short': user_data.get('short_term_memory') or '',
                'long': user_data.get('long_term_memory') or ''
            }
        else:
            return {'short': '', 'long': ''}
    
    async def update_user_memory(self, hardware_id_hash: str, short_memory: str, long_memory: str) -> bool:
        """Обновление памяти пользователя"""
        data = {
            'short_term_memory': short_memory,
            'long_term_memory': long_memory,
            'memory_updated_at': datetime.now(timezone.utc)
        }
        filters = {'hardware_id_hash': hardware_id_hash}
        
        result = await self._execute_operation('update', 'users', data, filters)
        
        return result['success']
    
    async def cleanup_expired_short_term_memory(self, hours: int = 24) -> int:
        """Очистка устаревшей краткосрочной памяти"""
        try:
            # Получаем соединение из пула
            conn = self.connection_pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    # Выполняем SQL функцию очистки
                    cursor.execute("SELECT cleanup_expired_short_term_memory(%s)", (hours,))
                    result = cursor.fetchone()
                    
                    affected_rows = result[0] if result else 0
                    
                    # Коммитим транзакцию
                    conn.commit()
                    
                    logger.info(f"Cleaned up {affected_rows} expired short-term memory records")
                    return affected_rows
                    
            finally:
                # Возвращаем соединение в пул
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error cleaning up expired short-term memory: {e}")
            return 0
    
    async def get_memory_statistics(self) -> Dict[str, Any]:
        """Получение статистики памяти"""
        try:
            # Получаем соединение из пула
            conn = self.connection_pool.getconn()
            
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Выполняем SQL функцию статистики
                    cursor.execute("SELECT * FROM get_memory_stats()")
                    result = cursor.fetchone()
                    
                    if result:
                        return dict(result)
                    else:
                        return {}
                        
            finally:
                # Возвращаем соединение в пул
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error getting memory statistics: {e}")
            return {}
    
    async def get_users_with_active_memory(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Получение пользователей с активной памятью"""
        try:
            # Получаем соединение из пула
            conn = self.connection_pool.getconn()
            
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Выполняем SQL запрос
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
                    
            finally:
                # Возвращаем соединение в пул
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error getting users with active memory: {e}")
            return []
    
    # =====================================================
    # АНАЛИТИЧЕСКИЕ МЕТОДЫ
    # =====================================================
    
    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Получение статистики пользователя"""
        try:
            # Получаем соединение из пула
            conn = self.connection_pool.getconn()
            
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
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
                    
            finally:
                # Возвращаем соединение в пул
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
    
    async def get_session_commands(self, session_id: str) -> List[Dict[str, Any]]:
        """Получение всех команд сессии с ответами LLM"""
        try:
            # Получаем соединение из пула
            conn = self.connection_pool.getconn()
            
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
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
                    
            finally:
                # Возвращаем соединение в пул
                self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error getting session commands: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение расширенного статуса PostgreSQL провайдера
        
        Returns:
            Словарь со статусом провайдера
        """
        base_status = super().get_status()
        
        # Добавляем специфичную информацию
        base_status.update({
            "provider_type": "postgresql",
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "min_connections": self.min_connections,
            "max_connections": self.max_connections,
            "connection_timeout": self.connection_timeout,
            "command_timeout": self.command_timeout,
            "retry_attempts": self.retry_attempts,
            "enable_metrics": self.enable_metrics,
            "health_check_interval": self.health_check_interval,
            "pool_available": bool(self.connection_pool),
            "connection_available": bool(self.connection)
        })
        
        return base_status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение расширенных метрик PostgreSQL провайдера
        
        Returns:
            Словарь с метриками провайдера
        """
        base_metrics = super().get_metrics()
        
        # Добавляем специфичные метрики
        base_metrics.update({
            "provider_type": "postgresql",
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "pool_available": bool(self.connection_pool),
            "connection_available": bool(self.connection),
            "enable_metrics": self.enable_metrics
        })
        
        return base_metrics
