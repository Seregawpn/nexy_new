"""
Конфигурация модуля Database
"""

import os
from typing import Dict, Any, Optional

class DatabaseConfig:
    """Конфигурация модуля управления базой данных"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация конфигурации
        
        Args:
            config: Словарь с конфигурацией (опционально)
        """
        self.config = config or {}
        
        # Настройки подключения к БД
        self.connection_string = self.config.get('connection_string', 'postgresql://localhost/voice_assistant_db')
        self.host = self.config.get('host', 'localhost')
        self.port = self.config.get('port', 5432)
        self.database = self.config.get('database', 'voice_assistant_db')
        self.username = self.config.get('username', 'postgres')
        self.password = self.config.get('password', '')
        
        # Настройки пула соединений
        self.min_connections = self.config.get('min_connections', 1)
        self.max_connections = self.config.get('max_connections', 10)
        self.connection_timeout = self.config.get('connection_timeout', 30)
        self.command_timeout = self.config.get('command_timeout', 60)
        
        # Настройки повторных попыток
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.retry_delay = self.config.get('retry_delay', 1)
        self.retry_backoff = self.config.get('retry_backoff', 2)
        
        # Настройки транзакций
        self.autocommit = self.config.get('autocommit', False)
        self.isolation_level = self.config.get('isolation_level', 'READ_COMMITTED')
        self.transaction_timeout = self.config.get('transaction_timeout', 300)
        
        # Настройки производительности
        self.fetch_size = self.config.get('fetch_size', 1000)
        self.batch_size = self.config.get('batch_size', 100)
        self.enable_prepared_statements = self.config.get('enable_prepared_statements', True)
        self.enable_connection_pooling = self.config.get('enable_connection_pooling', True)
        
        # Настройки логирования
        self.log_level = self.config.get('log_level', 'INFO')
        self.log_queries = self.config.get('log_queries', False)
        self.log_slow_queries = self.config.get('log_slow_queries', True)
        self.slow_query_threshold = self.config.get('slow_query_threshold', 1000)  # мс
        
        # Настройки безопасности
        self.ssl_mode = self.config.get('ssl_mode', 'prefer')
        self.ssl_cert = self.config.get('ssl_cert', None)
        self.ssl_key = self.config.get('ssl_key', None)
        self.ssl_ca = self.config.get('ssl_ca', None)
        self.verify_ssl = self.config.get('verify_ssl', True)
        
        # Настройки мониторинга
        self.enable_metrics = self.config.get('enable_metrics', True)
        self.health_check_interval = self.config.get('health_check_interval', 300)  # 5 минут
        self.connection_health_check = self.config.get('connection_health_check', True)
        
        # Настройки очистки
        self.cleanup_interval = self.config.get('cleanup_interval', 3600)  # 1 час
        self.cleanup_batch_size = self.config.get('cleanup_batch_size', 1000)
        self.enable_auto_cleanup = self.config.get('enable_auto_cleanup', True)
        
        # Настройки схемы БД
        self.schema_name = self.config.get('schema_name', 'public')
        self.table_prefix = self.config.get('table_prefix', '')
        self.enable_migrations = self.config.get('enable_migrations', True)
        self.migration_path = self.config.get('migration_path', 'database/migrations')
        
    def get_connection_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации подключения к БД
        
        Returns:
            Словарь с конфигурацией подключения
        """
        return {
            'connection_string': self.connection_string,
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'password': self.password,
            'ssl_mode': self.ssl_mode,
            'ssl_cert': self.ssl_cert,
            'ssl_key': self.ssl_key,
            'ssl_ca': self.ssl_ca,
            'verify_ssl': self.verify_ssl
        }
    
    def get_pool_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации пула соединений
        
        Returns:
            Словарь с конфигурацией пула
        """
        return {
            'min_connections': self.min_connections,
            'max_connections': self.max_connections,
            'connection_timeout': self.connection_timeout,
            'command_timeout': self.command_timeout,
            'enable_connection_pooling': self.enable_connection_pooling
        }
    
    def get_retry_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации повторных попыток
        
        Returns:
            Словарь с конфигурацией retry
        """
        return {
            'retry_attempts': self.retry_attempts,
            'retry_delay': self.retry_delay,
            'retry_backoff': self.retry_backoff
        }
    
    def get_transaction_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации транзакций
        
        Returns:
            Словарь с конфигурацией транзакций
        """
        return {
            'autocommit': self.autocommit,
            'isolation_level': self.isolation_level,
            'transaction_timeout': self.transaction_timeout
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации производительности
        
        Returns:
            Словарь с конфигурацией производительности
        """
        return {
            'fetch_size': self.fetch_size,
            'batch_size': self.batch_size,
            'enable_prepared_statements': self.enable_prepared_statements,
            'log_queries': self.log_queries,
            'log_slow_queries': self.log_slow_queries,
            'slow_query_threshold': self.slow_query_threshold
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации мониторинга
        
        Returns:
            Словарь с конфигурацией мониторинга
        """
        return {
            'enable_metrics': self.enable_metrics,
            'health_check_interval': self.health_check_interval,
            'connection_health_check': self.connection_health_check
        }
    
    def get_cleanup_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации очистки
        
        Returns:
            Словарь с конфигурацией очистки
        """
        return {
            'cleanup_interval': self.cleanup_interval,
            'cleanup_batch_size': self.cleanup_batch_size,
            'enable_auto_cleanup': self.enable_auto_cleanup
        }
    
    def get_schema_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации схемы БД
        
        Returns:
            Словарь с конфигурацией схемы
        """
        return {
            'schema_name': self.schema_name,
            'table_prefix': self.table_prefix,
            'enable_migrations': self.enable_migrations,
            'migration_path': self.migration_path
        }
    
    def validate(self) -> bool:
        """
        Валидация конфигурации
        
        Returns:
            True если конфигурация валидна, False иначе
        """
        # Проверяем корректность параметров подключения
        if not self.host:
            print("❌ host не может быть пустым")
            return False
            
        if not isinstance(self.port, int) or self.port < 1 or self.port > 65535:
            print("❌ port должен быть числом от 1 до 65535")
            return False
            
        if not self.database:
            print("❌ database не может быть пустой")
            return False
            
        # Проверяем корректность параметров пула
        if self.min_connections < 0:
            print("❌ min_connections должен быть неотрицательным")
            return False
            
        if self.max_connections < self.min_connections:
            print("❌ max_connections должен быть больше или равен min_connections")
            return False
            
        if self.connection_timeout <= 0:
            print("❌ connection_timeout должен быть положительным")
            return False
            
        if self.command_timeout <= 0:
            print("❌ command_timeout должен быть положительным")
            return False
            
        # Проверяем корректность параметров retry
        if self.retry_attempts < 0:
            print("❌ retry_attempts должен быть неотрицательным")
            return False
            
        if self.retry_delay <= 0:
            print("❌ retry_delay должен быть положительным")
            return False
            
        if self.retry_backoff <= 0:
            print("❌ retry_backoff должен быть положительным")
            return False
            
        # Проверяем корректность параметров производительности
        if self.fetch_size <= 0:
            print("❌ fetch_size должен быть положительным")
            return False
            
        if self.batch_size <= 0:
            print("❌ batch_size должен быть положительным")
            return False
            
        if self.slow_query_threshold <= 0:
            print("❌ slow_query_threshold должен быть положительным")
            return False
            
        # Проверяем корректность параметров мониторинга
        if self.health_check_interval <= 0:
            print("❌ health_check_interval должен быть положительным")
            return False
            
        # Проверяем корректность параметров очистки
        if self.cleanup_interval <= 0:
            print("❌ cleanup_interval должен быть положительным")
            return False
            
        if self.cleanup_batch_size <= 0:
            print("❌ cleanup_batch_size должен быть положительным")
            return False
            
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса конфигурации
        
        Returns:
            Словарь со статусом конфигурации
        """
        return {
            'connection_string': self.connection_string,
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'password_set': bool(self.password),
            'min_connections': self.min_connections,
            'max_connections': self.max_connections,
            'connection_timeout': self.connection_timeout,
            'command_timeout': self.command_timeout,
            'retry_attempts': self.retry_attempts,
            'retry_delay': self.retry_delay,
            'retry_backoff': self.retry_backoff,
            'autocommit': self.autocommit,
            'isolation_level': self.isolation_level,
            'transaction_timeout': self.transaction_timeout,
            'fetch_size': self.fetch_size,
            'batch_size': self.batch_size,
            'enable_prepared_statements': self.enable_prepared_statements,
            'enable_connection_pooling': self.enable_connection_pooling,
            'log_level': self.log_level,
            'log_queries': self.log_queries,
            'log_slow_queries': self.log_slow_queries,
            'slow_query_threshold': self.slow_query_threshold,
            'ssl_mode': self.ssl_mode,
            'verify_ssl': self.verify_ssl,
            'enable_metrics': self.enable_metrics,
            'health_check_interval': self.health_check_interval,
            'connection_health_check': self.connection_health_check,
            'cleanup_interval': self.cleanup_interval,
            'cleanup_batch_size': self.cleanup_batch_size,
            'enable_auto_cleanup': self.enable_auto_cleanup,
            'schema_name': self.schema_name,
            'table_prefix': self.table_prefix,
            'enable_migrations': self.enable_migrations,
            'migration_path': self.migration_path
        }
    
    def get_security_settings(self) -> Dict[str, Any]:
        """
        Получение настроек безопасности
        
        Returns:
            Словарь с настройками безопасности
        """
        return {
            'ssl_mode': self.ssl_mode,
            'ssl_cert': bool(self.ssl_cert),
            'ssl_key': bool(self.ssl_key),
            'ssl_ca': bool(self.ssl_ca),
            'verify_ssl': self.verify_ssl,
            'password_set': bool(self.password)
        }
    
    def get_performance_settings(self) -> Dict[str, Any]:
        """
        Получение настроек производительности
        
        Returns:
            Словарь с настройками производительности
        """
        return {
            'fetch_size': self.fetch_size,
            'batch_size': self.batch_size,
            'enable_prepared_statements': self.enable_prepared_statements,
            'enable_connection_pooling': self.enable_connection_pooling,
            'min_connections': self.min_connections,
            'max_connections': self.max_connections,
            'connection_timeout': self.connection_timeout,
            'command_timeout': self.command_timeout,
            'slow_query_threshold': self.slow_query_threshold
        }
    
    def get_monitoring_settings(self) -> Dict[str, Any]:
        """
        Получение настроек мониторинга
        
        Returns:
            Словарь с настройками мониторинга
        """
        return {
            'enable_metrics': self.enable_metrics,
            'health_check_interval': self.health_check_interval,
            'connection_health_check': self.connection_health_check,
            'log_queries': self.log_queries,
            'log_slow_queries': self.log_slow_queries,
            'log_level': self.log_level
        }
    
    def get_cleanup_settings(self) -> Dict[str, Any]:
        """
        Получение настроек очистки
        
        Returns:
            Словарь с настройками очистки
        """
        return {
            'cleanup_interval': self.cleanup_interval,
            'cleanup_batch_size': self.cleanup_batch_size,
            'enable_auto_cleanup': self.enable_auto_cleanup
        }
    
    def get_schema_settings(self) -> Dict[str, Any]:
        """
        Получение настроек схемы
        
        Returns:
            Словарь с настройками схемы
        """
        return {
            'schema_name': self.schema_name,
            'table_prefix': self.table_prefix,
            'enable_migrations': self.enable_migrations,
            'migration_path': self.migration_path
        }
    
    def get_connection_string(self) -> str:
        """
        Получение строки подключения
        
        Returns:
            Строка подключения к БД
        """
        if self.connection_string and self.connection_string != 'postgresql://localhost/voice_assistant_db':
            return self.connection_string
        
        # Формируем строку подключения из параметров
        ssl_params = ""
        if self.ssl_mode and self.ssl_mode != 'prefer':
            ssl_params = f"?sslmode={self.ssl_mode}"
        
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}{ssl_params}"
    
    def get_environment_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации из переменных окружения
        
        Returns:
            Словарь с конфигурацией из env
        """
        return {
            'connection_string': os.getenv('DATABASE_URL', self.connection_string),
            'host': os.getenv('DB_HOST', self.host),
            'port': int(os.getenv('DB_PORT', self.port)),
            'database': os.getenv('DB_NAME', self.database),
            'username': os.getenv('DB_USER', self.username),
            'password': os.getenv('DB_PASSWORD', self.password),
            'ssl_mode': os.getenv('DB_SSL_MODE', self.ssl_mode),
            'log_level': os.getenv('DB_LOG_LEVEL', self.log_level)
        }
