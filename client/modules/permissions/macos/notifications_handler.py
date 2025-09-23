"""
Реальный обработчик уведомлений для macOS
Использует UserNotifications framework через PyObjC
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

class NotificationsHandler:
    """Обработчик уведомлений для macOS"""
    
    def __init__(self):
        try:
            from UserNotifications import (
                UNUserNotificationCenter,
                UNAuthorizationOptions,
                UNNotificationRequest,
                UNMutableNotificationContent,
                UNTimeIntervalNotificationTrigger,
                UNNotificationPresentationOptions
            )
            self._center = UNUserNotificationCenter.currentNotificationCenter()
            self._authorization_granted: Optional[bool] = None
            self._available = True
        except ImportError as e:
            logger.warning(f"UserNotifications framework недоступен: {e}")
            self._center = None
            self._authorization_granted = False
            self._available = False
    
    async def check_permission(self) -> bool:
        """
        Проверяет разрешение на уведомления
        
        Returns:
            bool: True если разрешение предоставлено
        """
        try:
            if not self._available or not self._center:
                logger.warning("⚠️ UserNotifications framework недоступен")
                return False
            
            # Используем правильный метод для получения настроек
            def get_settings():
                return self._center.getNotificationSettings()
            
            settings = get_settings()
            # UNAuthorizationStatusAuthorized = 3
            granted = settings.authorizationStatus() == 3
            
            self._authorization_granted = granted
            
            if granted:
                logger.info("✅ Notifications permission granted")
            else:
                logger.warning("⚠️ Notifications permission not granted")
            
            return granted
            
        except Exception as e:
            logger.error(f"❌ Error checking notifications permission: {e}")
            self._authorization_granted = False
            return False
    
    async def request_permission(self) -> bool:
        """
        Запрашивает разрешение на уведомления
        
        Returns:
            bool: True если разрешение предоставлено
        """
        try:
            if not self._available or not self._center:
                logger.warning("⚠️ UserNotifications framework недоступен")
                return False
            
            # Запрашиваем разрешения на уведомления и звуки
            options = UNAuthorizationOptions.Alert | UNAuthorizationOptions.Sound | UNAuthorizationOptions.Badge
            
            def request_auth():
                return self._center.requestAuthorizationWithOptions_completionHandler_(options, None)
            
            granted, error = request_auth()
            
            if error:
                logger.error(f"❌ Error requesting notifications permission: {error}")
                self._authorization_granted = False
                return False
            
            self._authorization_granted = granted
            
            if granted:
                logger.info("✅ Notifications permission granted by user")
            else:
                logger.warning("⚠️ Notifications permission denied by user")
            
            return granted
            
        except Exception as e:
            logger.error(f"❌ Error requesting notifications permission: {e}")
            self._authorization_granted = False
            return False
    
    async def send_notification(self, title: str, body: str, identifier: str = "nexy") -> bool:
        """
        Отправляет уведомление
        
        Args:
            title: Заголовок уведомления
            body: Текст уведомления
            identifier: Уникальный идентификатор
            
        Returns:
            bool: True если уведомление отправлено
        """
        try:
            if not self._available or not self._center:
                logger.warning("⚠️ UserNotifications framework недоступен")
                return False
            
            if not await self.check_permission():
                logger.warning("⚠️ Cannot send notification - permission not granted")
                return False
            
            # Создаем содержимое уведомления
            content = UNMutableNotificationContent.alloc().init()
            content.setTitle_(title)
            content.setBody_(body)
            content.setSound_("default")
            
            # Создаем триггер (немедленно)
            trigger = UNTimeIntervalNotificationTrigger.triggerWithTimeInterval_repeats_(0.1, False)
            
            # Создаем запрос
            request = UNNotificationRequest.requestWithIdentifier_trigger_content_(
                identifier, trigger, content
            )
            
            # Добавляем уведомление
            self._center.addNotificationRequest_withCompletionHandler_(request, None)
            
            logger.info(f"✅ Notification sent: {title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending notification: {e}")
            return False
    
    @property
    def is_granted(self) -> bool:
        """Возвращает текущий статус разрешения"""
        if self._authorization_granted is None:
            return False
        return self._authorization_granted
    
    @property
    def is_available(self) -> bool:
        """Проверяет доступность UserNotifications framework"""
        return self._available
