"""Detects N quick left-clicks in the same spot (like a double/triple click)."""
import ctypes
import time
from typing import Callable

_user32 = ctypes.windll.user32
SM_CXDOUBLECLK, SM_CYDOUBLECLK = 36, 37


class MultiClickDetector:
    """Feed it pynput mouse events; calls `on_trigger` on release of the Nth click.

    Clicks count as one sequence when each comes within the Windows double-click
    time and distance of the previous one, so ordinary clicking won't trigger it.
    """

    def __init__(self, on_trigger: Callable[[], None]):
        self.on_trigger = on_trigger
        self.required = 0  # 0 = off
        self._count = 0
        self._last_time = 0.0
        self._last_pos = (0, 0)
        self._pending = False

    def press(self, x: int, y: int) -> None:
        if self.required < 2:
            return
        now = time.monotonic()
        max_gap = _user32.GetDoubleClickTime() / 1000.0
        dx = max(_user32.GetSystemMetrics(SM_CXDOUBLECLK), 4)
        dy = max(_user32.GetSystemMetrics(SM_CYDOUBLECLK), 4)
        lx, ly = self._last_pos
        if now - self._last_time <= max_gap and abs(x - lx) <= dx and abs(y - ly) <= dy:
            self._count += 1
        else:
            self._count = 1
        self._last_time, self._last_pos = now, (x, y)
        if self._count >= self.required:
            self._count = 0
            self._pending = True

    def release(self) -> None:
        if self._pending:
            self._pending = False
            self.on_trigger()
