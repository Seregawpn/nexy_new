"""
Session Tracker для отслеживания и управления активными сессиями
"""

import asyncio
import logging
import time
import uuid
from typing import AsyncGenerator, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from integrations.core.universal_provider_interface import UniversalProviderInterface

logger = logging.getLogger(__name__)

@dataclass
class SessionData:
    """Данные сессии"""
    session_id: str
    hardware_id: str
    created_at: float
    last_activity: float
    status: str = "active"  # active, interrupted, completed, expired
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    interrupt_flag: bool = False
    interrupt_reason: Optional[str] = None

class SessionTracker(UniversalProviderInterface):
    """
    Провайдер для отслеживания и управления активными сессиями
    
    Отслеживает активные сессии пользователей, управляет их жизненным циклом
    и обеспечивает прерывание операций.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация Session Tracker провайдера
        
        Args:
            config: Конфигурация провайдера
        """
        super().__init__(
            name="session_tracker",
            priority=1,  # Основной провайдер
            config=config
        )
        
        # Настройки сессий
        self.session_timeout = config.get('session_timeout', 3600)
        self.session_cleanup_interval = config.get('session_cleanup_interval', 300)
        self.max_concurrent_sessions = config.get('max_concurrent_sessions', 100)
        self.session_heartbeat_interval = config.get('session_heartbeat_interval', 30)
        
        # Настройки отслеживания
        self.tracking_enabled = config.get('tracking_enabled', True)
        self.track_user_agents = config.get('track_user_agents', True)
        self.track_ip_addresses = config.get('track_ip_addresses', False)
        self.track_timestamps = config.get('track_timestamps', True)
        
        # Настройки производительности
        self.max_session_history = config.get('max_session_history', 1000)
        self.session_data_retention = config.get('session_data_retention', 86400)
        self.cleanup_batch_size = config.get('cleanup_batch_size', 50)
        
        # Настройки безопасности
        self.validate_session_ownership = config.get('validate_session_ownership', True)
        self.encrypt_session_data = config.get('encrypt_session_data', False)
        
        # Активные сессии
        self.active_sessions: Dict[str, SessionData] = {}
        self.session_history: list = []
        
        # Флаги прерывания
        self.global_interrupt_flag = False
        self.interrupted_sessions: Set[str] = set()
        
        # Фоновые задачи
        self.cleanup_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        logger.info(f"Session Tracker initialized with max_sessions: {self.max_concurrent_sessions}")
    
    async def initialize(self) -> bool:
        """
        Инициализация Session Tracker провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing Session Tracker...")
            
            # Запускаем фоновые задачи
            await self._start_background_tasks()
            
            self.is_initialized = True
            logger.info("Session Tracker initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Session Tracker: {e}")
            return False
    
    async def process(self, input_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Обработка запроса сессии
        
        Args:
            input_data: Данные запроса (hardware_id, user_agent, ip_address и т.д.)
            
        Yields:
            Данные сессии
        """
        try:
            if not self.is_initialized:
                raise Exception("Session Tracker not initialized")
            
            # Извлекаем данные запроса
            hardware_id = input_data.get('hardware_id')
            user_agent = input_data.get('user_agent') if self.track_user_agents else None
            ip_address = input_data.get('ip_address') if self.track_ip_addresses else None
            context = input_data.get('context', {})
            
            if not hardware_id:
                raise Exception("Hardware ID is required")
            
            # Создаем или обновляем сессию
            session_data = await self._create_or_update_session(
                hardware_id=hardware_id,
                user_agent=user_agent,
                ip_address=ip_address,
                context=context
            )
            
            # Обновляем метрики
            self.total_requests += 1
            self.report_success()
            
            # Возвращаем данные сессии
            yield {
                'session_id': session_data.session_id,
                'hardware_id': session_data.hardware_id,
                'status': session_data.status,
                'created_at': session_data.created_at,
                'last_activity': session_data.last_activity,
                'context': session_data.context,
                'interrupt_flag': session_data.interrupt_flag
            }
            
            logger.debug(f"Session processed: {session_data.session_id[:8]}...")
            
        except Exception as e:
            logger.error(f"Session Tracker processing error: {e}")
            self.report_error(str(e))
            raise e
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов Session Tracker провайдера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up Session Tracker...")
            
            # Останавливаем фоновые задачи
            await self._stop_background_tasks()
            
            # Очищаем сессии
            self.active_sessions.clear()
            self.session_history.clear()
            self.interrupted_sessions.clear()
            
            self.is_initialized = False
            logger.info("Session Tracker cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up Session Tracker: {e}")
            return False
    
    async def _create_or_update_session(self, hardware_id: str, user_agent: Optional[str] = None, 
                                      ip_address: Optional[str] = None, context: Dict[str, Any] = None) -> SessionData:
        """
        Создание или обновление сессии
        
        Args:
            hardware_id: Hardware ID пользователя
            user_agent: User Agent браузера
            ip_address: IP адрес пользователя
            context: Контекстные данные
            
        Returns:
            Данные сессии
        """
        current_time = time.time()
        
        # Ищем существующую активную сессию для данного hardware_id
        existing_session = None
        for session in self.active_sessions.values():
            if (session.hardware_id == hardware_id and 
                session.status == "active" and 
                current_time - session.last_activity < self.session_timeout):
                existing_session = session
                break
        
        if existing_session:
            # Обновляем существующую сессию
            existing_session.last_activity = current_time
            existing_session.context.update(context or {})
            logger.debug(f"Updated existing session: {existing_session.session_id[:8]}...")
            return existing_session
        else:
            # Создаем новую сессию
            if len(self.active_sessions) >= self.max_concurrent_sessions:
                # Очищаем старые сессии
                await self._cleanup_expired_sessions()
                
                if len(self.active_sessions) >= self.max_concurrent_sessions:
                    raise Exception("Maximum concurrent sessions reached")
            
            session_id = str(uuid.uuid4())
            session_data = SessionData(
                session_id=session_id,
                hardware_id=hardware_id,
                created_at=current_time,
                last_activity=current_time,
                user_agent=user_agent,
                ip_address=ip_address,
                context=context or {}
            )
            
            self.active_sessions[session_id] = session_data
            logger.info(f"Created new session: {session_id[:8]}... for hardware_id: {hardware_id[:8]}...")
            
            return session_data
    
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
            if session_id not in self.active_sessions:
                logger.warning(f"Session not found for interrupt: {session_id}")
                return False
            
            session = self.active_sessions[session_id]
            session.interrupt_flag = True
            session.interrupt_reason = reason
            session.status = "interrupted"
            
            self.interrupted_sessions.add(session_id)
            
            logger.info(f"Session interrupted: {session_id[:8]}... reason: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error interrupting session {session_id}: {e}")
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
            self.global_interrupt_flag = True
            interrupted_count = 0
            
            for session_id, session in self.active_sessions.items():
                if session.status == "active":
                    session.interrupt_flag = True
                    session.interrupt_reason = reason
                    session.status = "interrupted"
                    self.interrupted_sessions.add(session_id)
                    interrupted_count += 1
            
            logger.info(f"Interrupted {interrupted_count} sessions, reason: {reason}")
            return interrupted_count
            
        except Exception as e:
            logger.error(f"Error interrupting all sessions: {e}")
            return 0
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение статуса сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            Статус сессии или None если не найдена
        """
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        return {
            'session_id': session.session_id,
            'hardware_id': session.hardware_id,
            'status': session.status,
            'created_at': session.created_at,
            'last_activity': session.last_activity,
            'interrupt_flag': session.interrupt_flag,
            'interrupt_reason': session.interrupt_reason,
            'context': session.context
        }
    
    async def _start_background_tasks(self):
        """Запуск фоновых задач"""
        try:
            # Запускаем задачу очистки
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            # Запускаем задачу heartbeat
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            logger.info("Background tasks started")
            
        except Exception as e:
            logger.error(f"Error starting background tasks: {e}")
            raise e
    
    async def _stop_background_tasks(self):
        """Остановка фоновых задач"""
        try:
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("Background tasks stopped")
            
        except Exception as e:
            logger.error(f"Error stopping background tasks: {e}")
    
    async def _cleanup_loop(self):
        """Цикл очистки устаревших сессий"""
        while True:
            try:
                await asyncio.sleep(self.session_cleanup_interval)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _heartbeat_loop(self):
        """Цикл heartbeat для мониторинга сессий"""
        while True:
            try:
                await asyncio.sleep(self.session_heartbeat_interval)
                await self._update_session_heartbeats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Очистка устаревших сессий"""
        try:
            current_time = time.time()
            expired_sessions = []
            
            for session_id, session in self.active_sessions.items():
                if current_time - session.last_activity > self.session_timeout:
                    session.status = "expired"
                    expired_sessions.append(session_id)
            
            # Удаляем устаревшие сессии
            for session_id in expired_sessions:
                session = self.active_sessions.pop(session_id, None)
                if session:
                    self.session_history.append(session)
                    logger.debug(f"Session expired and archived: {session_id[:8]}...")
            
            # Ограничиваем историю сессий
            if len(self.session_history) > self.max_session_history:
                self.session_history = self.session_history[-self.max_session_history:]
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
    
    async def _update_session_heartbeats(self):
        """Обновление heartbeat для активных сессий"""
        try:
            current_time = time.time()
            active_count = 0
            
            for session in self.active_sessions.values():
                if session.status == "active":
                    active_count += 1
                    # Обновляем last_activity если сессия недавно использовалась
                    if current_time - session.last_activity < self.session_heartbeat_interval * 2:
                        session.last_activity = current_time
            
            if active_count > 0:
                logger.debug(f"Heartbeat updated for {active_count} active sessions")
                
        except Exception as e:
            logger.error(f"Error updating session heartbeats: {e}")
    
    async def _custom_health_check(self) -> bool:
        """
        Кастомная проверка здоровья Session Tracker провайдера
        
        Returns:
            True если провайдер здоров, False иначе
        """
        try:
            # Проверяем, что фоновые задачи запущены
            if not self.cleanup_task or self.cleanup_task.done():
                return False
            
            if not self.heartbeat_task or self.heartbeat_task.done():
                return False
            
            # Проверяем, что не превышено максимальное количество сессий
            if len(self.active_sessions) > self.max_concurrent_sessions:
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Session Tracker health check failed: {e}")
            return False
    
    def get_active_sessions_count(self) -> int:
        """Получение количества активных сессий"""
        return len([s for s in self.active_sessions.values() if s.status == "active"])
    
    def get_interrupted_sessions_count(self) -> int:
        """Получение количества прерванных сессий"""
        return len(self.interrupted_sessions)
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Получение статистики сессий"""
        current_time = time.time()
        active_count = 0
        expired_count = 0
        interrupted_count = 0
        
        for session in self.active_sessions.values():
            if session.status == "active":
                active_count += 1
            elif session.status == "expired":
                expired_count += 1
            elif session.status == "interrupted":
                interrupted_count += 1
        
        return {
            'active_sessions': active_count,
            'expired_sessions': expired_count,
            'interrupted_sessions': interrupted_count,
            'total_sessions': len(self.active_sessions),
            'session_history_count': len(self.session_history),
            'global_interrupt_flag': self.global_interrupt_flag,
            'max_concurrent_sessions': self.max_concurrent_sessions,
            'session_timeout': self.session_timeout
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение расширенного статуса Session Tracker провайдера
        
        Returns:
            Словарь со статусом провайдера
        """
        base_status = super().get_status()
        
        # Добавляем специфичную информацию
        base_status.update({
            "provider_type": "session_tracker",
            "session_timeout": self.session_timeout,
            "max_concurrent_sessions": self.max_concurrent_sessions,
            "tracking_enabled": self.tracking_enabled,
            "global_interrupt_flag": self.global_interrupt_flag,
            "statistics": self.get_session_statistics()
        })
        
        return base_status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение расширенных метрик Session Tracker провайдера
        
        Returns:
            Словарь с метриками провайдера
        """
        base_metrics = super().get_metrics()
        
        # Добавляем специфичные метрики
        base_metrics.update({
            "provider_type": "session_tracker",
            "active_sessions": self.get_active_sessions_count(),
            "interrupted_sessions": self.get_interrupted_sessions_count(),
            "session_statistics": self.get_session_statistics()
        })
        
        return base_metrics
