"""
macOS специфичные bridge-модули для захвата экрана
"""

# Экспорт основных классов
from .simple_bridge import SimpleCoreGraphicsBridge
from .test_bridge import TestCoreGraphicsBridge

__all__ = [
    'SimpleCoreGraphicsBridge',
    'TestCoreGraphicsBridge',
]
