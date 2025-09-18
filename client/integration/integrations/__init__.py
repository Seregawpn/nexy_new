"""
Integrations Module
Интеграции модулей с системой событий
Четкое разделение ответственности без дублирования
"""

from .input_processing_integration import InputProcessingIntegration
from .voice_recognition_integration import VoiceRecognitionIntegration
from .tray_controller_integration import TrayControllerIntegration
from .hardware_id_integration import HardwareIdIntegration, HardwareIdIntegrationConfig
from .grpc_client_integration import GrpcClientIntegration, GrpcClientIntegrationConfig
from .speech_playback_integration import SpeechPlaybackIntegration
# from .permissions_integration import PermissionsIntegration  # Временно отключено
# from .network_manager_integration import NetworkManagerIntegration  # Временно отключено

__all__ = [
    'InputProcessingIntegration',
    'VoiceRecognitionIntegration',
    'TrayControllerIntegration',
    'HardwareIdIntegration',
    'HardwareIdIntegrationConfig',
    'GrpcClientIntegration',
    'GrpcClientIntegrationConfig',
    'SpeechPlaybackIntegration',
    # 'PermissionsIntegration',  # Временно отключено
    # 'NetworkManagerIntegration'  # Временно отключено
]

__version__ = "1.0.0"
__author__ = "Nexy Team"
