"""
Integrations Module
Интеграции модулей с системой событий
Четкое разделение ответственности без дублирования
"""

from .input_processing_integration import InputProcessingIntegration
from .tray_controller_integration import TrayControllerIntegration
# from .permissions_integration import PermissionsIntegration  # Временно отключено
# from .network_manager_integration import NetworkManagerIntegration  # Временно отключено

__all__ = [
    'InputProcessingIntegration',
    'TrayControllerIntegration',
    # 'PermissionsIntegration',  # Временно отключено
    # 'NetworkManagerIntegration'  # Временно отключено
]

__version__ = "1.0.0"
__author__ = "Nexy Team"