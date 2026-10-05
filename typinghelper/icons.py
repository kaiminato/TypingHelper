"""App / tray icon: a keyboard on a coloured rounded tile (colour = status)."""
import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPixmap

IDLE_COLOR = "#27ae60"
BUSY_COLOR = "#e74c3c"
_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def _paint(size: int, color: str) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 64, size / 64)  # draw on a 64x64 grid

    base = QColor(color)
    grad = QLinearGradient(0, 0, 0, 64)
    grad.setColorAt(0, base.lighter(125))
    grad.setColorAt(1, base.darker(115))
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawRoundedRect(QRectF(1, 1, 62, 62), 14, 14)

    # Keyboard body
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(QRectF(7, 15, 50, 36), 6, 6)

    # Keys are cut out in the tile colour
    p.setBrush(base.darker(110))
    key_w, gap = 6.8, 2.0
    for y in (20, 28.5):
        for k in range(5):
            p.drawRoundedRect(QRectF(11.5 + k * (key_w + gap), y, key_w, 6), 1.5, 1.5)
    p.drawRoundedRect(QRectF(18, 37.5, 28, 6.5), 1.5, 1.5)  # space bar
    p.end()
    return pm


def status_icon(color: str) -> QIcon:
    icon = QIcon()
    for s in _SIZES:
        icon.addPixmap(_paint(s, color))
    return icon


def save_ico(path: str) -> None:
    """Write a multi-size .ico for the .exe (used by build.bat)."""
    from PySide6.QtGui import QGuiApplication, QImageWriter

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841
    writer = QImageWriter(path, b"ico")
    # Qt's ICO writer stores one image; use the largest for best quality.
    if not writer.write(_paint(256, IDLE_COLOR).toImage()):
        raise RuntimeError(writer.errorString())


if __name__ == "__main__":
    save_ico(sys.argv[1] if len(sys.argv) > 1 else "icon.ico")
