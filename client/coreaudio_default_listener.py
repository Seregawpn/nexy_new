import threading
import logging
import time

try:
    # Пытаемся подключить PyObjC CoreAudio/CoreFoundation
    import objc  # type: ignore
    from CoreFoundation import CFRunLoopGetCurrent  # type: ignore
    from CoreAudio import (  # type: ignore
        AudioObjectAddPropertyListenerBlock,
        AudioObjectRemovePropertyListenerBlock,
        AudioObjectGetPropertyData,
        AudioObjectPropertyAddress,
        kAudioObjectSystemObject,
        kAudioObjectPropertyScopeGlobal,
        kAudioObjectPropertyElementMaster,
        kAudioHardwarePropertyDefaultOutputDevice,
        kAudioHardwarePropertyDefaultInputDevice,
        kAudioHardwarePropertyDevices,
    )
    pyobjc_available = True
except Exception:  # pragma: no cover
    pyobjc_available = False

try:
    import sounddevice as sd  # для резервного считывания CoreAudio default
except Exception:  # pragma: no cover
    sd = None

logger = logging.getLogger(__name__)

class CoreAudioDefaultListener:
    """
    Заглушка listener-а CoreAudio default устройств.
    MVP-1: только хранит кэш и предоставляет методы обновления/чтения.
    (Позже будет заменено реализацией через PyObjC.)
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._default_input_index = None
        self._default_output_index = None
        self._callbacks_output = []
        self._callbacks_input = []
        self._activity_provider = None  # функция, возвращающая bool (есть активность?)
        self._stop_event = threading.Event()
        self._thread = None
        # PyObjC listeners
        self._ca_output_addr = None
        self._ca_input_addr = None
        self._ca_output_block = None
        self._ca_input_block = None
        self._ca_devices_addr = None
        self._ca_devices_block = None

    def set_defaults(self, input_index, output_index):
        with self._lock:
            self._default_input_index = input_index
            changed = (self._default_output_index != output_index)
            self._default_output_index = output_index
        if changed:
            self._emit_output_changed(output_index)

    # ===== Диагностика =====
    def snapshot_coreaudio_state(self):
        """Возвращает диагностический снимок: default input/output и список устройств (только значимые поля)."""
        data = {"default_input": None, "default_output": None, "devices": []}
        try:
            if sd is None:
                return data
            # Default из hostapi
            try:
                hostapis = sd.query_hostapis()
                core_idx = next((i for i, a in enumerate(hostapis) if 'core' in (a.get('name','').lower())), 0)
                api = sd.query_hostapis(core_idx)
                din = api.get('default_input_device', -1)
                dout = api.get('default_output_device', -1)
                data["default_input"] = din if din != -1 else None
                data["default_output"] = dout if dout != -1 else None
            except Exception:
                pass
            # Список устройств
            try:
                devices = sd.query_devices()
                for idx, dev in enumerate(devices):
                    try:
                        name = dev.get('name')
                        in_ch = int(dev.get('max_input_channels') or 0)
                        out_ch = int(dev.get('max_output_channels') or 0)
                        sr = float(dev.get('default_samplerate') or 0)
                        if in_ch > 0 or out_ch > 0:
                            data["devices"].append({
                                "index": idx,
                                "name": name,
                                "in": in_ch,
                                "out": out_ch,
                                "sr": sr,
                            })
                    except Exception:
                        continue
            except Exception:
                pass
        finally:
            return data

    def _emit_output_changed(self, new_index):
        try:
            for cb in list(self._callbacks_output):
                try:
                    cb(new_index)
                except Exception:
                    pass
        except Exception:
            pass

    def on_output_changed(self, callback):
        with self._lock:
            self._callbacks_output.append(callback)

    def on_input_changed(self, callback):
        with self._lock:
            self._callbacks_input.append(callback)

    def _emit_input_changed(self, new_index):
        try:
            for cb in list(self._callbacks_input):
                try:
                    cb(new_index)
                except Exception:
                    pass
        except Exception:
            pass

    def get_default_input(self):
        with self._lock:
            return self._default_input_index

    def get_default_output(self):
        with self._lock:
            return self._default_output_index

    # ===== Инициализация/мониторинг =====
    def set_activity_provider(self, provider):
        """Устанавливает провайдер активности (например, audio_player.is_playing)."""
        self._activity_provider = provider

    def start(self):
        """Старт listener-а. Если PyObjC недоступен — включает лёгкий фоновый монитор.
        Монитор читает CoreAudio default и срабатывает ТОЛЬКО при активности.
        """
        started_pyobjc = False
        if pyobjc_available:
            try:
                self._start_pyobjc_listeners()
                started_pyobjc = True
                logger.info("🔔 CoreAudio listener запущен через PyObjC property listeners")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось запустить PyObjC listeners: {e}")
                started_pyobjc = False
        if not started_pyobjc:
            # Запускаем мягкий монитор
            if self._thread is None or not self._thread.is_alive():
                self._stop_event.clear()
                self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
                self._thread.start()

    def stop(self):
        try:
            self._stop_event.set()
        except Exception:
            pass
        # Отключаем PyObjC listeners
        if pyobjc_available:
            try:
                self._stop_pyobjc_listeners()
            except Exception:
                pass

    def _monitor_loop(self):
        """Лёгкий монитор CoreAudio default: активен только при активности (воспроизведение/окно)."""
        last_out = None
        last_in = None
        while not self._stop_event.is_set():
            try:
                active = False
                try:
                    if callable(self._activity_provider):
                        active = bool(self._activity_provider())
                except Exception:
                    active = False

                if not active:
                    time.sleep(0.25)
                    continue

                din = dout = None
                if sd is not None:
                    try:
                        hostapis = sd.query_hostapis()
                        core_idx = next((i for i,a in enumerate(hostapis) if 'core' in (a.get('name','').lower())), 0)
                        api = sd.query_hostapis(core_idx)
                        din = api.get('default_input_device', -1)
                        dout = api.get('default_output_device', -1)
                        din = din if din != -1 else None
                        dout = dout if dout != -1 else None
                    except Exception:
                        pass

                # Обновляем кэш и эмитим изменение входа/выхода
                changed_out = False
                changed_in = False
                with self._lock:
                    if din is not None and din != self._default_input_index:
                        self._default_input_index = din
                        changed_in = True
                    if dout is not None and dout != self._default_output_index:
                        self._default_output_index = dout
                        changed_out = True

                if changed_in:
                    self._emit_input_changed(din)
                if changed_out:
                    self._emit_output_changed(dout)

                time.sleep(0.25)
            except Exception:
                time.sleep(0.25)

    # ===== Реализация через PyObjC listeners =====
    def _refresh_defaults_from_coreaudio(self):
        """Считывает текущие CoreAudio default input/output (через sounddevice hostapi) и обновляет кэш."""
        din = dout = None
        if sd is not None:
            try:
                hostapis = sd.query_hostapis()
                core_idx = next((i for i, a in enumerate(hostapis) if 'core' in (a.get('name', '').lower())), 0)
                api = sd.query_hostapis(core_idx)
                din = api.get('default_input_device', -1)
                dout = api.get('default_output_device', -1)
                din = din if din != -1 else None
                dout = dout if dout != -1 else None
            except Exception:
                din = dout = None
        changed_out = False
        changed_in = False
        old_in = None
        old_out = None
        with self._lock:
            if din is not None:
                if din != self._default_input_index:
                    old_in = self._default_input_index
                    self._default_input_index = din
                    changed_in = True
            if dout is not None and dout != self._default_output_index:
                old_out = self._default_output_index
                self._default_output_index = dout
                changed_out = True

        # Логируем информативно (имя устройства)
        def _fmt(idx):
            if sd is None or idx in (None, -1):
                return (idx, 'None')
            try:
                info = sd.query_devices(idx)
                return (idx, info.get('name'))
            except Exception:
                return (idx, str(idx))

        if changed_in:
            ni, nn = _fmt(self._default_input_index)
            oi, on = _fmt(old_in)
            logger.info(f"🎙️ CoreAudio: default input changed: {on} ({oi}) → {nn} ({ni})")
            self._emit_input_changed(self._default_input_index)
        if changed_out:
            ni, nn = _fmt(self._default_output_index)
            oi, on = _fmt(old_out)
            logger.info(f"🔊 CoreAudio: default output changed: {on} ({oi}) → {nn} ({ni})")
            self._emit_output_changed(self._default_output_index)

    def _start_pyobjc_listeners(self):
        """Регистрирует CoreAudio property listeners для default input/output."""
        # Адрес для Default Output
        self._ca_output_addr = AudioObjectPropertyAddress(
            mSelector=kAudioHardwarePropertyDefaultOutputDevice,
            mScope=kAudioObjectPropertyScopeGlobal,
            mElement=kAudioObjectPropertyElementMaster,
        )
        # Адрес для Default Input
        self._ca_input_addr = AudioObjectPropertyAddress(
            mSelector=kAudioHardwarePropertyDefaultInputDevice,
            mScope=kAudioObjectPropertyScopeGlobal,
            mElement=kAudioObjectPropertyElementMaster,
        )

        def _on_output_changed(inNumberAddresses, inAddresses):
            try:
                self._refresh_defaults_from_coreaudio()
                logger.debug("📢 CoreAudio: default output changed event")
                try:
                    snap = self.snapshot_coreaudio_state()
                    logger.info(f"🧪 Snapshot после default-output: din={snap.get('default_input')} dout={snap.get('default_output')} devices={len(snap.get('devices', []))}")
                except Exception:
                    pass
            except Exception:
                pass

        def _on_input_changed(inNumberAddresses, inAddresses):
            try:
                self._refresh_defaults_from_coreaudio()
                logger.debug("🎙️ CoreAudio: default input changed event")
                try:
                    snap = self.snapshot_coreaudio_state()
                    logger.info(f"🧪 Snapshot после default-input: din={snap.get('default_input')} dout={snap.get('default_output')} devices={len(snap.get('devices', []))}")
                except Exception:
                    pass
            except Exception:
                pass

        def _on_devices_changed(inNumberAddresses, inAddresses):
            try:
                logger.debug("🧩 CoreAudio: devices list changed event")
                self._refresh_defaults_from_coreaudio()
                try:
                    snap = self.snapshot_coreaudio_state()
                    logger.info(f"🧪 Snapshot после devices-changed: din={snap.get('default_input')} dout={snap.get('default_output')} devices={len(snap.get('devices', []))}")
                except Exception:
                    pass
                # Отложенная повторная проверка default — ловим ситуации, когда macOS меняет default с задержкой
                def _delayed_check(delay_ms: int):
                    try:
                        time.sleep(max(0.001, delay_ms/1000.0))
                        self._refresh_defaults_from_coreaudio()
                        ds = self.snapshot_coreaudio_state()
                        logger.info(f"🧪 Delayed check (+{delay_ms}ms): din={ds.get('default_input')} dout={ds.get('default_output')} devices={len(ds.get('devices', []))}")
                    except Exception:
                        pass
                try:
                    threading.Thread(target=_delayed_check, args=(300,), daemon=True).start()
                    threading.Thread(target=_delayed_check, args=(1000,), daemon=True).start()
                except Exception:
                    pass
            except Exception:
                pass

        # Храним ссылки, чтобы блоки не были собраны GC
        self._ca_output_block = _on_output_changed
        self._ca_input_block = _on_input_changed
        self._ca_devices_block = _on_devices_changed

        # Первичное обновление кэша
        self._refresh_defaults_from_coreaudio()

        # Регистрируем слушатели
        AudioObjectAddPropertyListenerBlock(kAudioObjectSystemObject, self._ca_output_addr, None, self._ca_output_block)
        AudioObjectAddPropertyListenerBlock(kAudioObjectSystemObject, self._ca_input_addr, None, self._ca_input_block)
        # Изменение состава устройств
        self._ca_devices_addr = AudioObjectPropertyAddress(
            mSelector=kAudioHardwarePropertyDevices,
            mScope=kAudioObjectPropertyScopeGlobal,
            mElement=kAudioObjectPropertyElementMaster,
        )
        AudioObjectAddPropertyListenerBlock(kAudioObjectSystemObject, self._ca_devices_addr, None, self._ca_devices_block)

    def _stop_pyobjc_listeners(self):
        try:
            if self._ca_output_addr and self._ca_output_block:
                AudioObjectRemovePropertyListenerBlock(kAudioObjectSystemObject, self._ca_output_addr, self._ca_output_block)
        except Exception:
            pass
        try:
            if self._ca_input_addr and self._ca_input_block:
                AudioObjectRemovePropertyListenerBlock(kAudioObjectSystemObject, self._ca_input_addr, self._ca_input_block)
        except Exception:
            pass
        try:
            if self._ca_devices_addr and self._ca_devices_block:
                AudioObjectRemovePropertyListenerBlock(kAudioObjectSystemObject, self._ca_devices_addr, self._ca_devices_block)
        except Exception:
            pass


