"""
Signals Module — Config Types

Dataclasses describing configuration for signals. Validation and defaults
are conservative and do not require external libraries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from ..core.interfaces import SignalPattern


@dataclass
class PatternConfig:
    audio: bool = True
    visual: bool = False
    volume: float = 0.2
    tone_hz: int = 880
    duration_ms: int = 120
    cooldown_ms: int = 300


@dataclass
class SignalsConfig:
    enabled: bool = True
    sample_rate: int = 48_000
    default_volume: float = 0.2
    patterns: Dict[str, PatternConfig] = field(default_factory=lambda: {
        SignalPattern.LISTEN_START.value: PatternConfig(audio=True, visual=False, volume=0.2, tone_hz=880, duration_ms=120, cooldown_ms=300),
        SignalPattern.PROCESSING_START.value: PatternConfig(audio=False, visual=True, duration_ms=100),
        SignalPattern.DONE.value: PatternConfig(audio=True, visual=False, volume=0.18, tone_hz=660, duration_ms=100, cooldown_ms=150),
        SignalPattern.ERROR.value: PatternConfig(audio=True, visual=False, volume=0.22, tone_hz=440, duration_ms=140, cooldown_ms=150),
        SignalPattern.CANCEL.value: PatternConfig(audio=True, visual=False, volume=0.2, tone_hz=520, duration_ms=120, cooldown_ms=150),
    })

    def get(self, pattern: SignalPattern) -> PatternConfig:
        return self.patterns.get(pattern.value, PatternConfig())

