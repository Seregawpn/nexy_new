"""VoiceOver control for macOS.

The controller uses accessibility APIs to silence VoiceOver speech when the
application switches into interactive modes (e.g. LISTENING).
"""

from __future__ import annotations

import asyncio
import logging
import platform
import subprocess
import time
from dataclasses import dataclass
from typing import Literal, Optional, Sequence

logger = logging.getLogger(__name__)

_KEY_CODE_CONTROL = 59  # macOS virtual key code for the left Control key

# Attempt to import Quartz only on macOS. The module is part of pyobjc.
if platform.system() == "Darwin":  # pragma: no branch - platform guard
    try:  # pragma: no cover - Quartz is only available on macOS runtime
        from Quartz import (  # type: ignore
            CGEventCreateKeyboardEvent,
            CGEventPost,
            CGEventSetFlags,
            kCGEventFlagMaskControl,
            kCGHIDEventTap,
        )
    except Exception:  # pragma: no cover - import failure fallback
        CGEventCreateKeyboardEvent = None  # type: ignore
        CGEventPost = None  # type: ignore
        CGEventSetFlags = None  # type: ignore
        kCGEventFlagMaskControl = None  # type: ignore
        kCGHIDEventTap = None  # type: ignore
else:  # Non-macOS platforms
    CGEventCreateKeyboardEvent = None  # type: ignore
    CGEventPost = None  # type: ignore
    CGEventSetFlags = None  # type: ignore
    kCGEventFlagMaskControl = None  # type: ignore
    kCGHIDEventTap = None  # type: ignore


@dataclass
class VoiceOverControlSettings:
    """Configuration for VoiceOverController."""

    enabled: bool = True
    duck_modes: Sequence[str] = ("listening", "processing")
    release_modes: Sequence[str] = ("sleeping",)
    debounce_seconds: float = 0.25
    stop_repeats: int = 2
    stop_repeat_delay: float = 0.05
    use_apple_script_fallback: bool = True
    mode: Literal["stop", "mute_speech"] = "stop"
    engage_on_keyboard_events: bool = True
    # Настройки детального логирования для диагностики
    debug_logging: bool = False
    log_osascript_commands: bool = False
    log_voiceover_state: bool = False

    def __post_init__(self) -> None:
        self.duck_modes = tuple(str(m).lower() for m in self.duck_modes or ())
        self.release_modes = tuple(str(m).lower() for m in self.release_modes or ())
        self.debounce_seconds = max(0.0, float(self.debounce_seconds))
        self.stop_repeats = max(1, int(self.stop_repeats))
        self.stop_repeat_delay = max(0.0, float(self.stop_repeat_delay))
        if self.mode not in {"stop", "mute_speech"}:
            logger.warning("VoiceOverControlSettings: unknown mode %s, fallback to 'stop'", self.mode)
            self.mode = "stop"


