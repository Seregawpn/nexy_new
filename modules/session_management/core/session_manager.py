"""
Основной SessionManager - координатор модуля управления сессиями
"""

import logging
from typing import Dict, Any, Optional, AsyncGenerator
from modules.session_management.config import SessionManagementConfig
from modules.session_management.providers.hardware_id_provider import HardwareIDProvider
from modules.session_management.providers.session_tracker import SessionTracker

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Основной менеджер сессий
    
    Координирует работу Hardware ID Provider и Session Tracker,
    обеспечивает единый интерфейс для управления сессиями пользователей.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация менеджера сессий
        
        Args:
            config: Конфигурация модуля
        """
        self.config = SessionManagementConfig(config)
        self.hardware_id_provider = None
        self.session_tracker = None
        self.is_initialized = False
        
        logger.info("SessionManager initialized")
    
    async def initialize(self) -> bool:
        """
        Инициализация менеджера сессий
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing SessionManager...")
            
            # Валидируем конфигурацию
            if not self.config.validate():
                logger.error("Session management configuration validation failed")
                return False
            
            # Создаем провайдеры
            await self._create_providers()
            
            # Инициализируем провайдеры
            await self._initialize_providers()
            
            self.is_initialized = True
            logger.info("SessionManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SessionManager: {e}")
            return False
    
    async def _create_providers(self):
        """Создание провайдеров сессий"""
        try:
            # Hardware ID Provider
            hardware_config = self.config.get_hardware_id_config()
            self.hardware_id_provider = HardwareIDProvider(hardware_config)
            
            # Session Tracker
            tracker_config = self.config.get_session_tracker_config()
            self.session_tracker = SessionTracker(tracker_config)
            
            logger.info("Created session management providers")
            
        except Exception as e:
            logger.error(f"Error creating providers: {e}")
            raise e
    
    async def _initialize_providers(self):
        """Инициализация всех провайдеров"""
        initialized_count = 0
        
        # Инициализируем Hardware ID Provider
        try:
            if await self.hardware_id_provider.initialize():
                initialized_count += 1
                logger.info("Hardware ID Provider initialized successfully")
            else:
                logger.warning("Hardware ID Provider initialization failed")
        except Exception as e:
            logger.error(f"Error initializing Hardware ID Provider: {e}")
        
        # Инициализируем Session Tracker
        try:
            if await self.session_tracker.initialize():
                initialized_count += 1
                logger.info("Session Tracker initialized successfully")
            else:
                logger.warning("Session Tracker initialization failed")
        except Exception as e:
            logger.error(f"Error initializing Session Tracker: {e}")
        
        if initialized_count == 0:
            raise Exception("No providers could be initialized")
        
        logger.info(f"Initialized {initialized_count}/2 providers")
    
    async def create_session(self, user_agent: Optional[str] = None, 
                           ip_address: Optional[str] = None, 
                           context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Создание новой сессии
        
        Args:
            user_agent: User Agent браузера
            ip_address: IP адрес пользователя
            context: Контекстные данные
            
        Returns:
            Данные созданной сессии
        """
        try:
            if not self.is_initialized:
                raise Exception("SessionManager not initialized")
            
            # Получаем Hardware ID
            hardware_id = await self._get_hardware_id()
            if not hardware_id:
                raise Exception("Failed to get Hardware ID")
            
            # Создаем сессию через Session Tracker
            session_data = {
                'hardware_id': hardware_id,
                'user_agent': user_agent,
                'ip_address': ip_address,
                'context': context or {}
            }
            
            session_result = None
            async for result in self.session_tracker.process(session_data):
                session_result = result
                break
            
            if not session_result:
                raise Exception("Failed to create session")
            
            logger.info(f"Session created: {session_result['session_id'][:8]}... for hardware_id: {hardware_id[:8]}...")
            return session_result
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise e
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение статуса сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            Статус сессии или None если не найдена
        """
        try:
            if not self.is_initialized:
                raise Exception("SessionManager not initialized")
            
            return await self.session_tracker.get_session_status(session_id)
            
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return None
    
    async def interrupt_session(self, session_id: str, reason: str = "user_request") -> bool:
        """
        Прерывание сессии
        
        Args:
            session_id: ID сессии для прерывания
            reason: Причина прерывания
            
        Returns:
            True если прерывание успешно, False иначе
        """
        try:
            if not self.is_initialized:
                raise Exception("SessionManager not initialized")
            
            return await self.session_tracker.interrupt_session(session_id, reason)
            
        except Exception as e:
            logger.error(f"Error interrupting session: {e}")
            return False
    
    async def interrupt_all_sessions(self, reason: str = "global_interrupt") -> int:
        """
        Прерывание всех активных сессий
        
        Args:
            reason: Причина прерывания
            
        Returns:
            Количество прерванных сессий
        """
        try:
            if not self.is_initialized:
                raise Exception("SessionManager not initialized")
            
            return await self.session_tracker.interrupt_all_sessions(reason)
            
        except Exception as e:
            logger.error(f"Error interrupting all sessions: {e}")
            return 0
    
    async def get_hardware_id(self) -> Optional[str]:
        """
        Получение Hardware ID
        
        Returns:
            Hardware ID или None если не инициализирован
        """
        try:
            if not self.is_initialized:
                raise Exception("SessionManager not initialized")
            
            return await self._get_hardware_id()
            
        except Exception as e:
            logger.error(f"Error getting hardware ID: {e}")
            return None
    
    async def _get_hardware_id(self) -> Optional[str]:
        """Получение Hardware ID из провайдера"""
        try:
            hardware_id_result = None
            async for result in self.hardware_id_provider.process(None):
                hardware_id_result = result
                break
            
            return hardware_id_result
            
        except Exception as e:
            logger.error(f"Error getting hardware ID from provider: {e}")
            return None
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов менеджера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up SessionManager...")
            
            # Очищаем провайдеры
            if self.session_tracker:
                await self.session_tracker.cleanup()
            
            if self.hardware_id_provider:
                await self.hardware_id_provider.cleanup()
            
            self.is_initialized = False
            logger.info("SessionManager cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up SessionManager: {e}")
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
            "hardware_id_provider": None,
            "session_tracker": None
        }
        
        # Добавляем статус каждого провайдера
        if self.hardware_id_provider:
            status["hardware_id_provider"] = self.hardware_id_provider.get_status()
        
        if self.session_tracker:
            status["session_tracker"] = self.session_tracker.get_status()
        
        return status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик менеджера
        
        Returns:
            Словарь с метриками менеджера
        """
        metrics = {
            "is_initialized": self.is_initialized,
            "hardware_id_provider": None,
            "session_tracker": None
        }
        
        # Добавляем метрики каждого провайдера
        if self.hardware_id_provider:
            metrics["hardware_id_provider"] = self.hardware_id_provider.get_metrics()
        
        if self.session_tracker:
            metrics["session_tracker"] = self.session_tracker.get_metrics()
        
        return metrics
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики сессий
        
        Returns:
            Словарь со статистикой сессий
        """
        if self.session_tracker:
            return self.session_tracker.get_session_statistics()
        else:
            return {
                'active_sessions': 0,
                'expired_sessions': 0,
                'interrupted_sessions': 0,
                'total_sessions': 0,
                'session_history_count': 0,
                'global_interrupt_flag': False
            }
    
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
    
    def get_tracking_settings(self) -> Dict[str, Any]:
        """
        Получение настроек отслеживания
        
        Returns:
            Словарь с настройками отслеживания
        """
        return self.config.get_tracking_settings()
    
    def reset_metrics(self):
        """Сброс метрик менеджера"""
        if self.hardware_id_provider:
            self.hardware_id_provider.reset_metrics()
        
        if self.session_tracker:
            self.session_tracker.reset_metrics()
        
        logger.info("SessionManager metrics reset")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Получение краткой сводки по менеджеру
        
        Returns:
            Словарь со сводкой
        """
        summary = {
            "is_initialized": self.is_initialized,
            "hardware_id_available": self.hardware_id_provider.is_available if self.hardware_id_provider else False,
            "session_tracker_available": self.session_tracker.is_available if self.session_tracker else False,
            "config_valid": self.config.validate(),
            "session_statistics": self.get_session_statistics(),
            "security_settings": self.get_security_settings()
        }
        
        return summary
    
    def __str__(self) -> str:
        """Строковое представление менеджера"""
        return f"SessionManager(initialized={self.is_initialized}, providers=2)"
    
    def __repr__(self) -> str:
        """Представление менеджера для отладки"""
        return (
            f"SessionManager("
            f"initialized={self.is_initialized}, "
            f"hardware_id_available={self.hardware_id_provider.is_available if self.hardware_id_provider else False}, "
            f"session_tracker_available={self.session_tracker.is_available if self.session_tracker else False}"
            f")"
        )
