"""Dark theme for the whole app, including the Windows title bar."""
import ctypes
import sys

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget

BG = QColor("#1e1f22")
BASE = QColor("#2b2d30")
TEXT = QColor("#dfe1e5")
DIM = QColor("#7f838a")
ACCENT = QColor("#3574f0")


def apply_dark_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 11))
    p = QPalette()
    p.setColor(QPalette.Window, BG)
    p.setColor(QPalette.WindowText, TEXT)
    p.setColor(QPalette.Base, BASE)
    p.setColor(QPalette.AlternateBase, BG)
    p.setColor(QPalette.Text, TEXT)
    p.setColor(QPalette.Button, BASE)
    p.setColor(QPalette.ButtonText, TEXT)
    p.setColor(QPalette.ToolTipBase, BASE)
    p.setColor(QPalette.ToolTipText, TEXT)
    p.setColor(QPalette.PlaceholderText, DIM)
    p.setColor(QPalette.Highlight, ACCENT)
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.Link, ACCENT)
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, DIM)
    app.setPalette(p)
    app.setStyleSheet(
        """
        QToolTip { border: 1px solid #43454a; }
        QMenu { background: #2b2d30; border: 1px solid #43454a; }
        QMenu::item:selected { background: #3574f0; }
        QMenu::item:disabled { color: #7f838a; }
        """
    )


def dark_title_bar(widget: QWidget) -> None:
    """Ask Windows 10/11 to draw this window's title bar dark."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        value = ctypes.c_int(1)
        # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE (Win10 2004+), 19 on older builds.
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)
            ) == 0:
                break
    except Exception:
        pass
