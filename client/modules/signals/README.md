# Signals Module

Purpose: provide short, user-friendly cues (audio/visual) for key moments like entering LISTENING ("you can speak now"), finishing playback, or errors/cancels.

Design principles
- Decoupled: no EventBus or UI imports here. Integration supplies adapters.
- Pure-Python: no new native dependencies; safe for macOS PKG/signing/notarization.
- Single audio path: reuse existing playback via an injected AudioSink.

Structure
```
modules/signals/
  core/
    interfaces.py   # types: SignalPattern/Kind/Request, SignalChannel, SignalService, AudioSink
    service.py      # SimpleSignalService with cooldown + metrics
  channels/
    audio_tone.py   # short sine generation (s16le mono) → AudioSink
    visual_tray.py  # tray blink abstraction (injected blinker)
  config/
    types.py        # SignalsConfig and PatternConfig dataclasses
```

Usage (sketch)
```python
from modules.signals.core.service import SimpleSignalService, CooldownPolicy
from modules.signals.core.interfaces import SignalRequest, SignalPattern, SignalKind
from modules.signals.channels.audio_tone import AudioToneChannel

# Implement an AudioSink adapter that feeds existing playback
class MySink:
    async def play_pcm(self, pcm_s16le_mono: bytes, sample_rate: int, channels: int = 1, gain: float = 1.0, priority: int = 10):
        ...  # enqueue to speech playback (signal-queue)

sink = MySink()
audio_channel = AudioToneChannel(sink, sample_rate=48000, default_volume=0.2)

svc = SimpleSignalService(
    channels=[audio_channel],
    cooldowns={SignalPattern.LISTEN_START: CooldownPolicy(cooldown_ms=300)},
)

await svc.emit(SignalRequest(pattern=SignalPattern.LISTEN_START, kind=SignalKind.AUDIO))
```

Compliance (macOS)
- No new entitlements or private APIs.
- No new native frameworks; pure Python sine generation.
- Playback through existing audio path ensures PKG signing/notarization compatibility.

