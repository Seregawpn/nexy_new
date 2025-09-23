"""
Обработчик разрешений Screen Capture для macOS
Использует правильные API вместо прямых TCC вызовов
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ScreenCapturePermissionManager:
    """Обработчик разрешений Screen Capture для macOS"""
    
    def __init__(self):
        self.bundle_id = "com.nexy.assistant"
        self._available = False
        
        try:
            from Quartz import CGPreflightScreenCaptureAccess, CGRequestScreenCaptureAccess
            self._preflight = CGPreflightScreenCaptureAccess
            self._request = CGRequestScreenCaptureAccess
            self._available = True
        except ImportError as e:
            logger.warning(f"Quartz framework недоступен: {e}")
            self._preflight = None
            self._request = None
    
    def check_permission(self) -> bool:
        """
        Проверяет разрешение Screen Capture
        
        Returns:
            bool: True если разрешение предоставлено
        """
        try:
            if not self._available or not self._preflight:
                logger.warning("⚠️ Quartz framework недоступен")
                return False
            
            # Используем правильный API для проверки
            has_permission = self._preflight()
            
            if has_permission:
                logger.info("✅ Screen Capture permission granted")
            else:
                logger.warning("⚠️ Screen Capture permission not granted")
            
            return has_permission
            
        except Exception as e:
            logger.error(f"❌ Error checking Screen Capture permission: {e}")
            return False
    
    def request_permission(self) -> bool:
        """
        Запрашивает разрешение Screen Capture
        
        Returns:
            bool: True если разрешение предоставлено
        """
        try:
            if not self._available or not self._request:
                logger.warning("⚠️ Quartz framework недоступен")
                return False
            
            # Запрашиваем разрешение (вызовет системный диалог)
            granted = self._request()
            
            if granted:
                logger.info("✅ Screen Capture permission granted after request")
            else:
                logger.warning("⚠️ Screen Capture permission denied by user")
            
            return granted
            
        except Exception as e:
            logger.error(f"❌ Error requesting Screen Capture permission: {e}")
            return False
    
    def get_instructions(self) -> str:
        """
        Получает инструкции по настройке Screen Capture
        
        Returns:
            str: Инструкции
        """
        return """
📸 РАЗРЕШЕНИЕ ЗАХВАТА ЭКРАНА

1. Откройте 'Системные настройки'
2. Перейдите в 'Конфиденциальность и безопасность'
3. Выберите 'Захват содержимого экрана'
4. Включите переключатель для Nexy AI Assistant

Или используйте команду:
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"

ВАЖНО: Это разрешение необходимо для работы скриншотов и анализа экрана.
        """
    
    @property
    def is_available(self) -> bool:
        """Проверяет доступность Screen Capture API"""
        return self._available
