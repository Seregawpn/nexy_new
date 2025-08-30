import threading
from typing import Optional, Callable

from PIL import Image, ImageDraw
import pystray


class TrayController:
    """
    Контроллер иконки в меню-баре macOS через pystray.

    - Иконка меняется в зависимости от статуса (цвет кружка)
    - Меню содержит пункт "Quit Nexy" для корректного выхода
    - Запускается неблокирующе через run_detached()
    """

    def __init__(self, loop, on_quit: Optional[Callable] = None):
        self._loop = loop
        self._on_quit = on_quit
        self._icon: Optional[pystray.Icon] = None
        self._lock = threading.Lock()

        # Предсоздаём иконки
        self._icons = {
            "SLEEPING": self._create_dot_icon((160, 160, 160)),  # gray
            "LISTENING": self._create_dot_icon((46, 204, 113)),  # green
            "IN_PROCESS": self._create_dot_icon((52, 152, 219)),  # blue
            "DEFAULT": self._create_dot_icon((127, 127, 127)),
        }

        self._menu = pystray.Menu(
            pystray.MenuItem("Open Nexy", self._noop, default=False),
            pystray.MenuItem("Quit Nexy", self._handle_quit, default=False)
        )

    def start(self, initial_state: str = "SLEEPING"):
        with self._lock:
            if self._icon is not None:
                return
            icon_image = self._icons.get(initial_state, self._icons["DEFAULT"])  # type: ignore
            self._icon = pystray.Icon(
                name="Nexy",
                icon=icon_image,
                title=f"Nexy: {initial_state}",
                menu=self._menu
            )
            # Неблокирующий запуск в отдельном потоке
            self._icon.run_detached()

    def update_status(self, state_name: str):
        with self._lock:
            if not self._icon:
                return
            img = self._icons.get(state_name, self._icons["DEFAULT"])  # type: ignore
            try:
                self._icon.icon = img
                self._icon.title = f"Nexy: {state_name}"
            except Exception:
                pass

    def stop(self):
        with self._lock:
            try:
                if self._icon:
                    self._icon.stop()
            finally:
                self._icon = None

    def _handle_quit(self, icon, item):  # pystray callback из другого потока
        if callable(self._on_quit):
            try:
                # Безопасно планируем коллбек на asyncio loop
                if self._loop:
                    self._loop.call_soon_threadsafe(self._on_quit)
                else:
                    self._on_quit()
            except Exception:
                pass

    @staticmethod
    def _noop(*args, **kwargs):
        return

    @staticmethod
    def _create_dot_icon(rgb_color, size: int = 18) -> Image.Image:
        # Простой кружок
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        radius = size // 2 - 1
        center = (size // 2, size // 2)
        bbox = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
        draw.ellipse(bbox, fill=rgb_color + (255,), outline=(60, 60, 60, 255))
        return img


