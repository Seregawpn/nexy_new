"""
Типы данных для модуля автозапуска.
"""

from enum import Enum
from dataclasses import dataclass

class AutostartStatus(Enum):
    """Статус автозапуска."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"

@dataclass
class AutostartConfig:
    """Конфигурация модуля автозапуска."""
    enabled: bool = False
    delay_seconds: int = 5
    method: str = "launch_agent"  # "launch_agent" или "login_item"
    launch_agent_path: str = "~/Library/LaunchAgents/com.nexy.assistant.plist"
    bundle_id: str = "com.nexy.assistant"
