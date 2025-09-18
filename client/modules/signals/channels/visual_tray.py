"""
Signals Module — Visual Tray Channel (placeholder)

This channel defines a visual cue abstraction (e.g., tray icon blink).
Actual tray implementation is injected by integration via a small adapter,
keeping this module decoupled from UI specifics.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from ..core.interfaces import SignalChannel, SignalRequest, SignalKind

logger = logging.getLogger(__name__)


class TrayBlinker(Protocol):
    async def blink(self, pattern: str, duration_ms: int = 120) -> None:
        ...


class VisualTrayChannel(SignalChannel):
    def __init__(self, blinker: TrayBlinker) -> None:
        self._blinker = blinker

    def can_handle(self, kind: SignalKind) -> bool:
        return kind == SignalKind.VISUAL

    async def emit(self, req: SignalRequest) -> None:
        # Minimal mapping: reuse pattern name and duration
        try:
            await self._blinker.blink(pattern=req.pattern.value, duration_ms=max(60, req.duration_ms))
        except Exception as e:
            logger.debug(f"VisualTrayChannel blink failed: {e}")

