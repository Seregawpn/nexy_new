"""
Основной класс для управления автозапуском приложения.
"""

import os
from typing import Optional
from .types import AutostartStatus, AutostartConfig
from ..macos.launch_agent import LaunchAgentManager

class AutostartManager:
    """Менеджер автозапуска приложения."""
    
    def __init__(self, config: AutostartConfig):
        self.config = config
        self.launch_agent_manager = LaunchAgentManager(config)
        
    async def enable_autostart(self) -> AutostartStatus:
        """Включение автозапуска."""
        try:
            if self.config.method == "launch_agent":
                success = await self.launch_agent_manager.install()
                if success:
                    print("✅ Автозапуск включен (LaunchAgent)")
                    return AutostartStatus.ENABLED
                else:
                    print("❌ Ошибка включения автозапуска")
                    return AutostartStatus.ERROR
            else:
                print("❌ Неподдерживаемый метод автозапуска")
                return AutostartStatus.ERROR
                
        except Exception as e:
            print(f"❌ Ошибка включения автозапуска: {e}")
            return AutostartStatus.ERROR
    
    async def disable_autostart(self) -> AutostartStatus:
        """Отключение автозапуска."""
        try:
            if self.config.method == "launch_agent":
                success = await self.launch_agent_manager.uninstall()
                if success:
                    print("✅ Автозапуск отключен")
                    return AutostartStatus.DISABLED
                else:
                    print("❌ Ошибка отключения автозапуска")
                    return AutostartStatus.ERROR
            else:
                print("❌ Неподдерживаемый метод автозапуска")
                return AutostartStatus.ERROR
                
        except Exception as e:
            print(f"❌ Ошибка отключения автозапуска: {e}")
            return AutostartStatus.ERROR
    
    async def get_autostart_status(self) -> AutostartStatus:
        """Получение статуса автозапуска."""
        try:
            if self.config.method == "launch_agent":
                is_installed = await self.launch_agent_manager.is_installed()
                return AutostartStatus.ENABLED if is_installed else AutostartStatus.DISABLED
            else:
                return AutostartStatus.DISABLED
                
        except Exception as e:
            print(f"❌ Ошибка получения статуса автозапуска: {e}")
            return AutostartStatus.ERROR
