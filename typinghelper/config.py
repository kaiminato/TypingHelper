import winreg
from dataclasses import dataclass, fields

REG_PATH = r"Software\TypingHelper"


@dataclass
class Settings:
    key_delay_min: int = 60        # ms between keystrokes
    key_delay_max: int = 90
    line_delay_min: int = 1000     # ms pause after each Enter
    line_delay_max: int = 3000
    typos_min: int = 5             # typos per 1000 characters
    typos_max: int = 20
    hide_while_typing: bool = True
    skip_indent: bool = False      # drop leading whitespace after Enter (for auto-indenting editors)
    countdown: int = 3             # seconds before typing starts
    opacity: int = 100             # window opacity, percent

    @classmethod
    def load(cls) -> "Settings":
        """Read from HKCU\\Software\\TypingHelper; missing or bad values keep their defaults."""
        s = cls()
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        except OSError:
            return s
        with key:
            for f in fields(cls):
                try:
                    value, kind = winreg.QueryValueEx(key, f.name)
                except OSError:
                    continue
                if kind == winreg.REG_DWORD:
                    setattr(s, f.name, bool(value) if f.type in (bool, "bool") else int(value))
        return s

    def save(self) -> None:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            for f in fields(self):
                winreg.SetValueEx(key, f.name, 0, winreg.REG_DWORD, int(getattr(self, f.name)))
