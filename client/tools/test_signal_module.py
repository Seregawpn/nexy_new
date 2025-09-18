"""
Standalone test of Signals module (audio tone) without full integration.

Plays a short beep (listen_start) via the existing SequentialSpeechPlayer
using a minimal AudioSink adapter. No EventBus required.

Usage:
  source .venv/bin/activate && python client/tools/test_signal_module.py

Expected:
  You should hear a short beep (~120 ms) on the current output device.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import numpy as np

import sys
from pathlib import Path

# Ensure 'client' directory is on sys.path so 'modules.*' imports work
sys.path.append(str(Path(__file__).resolve().parents[1]))  # adds .../client

from modules.speech_playback.core.player import SequentialSpeechPlayer, PlayerConfig
from modules.speech_playback.core.state import PlaybackState
from modules.signals.core.interfaces import AudioSink, SignalRequest, SignalPattern, SignalKind
from modules.signals.core.service import SimpleSignalService, CooldownPolicy
from modules.signals.channels.audio_tone import AudioToneChannel


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("signals_test")


class DirectPlayerAudioSink(AudioSink):
    """AudioSink adapter that feeds PCM directly to SequentialSpeechPlayer.

    This is a test-only sink to validate tone generation without EventBus.
    """

    def __init__(self, player: SequentialSpeechPlayer) -> None:
        self._player = player

    async def play_pcm(
        self,
        pcm_s16le_mono: bytes,
        sample_rate: int,
        channels: int = 1,
        gain: float = 1.0,
        priority: int = 10,
        pattern: Optional[str] = None,
    ) -> None:
        # Decode PCM bytes to numpy int16
        try:
            arr = np.frombuffer(pcm_s16le_mono, dtype=np.int16)
        except Exception:
            return

        # Apply simple gain (clamped)
        try:
            g = max(0.0, min(1.0, float(gain)))
            if g != 1.0:
                a = arr.astype(np.float32) * g
                a = np.clip(a, -32768.0, 32767.0).astype(np.int16)
            else:
                a = arr
        except Exception:
            a = arr

        # Ensure player is ready and SR matches configuration
        target_sr = int(self._player.config.sample_rate)
        if sample_rate != target_sr:
            logger.warning(f"Signal sample rate mismatch: got={sample_rate}, player={target_sr} — playing anyway (may resample by device)")

        # Add audio and start/resume playback
        meta = {"kind": "signal", "pattern": pattern}
        self._player.add_audio_data(a, priority=priority, metadata=meta)
        state = self._player.state_manager.get_state()
        if state == PlaybackState.PAUSED:
            self._player.resume_playback()
        elif state != PlaybackState.PLAYING:
            if not self._player.initialize():
                raise RuntimeError("player_init_failed")
            if not self._player.start_playback():
                raise RuntimeError("start_playback_failed")


async def main():
    # Prepare player (uses centralized config by default)
    player = SequentialSpeechPlayer(PlayerConfig.from_centralized_config())
    sink = DirectPlayerAudioSink(player)

    # Build signals service with audio channel
    audio_ch = AudioToneChannel(sink, sample_rate=player.config.sample_rate, default_volume=0.2)
    svc = SimpleSignalService(
        channels=[audio_ch],
        cooldowns={SignalPattern.LISTEN_START: CooldownPolicy(300)},
        enabled=True,
    )

    # Emit a listen_start tone
    logger.info("▶️ Emitting listen_start tone…")
    await svc.emit(SignalRequest(pattern=SignalPattern.LISTEN_START, kind=SignalKind.AUDIO, volume=0.2, tone_hz=880, duration_ms=120, priority=10))

    # Give time to play
    await asyncio.sleep(0.6)

    # Cleanly stop player
    try:
        player.stop_playback()
        player.shutdown()
    except Exception:
        pass
    logger.info("✅ Done")


if __name__ == "__main__":
    asyncio.run(main())
