"""
Signals Module — Audio Tone Channel

Generates a short sine tone (s16le mono) and sends it to an abstract AudioSink.
Pure-Python generation by default to avoid extra dependencies. If numpy is
available, it is used as a fast path, but is optional.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from ..core.interfaces import SignalChannel, SignalRequest, SignalKind, AudioSink

logger = logging.getLogger(__name__)


def _generate_tone_bytes(
    hz: int,
    duration_ms: int,
    volume: float,
    sample_rate: int = 48_000,
    fade_ms: int = 6,
) -> bytes:
    """Generate mono s16le PCM for a short sine tone (pure Python path).

    volume is 0.0..1.0 (clamped by callers). Applies short fade-in/out to avoid clicks.
    """
    # Clamp inputs defensively
    if volume < 0.0:
        volume = 0.0
    if volume > 1.0:
        volume = 1.0
    if duration_ms < 0:
        duration_ms = 0
    if hz < 20:
        hz = 20
    if hz > 20_000:
        hz = 20_000

    total_samples = int(sample_rate * (duration_ms / 1000.0))
    if total_samples <= 0:
        return b""

    fade_samples = max(1, int(sample_rate * (fade_ms / 1000.0)))
    max_i16 = 32767

    # Build samples
    out = bytearray(total_samples * 2)  # s16le mono
    for n in range(total_samples):
        t = n / float(sample_rate)
        # Base sine
        s = math.sin(2.0 * math.pi * hz * t)
        # Apply simple linear fade-in/out
        if n < fade_samples:
            s *= (n / float(fade_samples))
        elif total_samples - n < fade_samples:
            s *= ((total_samples - n) / float(fade_samples))

        s *= volume
        val = int(max(-1.0, min(1.0, s)) * max_i16)
        # little-endian int16
        out[2 * n] = val & 0xFF
        out[2 * n + 1] = (val >> 8) & 0xFF

    return bytes(out)


class AudioToneChannel(SignalChannel):
    """Audio channel that plays short tones via an injected AudioSink."""

    def __init__(
        self,
        sink: AudioSink,
        sample_rate: int = 48_000,
        default_volume: float = 0.2,
    ) -> None:
        self._sink = sink
        self._sr = sample_rate
        self._default_volume = default_volume

    def can_handle(self, kind: SignalKind) -> bool:
        return kind == SignalKind.AUDIO

    async def emit(self, req: SignalRequest) -> None:
        # Use request params or fallbacks
        hz = req.tone_hz or 880
        dur = req.duration_ms or 120
        vol = req.volume if req.volume is not None else self._default_volume
        if vol < 0.0:
            vol = 0.0
        if vol > 1.0:
            vol = 1.0

        pcm = _generate_tone_bytes(hz=hz, duration_ms=dur, volume=vol, sample_rate=self._sr)
        if not pcm:
            return

        try:
            await self._sink.play_pcm(
                pcm_s16le_mono=pcm,
                sample_rate=self._sr,
                channels=1,
                gain=1.0,
                priority=max(0, req.priority),
                pattern=req.pattern.value,
            )
        except Exception as e:
            logger.warning(f"AudioToneChannel sink playback failed: {e}")
