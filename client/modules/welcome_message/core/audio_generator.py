"""Welcome Audio Generator

Основной генератор аудио для приветственного сообщения.
Пытается получить аудио с сервера через gRPC и использует локальные fallback'и.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np
from pydub import AudioSegment

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
        """Генерирует аудио для приветственного текста"""
        try:
            logger.info("🎵 [WELCOME_AUDIO] Генерация аудио для приветствия")

            audio_data = await self.generate_server_audio(text)
            if audio_data is not None:
                logger.info(f"✅ [WELCOME_AUDIO] Серверное аудио получено: {len(audio_data)} samples")
                return audio_data

            logger.warning("⚠️ [WELCOME_AUDIO] Серверная генерация не удалась, пробуем macOS say")

            audio_data = await self._generate_with_macos_say(text)
            if audio_data is not None:
                logger.info(f"✅ [WELCOME_AUDIO] macOS say fallback сработал: {len(audio_data)} samples")
                return audio_data

            logger.warning("⚠️ [WELCOME_AUDIO] macOS say недоступен, генерируем fallback tone")
            audio_data = self._generate_fallback_tone()
            if audio_data is not None:
                return audio_data

            logger.error("❌ [WELCOME_AUDIO] Все методы генерации приветствия не удались")
            return None
        except Exception as exc:
            logger.error(f"💥 [WELCOME_AUDIO] Критическая ошибка генерации: {exc}")
            return None

    async def generate_server_audio(self, text: str) -> Optional[np.ndarray]:
        """Пытается получить приветствие только с сервера"""
        if not self.config.use_server:
            return None
        return await self._generate_with_server(text)

    async def generate_local_fallback(self, text: str) -> Optional[np.ndarray]:
        """Генерирует приветствие локальными средствами без сервера"""
        audio_data = await self._generate_with_macos_say(text)
        if audio_data is not None:
            return audio_data
        return self._generate_fallback_tone()

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

    async def _generate_with_macos_say(self, text: str) -> Optional[np.ndarray]:
        """Генерация аудио через macOS say"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            try:
                cmd = ['say', '-v', 'Samantha', '-r', '180', '-o', str(temp_path), text]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0 and temp_path.exists():
                    segment = AudioSegment.from_file(str(temp_path))
                    if segment.frame_rate != self.config.sample_rate:
                        segment = segment.set_frame_rate(self.config.sample_rate)
                    if segment.channels != self.config.channels:
                        segment = segment.set_channels(self.config.channels)

                    samples = np.array(segment.get_array_of_samples(), dtype=np.int16)
                    logger.info(
                        "✅ [WELCOME_AUDIO] macOS say: %s samples, %.1fs",
                        len(samples),
                        len(samples) / self.config.sample_rate,
                    )
                    return samples

                logger.error(f"❌ [WELCOME_AUDIO] macOS say завершился с ошибкой: {result.stderr}")
                return None
            finally:
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass
        except subprocess.TimeoutExpired:
            logger.error("⏰ [WELCOME_AUDIO] macOS say превысил таймаут 10s")
            return None
        except Exception as exc:
            logger.error(f"❌ [WELCOME_AUDIO] macOS say ошибка: {exc}")
            return None

    def _generate_fallback_tone(self) -> Optional[np.ndarray]:
        """Генерирует короткий приветственный тон"""
        try:
            sr = self.config.sample_rate
            duration_sec = 1.5
            total_samples = int(sr * duration_sec)

            t = np.linspace(0, duration_sec, total_samples, endpoint=False, dtype=np.float32)
            audio = np.zeros(total_samples, dtype=np.float32)

            note1_duration = 0.6
            pause_duration = 0.3
            note2_duration = 0.6

            note1 = np.sin(2 * np.pi * 523.25 * t[: int(note1_duration * sr)])
            pause = np.zeros(int(pause_duration * sr), dtype=np.float32)
            note2 = np.sin(2 * np.pi * 659.25 * t[: int(note2_duration * sr)])

            melody = np.concatenate([note1, pause, note2])
            if len(melody) < total_samples:
                melody = np.concatenate([melody, np.zeros(total_samples - len(melody), dtype=np.float32)])

            audio[: len(melody)] = melody
            audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
            logger.info(f"✅ [WELCOME_AUDIO] Fallback tone создан: {len(audio_int16)} samples")
            return audio_int16
        except Exception as exc:
            logger.error(f"❌ [WELCOME_AUDIO] Ошибка fallback tone: {exc}")
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
