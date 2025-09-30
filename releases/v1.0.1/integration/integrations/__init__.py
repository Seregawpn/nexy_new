"""
Integrations Module
Интеграции модулей с системой событий
Четкое разделение ответственности без дублирования
"""

from .instance_manager_integration import InstanceManagerIntegration
from .autostart_manager_integration import AutostartManagerIntegration
from .input_processing_integration import InputProcessingIntegration
from .voice_recognition_integration import VoiceRecognitionIntegration
from .tray_controller_integration import TrayControllerIntegration
from .hardware_id_integration import HardwareIdIntegration, HardwareIdIntegrationConfig
from .grpc_client_integration import GrpcClientIntegration, GrpcClientIntegrationConfig
from .speech_playback_integration import SpeechPlaybackIntegration
from .permissions_integration import PermissionsIntegration
from .network_manager_integration import NetworkManagerIntegration
from .updater_integration import UpdaterIntegration
from .audio_device_integration import AudioDeviceIntegration
from .interrupt_management_integration import InterruptManagementIntegration
from .screenshot_capture_integration import ScreenshotCaptureIntegration
from .mode_management_integration import ModeManagementIntegration
from .signal_integration import SignalIntegration

__all__ = [
    'InstanceManagerIntegration',
    'AutostartManagerIntegration',
    'InputProcessingIntegration',
    'VoiceRecognitionIntegration',
    'TrayControllerIntegration',
    'HardwareIdIntegration',
    'HardwareIdIntegrationConfig',
    'GrpcClientIntegration',
    'GrpcClientIntegrationConfig',
    'SpeechPlaybackIntegration',
    'PermissionsIntegration',
    'NetworkManagerIntegration',
    'UpdaterIntegration',
    'AudioDeviceIntegration',
    'InterruptManagementIntegration',
    'ScreenshotCaptureIntegration',
    'ModeManagementIntegration',
    'SignalIntegration',
]

__version__ = "1.0.0"
__author__ = "Nexy Team"
