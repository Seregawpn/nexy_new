"""
Основной DatabaseManager - координатор модуля управления базой данных
"""

import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from modules.database.config import DatabaseConfig
from modules.database.providers.postgresql_provider import PostgreSQLProvider

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Основной менеджер базы данных
    
    Координирует работу PostgreSQL Provider,
    обеспечивает единый интерфейс для работы с базой данных.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация менеджера базы данных
        
        Args:
            config: Конфигурация модуля
        """
        self.config = DatabaseConfig(config)
        self.postgresql_provider = None
        self.is_initialized = False
        
        logger.info("DatabaseManager initialized")
    
    async def initialize(self) -> bool:
        """
        Инициализация менеджера базы данных
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing DatabaseManager...")
            
            # Валидируем конфигурацию
            if not self.config.validate():
                logger.error("Database configuration validation failed")
                return False
            
            # Создаем провайдер
            await self._create_provider()
            
            # Инициализируем провайдер
            await self._initialize_provider()
            
            self.is_initialized = True
            logger.info("DatabaseManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize DatabaseManager: {e}")
            return False
    
    async def _create_provider(self):
        """Создание провайдера базы данных"""
        try:
            # PostgreSQL Provider
            provider_config = self._get_provider_config()
            self.postgresql_provider = PostgreSQLProvider(provider_config)
            
            logger.info("Created database provider")
            
        except Exception as e:
            logger.error(f"Error creating provider: {e}")
            raise e
    
    async def _initialize_provider(self):
        """Инициализация провайдера"""
        try:
            if await self.postgresql_provider.initialize():
                logger.info("PostgreSQL Provider initialized successfully")
            else:
                logger.error("PostgreSQL Provider initialization failed")
                raise Exception("PostgreSQL Provider initialization failed")
                
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL Provider: {e}")
            raise e
    
    def _get_provider_config(self) -> Dict[str, Any]:
        """Получение конфигурации для провайдера"""
        return {
            'connection_string': self.config.get_connection_string(),
            'host': self.config.host,
            'port': self.config.port,
            'database': self.config.database,
            'username': self.config.username,
            'password': self.config.password,
            'min_connections': self.config.min_connections,
            'max_connections': self.config.max_connections,
            'connection_timeout': self.config.connection_timeout,
            'command_timeout': self.config.command_timeout,
            'retry_attempts': self.config.retry_attempts,
            'retry_delay': self.config.retry_delay,
            'retry_backoff': self.config.retry_backoff,
            'fetch_size': self.config.fetch_size,
            'batch_size': self.config.batch_size,
            'enable_prepared_statements': self.config.enable_prepared_statements,
            'log_queries': self.config.log_queries,
            'log_slow_queries': self.config.log_slow_queries,
            'slow_query_threshold': self.config.slow_query_threshold,
            'enable_metrics': self.config.enable_metrics,
            'health_check_interval': self.config.health_check_interval
        }
    
    # =====================================================
    # УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
    # =====================================================
    
    async def create_user(self, hardware_id_hash: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        Создание нового пользователя
        
        Args:
            hardware_id_hash: Хеш аппаратного ID
            metadata: Метаданные пользователя
            
        Returns:
            UUID пользователя или None при ошибке
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.create_user(hardware_id_hash, metadata)
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    async def get_user_by_hardware_id(self, hardware_id_hash: str) -> Optional[Dict[str, Any]]:
        """
        Получение пользователя по аппаратному ID
        
        Args:
            hardware_id_hash: Хеш аппаратного ID
            
        Returns:
            Данные пользователя или None если не найден
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.get_user_by_hardware_id(hardware_id_hash)
            
        except Exception as e:
            logger.error(f"Error getting user by hardware ID: {e}")
            return None
    
    # =====================================================
    # УПРАВЛЕНИЕ СЕССИЯМИ
    # =====================================================
    
    async def create_session(self, user_id: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        Создание новой сессии
        
        Args:
            user_id: ID пользователя
            metadata: Метаданные сессии
            
        Returns:
            UUID сессии или None при ошибке
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.create_session(user_id, metadata)
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
    
    async def end_session(self, session_id: str) -> bool:
        """
        Завершение сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            True если завершение успешно, False иначе
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.end_session(session_id)
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return False
    
    # =====================================================
    # УПРАВЛЕНИЕ КОМАНДАМИ
    # =====================================================
    
    async def create_command(self, session_id: str, prompt: str, metadata: Dict[str, Any] = None, language: str = 'en') -> Optional[str]:
        """
        Создание новой команды
        
        Args:
            session_id: ID сессии
            prompt: Текст команды
            metadata: Метаданные команды
            language: Язык команды
            
        Returns:
            UUID команды или None при ошибке
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.create_command(session_id, prompt, metadata, language)
            
        except Exception as e:
            logger.error(f"Error creating command: {e}")
            return None
    
    # =====================================================
    # УПРАВЛЕНИЕ ОТВЕТАМИ LLM
    # =====================================================
    
    async def create_llm_answer(self, command_id: str, prompt: str, response: str,
                               model_info: Dict[str, Any] = None,
                               performance_metrics: Dict[str, Any] = None) -> Optional[str]:
        """
        Создание ответа LLM
        
        Args:
            command_id: ID команды
            prompt: Исходный промпт
            response: Ответ LLM
            model_info: Информация о модели
            performance_metrics: Метрики производительности
            
        Returns:
            UUID ответа или None при ошибке
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.create_llm_answer(
                command_id, prompt, response, model_info, performance_metrics
            )
            
        except Exception as e:
            logger.error(f"Error creating LLM answer: {e}")
            return None
    
    # =====================================================
    # УПРАВЛЕНИЕ СКРИНШОТАМИ
    # =====================================================
    
    async def create_screenshot(self, session_id: str, file_path: str = None, file_url: str = None,
                               metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        Создание записи о скриншоте
        
        Args:
            session_id: ID сессии
            file_path: Путь к файлу
            file_url: URL файла
            metadata: Метаданные скриншота
            
        Returns:
            UUID скриншота или None при ошибке
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.create_screenshot(session_id, file_path, file_url, metadata)
            
        except Exception as e:
            logger.error(f"Error creating screenshot: {e}")
            return None
    
    # =====================================================
    # УПРАВЛЕНИЕ МЕТРИКАМИ
    # =====================================================
    
    async def create_performance_metric(self, session_id: str, metric_type: str, 
                                       metric_value: Dict[str, Any]) -> Optional[str]:
        """
        Создание метрики производительности
        
        Args:
            session_id: ID сессии
            metric_type: Тип метрики
            metric_value: Значение метрики
            
        Returns:
            UUID метрики или None при ошибке
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.create_performance_metric(session_id, metric_type, metric_value)
            
        except Exception as e:
            logger.error(f"Error creating performance metric: {e}")
            return None
    
    # =====================================================
    # АНАЛИТИЧЕСКИЕ ЗАПРОСЫ
    # =====================================================
    
    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Получение статистики пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь со статистикой пользователя
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.get_user_statistics(user_id)
            
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
    
    async def get_session_commands(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Получение всех команд сессии с ответами LLM
        
        Args:
            session_id: ID сессии
            
        Returns:
            Список команд с ответами
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.get_session_commands(session_id)
            
        except Exception as e:
            logger.error(f"Error getting session commands: {e}")
            return []
    
    # =====================================================
    # УПРАВЛЕНИЕ ПАМЯТЬЮ (БЕЗ ЛОГИКИ)
    # =====================================================
    
    async def get_user_memory(self, hardware_id_hash: str) -> Dict[str, str]:
        """
        Получение памяти пользователя
        
        Args:
            hardware_id_hash: Хеш аппаратного ID
            
        Returns:
            Словарь с памятью пользователя
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.get_user_memory(hardware_id_hash)
            
        except Exception as e:
            logger.error(f"Error getting user memory: {e}")
            return {'short': '', 'long': ''}
    
    async def update_user_memory(self, hardware_id_hash: str, short_memory: str, long_memory: str) -> bool:
        """
        Обновление памяти пользователя
        
        Args:
            hardware_id_hash: Хеш аппаратного ID
            short_memory: Краткосрочная память
            long_memory: Долгосрочная память
            
        Returns:
            True если обновление успешно, False иначе
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.update_user_memory(hardware_id_hash, short_memory, long_memory)
            
        except Exception as e:
            logger.error(f"Error updating user memory: {e}")
            return False
    
    async def cleanup_expired_short_term_memory(self, hours: int = 24) -> int:
        """
        Очистка устаревшей краткосрочной памяти
        
        Args:
            hours: Количество часов для очистки
            
        Returns:
            Количество очищенных записей
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.cleanup_expired_short_term_memory(hours)
            
        except Exception as e:
            logger.error(f"Error cleaning up expired short-term memory: {e}")
            return 0
    
    async def get_memory_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики памяти
        
        Returns:
            Словарь со статистикой памяти
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.get_memory_statistics()
            
        except Exception as e:
            logger.error(f"Error getting memory statistics: {e}")
            return {}
    
    async def get_users_with_active_memory(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получение пользователей с активной памятью
        
        Args:
            limit: Максимальное количество пользователей
            
        Returns:
            Список пользователей с памятью
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            return await self.postgresql_provider.get_users_with_active_memory(limit)
            
        except Exception as e:
            logger.error(f"Error getting users with active memory: {e}")
            return []
    
    # =====================================================
    # УНИВЕРСАЛЬНЫЕ МЕТОДЫ
    # =====================================================
    
    async def execute_query(self, operation: str, table: str, data: Dict[str, Any] = None, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Универсальное выполнение запроса к базе данных
        
        Args:
            operation: Тип операции (create, read, update, delete)
            table: Название таблицы
            data: Данные для операции
            filters: Фильтры для операции
            
        Returns:
            Результат операции
        """
        try:
            if not self.is_initialized:
                raise Exception("DatabaseManager not initialized")
            
            input_data = {
                'operation': operation,
                'table': table,
                'data': data or {},
                'filters': filters or {}
            }
            
            result = None
            async for res in self.postgresql_provider.process(input_data):
                result = res
                break
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation': operation,
                'table': table
            }
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов менеджера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up DatabaseManager...")
            
            # Очищаем провайдер
            if self.postgresql_provider:
                await self.postgresql_provider.cleanup()
            
            self.is_initialized = False
            logger.info("DatabaseManager cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up DatabaseManager: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса менеджера
        
        Returns:
            Словарь со статусом менеджера
        """
        status = {
            "is_initialized": self.is_initialized,
            "config_status": self.config.get_status(),
            "postgresql_provider": None
        }
        
        # Добавляем статус провайдера
        if self.postgresql_provider:
            status["postgresql_provider"] = self.postgresql_provider.get_status()
        
        return status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик менеджера
        
        Returns:
            Словарь с метриками менеджера
        """
        metrics = {
            "is_initialized": self.is_initialized,
            "postgresql_provider": None
        }
        
        # Добавляем метрики провайдера
        if self.postgresql_provider:
            metrics["postgresql_provider"] = self.postgresql_provider.get_metrics()
        
        return metrics
    
    def get_config_status(self) -> Dict[str, Any]:
        """
        Получение статуса конфигурации
        
        Returns:
            Словарь со статусом конфигурации
        """
        return self.config.get_status()
    
    def get_security_settings(self) -> Dict[str, Any]:
        """
        Получение настроек безопасности
        
        Returns:
            Словарь с настройками безопасности
        """
        return self.config.get_security_settings()
    
    def get_performance_settings(self) -> Dict[str, Any]:
        """
        Получение настроек производительности
        
        Returns:
            Словарь с настройками производительности
        """
        return self.config.get_performance_settings()
    
    def get_monitoring_settings(self) -> Dict[str, Any]:
        """
        Получение настроек мониторинга
        
        Returns:
            Словарь с настройками мониторинга
        """
        return self.config.get_monitoring_settings()
    
    def get_cleanup_settings(self) -> Dict[str, Any]:
        """
        Получение настроек очистки
        
        Returns:
            Словарь с настройками очистки
        """
        return self.config.get_cleanup_settings()
    
    def get_schema_settings(self) -> Dict[str, Any]:
        """
        Получение настроек схемы
        
        Returns:
            Словарь с настройками схемы
        """
        return self.config.get_schema_settings()
    
    def reset_metrics(self):
        """Сброс метрик менеджера"""
        if self.postgresql_provider:
            self.postgresql_provider.reset_metrics()
        
        logger.info("DatabaseManager metrics reset")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Получение краткой сводки по менеджеру
        
        Returns:
            Словарь со сводкой
        """
        summary = {
            "is_initialized": self.is_initialized,
            "postgresql_provider_available": self.postgresql_provider.is_initialized if self.postgresql_provider else False,
            "config_valid": self.config.validate(),
            "security_settings": self.get_security_settings(),
            "performance_settings": self.get_performance_settings()
        }
        
        return summary
    
    def __str__(self) -> str:
        """Строковое представление менеджера"""
        return f"DatabaseManager(initialized={self.is_initialized}, provider=1)"
    
    def __repr__(self) -> str:
        """Представление менеджера для отладки"""
        return (
            f"DatabaseManager("
            f"initialized={self.is_initialized}, "
            f"postgresql_provider_available={self.postgresql_provider.is_initialized if self.postgresql_provider else False}"
            f")"
        )
