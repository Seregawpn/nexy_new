# ⏹️ Interrupts & Barge‑In — План и спецификация

Дата: 19 сентября 2025
Статус: MVP реализован (press‑first interrupt); донастройки — в работе

## Цели
- Мгновенное прерывание по нажатию ПРОБЕЛ: остановить воспроизведение, отменить активный gRPC, прервать распознавание.
- Короткое нажатие: только прерывание → режим SLEEPING.
- Длинное нажатие: прерывание → сразу LISTENING (новая запись); на RELEASE → PROCESSING.

## Поведение (спецификация)
- PRESS (при любом нажатии — коротком или длинном):
  - Немедленно прерывает всё: плеер (без дренажа), активный gRPC (отмена), распознавание/прослушивание (отмена).
  - Не открывает микрофон, не меняет режим сам по себе.
- SHORT_PRESS:
  - Только переводит в SLEEPING (микрофон не открывается).
- LONG_PRESS:
  - Начинает новую голосовую сессию: новый `session_id`, `voice.recording_start`, перевод в LISTENING.
- RELEASE (после LONG):
  - `voice.recording_stop` → переход в PROCESSING.

## Событийный контракт
- Вход: `keyboard.press`, `keyboard.short_press`, `keyboard.long_press`, `keyboard.release`.
- Управляющие:
  - `interrupt.request { scope:'playback', source:'keyboard', reason:'key_press' }` — инициирует стоп плеера/отмены.
  - `voice.recording_start|stop { session_id }` — управление микрофоном.
  - `mode.request { target: SLEEPING|LISTENING|PROCESSING }` — смена режимов.
  - (Опционально) `grpc.request_cancel { session_id? }` — явная отмена активного RPC.
- Выход/состояние:
  - `playback.cancelled { reason:'interrupt' }`
  - `grpc.request_failed { error:'cancelled' }`
  - `voice.mic_opened|closed`, `app.mode_changed`

## Последовательности (строгий порядок)
1) PRESS (из любого режима)
   - publish `interrupt.request` (scope=playback, source=keyboard, reason=key_press)
   - (при наличии) отмена активного gRPC; отмена распознавания; мгновенная тишина
   - подготовка `session_id` (не открывая микрофон)
2) SHORT_PRESS
   - publish `mode.request { target: SLEEPING }`
3) LONG_PRESS
   - publish `voice.recording_start { session_id }`
   - publish `mode.request { target: LISTENING }`
4) RELEASE (после LONG)
   - publish `voice.recording_stop { session_id }`
   - publish `mode.request { target: PROCESSING }`

## Ответственности модулей
- InputProcessingIntegration
  - На PRESS: публикует `interrupt.request` (press‑first), подготавливает `session_id`.
  - На SHORT: `mode.request SLEEPING` (без открытия микрофона).
  - На LONG: `voice.recording_start` + `mode.request LISTENING`; на RELEASE → `voice.recording_stop` + `mode.request PROCESSING`.
- SpeechPlaybackIntegration
  - На `interrupt.request|keyboard.short_press`: жёсткий `stop_playback()` + очистка буфера; publish `playback.cancelled`; не публикует `mode.request`.
- GrpcClientIntegration
  - На `interrupt.request|keyboard.short_press`: отменяет активный стрим (task.cancel) и публикует `grpc.request_failed { error:'cancelled' }`.
  - (Донастройка) Поддержка `grpc.request_cancel { session_id? }`.
- VoiceRecognitionIntegration
  - На `interrupt.request|keyboard.short_press`: отменяет распознавание/прослушивание, закрывает микрофон.
  - На `voice.recording_start`: открывает микрофон и публикует `voice.mic_opened`.
- StateManager
  - Все смены режимов только через `mode.request`.

## Риски и нюансы
- Дубли режимов: все переходы только через Input/Workflows; плеер не переводит режим.
- «Хвост» звука: стоп без дренажа, очищать буфер перед выходом.
- Поздние события gRPC: после cancel возможны отложенные финалы — игнорировать/помечать как отменённые.
- Debounce SHORT в LISTENING: 100–150 мс (добавить при необходимости).
- No‑op: cancel при отсутствии активного RPC/плеера — без ошибок.

## Тест‑чеклист
- PROCESSING → PRESS→SHORT: мгновенная тишина, `grpc…cancelled`, режим SLEEPING.
- PROCESSING → PRESS→LONG: тишина, cancel, `voice.mic_opened`, LISTENING; RELEASE → PROCESSING.
- SLEEPING → SHORT: остаётся SLEEPING; → LONG: LISTENING.
- LISTENING → SHORT: cancel‑only → SLEEPING; → LONG: no‑op (остаёмся LISTENING).

## Текущее состояние (MVP)
- Реализовано:
  - press‑first interrupt в InputProcessingIntegration
  - Жёсткий стоп плеера без смены режима в SpeechPlaybackIntegration
  - Отмена gRPC по interrupt/short (через отмену активной задачи) в GrpcClientIntegration
  - Отмена распознавания по interrupt/short в VoiceRecognitionIntegration
- Донастройки (рекомендованы):
  - Явный канал `grpc.request_cancel { session_id? }` для адресной отмены
  - Debounce SHORT в LISTENING (≤150 мс)
  - Фильтр «поздних» аудио‑чанков после cancel (по session_id)

