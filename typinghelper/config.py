import json
import os
from dataclasses import asdict, dataclass, fields


def config_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "TypingHelper")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "settings.json")


@dataclass
class Settings:
    key_delay_min: int = 80        # ms between keystrokes
    key_delay_max: int = 120
    line_delay_min: int = 1000     # ms pause after each Enter
    line_delay_max: int = 3000
    typos_min: int = 5             # typos per 1000 characters
    typos_max: int = 20
    hide_while_typing: bool = True
    skip_indent: bool = False      # drop leading whitespace after Enter (for auto-indenting editors)
    countdown: int = 3             # seconds before typing starts
    opacity: int = 100            # window opacity, percent

    @classmethod
    def load(cls) -> "Settings":
        try:
            with open(config_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self) -> None:
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
