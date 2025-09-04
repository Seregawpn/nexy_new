from AppKit import NSStatusBar, NSVariableStatusItemLength, NSMenu, NSMenuItem
from Foundation import NSObject


STATUS_EMOJI = {
    "SLEEPING": "⚪️",
    "LISTENING": "🟢",
    "IN_PROCESS": "🔵",
}


class _MenuHandler(NSObject):
    def initWithQuitCallback_(self, cb):
        self = super().init()
        if self is None:
            return None
        self._quit_cb = cb
        return self

    def quit_(self, _sender):
        try:
            if callable(self._quit_cb):
                self._quit_cb()
        except Exception:
            pass


class TrayController:
    """Нативный статус-бар через AppKit. Без блокировки главного потока.

    Интерфейс: start(initial_state), update_status(state), stop()
    """

    def __init__(self, loop=None, on_quit=None):
        self._loop = loop
        self._on_quit = on_quit
        self._status_item = None
        self._menu_handler = _MenuHandler.alloc().initWithQuitCallback_(self._on_quit)

    def _ensure_created(self, initial_state: str):
        if self._status_item is not None:
            return
        bar = NSStatusBar.systemStatusBar()
        self._status_item = bar.statusItemWithLength_(NSVariableStatusItemLength)
        # Кнопка статуса
        btn = self._status_item.button()
        btn.setTitle_(f"{STATUS_EMOJI.get(initial_state, '⚪️')} Nexy")

        # Меню
        menu = NSMenu.alloc().init()
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit Nexy", "quit:", ""
        )
        quit_item.setTarget_(self._menu_handler)
        menu.addItem_(quit_item)
        self._status_item.setMenu_(menu)

    def start(self, initial_state: str = "SLEEPING"):
        try:
            self._ensure_created(initial_state)
        except Exception:
            pass

    def update_status(self, state_name: str):
        try:
            if self._status_item is None:
                self._ensure_created(state_name)
            btn = self._status_item.button()
            btn.setTitle_(f"{STATUS_EMOJI.get(state_name, '⚪️')} Nexy")
        except Exception:
            pass

    def stop(self):
        try:
            if self._status_item is not None:
                NSStatusBar.systemStatusBar().removeStatusItem_(self._status_item)
                self._status_item = None
        except Exception:
            pass

