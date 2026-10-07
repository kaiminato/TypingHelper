"""Global hotkey matching for the Windows low-level keyboard hook (used via pynput)."""
import ctypes
from typing import Optional

_user32 = ctypes.windll.user32

WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_KEYUP = 0x0101
WM_SYSKEYUP = 0x0105
LLKHF_INJECTED = 0x10

# modifier name -> virtual-key codes that count as that modifier
_MODIFIERS = {
    "ctrl": (0x11,),
    "shift": (0x10,),
    "alt": (0x12,),
    "win": (0x5B, 0x5C),
}
_ALIASES = {"control": "ctrl", "meta": "win"}  # Qt calls the Windows key "Meta"

_NAMED_KEYS = {
    "space": 0x20, "tab": 0x09, "backspace": 0x08, "return": 0x0D, "enter": 0x0D,
    "esc": 0x1B, "escape": 0x1B, "ins": 0x2D, "insert": 0x2D, "del": 0x2E, "delete": 0x2E,
    "home": 0x24, "end": 0x23, "pgup": 0x21, "pgdown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "pause": 0x13,
    ",": 0xBC, "-": 0xBD, ".": 0xBE, "/": 0xBF, ";": 0xBA, "=": 0xBB,
    "`": 0xC0, "[": 0xDB, "\\": 0xDC, "]": 0xDD, "'": 0xDE,
}


def _key_down(vk: int) -> bool:
    return bool(_user32.GetAsyncKeyState(vk) & 0x8000)


def modifiers_down() -> bool:
    return any(_key_down(vk) for vks in _MODIFIERS.values() for vk in vks)


class Hotkey:
    def __init__(self, mods: frozenset, vk: int):
        self.mods = mods
        self.vk = vk

    @classmethod
    def parse(cls, text: str) -> Optional["Hotkey"]:
        """Parse 'Ctrl+Shift+V' style text. Returns None if empty or not usable.

        A hotkey needs a modifier (or be an F-key), otherwise it would fire
        while the user types normally.
        """
        parts = [p.strip().lower() for p in text.split("+") if p.strip()]
        if not parts:
            return None
        *mod_parts, key = parts
        mods = set()
        for m in mod_parts:
            m = _ALIASES.get(m, m)
            if m not in _MODIFIERS:
                return None
            mods.add(m)

        is_fkey = key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24
        if is_fkey:
            vk = 0x70 + int(key[1:]) - 1
        elif len(key) == 1 and key.isascii() and key.isalnum():
            vk = ord(key.upper())
        elif key in _NAMED_KEYS:
            vk = _NAMED_KEYS[key]
        else:
            return None
        if not mods and not is_fkey:
            return None
        return cls(frozenset(mods), vk)

    def matches(self, vk: int) -> bool:
        """True if `vk` was just pressed with exactly this hotkey's modifiers held."""
        if vk != self.vk:
            return False
        for name, vks in _MODIFIERS.items():
            if any(_key_down(v) for v in vks) != (name in self.mods):
                return False
        return True
