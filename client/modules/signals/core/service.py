"""
Signals Module — Service implementation

Provides an async, lightweight dispatcher with per-pattern cooldowns and
basic priority hinting. No external dependencies.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .interfaces import SignalService, SignalChannel, SignalRequest, SignalPattern

logger = logging.getLogger(__name__)


@dataclass
class CooldownPolicy:
    cooldown_ms: int = 300


@dataclass
class SignalMetrics:
    trigger_count: int = 0
    suppressed_by_cooldown: int = 0
    failed_count: int = 0


class SimpleSignalService(SignalService):
    """Simple async signal service with per-pattern cooldown and metrics."""

    def __init__(
        self,
        channels: List[SignalChannel],
        cooldowns: Optional[Dict[SignalPattern, CooldownPolicy]] = None,
        enabled: bool = True,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self._channels = channels
        self._enabled = enabled
        self._cooldowns = cooldowns or {}
        self._last_emitted_at_ms: Dict[SignalPattern, int] = {}
        self._metrics: Dict[SignalPattern, SignalMetrics] = {}
        self._lock = asyncio.Lock()
        self._loop = loop or asyncio.get_event_loop()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def get_metrics(self) -> Dict[SignalPattern, SignalMetrics]:
        return self._metrics

    def _cooldown_ok(self, pattern: SignalPattern) -> bool:
        policy = self._cooldowns.get(pattern)
        if not policy or policy.cooldown_ms <= 0:
            return True
        now_ms = int(time.time() * 1000)
        last_ms = self._last_emitted_at_ms.get(pattern, 0)
        return (now_ms - last_ms) >= policy.cooldown_ms

    def _note_emitted(self, pattern: SignalPattern) -> None:
        self._last_emitted_at_ms[pattern] = int(time.time() * 1000)

    async def emit(self, req: SignalRequest) -> None:
        if not self._enabled:
            return

        # Lazy init metrics entry
        metrics = self._metrics.setdefault(req.pattern, SignalMetrics())
        metrics.trigger_count += 1

        async with self._lock:
            if not self._cooldown_ok(req.pattern):
                metrics.suppressed_by_cooldown += 1
                logger.debug(
                    f"Signal suppressed by cooldown: pattern={req.pattern}, kind={req.kind}"
                )
                return

            # Find a channel for the request kind
            channel = next((c for c in self._channels if c.can_handle(req.kind)), None)
            if not channel:
                logger.debug(f"No channel found for kind={req.kind}")
                return

            # Mark emit time before actual dispatch to maintain cooldown semantics
            self._note_emitted(req.pattern)

            # Synchronously await channel emit to guarantee publication timing
            try:
                # Clamp volume defensively
                if req.volume < 0.0:
                    req.volume = 0.0
                if req.volume > 1.0:
                    req.volume = 1.0
                await channel.emit(req)
            except Exception as e:
                metrics.failed_count += 1
                logger.warning(
                    f"Signal emit failed: pattern={req.pattern}, kind={req.kind}, err={e}"
                )
