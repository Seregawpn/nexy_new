"""
Конфигурация модуля Session Management
"""

import os
from typing import Dict, Any, Optional

class SessionManagementConfig:
    """Конфигурация модуля управления сессиями"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация конфигурации
        
        Args:
            config: Словарь с конфигурацией (опционально)
        """
        self.config = config or {}
        
        # Настройки Hardware ID
        self.hardware_id_cache_file = self.config.get('hardware_id_cache_file', 'hardware_id.cache')
        self.hardware_id_length = self.config.get('hardware_id_length', 32)
        self.hardware_id_charset = self.config.get('hardware_id_charset', 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        
        # Настройки сессий
        self.session_timeout = self.config.get('session_timeout', 3600)  # 1 час
        self.session_cleanup_interval = self.config.get('session_cleanup_interval', 300)  # 5 минут
        self.max_concurrent_sessions = self.config.get('max_concurrent_sessions', 100)
        self.session_heartbeat_interval = self.config.get('session_heartbeat_interval', 30)  # 30 секунд
        
        # Настройки прерываний
        self.interrupt_timeout = self.config.get('interrupt_timeout', 5)  # 5 секунд
        self.interrupt_cleanup_delay = self.config.get('interrupt_cleanup_delay', 10)  # 10 секунд
        self.global_interrupt_enabled = self.config.get('global_interrupt_enabled', True)
        
        # Настройки отслеживания
        self.tracking_enabled = self.config.get('tracking_enabled', True)
        self.track_user_agents = self.config.get('track_user_agents', True)
        self.track_ip_addresses = self.config.get('track_ip_addresses', False)
        self.track_timestamps = self.config.get('track_timestamps', True)
        
        # Настройки производительности
        self.max_session_history = self.config.get('max_session_history', 1000)
        self.session_data_retention = self.config.get('session_data_retention', 86400)  # 24 часа
        self.cleanup_batch_size = self.config.get('cleanup_batch_size', 50)
        
        # Настройки безопасности
        self.require_hardware_id = self.config.get('require_hardware_id', True)
        self.validate_session_ownership = self.config.get('validate_session_ownership', True)
        self.encrypt_session_data = self.config.get('encrypt_session_data', False)
        
        # Настройки логирования
        self.log_level = self.config.get('log_level', 'INFO')
        self.log_sessions = self.config.get('log_sessions', True)
        self.log_interrupts = self.config.get('log_interrupts', True)
        self.log_hardware_ids = self.config.get('log_hardware_ids', False)  # Безопасность
        
    def get_hardware_id_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации Hardware ID Provider
        
        Returns:
            Словарь с конфигурацией Hardware ID
        """
        return {
            'cache_file': self.hardware_id_cache_file,
            'length': self.hardware_id_length,
            'charset': self.hardware_id_charset,
            'require_hardware_id': self.require_hardware_id
        }
    
    def get_session_tracker_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации Session Tracker
        
        Returns:
            Словарь с конфигурацией Session Tracker
        """
        return {
            'session_timeout': self.session_timeout,
            'session_cleanup_interval': self.session_cleanup_interval,
            'max_concurrent_sessions': self.max_concurrent_sessions,
            'session_heartbeat_interval': self.session_heartbeat_interval,
            'tracking_enabled': self.tracking_enabled,
            'track_user_agents': self.track_user_agents,
            'track_ip_addresses': self.track_ip_addresses,
            'track_timestamps': self.track_timestamps,
            'max_session_history': self.max_session_history,
            'session_data_retention': self.session_data_retention,
            'cleanup_batch_size': self.cleanup_batch_size,
            'validate_session_ownership': self.validate_session_ownership,
            'encrypt_session_data': self.encrypt_session_data
        }
    
    def get_interrupt_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации прерываний
        
        Returns:
            Словарь с конфигурацией прерываний
        """
        return {
            'interrupt_timeout': self.interrupt_timeout,
            'interrupt_cleanup_delay': self.interrupt_cleanup_delay,
            'global_interrupt_enabled': self.global_interrupt_enabled
        }
    
    def validate(self) -> bool:
        """
        Валидация конфигурации
        
        Returns:
            True если конфигурация валидна, False иначе
        """
        # Проверяем корректность параметров Hardware ID
        if self.hardware_id_length < 8 or self.hardware_id_length > 64:
            print("❌ hardware_id_length должен быть между 8 и 64")
            return False
            
        if len(self.hardware_id_charset) < 10:
            print("❌ hardware_id_charset должен содержать минимум 10 символов")
            return False
            
        # Проверяем корректность параметров сессий
        if self.session_timeout <= 0:
            print("❌ session_timeout должен быть положительным")
            return False
            
        if self.max_concurrent_sessions <= 0:
            print("❌ max_concurrent_sessions должен быть положительным")
            return False
            
        if self.session_heartbeat_interval <= 0:
            print("❌ session_heartbeat_interval должен быть положительным")
            return False
            
        # Проверяем корректность параметров прерываний
        if self.interrupt_timeout <= 0:
            print("❌ interrupt_timeout должен быть положительным")
            return False
            
        if self.interrupt_cleanup_delay <= 0:
            print("❌ interrupt_cleanup_delay должен быть положительным")
            return False
            
        # Проверяем корректность параметров производительности
        if self.max_session_history <= 0:
            print("❌ max_session_history должен быть положительным")
            return False
            
        if self.session_data_retention <= 0:
            print("❌ session_data_retention должен быть положительным")
            return False
            
        if self.cleanup_batch_size <= 0:
            print("❌ cleanup_batch_size должен быть положительным")
            return False
            
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса конфигурации
        
        Returns:
            Словарь со статусом конфигурации
        """
        return {
            'hardware_id_cache_file': self.hardware_id_cache_file,
            'hardware_id_length': self.hardware_id_length,
            'session_timeout': self.session_timeout,
            'session_cleanup_interval': self.session_cleanup_interval,
            'max_concurrent_sessions': self.max_concurrent_sessions,
            'session_heartbeat_interval': self.session_heartbeat_interval,
            'interrupt_timeout': self.interrupt_timeout,
            'interrupt_cleanup_delay': self.interrupt_cleanup_delay,
            'global_interrupt_enabled': self.global_interrupt_enabled,
            'tracking_enabled': self.tracking_enabled,
            'track_user_agents': self.track_user_agents,
            'track_ip_addresses': self.track_ip_addresses,
            'track_timestamps': self.track_timestamps,
            'max_session_history': self.max_session_history,
            'session_data_retention': self.session_data_retention,
            'cleanup_batch_size': self.cleanup_batch_size,
            'require_hardware_id': self.require_hardware_id,
            'validate_session_ownership': self.validate_session_ownership,
            'encrypt_session_data': self.encrypt_session_data,
            'log_level': self.log_level,
            'log_sessions': self.log_sessions,
            'log_interrupts': self.log_interrupts,
            'log_hardware_ids': self.log_hardware_ids
        }
    
    def get_security_settings(self) -> Dict[str, Any]:
        """
        Получение настроек безопасности
        
        Returns:
            Словарь с настройками безопасности
        """
        return {
            'require_hardware_id': self.require_hardware_id,
            'validate_session_ownership': self.validate_session_ownership,
            'encrypt_session_data': self.encrypt_session_data,
            'track_ip_addresses': self.track_ip_addresses,
            'log_hardware_ids': self.log_hardware_ids
        }
    
    def get_performance_settings(self) -> Dict[str, Any]:
        """
        Получение настроек производительности
        
        Returns:
            Словарь с настройками производительности
        """
        return {
            'max_concurrent_sessions': self.max_concurrent_sessions,
            'session_timeout': self.session_timeout,
            'session_cleanup_interval': self.session_cleanup_interval,
            'session_heartbeat_interval': self.session_heartbeat_interval,
            'max_session_history': self.max_session_history,
            'session_data_retention': self.session_data_retention,
            'cleanup_batch_size': self.cleanup_batch_size
        }
    
    def get_tracking_settings(self) -> Dict[str, Any]:
        """
        Получение настроек отслеживания
        
        Returns:
            Словарь с настройками отслеживания
        """
        return {
            'tracking_enabled': self.tracking_enabled,
            'track_user_agents': self.track_user_agents,
            'track_ip_addresses': self.track_ip_addresses,
            'track_timestamps': self.track_timestamps,
            'log_sessions': self.log_sessions,
            'log_interrupts': self.log_interrupts
        }
