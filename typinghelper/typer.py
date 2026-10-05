"""Background worker that types text like a human, with jitter and typos."""
import random
import threading
import time
import unicodedata
from typing import Callable, Optional

from pynput.keyboard import Controller, Key

from .config import Settings

# US QWERTY rows with their horizontal offset (in key widths) from the left edge.
_ROWS = [
    ("`1234567890-=", 0.0),
    ("qwertyuiop[]\\", 1.5),
    ("asdfghjkl;'", 1.75),
    ("zxcvbnm,./", 2.25),
]


def _build_neighbors() -> dict:
    pos = {}
    for r, (row, offset) in enumerate(_ROWS):
        for c, ch in enumerate(row):
            pos[ch] = (r, offset + c)
    neighbors = {}
    for ch, (r, x) in pos.items():
        near = []
        for other, (r2, x2) in pos.items():
            if other == ch:
                continue
            if (r2 == r and abs(x2 - x) == 1) or (abs(r2 - r) == 1 and abs(x2 - x) < 1):
                near.append(other)
        # Only letters/digits make convincing typos.
        neighbors[ch] = [n for n in near if n.isalnum()]
    return {k: v for k, v in neighbors.items() if k.isalnum() and v}


NEIGHBORS = _build_neighbors()


class TypingWorker:
    """Types `text` into the focused window on a background thread.

    Callbacks are invoked from the worker thread; pass Qt signal `.emit`s.
    """

    def __init__(
        self,
        text: str,
        settings: Settings,
        on_progress: Callable[[int, int], None],
        on_finished: Callable[[str], None],
    ):
        self.text = text.replace("\r\n", "\n").replace("\r", "\n")
        self.s = settings
        self.on_progress = on_progress
        self.on_finished = on_finished
        self.kb = Controller()
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.skipped = 0

    # ----- control -----
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def toggle_pause(self) -> bool:
        if self._paused.is_set():
            self._paused.clear()
        else:
            self._paused.set()
        return self._paused.is_set()

    @property
    def paused(self) -> bool:
        return self._paused.is_set()

    # ----- timing helpers -----
    def _sleep_ms(self, ms: float) -> bool:
        """Interruptible sleep that also honours pause. Returns False if stopped."""
        remaining = ms / 1000.0
        while True:
            if self._stop.is_set():
                return False
            if self._paused.is_set():
                self._stop.wait(0.05)
                continue
            if remaining <= 0:
                return True
            step = min(remaining, 0.02)
            t0 = time.perf_counter()
            self._stop.wait(step)
            remaining -= time.perf_counter() - t0

    def _key_delay(self, factor: float = 1.0) -> bool:
        s = self.s
        return self._sleep_ms(random.uniform(s.key_delay_min, s.key_delay_max) * factor)

    # ----- key output -----
    def _tap(self, key) -> None:
        self.kb.press(key)
        self.kb.release(key)

    def _type_char(self, ch: str) -> None:
        if ch == "\t":
            self._tap(Key.tab)
            return
        # Invisible control characters (form feed, NUL, ...) have no key; skip them.
        if unicodedata.category(ch) == "Cc":
            self.skipped += 1
            return
        # Keys on the current layout are sent as real key presses; anything else
        # (accents, CJK, emoji, smart quotes) is sent as a Unicode character.
        try:
            self.kb.type(ch)
        except Exception:
            self.skipped += 1

    def _typo(self, i: int) -> bool:
        """Type a wrong neighbouring key (maybe a couple more chars), notice, backspace."""
        ch = self.text[i]
        wrong = random.choice(NEIGHBORS[ch.lower()])
        if ch.isupper():
            wrong = wrong.upper()
        typed = [wrong]
        # Sometimes the mistake is only noticed after a character or two.
        if random.random() < 0.3:
            for nxt in self.text[i + 1 : i + 1 + random.randint(1, 2)]:
                if nxt in "\n\t":
                    break
                typed.append(nxt)

        for c in typed:
            self._type_char(c)
            if not self._key_delay():
                return False
        # Reaction time before correcting.
        if not self._sleep_ms(random.uniform(150, 450)):
            return False
        for _ in typed:
            self._tap(Key.backspace)
            if not self._key_delay(0.7):
                return False
        return self._sleep_ms(random.uniform(50, 200))

    # ----- main loop -----
    def _run(self) -> None:
        reason = "done"
        try:
            reason = "done" if self._type_all() else "stopped"
            if self.skipped:
                reason += f" ({self.skipped} untypable char(s) skipped)"
        except Exception as e:  # keep the UI alive whatever happens
            reason = f"error: {e}"
        finally:
            self.on_finished(reason)

    def _type_all(self) -> bool:
        s, text = self.s, self.text
        n = len(text)
        typo_rate = random.uniform(s.typos_min, s.typos_max) / 1000.0
        i = 0
        while i < n:
            if not self._sleep_ms(0):
                return False
            ch = text[i]

            if ch == "\n":
                self._tap(Key.enter)
                i += 1
                if s.skip_indent:
                    while i < n and text[i] in " \t":
                        i += 1
                self.on_progress(i, n)
                if not self._sleep_ms(random.uniform(s.line_delay_min, s.line_delay_max)):
                    return False
                continue

            if ch.lower() in NEIGHBORS and random.random() < typo_rate:
                if not self._typo(i):
                    return False

            self._type_char(ch)
            i += 1
            self.on_progress(i, n)
            if not self._key_delay():
                return False
        return True
