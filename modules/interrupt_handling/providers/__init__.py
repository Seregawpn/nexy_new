"""
Провайдеры для Interrupt Handling Module
"""

from .global_flag_provider import GlobalFlagProvider
from .session_tracker_provider import SessionTrackerProvider

__all__ = ['GlobalFlagProvider', 'SessionTrackerProvider']
