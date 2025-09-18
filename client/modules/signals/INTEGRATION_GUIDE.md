# Signals Module — Integration Guide (API & Wiring)

This guide explains how to wire the Signals module into the existing Nexy client
architecture safely (macOS/PKG/notarization‑friendly) and cleanly (no tight coupling).

Contents
- Goals & constraints
- Integration surfaces (Audio, Visual, EventBus)
- API contracts (quick reference)
- Recommended wiring steps
- Configuration mapping (UnifiedConfig)
- macOS compliance checklist
- Testing checklist

---

## Goals & constraints
- Provide short cues for key moments (listen_start, done, error, cancel, processing_start).
- Keep the module independent from EventBus, Tray, and Playback internals.
- No new entitlements, no private APIs, no native frameworks; PKG signing/notarization must remain unaffected.
- Reuse the existing audio pipeline (CoreAudio via speech playback) — one device, one path.

---

## Integration surfaces

1) Audio (required)
- Adapter: implement an `AudioSink` that passes a short mono s16le buffer into the existing playback.
- Recommended approach: add a high‑priority “signal queue” in the speech playback component and expose a method `enqueue_signal(...)`.
- Advantage: no extra CoreAudio streams, predictable volume/device selection.

2) Visual (optional)
- Adapter: implement a `TrayBlinker` for a quick visual cue (blink/flash) in the tray.
- Keep it thin (e.g., wrapper over Tray API); avoid coupling Signals to tray implementation.

3) EventBus (via a separate integration)
- Create `SignalIntegration` in `client/integration/integrations/signal_integration.py`.
- Subscribe to: `app.mode_changed`, `voice.mic_opened`, `playback.*`, `grpc.request_*`, `voice.recognition_*`, `interrupt.request`.
- Map events → `SignalRequest` (per configuration) → `SignalService.emit()`.

---

## API contracts (quick reference)

From `core/interfaces.py`:

```
class SignalPattern(str, Enum):
    LISTEN_START, PROCESSING_START, DONE, ERROR, CANCEL

class SignalKind(str, Enum):
    AUDIO, VISUAL

@dataclass(slots=True)
class SignalRequest:
    pattern: SignalPattern
    kind: SignalKind
    session_id: Optional[str] = None
    volume: float = 0.2
    tone_hz: int = 880
    duration_ms: int = 120
    priority: int = 0

class SignalChannel(Protocol):
    def can_handle(self, kind: SignalKind) -> bool: ...
    async def emit(self, req: SignalRequest) -> None: ...

class SignalService(Protocol):
    async def emit(self, req: SignalRequest) -> None: ...

class AudioSink(Protocol):
    async def play_pcm(self, pcm_s16le_mono: bytes, sample_rate: int,
                       channels: int = 1, gain: float = 1.0,
                       priority: int = 10) -> None: ...
```

Channels:
- `AudioToneChannel(sink, sample_rate=48000, default_volume=0.2)` — generates s16le mono tone and calls `sink.play_pcm(...)`.
- `VisualTrayChannel(blinker)` — calls `blinker.blink(pattern: str, duration_ms: int)`.

Service:
- `SimpleSignalService(channels=[...], cooldowns={...}, enabled=True)` — async, per‑pattern cooldown, basic metrics.

Config types:
- `SignalsConfig` with `patterns[pattern_name] -> PatternConfig(audio, visual, volume, tone_hz, duration_ms, cooldown_ms)`.

---

## Recommended wiring steps

A) Audio path (Adapter)
1. Extend the existing speech playback to accept short “signal” buffers with priority.
   - Add a method similar to:
     ```
     async def enqueue_signal(self, pcm_s16le_mono: bytes, sample_rate: int,
                              channels: int = 1, gain: float = 1.0,
                              priority: int = 10) -> None: ...
     ```
   - Internally, keep a tiny signal queue with higher priority than normal chunks.
   - Clamp gain; keep duration short (≤150 ms). Apply small fade‑in/out to avoid clicks.

2. Implement an `AudioSink` adapter:
   ```
   from modules.signals.core.interfaces import AudioSink

   class PlaybackSink(AudioSink):
       def __init__(self, player):
           self._player = player
       async def play_pcm(self, pcm_s16le_mono: bytes, sample_rate: int,
                          channels: int = 1, gain: float = 1.0, priority: int = 10) -> None:
           await self._player.enqueue_signal(pcm_s16le_mono, sample_rate, channels, gain, priority)
   ```

3. Create the audio channel:
   ```
   from modules.signals.channels.audio_tone import AudioToneChannel
   sink = PlaybackSink(player)
   audio_ch = AudioToneChannel(sink, sample_rate=48000, default_volume=0.2)
   ```

B) Service
- Instantiate `SimpleSignalService` with channels and cooldowns derived from config.
- Example:
  ```
  from modules.signals.core.service import SimpleSignalService, CooldownPolicy
  from modules.signals.core.interfaces import SignalPattern

  svc = SimpleSignalService(
      channels=[audio_ch],
      cooldowns={
          SignalPattern.LISTEN_START: CooldownPolicy(cooldown_ms=300),
          SignalPattern.DONE: CooldownPolicy(cooldown_ms=150),
      },
  )
  ```

C) Integration (later, in SignalIntegration)
- Subscribe to events and map them to `SignalRequest` based on configuration.
- Examples:
  ```
  await svc.emit(SignalRequest(pattern=SignalPattern.LISTEN_START, kind=SignalKind.AUDIO))
  await svc.emit(SignalRequest(pattern=SignalPattern.DONE, kind=SignalKind.AUDIO))
  ```

---

## Configuration mapping (UnifiedConfig)
- Add a section like:
  ```
  integrations:
    signals:
      enabled: true
      sample_rate: 48000
      default_volume: 0.2
      patterns:
        listen_start: { audio: true, visual: false, volume: 0.2, tone_hz: 880, duration_ms: 120, cooldown_ms: 300 }
        done: { audio: true, visual: false, volume: 0.18, tone_hz: 660, duration_ms: 100, cooldown_ms: 150 }
        error: { audio: true }
        cancel: { audio: true }
  ```
- Parse into `SignalsConfig` and create `CooldownPolicy` per pattern.

---

## macOS compliance checklist
- No new entitlements (we reuse existing audio stack; no NSSound/AVFoundation in the first version).
- No private APIs; no native frameworks; pure-Python tone generation.
- Hardened Runtime unchanged; all binaries signed by existing process.
- Notarization unaffected (no new dylib/framework artifacts).

---

## Testing checklist
- Unit tests: `SimpleSignalService` cooldown suppresses duplicates; metrics update correctly.
- Audio: entering LISTENING → short tone (≤150 ms), no clicks (fade), correct device (same as playback).
- Event flow: playback.completed → DONE tone; grpc/voice failures → ERROR tone; interrupt/cancel → CANCEL tone.
- Stress: rapid LISTENING toggles → only one tone due to cooldown; during long playback, signal still audible or deferred per design.

---

Notes
- Keep signal durations short and volumes moderate. The goal is feedback, not notification overload.
- Visual cues are optional and wired via a small tray adapter.
