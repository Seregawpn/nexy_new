# 🔔 Signals & Cues Plan (Аудио/визуальные сигналы)

Дата: 18 сентября 2025
Статус: Implemented ✅

## Цель
Дать пользователю чёткий сигнал в ключевые моменты, в первую очередь — после входа в режим LISTENING, чтобы он понимал: «можно говорить».

## Сценарии и сигналы
- listen_start: вход в LISTENING → короткий звуковой «beep» и/или визуальный всплеск в трее.
- recording_stop: фиксируем окончание записи → короткий «tick».
- processing_start: переход в PROCESSING → мягкий «whoosh» (опционально).
- success/end: успешное завершение PROCESSING/playback → короткий «done» сигнал.
- error/cancel: ошибка/прерывание → отрицательный «beep-beep».

## Событийный контракт
- signal.request { kind: 'audio'|'visual', pattern: 'listen_start'|'processing_start'|'done'|'error'|'cancel', volume?: float, device?: str, priority?: int, session_id?: str }
- signal.completed { pattern, session_id? }
- signal.failed { pattern, error, session_id? }

Рекомендуемые автосигналы (без явного signal.request):
- app.mode_changed → LISTENING → emit listen_start (если включено в конфиге)
- voice.mic_opened → emit listen_start (дублируем только если режим уже в LISTENING)
- app.mode_changed → PROCESSING → emit processing_start (опционально)
- playback.completed → emit done
- interrupt.request / playback.cancelled → emit cancel
- grpc.request_failed / voice.recognition_failed → emit error

## Архитектура
- SignalIntegration (integration/integrations/signal_integration.py)
  - Подписки: app.mode_changed, voice.mic_opened, playback.*, interrupt.request, grpc.request_*, voice.recognition_*
  - Публикует: signal.request (если нужны промежуточные мосты), signal.completed/failed
  - Каналы:
    - audio: простой звуковой сигнал (см. Реализация)
    - visual: вспышка/мигание иконки/значка в трее (микроиндикация)

## Реализация аудио‑сигналов
Выбран подход через существующий SpeechPlayback (единый стек):
- Генерация короткой синус‑волны (880 Hz, ~120 ms) в `AudioToneChannel`.
- Адаптер `EventBusAudioSink` публикует событие `playback.signal` с PCM (s16le, 48 kHz).
- `SpeechPlaybackIntegration` воспроизводит сигнал немедленно.

Пример генерации «beep» (псевдокод):
```python
sr = 48000; duration = 0.12; freq = 880
t = np.linspace(0, duration, int(sr*duration), endpoint=False)
wave = 0.2 * np.sin(2*np.pi*freq*t)  # громкость 20%
pcm = (wave * 32767).astype(np.int16)
emit_event('grpc.response.audio', make_chunk(pcm, shape=(len(pcm),), dtype='int16'))
```

## Конфигурация
```yaml
integrations:
  signals:
    enabled: true
    on_listening_start:
      audio: true
      visual: false
      volume: 0.2
      tone_hz: 880
      duration_ms: 120
    on_processing_start:
      audio: false
      visual: true
    on_done:
      audio: true
      visual: false
    on_error:
      audio: true
      visual: false
```

## Шаги внедрения (выполнено)
1) [x] SignalIntegration: подписки на ключевые события → emit(pattern)
2) [x] Включено в SimpleModuleCoordinator (инициализация/запуск)
3) [x] Аудио‑beep через `playback.signal` (EventBusAudioSink)
4) [ ] Visual‑мигание в TrayControllerIntegration (позже)
5) [x] Автосигналы: LISTENING→listen_start; playback.completed→done; interrupt/cancel→cancel; grpc/voice.failed→error
6) [x] Конфиг по умолчанию в коде; расширяемый через SignalsIntegrationConfig
7) [x] Тест: ручная проверка LISTENING beep; логи подтверждают `playback.signal`

## Вариант «speech start» (VAD‑сигнал)
- VoiceRecognitionIntegration публикует `voice.speech_started` при превышении порога энергии → можно мигнуть в трее «идёт речь».
- Параметры VAD берём из уже калиброванного порога; добавляем событие без изменения основной логики PTT.
