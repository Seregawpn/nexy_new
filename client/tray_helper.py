import os
import sys
import json
import signal

try:
    import rumps
except Exception as e:
    print(f"[tray_helper] rumps import failed: {e}")
    sys.exit(1)


STATUS_EMOJI = {
    "SLEEPING": "⚪️",
    "LISTENING": "🟢",
    "IN_PROCESS": "🔵",
}


def parse_args(argv):
    status_file = os.path.join(
        os.path.expanduser("~"), "Library", "Application Support", "Nexy", "tray_status.json"
    )
    main_pid = None
    for i, a in enumerate(argv):
        if a == "--status-file" and i + 1 < len(argv):
            status_file = argv[i + 1]
        if a == "--pid" and i + 1 < len(argv):
            try:
                main_pid = int(argv[i + 1])
            except Exception:
                main_pid = None
    os.makedirs(os.path.dirname(status_file), exist_ok=True)
    return status_file, main_pid


class TrayApp(rumps.App):
    def __init__(self, status_file: str, main_pid: int | None):
        super().__init__("Nexy")
        self.status_file = status_file
        self.main_pid = main_pid
        self._current = "SLEEPING"
        self.title = f"{STATUS_EMOJI.get(self._current, '⚪️')} Nexy"
        # Отключаем стандартную кнопку выхода и добавляем одну собственную
        self.quit_button = None
        self.menu = [rumps.MenuItem("Quit Nexy", callback=self._on_quit)]
        self._timer = rumps.Timer(self._tick, 0.5)
        self._timer.start()

    def _tick(self, _):
        # 1) если основной процесс завершился — закрываемся
        if self.main_pid:
            try:
                os.kill(self.main_pid, 0)
            except Exception:
                rumps.quit_application()
                return
        # 2) читаем статус
        try:
            with open(self.status_file, "r") as f:
                data = json.load(f)
            st = data.get("state")
            if st and st != self._current:
                self._current = st
                self.title = f"{STATUS_EMOJI.get(self._current, '⚪️')} Nexy"
        except Exception:
            pass

    def _on_quit(self, _):
        if self.main_pid:
            try:
                os.kill(self.main_pid, signal.SIGTERM)
            except Exception:
                pass
        rumps.quit_application()


if __name__ == "__main__":
    status_file, main_pid = parse_args(sys.argv)
    TrayApp(status_file, main_pid).run()

