"""
Signals Module — Core Interfaces and Types

Pure-Python contracts for signaling (audio/visual) without assuming
any specific playback or tray implementation.

No external dependencies. Safe for macOS packaging, signing and notarization.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol, runtime_checkable


class SignalPattern(str, Enum):
    """Logical signal patterns to standardize user cues.

    - LISTEN_START: play when app enters LISTENING (user can speak now)
    - PROCESSING_START: optional cue on PROCESSING entry
    - DONE: successful completion (e.g., after playback)
    - ERROR: error occurred
    - CANCEL: cancel/interrupt occurred
    """

    LISTEN_START = "listen_start"
    PROCESSING_START = "processing_start"
    DONE = "done"
    ERROR = "error"
    CANCEL = "cancel"


class SignalKind(str, Enum):
    AUDIO = "audio"
    VISUAL = "visual"


@dataclass
class SignalRequest:
    """A single signal request, ready to be emitted via a channel/service."""

    pattern: SignalPattern
    kind: SignalKind
    session_id: Optional[str] = None
    volume: float = 0.2  # 0.0..1.0 (service clamps)
    tone_hz: int = 880
    duration_ms: int = 120
    priority: int = 0


@runtime_checkable
class SignalChannel(Protocol):
    """Channel is responsible for actual signal emission for a given kind."""

    def can_handle(self, kind: SignalKind) -> bool:
        ...

    async def emit(self, req: SignalRequest) -> None:
        ...


@runtime_checkable
class SignalService(Protocol):
    """Service accepts requests, applies policies (cooldown/priority), and dispatches to channels."""

    async def emit(self, req: SignalRequest) -> None:
        ...


@runtime_checkable
class AudioSink(Protocol):
    """Abstract sink for PCM playback used by AudioToneChannel.

    Integration will provide an adapter to the existing speech playback pipeline.
    This abstraction avoids direct dependency on playback internals here.
    """

    async def play_pcm(
        self,
        pcm_s16le_mono: bytes,
        sample_rate: int,
        channels: int = 1,
        gain: float = 1.0,
        priority: int = 10,
        pattern: Optional[str] = None,
    ) -> None:
        ...
