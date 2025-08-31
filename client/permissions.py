import logging

logger = logging.getLogger(__name__)


def request_screen_recording_permission() -> None:
    """Проверяет и (при необходимости) запрашивает доступ к записи экрана.
    Вызывает системный диалог macOS один раз, если доступ ещё не выдан.
    """
    try:
        from Quartz import (
            CGPreflightScreenCaptureAccess,
            CGRequestScreenCaptureAccess,
        )

        has_access = bool(CGPreflightScreenCaptureAccess())
        if not has_access:
            logger.info("🔐 Запрашиваю разрешение на Screen Recording...")
            CGRequestScreenCaptureAccess()
        else:
            logger.info("✅ Разрешение на Screen Recording уже выдано")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось проверить/запросить Screen Recording: {e}")


def request_accessibility_permission() -> None:
    """Запрашивает разрешение на Accessibility (управление другими приложениями).
    macOS показывает системный диалог и предлагает включить в Privacy > Accessibility.
    """
    try:
        from Quartz import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt

        options = {kAXTrustedCheckOptionPrompt: True}
        trusted = bool(AXIsProcessTrustedWithOptions(options))
        if trusted:
            logger.info("✅ Accessibility уже разрешён")
        else:
            logger.info("🔐 Запрошен доступ Accessibility (см. System Settings → Privacy & Security → Accessibility)")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось проверить/запросить Accessibility: {e}")


def request_apple_events_permission() -> None:
    """Пробует отправить безопасное AppleEvent к System Events, чтобы вызвать TCC промпт
    на 'Automation' (Apple Events)."""
    try:
        from Foundation import NSAppleScript

        script = 'tell application "System Events"\n return "ok"\nend tell'
        ns_script = NSAppleScript.alloc().initWithSource_(script)
        _result, error = ns_script.executeAndReturnError_(None)
        if error is not None:
            # При первом вызове обычно возвращается ошибка до выдачи разрешения — это нормально
            logger.info("🔐 Запрошено разрешение на Automation (Apple Events)")
        else:
            logger.info("✅ Automation (Apple Events) уже разрешён")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось инициировать запрос Apple Events: {e}")


def request_microphone_permission() -> None:
    """Кратко открывает входной аудиопоток, чтобы macOS показал диалог Microphone.
    Поток сразу закрывается."""
    try:
        import sounddevice as sd

        logger.info("🔐 Проверяю доступ к микрофону (короткое открытие потока)...")
        try:
            with sd.InputStream(channels=1, samplerate=16000, blocksize=256, dtype='int16'):
                pass
            logger.info("✅ Микрофон доступен (поток открыт и закрыт)")
        except Exception as open_err:
            # Даже при ошибке открытие инициирует TCC-процесс; просто логируем
            logger.info(f"🔐 Диалог доступа к микрофону мог быть показан: {open_err}")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось инициировать запрос Microphone: {e}")


def ensure_permissions() -> None:
    """Последовательно инициирует все критичные разрешения на старте."""
    logger.info("🛡️ Инициирую запросы системных разрешений (Screen, Mic, Accessibility, Apple Events)...")
    request_screen_recording_permission()
    request_microphone_permission()
    request_accessibility_permission()
    request_apple_events_permission()
    logger.info("🛡️ Запросы разрешений инициированы")