class VoiceOverController:
    """Controller that mutes VoiceOver speech when required."""

    def __init__(self, settings: Optional[VoiceOverControlSettings] = None) -> None:
        self.settings = settings or VoiceOverControlSettings()
        self._lock = asyncio.Lock()
        self._ducked = False
        self._last_duck_ts = 0.0
        self._platform_supported = platform.system() == "Darwin"
        self._speech_muted_by_us = False
        self._speech_muted_supported = True
        self._voiceover_was_running = False  # Был ли VoiceOver запущен изначально
        self._voiceover_currently_running = False  # Текущее состояние VoiceOver

        if not self._platform_supported:
            logger.debug("VoiceOverController is only supported on macOS")
        elif not self.settings.enabled:
            logger.debug("VoiceOverController created but disabled via config")

    @property
    def is_supported(self) -> bool:
        return self._platform_supported

    @property
    def is_ducked(self) -> bool:
        return self._ducked

    async def initialize(self) -> bool:
        """Инициализация контроллера с диагностикой"""
        try:
            if not self._platform_supported:
                logger.warning("macOS frameworks not available - VoiceOver control disabled")
                return False
                
            if not self.settings.enabled:
                logger.info("VoiceOver control disabled via config")
                return True
            
            # ПРОВЕРЯЕМ СТАТУС VOICEOVER
            if self.settings.debug_logging:
                logger.info("🔍 VoiceOver: Начинаем диагностику...")
                status = await asyncio.to_thread(self._check_voiceover_status)
                logger.info(f"🔍 VoiceOver: Статус при инициализации: {status}")
                
                # Устанавливаем флаги состояния VoiceOver
                self._voiceover_was_running = status.get("voiceover_running", False)
                self._voiceover_currently_running = self._voiceover_was_running
                logger.info(f"🔍 VoiceOver: Was running initially: {self._voiceover_was_running}")
            else:
                # Даже без debug_logging проверяем статус для установки флагов
                status = await asyncio.to_thread(self._check_voiceover_status)
                self._voiceover_was_running = status.get("voiceover_running", False)
                self._voiceover_currently_running = self._voiceover_was_running
            
            logger.info(f"VoiceOverController initialized successfully (VoiceOver was running: {self._voiceover_was_running})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize VoiceOverController: {e}")
            return False

    async def apply_mode(self, mode: str) -> None:
        """Apply VoiceOver handling for the provided application mode."""
        if not self.settings.enabled or not self._platform_supported:
            return

        mode_value = str(mode).lower()

        if mode_value in self.settings.duck_modes:
            # Отключаем VoiceOver только если он сейчас запущен и еще не отключен
            if not self._ducked and self._voiceover_currently_running:
                await self._ensure_ducked(reason=f"mode:{mode_value}")
                logger.info(f"VoiceOverController: Ducking VoiceOver for mode {mode_value}")
            else:
                if not self._voiceover_currently_running:
                    logger.debug(f"VoiceOverController: VoiceOver is not currently running, skipping duck for mode {mode_value}")
                else:
                    logger.debug(f"VoiceOverController: VoiceOver already ducked, staying in mode {mode_value}")
        elif mode_value in self.settings.release_modes:
            # Включаем VoiceOver только если он был отключен нами и изначально был запущен
            if self._ducked and self._voiceover_was_running:
                await self.release()
                logger.info(f"VoiceOverController: Releasing VoiceOver for mode {mode_value}")
            else:
                if not self._voiceover_was_running:
                    logger.debug(f"VoiceOverController: VoiceOver was not running initially, skipping release for mode {mode_value}")
                else:
                    logger.debug(f"VoiceOverController: VoiceOver not ducked, staying in mode {mode_value}")

    async def duck(self, reason: Optional[str] = None) -> bool:
        """Explicitly request VoiceOver ducking."""
        if not self.settings.enabled or not self._platform_supported:
            return False
        
        # Не отключаем VoiceOver, если он сейчас не запущен
        if not self._voiceover_currently_running:
            logger.debug(f"VoiceOverController: VoiceOver is not currently running, skipping duck (reason={reason})")
            return False
            
        return await self._ensure_ducked(reason=reason or "manual")

    async def release(self, force: bool = False) -> None:
        """Release VoiceOver ducking state."""
        if not self.settings.enabled or not self._platform_supported:
            return

        async with self._lock:
            if not force and not self._ducked:
                return
            logger.debug("VoiceOverController: releasing ducking state")
            self._ducked = False
            self._log_voiceover_state("release:start")

            # Восстанавливаем VoiceOver через Command+F5
            # Это единственный рабочий метод на основе тестирования
            if self._speech_muted_by_us:
                success = await asyncio.to_thread(self._toggle_voiceover_with_command_f5)
                if success:
                    self._speech_muted_by_us = False
                    # Обновляем текущее состояние VoiceOver (переключили с выключенного на включенный)
                    self._voiceover_currently_running = True
                    self._log_voiceover_state("release:restored")
                    logger.info("VoiceOverController: VoiceOver restored via Command+F5")
                else:
                    logger.warning("VoiceOverController: failed to restore VoiceOver via Command+F5")
            else:
                logger.debug("VoiceOverController: VoiceOver was not disabled by us, no restoration needed")

    async def update_voiceover_status(self) -> None:
        """Обновить текущее состояние VoiceOver."""
        try:
            status = await asyncio.to_thread(self._check_voiceover_status)
            self._voiceover_currently_running = status.get("voiceover_running", False)
            logger.debug(f"VoiceOverController: Updated status - currently running: {self._voiceover_currently_running}")
        except Exception as exc:
            logger.warning(f"VoiceOverController: Failed to update VoiceOver status: {exc}")

    async def shutdown(self) -> None:
        """Ensure VoiceOver is released on shutdown."""
        await self.release(force=True)

    async def _ensure_ducked(self, reason: Optional[str] = None) -> bool:
        async with self._lock:
            if self._ducked:
                logger.debug("VoiceOverController: ducking already active, skip reapply")
                return True

            context = reason or "unknown"
            logger.info("VoiceOverController: duck requested (mode=%s, reason=%s)", self.settings.mode, context)

            success = await asyncio.to_thread(self._send_duck_command_sync, context)
            if success:
                self._ducked = True
                self._last_duck_ts = time.monotonic()
                # Обновляем текущее состояние VoiceOver (переключили с включенного на выключенный)
                self._voiceover_currently_running = False
                # Устанавливаем флаг, что мы отключили VoiceOver
                self._speech_muted_by_us = True
                logger.info("VoiceOverController: VoiceOver speech paused (reason=%s)", context)
                self._log_voiceover_state(f"duck:{context}")
                return True

            logger.warning("VoiceOverController: failed to pause VoiceOver speech (reason=%s)", context)
            return False

    def _send_duck_command_sync(self, context: str) -> bool:
        # Используем Command+F5 для полного отключения VoiceOver
        # Это единственный рабочий метод на основе тестирования
        logger.info(f"VoiceOverController: Using Command+F5 to disable VoiceOver (reason={context})")
        return self._toggle_voiceover_with_command_f5()

    def _toggle_voiceover_with_command_f5(self) -> bool:
        """Переключить VoiceOver через Command+F5 (единственный рабочий метод)"""
        try:
            success, output, stderr = self._run_osascript(
                'tell application "System Events" to key code 96 using {command down}'
            )
            
            if success:
                logger.info("VoiceOverController: Command+F5 executed successfully")
                return True
            else:
                logger.error(
                    "VoiceOverController: Command+F5 failed: %s", 
                    stderr.strip() if stderr else "Unknown error"
                )
                return False
                
        except Exception as exc:
            logger.error("VoiceOverController: Command+F5 exception: %s", exc)
            return False

    def _press_control_key(self) -> bool:
        if (
            CGEventCreateKeyboardEvent is not None
            and CGEventPost is not None
            and CGEventSetFlags is not None
            and kCGEventFlagMaskControl is not None
            and kCGHIDEventTap is not None
        ):
            try:
                event_down = CGEventCreateKeyboardEvent(None, _KEY_CODE_CONTROL, True)
                CGEventSetFlags(event_down, kCGEventFlagMaskControl)
                CGEventPost(kCGHIDEventTap, event_down)

                event_up = CGEventCreateKeyboardEvent(None, _KEY_CODE_CONTROL, False)
                CGEventPost(kCGHIDEventTap, event_up)
                logger.debug("VoiceOverController: control key sent via Quartz")
                return True
            except Exception as exc:  # pragma: no cover - Quartz exceptions are mac-specific
                logger.debug("VoiceOverController: Quartz key press failed: %s", exc)

        if self.settings.use_apple_script_fallback:
            return self._press_control_key_with_osascript()

        return False

    def _press_control_key_with_osascript(self) -> bool:
        success, _, stderr = self._run_osascript('tell application "System Events" to key code 59')
        if success:
            logger.debug("VoiceOverController: control key sent via AppleScript fallback")
            return True
        if stderr:
            logger.warning("VoiceOverController: AppleScript control key failed: %s", stderr.strip())
        return False

    def _stop_voiceover_speaking(self, context: str) -> None:
        success, _, stderr = self._run_osascript('tell application "VoiceOver" to stop speaking')
        if not success:
            logger.warning(
                "VoiceOverController: stop speaking failed (%s) context=%s",
                (stderr or "no error").strip(),
                context,
            )
            if self.settings.mode != "stop":
                # Fallback to control key tap when AppleScript fails
                self._press_control_key()
        else:
            logger.debug("VoiceOverController: stop speaking succeeded (context=%s)", context)

    def _run_osascript(self, script: str, capture_output: bool = False) -> tuple[bool, Optional[str], Optional[str]]:
        """Run a short AppleScript command."""
        try:
            # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ КОМАНД
            if self.settings.log_osascript_commands:
                logger.info(f"🔍 VoiceOver: Выполняем AppleScript: {script}")
            
            if capture_output:
                completed = subprocess.run(
                    ["osascript", "-e", script],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=1.0,
                )
                stdout = completed.stdout.strip() if completed.stdout else None
                stderr = completed.stderr.strip() if completed.stderr else None
                
                # ДЕТАЛЬНЫЕ ЛОГИ РЕЗУЛЬТАТОВ
                if self.settings.log_osascript_commands:
                    logger.info(f"🔍 VoiceOver: stdout='{stdout}', stderr='{stderr}'")
                
                if stderr:
                    logger.warning(f"🔍 VoiceOver: stderr={stderr}")
                return True, stdout, stderr
                
            # Без capture_output
            result = subprocess.run(
                ["osascript", "-e", script],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=1.0,
            )
            
            if self.settings.log_osascript_commands:
                logger.info(f"🔍 VoiceOver: Команда выполнена успешно, exit_code={result.returncode}")
            
            return True, None, None
            
        except subprocess.CalledProcessError as exc:
            error_msg = f"🔍 VoiceOver: CalledProcessError - exit_code={exc.returncode}, stderr='{exc.stderr}'"
            if self.settings.log_osascript_commands:
                logger.error(error_msg)
            else:
                logger.warning(error_msg)
            return False, None, str(exc.stderr) if exc.stderr else str(exc)
            
        except subprocess.TimeoutExpired as exc:
            error_msg = "🔍 VoiceOver: TimeoutExpired - команда превысила 1 секунду"
            if self.settings.log_osascript_commands:
                logger.error(error_msg)
            else:
                logger.warning(error_msg)
            return False, None, "timeout"
            
        except Exception as exc:
            error_msg = f"🔍 VoiceOver: Неожиданная ошибка: {type(exc).__name__}: {exc}"
            if self.settings.log_osascript_commands:
                logger.error(error_msg)
            else:
                logger.warning(error_msg)
            return False, None, str(exc)

    def _get_voiceover_speech_muted(self) -> Optional[bool]:
        if not self._speech_muted_supported:
            return None

        success, output, stderr = self._run_osascript('tell application "VoiceOver" to return speechMuted', capture_output=True)
        if not success or output is None:
            if stderr:
                self._handle_speech_muted_unsupported(stderr)
            return None
        lowered = output.strip().lower()
        if lowered in {"missing value", ""}:
            self._handle_speech_muted_unsupported("missing value", force=True)
            return None
        if lowered in {"true", "false"}:
            return lowered == "true"
        return None

    def _set_voiceover_speech_muted(self, muted: bool) -> bool:
        if not self._speech_muted_supported:
            return self._apply_voiceover_silence_fallback(muted, "unsupported")

        current = self._get_voiceover_speech_muted()
        if not self._speech_muted_supported:
            return self._apply_voiceover_silence_fallback(muted, "get_failed")

        if current is not None and current == muted:
            # Already in requested state, no further action needed.
            if muted:
                self._speech_muted_by_us = False
            return True

        success, _, stderr = self._run_osascript(
            f'tell application "VoiceOver" to set speechMuted to {str(muted).lower()}'
        )
        if success:
            if muted:
                self._speech_muted_by_us = current is False or current is None
            else:
                self._speech_muted_by_us = False
            self._log_voiceover_state(f"set_speechMuted:{muted}")
            return True

        if stderr:
            self._handle_speech_muted_unsupported(stderr)
            logger.warning("VoiceOverController: speechMuted script stderr: %s", stderr.strip())
        logger.debug("VoiceOverController: speechMuted script failed, attempting fallback")
        if self.settings.use_apple_script_fallback:
            if self._toggle_voiceover_speech_with_shortcut(muted, current):
                self._speech_muted_by_us = muted
                return True

        return self._apply_voiceover_silence_fallback(muted, "script_failed")

    def _toggle_voiceover_speech_with_shortcut(
        self,
        target_state: bool,
        current_state: Optional[bool],
    ) -> bool:
        if current_state is not None and current_state == target_state:
            return True

        success, _, stderr = self._run_osascript(
            'tell application "System Events" to key code 1 using {control down, option down, shift down}'
        )
        if not success:
            if stderr:
                logger.error("VoiceOverController: speech toggle shortcut failed: %s", stderr.strip())
            else:
                logger.error("VoiceOverController: speech toggle shortcut failed")
            return False

        if current_state is None:
            # Best effort: assume toggle put VoiceOver into desired state.
            return True

        toggled_state = not current_state
        if toggled_state != target_state:
            logger.warning(
                "VoiceOverController: toggle shortcut resulted in speechMuted=%s (expected %s)",
                toggled_state,
                target_state,
            )
        return toggled_state == target_state

    def _handle_speech_muted_unsupported(self, stderr: Optional[str], *, force: bool = False) -> None:
        if not self._speech_muted_supported:
            return

        message = (stderr or "").strip().lower()
        if not force:
            if "speechmuted" not in message and "speech muted" not in message:
                return
            if (
                "not defined" not in message
                and "doesn't understand" not in message
                and "missing value" not in message
            ):
                return

        self._speech_muted_supported = False
        logger.info(
            "VoiceOverController: speechMuted AppleScript commands unavailable - using control key fallback"
        )

    def _apply_voiceover_silence_fallback(self, muted: bool, reason: str) -> bool:
        if not muted:
            return True

        logger.debug("VoiceOverController: applying fallback VoiceOver silence (%s)", reason)
        success, _, stderr = self._run_osascript('tell application "VoiceOver" to stop speaking')
        control_sent = self._press_control_key()
        if success or control_sent:
            self._speech_muted_by_us = False
            return True

        if stderr:
            logger.warning(
                "VoiceOverController: fallback stop speaking failed (%s): %s", reason, stderr.strip()
            )
        else:
            logger.warning(
                "VoiceOverController: fallback stop speaking failed without error (%s)", reason
            )
        return False

    def _check_voiceover_status(self) -> dict:
        """Проверить статус VoiceOver и вернуть детальную информацию"""
        status = {
            "voiceover_running": False,
            "speech_muted": None,
            "accessible_apps": [],
            "errors": []
        }
        
        try:
            # Проверим, запущен ли VoiceOver
            success, output, stderr = self._run_osascript(
                'tell application "System Events" to get name of every application process',
                capture_output=True
            )
            
            if success and output:
                processes = output.split(", ")
                status["voiceover_running"] = "VoiceOver" in processes
                status["accessible_apps"] = processes
                if self.settings.log_voiceover_state:
                    logger.info(f"🔍 VoiceOver: Найденные процессы: {processes}")
            else:
                status["errors"].append(f"Не удалось получить список процессов: {stderr}")
                
            # Проверим состояние speechMuted, если платформа его поддерживает
            if self._speech_muted_supported:
                success, output, stderr = self._run_osascript(
                    'tell application "VoiceOver" to return speechMuted',
                    capture_output=True
                )

                if success and output:
                    lowered = output.strip().lower()
                    if lowered in {"true", "false"}:
                        status["speech_muted"] = lowered == "true"
                        if self.settings.log_voiceover_state:
                            logger.info(f"🔍 VoiceOver: speechMuted={status['speech_muted']}")
                    else:
                        status["errors"].append(f"Неизвестный ответ speechMuted: {output}")
                        self._handle_speech_muted_unsupported(output, force=True)
                else:
                    status["errors"].append(f"Не удалось получить speechMuted: {stderr}")
                    self._handle_speech_muted_unsupported(stderr)
            else:
                status["errors"].append("speechMuted недоступен на этой системе")
                
        except Exception as exc:
            status["errors"].append(f"Ошибка проверки статуса: {exc}")
        
        if self.settings.log_voiceover_state:
            logger.info(f"🔍 VoiceOver Status: {status}")
        
        return status

    def _log_voiceover_state(self, context: str) -> None:
        state = self._get_voiceover_speech_muted()
        if state is None:
            logger.debug("VoiceOverController: unable to determine speechMuted state (%s)", context)
        else:
            logger.debug("VoiceOverController: speechMuted=%s (%s)", state, context)


__all__ = ("VoiceOverControlSettings", "VoiceOverController")
