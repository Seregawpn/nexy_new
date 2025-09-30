"""
EventBus-backed AudioSink for Signals.

Converts short PCM requests from the Signals module into a `playback.signal`
event for SpeechPlaybackIntegration to consume. This keeps SignalIntegration
decoupled from playback internals and improves reliability.
"""

from __future__ import annotations

from typing import Optional

from integration.core.event_bus import EventBus, EventPriority
from modules.signals.core.interfaces import AudioSink


class EventBusAudioSink(AudioSink):
    def __init__(self, event_bus: EventBus) -> None:
        self._bus = event_bus

    async def play_pcm(
        self,
        pcm_s16le_mono: bytes,
        sample_rate: int,
        channels: int = 1,
        gain: float = 1.0,
        priority: int = 10,
        pattern: Optional[str] = None,
    ) -> None:
        # publish non-blocking; consumers must handle buffer sizes/priorities
        await self._bus.publish(
            "playback.signal",
            {
                "pcm": pcm_s16le_mono,
                "sample_rate": sample_rate,
                "channels": channels,
                "gain": gain,
                "priority": priority,
                "pattern": pattern,
            },
        )
