"""
Обработчик разрешений Accessibility и Input Monitoring для macOS
Проверяет доступность и открывает системные настройки
"""

import logging
import subprocess
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AccessibilityHandler:
    """Обработчик разрешений Accessibility для macOS"""
    
    def __init__(self):
        self.bundle_id = "com.nexy.assistant"
    
    def check_accessibility_permission(self) -> bool:
        """
        Проверяет разрешение Accessibility
        
        Returns:
            bool: True если разрешение предоставлено
        """
        try:
            # Проверяем через tccutil
            result = subprocess.run([
                'tccutil', 'check', 'Accessibility', self.bundle_id
            ], capture_output=True, text=True, timeout=5)
            
            granted = result.returncode == 0
            
            if granted:
                logger.info("✅ Accessibility permission granted")
            else:
                logger.warning("⚠️ Accessibility permission not granted")
            
            return granted
            
        except Exception as e:
            logger.error(f"❌ Error checking accessibility permission: {e}")
            return False
    
    def check_input_monitoring_permission(self) -> bool:
        """
        Проверяет разрешение Input Monitoring
        
        Returns:
            bool: True если разрешение предоставлено
        """
        try:
            # Проверяем через tccutil
            result = subprocess.run([
                'tccutil', 'check', 'ListenEvent', self.bundle_id
            ], capture_output=True, text=True, timeout=5)
            
            granted = result.returncode == 0
            
            if granted:
                logger.info("✅ Input Monitoring permission granted")
            else:
                logger.warning("⚠️ Input Monitoring permission not granted")
            
            return granted
            
        except Exception as e:
            logger.error(f"❌ Error checking input monitoring permission: {e}")
            return False
    
    def open_accessibility_settings(self) -> bool:
        """
        Открывает настройки Accessibility
        
        Returns:
            bool: True если настройки открыты
        """
        try:
            subprocess.run([
                'open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'
            ], check=True)
            logger.info("✅ Opened Accessibility settings")
            return True
        except Exception as e:
            logger.error(f"❌ Error opening Accessibility settings: {e}")
            return False
    
    def open_input_monitoring_settings(self) -> bool:
        """
        Открывает настройки Input Monitoring
        
        Returns:
            bool: True если настройки открыты
        """
        try:
            subprocess.run([
                'open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent'
            ], check=True)
            logger.info("✅ Opened Input Monitoring settings")
            return True
        except Exception as e:
            logger.error(f"❌ Error opening Input Monitoring settings: {e}")
            return False
    
    def get_permission_status(self) -> Dict[str, Any]:
        """
        Получает статус всех разрешений
        
        Returns:
            dict: Статус разрешений
        """
        return {
            'accessibility': self.check_accessibility_permission(),
            'input_monitoring': self.check_input_monitoring_permission(),
            'bundle_id': self.bundle_id
        }
    
    def get_instructions(self) -> str:
        """
        Получает инструкции по настройке разрешений
        
        Returns:
            str: Инструкции
        """
        return """
🔧 РАЗРЕШЕНИЯ ДОСТУПНОСТИ И ВВОДА

1. Accessibility (для мониторинга клавиатуры):
   - Откройте 'Системные настройки'
   - Перейдите в 'Конфиденциальность и безопасность'
   - Выберите 'Универсальный доступ'
   - Включите переключатель для Nexy AI Assistant

2. Input Monitoring (для мониторинга ввода):
   - Откройте 'Системные настройки'
   - Перейдите в 'Конфиденциальность и безопасность'
   - Выберите 'Мониторинг ввода'
   - Включите переключатель для Nexy AI Assistant

Или используйте команды:
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"
        """
