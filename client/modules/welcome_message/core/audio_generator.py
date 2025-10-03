"""Welcome Audio Generator — серверный источник приветствия."""

import logging
from typing import Optional, Dict, Any

import numpy as np

from config.unified_config_loader import UnifiedConfigLoader
from modules.grpc_client.core.grpc_client import GrpcClient

from .types import WelcomeConfig

logger = logging.getLogger(__name__)


class WelcomeAudioGenerator:
    """Генератор аудио для приветственного сообщения"""

    def __init__(self, config: WelcomeConfig):
        self.config = config
        self._last_server_metadata: Dict[str, Any] = {}

        self._grpc_client: Optional[GrpcClient] = None
        self._grpc_client_config: Optional[Dict[str, Any]] = None
        self._grpc_server_name: Optional[str] = None
        self._grpc_timeout: float = float(config.server_timeout_sec)

        self._load_grpc_settings()

    async def generate_audio(self, text: str) -> Optional[np.ndarray]:
        """Генерирует аудио на сервере (совместимость API)."""
        return await self.generate_server_audio(text)

    async def generate_server_audio(self, text: str) -> Optional[np.ndarray]:
        """Пытается получить приветствие только с сервера"""
        if not self.config.use_server:
            return None
        return await self._generate_with_server(text)

    async def _generate_with_server(self, text: str) -> Optional[np.ndarray]:
        """Запрашивает генерацию приветствия на сервере"""
        if not text:
            logger.error("❌ [WELCOME_AUDIO] Пустой текст приветствия")
            return None

        client = self._ensure_grpc_client()
        if not client:
            return None

        try:
            result = await client.generate_welcome_audio(
                text=text,
                voice=self.config.voice,
                language=None,
                server_name=self._grpc_server_name,
                timeout=self._grpc_timeout,
            )
            audio_array: Optional[np.ndarray] = result.get('audio')
            metadata = result.get('metadata', {})
            self._last_server_metadata = metadata

            if audio_array is None or len(audio_array) == 0:
                logger.error("❌ [WELCOME_AUDIO] Сервер вернул пустое аудио")
                return None

            sample_rate = metadata.get('sample_rate') or self.config.sample_rate
            channels = metadata.get('channels') or self.config.channels

            if sample_rate != self.config.sample_rate or channels != self.config.channels:
                logger.info(
                    "⚠️ [WELCOME_AUDIO] Несовпадение формата: server_sr=%s, config_sr=%s, server_ch=%s, config_ch=%s",
                    sample_rate,
                    self.config.sample_rate,
                    channels,
                    self.config.channels,
                )
                # Пока не выполняем ресэмплинг, сообщаем в лог.

            return audio_array
        except Exception as exc:
            logger.error(f"❌ [WELCOME_AUDIO] Ошибка серверной генерации: {exc}")
            return None

    def get_last_server_metadata(self) -> Dict[str, Any]:
        """Возвращает метаданные последней серверной генерации"""
        return self._last_server_metadata

    def _load_grpc_settings(self):
        try:
            loader = UnifiedConfigLoader()
            config_data = loader._load_config()
            integrations_cfg = (config_data.get('integrations') or {}).get('grpc_client', {})
            self._grpc_server_name = integrations_cfg.get('server')
            integration_timeout = float(integrations_cfg.get('request_timeout_sec', self._grpc_timeout))
            self._grpc_timeout = float(self.config.server_timeout_sec or integration_timeout)

            network_cfg = loader.get_network_config()
            servers_cfg: Dict[str, Dict[str, Any]] = {}
            for name, server in network_cfg.grpc_servers.items():
                servers_cfg[name] = {
                    'address': server.host,
                    'port': server.port,
                    'use_ssl': server.ssl,
                    'timeout': server.timeout,
                    'retry_attempts': server.retry_attempts,
                    'retry_delay': server.retry_delay,
                }

            self._grpc_client_config = {
                'servers': servers_cfg,
                'auto_fallback': network_cfg.auto_fallback,
                'connection_timeout': network_cfg.connection_check_interval,
                'max_retry_attempts': int(integrations_cfg.get('max_retries', 3)),
                'retry_delay': float(integrations_cfg.get('retry_delay', 1.0)),
                'welcome_timeout_sec': self._grpc_timeout,
            }
        except Exception as exc:
            logger.warning(f"⚠️ [WELCOME_AUDIO] Не удалось загрузить настройки gRPC: {exc}")
            self._grpc_client_config = None
            self._grpc_server_name = None
            self._grpc_timeout = 30.0

    def _ensure_grpc_client(self) -> Optional[GrpcClient]:
        try:
            if self._grpc_client is None:
                self._grpc_client = GrpcClient(config=self._grpc_client_config)
            return self._grpc_client
        except Exception as exc:
            logger.error(f"❌ [WELCOME_AUDIO] Ошибка создания gRPC клиента: {exc}")
            self._grpc_client = None
            return None
