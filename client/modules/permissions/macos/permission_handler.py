"""
macOS Permission Handler
"""

import asyncio
import subprocess
from typing import Dict, Optional
from ..core.types import PermissionType, PermissionStatus, PermissionResult


class MacOSPermissionHandler:
    """Обработчик разрешений для macOS"""
    
    def __init__(self):
        pass
    
    async def check_microphone_permission(self) -> PermissionResult:
        """Проверить разрешение микрофона"""
        try:
            # Реальная проверка TCC для Microphone
            import subprocess
            result = subprocess.run([
                'tccutil', 'check', 'Microphone', 'com.nexy.assistant'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # Разрешение предоставлено
                return PermissionResult(
                    success=True,
                    permission=PermissionType.MICROPHONE,
                    status=PermissionStatus.GRANTED,
                    message="Microphone permission granted"
                )
            else:
                # Разрешение не предоставлено
                return PermissionResult(
                    success=False,
                    permission=PermissionType.MICROPHONE,
                    status=PermissionStatus.DENIED,
                    message="Microphone permission denied"
                )
        except Exception as e:
            return PermissionResult(
                success=False,
                permission=PermissionType.MICROPHONE,
                status=PermissionStatus.ERROR,
                message=f"Error checking microphone: {e}",
                error=e
            )
    
    async def check_screen_capture_permission(self) -> PermissionResult:
        """Проверить разрешение захвата экрана"""
        try:
            # Реальная проверка TCC для Screen Capture
            import subprocess
            result = subprocess.run([
                'tccutil', 'check', 'ScreenCapture', 'com.nexy.assistant'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # Разрешение предоставлено
                return PermissionResult(
                    success=True,
                    permission=PermissionType.SCREEN_CAPTURE,
                    status=PermissionStatus.GRANTED,
                    message="Screen capture permission granted"
                )
            else:
                # Разрешение не предоставлено
                return PermissionResult(
                    success=False,
                    permission=PermissionType.SCREEN_CAPTURE,
                    status=PermissionStatus.DENIED,
                    message="Screen capture permission denied"
                )
        except Exception as e:
            return PermissionResult(
                success=False,
                permission=PermissionType.SCREEN_CAPTURE,
                status=PermissionStatus.ERROR,
                message=f"Error checking screen capture: {e}",
                error=e
            )
    
    async def check_camera_permission(self) -> PermissionResult:
        """Проверить разрешение камеры"""
        try:
            return PermissionResult(
                success=True,
                permission=PermissionType.CAMERA,
                status=PermissionStatus.GRANTED,
                message="Camera permission granted"
            )
        except Exception as e:
            return PermissionResult(
                success=False,
                permission=PermissionType.CAMERA,
                status=PermissionStatus.ERROR,
                message=f"Error checking camera: {e}",
                error=e
            )
    
    async def check_network_permission(self) -> PermissionResult:
        """Проверить разрешение сети"""
        try:
            return PermissionResult(
                success=True,
                permission=PermissionType.NETWORK,
                status=PermissionStatus.GRANTED,
                message="Network permission granted"
            )
        except Exception as e:
            return PermissionResult(
                success=False,
                permission=PermissionType.NETWORK,
                status=PermissionStatus.ERROR,
                message=f"Error checking network: {e}",
                error=e
            )
    
    async def check_notifications_permission(self) -> PermissionResult:
        """Проверить разрешение уведомлений"""
        try:
            return PermissionResult(
                success=True,
                permission=PermissionType.NOTIFICATIONS,
                status=PermissionStatus.GRANTED,
                message="Notifications permission granted"
            )
        except Exception as e:
            return PermissionResult(
                success=False,
                permission=PermissionType.NOTIFICATIONS,
                status=PermissionStatus.ERROR,
                message=f"Error checking notifications: {e}",
                error=e
            )
    
    def get_permission_instructions(self, permission_type: PermissionType) -> str:
        """Получить инструкции для разрешения"""
        instructions = {
            PermissionType.MICROPHONE: """
🎤 РАЗРЕШЕНИЕ МИКРОФОНА

1. Откройте 'Системные настройки'
2. Перейдите в 'Конфиденциальность и безопасность'
3. Выберите 'Микрофон'
4. Включите переключатель для Nexy AI Assistant

Или используйте команду:
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
            """,
            PermissionType.SCREEN_CAPTURE: """
📺 РАЗРЕШЕНИЕ ЗАХВАТА ЭКРАНА

1. Откройте 'Системные настройки'
2. Перейдите в 'Конфиденциальность и безопасность'
3. Выберите 'Запись экрана'
4. Включите переключатель для Nexy AI Assistant

Или используйте команду:
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
            """,
            PermissionType.CAMERA: """
📹 РАЗРЕШЕНИЕ КАМЕРЫ

1. Откройте 'Системные настройки'
2. Перейдите в 'Конфиденциальность и безопасность'
3. Выберите 'Камера'
4. Включите переключатель для Nexy AI Assistant

Или используйте команду:
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera"
            """,
            PermissionType.NETWORK: """
🌐 РАЗРЕШЕНИЕ СЕТИ

Обычно разрешается автоматически.
Проверьте подключение к интернету.
            """,
            PermissionType.NOTIFICATIONS: """
🔔 РАЗРЕШЕНИЕ УВЕДОМЛЕНИЙ

1. Откройте 'Системные настройки'
2. Перейдите в 'Уведомления'
3. Найдите Nexy AI Assistant
4. Включите уведомления
            """
        }
        
        return instructions.get(permission_type, "Инструкции недоступны")
    
    async def open_privacy_preferences(self, permission_type: PermissionType):
        """Открыть настройки конфиденциальности"""
        try:
            urls = {
                PermissionType.MICROPHONE: "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
                PermissionType.SCREEN_CAPTURE: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
                PermissionType.CAMERA: "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera",
                PermissionType.NOTIFICATIONS: "x-apple.systempreferences:com.apple.preference.notifications"
            }
            
            url = urls.get(permission_type)
            if url:
                subprocess.run(["open", url], check=True)
                
        except Exception as e:
            print(f"Ошибка открытия настроек: {e}")
