"""
Провайдер отслеживания активных сессий
"""

import time
import logging
import sys
import os
from typing import Dict, Any, Optional, List

# Добавляем путь к корневой директории сервера
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from integration.core.universal_provider_interface import UniversalProviderInterface, ProviderStatus

logger = logging.getLogger(__name__)

class SessionTrackerProvider(UniversalProviderInterface):
    """Провайдер для отслеживания активных сессий"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация провайдера отслеживания сессий
        
        Args:
            config: Конфигурация провайдера
        """
        super().__init__("session_tracker_provider", 1, config)
        
        # Активные сессии
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_counter = 0
        
        # Статистика
        self.total_sessions_created = 0
        self.total_sessions_cleaned = 0
        self.max_concurrent_sessions = 0
        
        logger.info("Session Tracker Provider created")
    
    async def initialize(self) -> bool:
        """
        Инициализация провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing Session Tracker Provider...")
            
            # Очищаем сессии в начальном состоянии
            self.active_sessions.clear()
            self.session_counter = 0
            
            self.is_initialized = True
            self.status = ProviderStatus.HEALTHY
            
            logger.info("Session Tracker Provider initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Session Tracker Provider: {e}")
            self.report_error(str(e))
            return False
    
    async def process(self, input_data: Any) -> Any:
        """
        Основная обработка отслеживания сессий
        
        Args:
            input_data: Данные для обработки
            
        Returns:
            Результат обработки
        """
        try:
            operation = input_data.get("operation", "get_status")
            
            if operation == "register_session":
                return await self.register_session(
                    input_data.get("session_id", ""),
                    input_data.get("hardware_id", ""),
                    input_data.get("session_data", {})
                )
            elif operation == "unregister_session":
                return await self.unregister_session(input_data.get("session_id", ""))
            elif operation == "cleanup_sessions":
                return await self.cleanup_sessions_for_hardware(input_data.get("hardware_id", ""))
            elif operation == "get_session_status":
                return self.get_session_status(input_data.get("session_id", ""))
            elif operation == "get_all_sessions":
                return self.get_all_sessions()
            elif operation == "get_status":
                return self.get_tracker_status()
            else:
                logger.warning(f"Unknown operation: {operation}")
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            logger.error(f"Error processing session tracker request: {e}")
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def register_session(self, session_id: str, hardware_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Регистрация активной сессии
        
        Args:
            session_id: ID сессии
            hardware_id: ID оборудования
            session_data: Данные сессии
            
        Returns:
            Результат регистрации
        """
        try:
            if not session_id:
                return {"success": False, "error": "Session ID is required"}
            
            if session_id in self.active_sessions:
                logger.warning(f"Session {session_id} already exists, updating...")
            
            # Создаем данные сессии
            session_info = {
                "session_id": session_id,
                "hardware_id": hardware_id,
                "start_time": time.time(),
                "last_activity": time.time(),
                "data": session_data,
                "status": "active"
            }
            
            self.active_sessions[session_id] = session_info
            self.session_counter += 1
            self.total_sessions_created += 1
            
            # Обновляем статистику максимального количества сессий
            current_sessions = len(self.active_sessions)
            if current_sessions > self.max_concurrent_sessions:
                self.max_concurrent_sessions = current_sessions
            
            self.report_success()
            
            logger.debug(f"Session {session_id} registered for hardware_id: {hardware_id}")
            
            return {
                "success": True,
                "session_id": session_id,
                "hardware_id": hardware_id,
                "timestamp": session_info["start_time"],
                "total_sessions": len(self.active_sessions)
            }
            
        except Exception as e:
            logger.error(f"Error registering session {session_id}: {e}")
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def unregister_session(self, session_id: str) -> Dict[str, Any]:
        """
        Отмена регистрации сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            Результат отмены регистрации
        """
        try:
            if session_id not in self.active_sessions:
                return {"success": False, "error": f"Session {session_id} not found"}
            
            session_info = self.active_sessions[session_id]
            del self.active_sessions[session_id]
            
            self.total_sessions_cleaned += 1
            self.report_success()
            
            logger.debug(f"Session {session_id} unregistered")
            
            return {
                "success": True,
                "session_id": session_id,
                "duration": time.time() - session_info["start_time"],
                "total_sessions": len(self.active_sessions)
            }
            
        except Exception as e:
            logger.error(f"Error unregistering session {session_id}: {e}")
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    async def cleanup_sessions_for_hardware(self, hardware_id: str) -> Dict[str, Any]:
        """
        Очистка всех сессий для указанного hardware_id
        
        Args:
            hardware_id: ID оборудования
            
        Returns:
            Результат очистки
        """
        try:
            sessions_to_remove = []
            cleaned_sessions = []
            
            for session_id, session_info in self.active_sessions.items():
                if session_info.get("hardware_id") == hardware_id:
                    sessions_to_remove.append(session_id)
                    cleaned_sessions.append({
                        "session_id": session_id,
                        "duration": time.time() - session_info["start_time"]
                    })
            
            # Удаляем сессии
            for session_id in sessions_to_remove:
                del self.active_sessions[session_id]
                self.total_sessions_cleaned += 1
            
            self.report_success()
            
            logger.info(f"Cleaned {len(cleaned_sessions)} sessions for hardware_id: {hardware_id}")
            
            return {
                "success": True,
                "hardware_id": hardware_id,
                "cleaned_sessions": cleaned_sessions,
                "sessions_count": len(cleaned_sessions),
                "remaining_sessions": len(self.active_sessions)
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions for {hardware_id}: {e}")
            self.report_error(str(e))
            return {"success": False, "error": str(e)}
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Получение статуса сессии
        
        Args:
            session_id: ID сессии
            
        Returns:
            Статус сессии
        """
        try:
            if session_id not in self.active_sessions:
                return {"found": False, "session_id": session_id}
            
            session_info = self.active_sessions[session_id]
            current_time = time.time()
            
            return {
                "found": True,
                "session_id": session_id,
                "hardware_id": session_info.get("hardware_id"),
                "start_time": session_info["start_time"],
                "duration": current_time - session_info["start_time"],
                "last_activity": session_info["last_activity"],
                "status": session_info["status"],
                "data_keys": list(session_info.get("data", {}).keys())
            }
            
        except Exception as e:
            logger.error(f"Error getting session status for {session_id}: {e}")
            self.report_error(str(e))
            return {"found": False, "error": str(e)}
    
    def get_all_sessions(self) -> Dict[str, Any]:
        """
        Получение информации о всех активных сессиях
        
        Returns:
            Информация о всех сессиях
        """
        try:
            current_time = time.time()
            sessions_info = []
            
            for session_id, session_info in self.active_sessions.items():
                sessions_info.append({
                    "session_id": session_id,
                    "hardware_id": session_info.get("hardware_id"),
                    "duration": current_time - session_info["start_time"],
                    "status": session_info["status"]
                })
            
            return {
                "total_sessions": len(self.active_sessions),
                "sessions": sessions_info,
                "timestamp": current_time
            }
            
        except Exception as e:
            logger.error(f"Error getting all sessions: {e}")
            self.report_error(str(e))
            return {"total_sessions": 0, "error": str(e)}
    
    def get_tracker_status(self) -> Dict[str, Any]:
        """
        Получение статуса трекера сессий
        
        Returns:
            Статус трекера
        """
        try:
            current_time = time.time()
            
            return {
                "active_sessions": len(self.active_sessions),
                "total_created": self.total_sessions_created,
                "total_cleaned": self.total_sessions_cleaned,
                "max_concurrent": self.max_concurrent_sessions,
                "session_counter": self.session_counter,
                "timestamp": current_time
            }
            
        except Exception as e:
            logger.error(f"Error getting tracker status: {e}")
            self.report_error(str(e))
            return {"error": str(e)}
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов провайдера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up Session Tracker Provider...")
            
            # Очищаем все активные сессии
            self.active_sessions.clear()
            
            # Сбрасываем статистику
            self.session_counter = 0
            self.total_sessions_created = 0
            self.total_sessions_cleaned = 0
            self.max_concurrent_sessions = 0
            
            self.is_initialized = False
            self.status = ProviderStatus.STOPPED
            
            logger.info("Session Tracker Provider cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up Session Tracker Provider: {e}")
            self.report_error(str(e))
            return False
