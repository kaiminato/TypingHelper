"""Big translucent, click-through countdown number shown in the middle of the screen."""
from PySide6.QtCore import QEasingCurve, QRect, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

SIZE = 320


class CountdownOverlay(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.resize(SIZE, SIZE)
        self.number = 0
        self.phase = 0.0  # 0 -> 1 over each second

        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(950)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._on_anim)

    def show_number(self, n: int) -> None:
        self.number = n
        if not self.isVisible():
            # Centre on the screen the mouse is on (where the target window likely is).
            screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
            self.move(screen.geometry().center() - self.rect().center())
            self.show()
        self.anim.stop()
        self.anim.start()

    def stop(self) -> None:
        self.anim.stop()
        self.hide()

    def _on_anim(self, v) -> None:
        self.phase = float(v)
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        fade = 1.0 - 0.55 * self.phase          # number fades a little each second
        scale = 1.15 - 0.15 * self.phase        # and settles from slightly larger

        # Soft dark disc behind the number
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, int(110 * fade)))
        r = SIZE * 0.42 * scale
        p.drawEllipse(QRectF(SIZE / 2 - r, SIZE / 2 - r, 2 * r, 2 * r))

        # Outlined number
        font = QFont("Segoe UI", int(150 * scale), QFont.Bold)
        path = QPainterPath()
        path.addText(0, 0, font, str(self.number))
        br = path.boundingRect()
        path.translate(SIZE / 2 - br.center().x(), SIZE / 2 - br.center().y())
        p.setPen(QPen(QColor(0, 0, 0, int(160 * fade)), 6))
        p.setBrush(QColor(255, 255, 255, int(230 * fade)))
        p.drawPath(path)

        # Hint
        p.setPen(QColor(255, 255, 255, int(170 * fade)))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(QRectF(0, SIZE - 52, SIZE, 20), Qt.AlignCenter, "F9 to cancel")
        p.end()


class ProgressBadge(QWidget):
    """Small translucent, click-through "42%" bubble shown just above the tray icon."""

    W, H = 84, 40

    def __init__(self):
        super().__init__(
            None,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.resize(self.W, self.H)
        self.percent = 0
        self.paused = False

    def show_progress(self, percent: int, anchor: QRect, paused: bool = False) -> None:
        self.percent = max(0, min(100, percent))
        self.paused = paused
        self._place(anchor)
        if not self.isVisible():
            self.show()
        self.update()

    def _place(self, icon: QRect) -> None:
        """Centre above the tray icon (below it if the taskbar is at the top)."""
        screen = None
        if icon.isValid() and not icon.isEmpty():
            screen = QGuiApplication.screenAt(icon.center())
        screen = screen or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        if screen.geometry().contains(icon.center()) and not icon.isEmpty():
            x = icon.center().x() - self.W // 2
            y = icon.top() - self.H - 6
            if y < avail.top():  # taskbar at the top of the screen
                y = icon.bottom() + 6
        else:  # icon hidden in the overflow area: use the bottom-right corner
            x = avail.right() - self.W - 12
            y = avail.bottom() - self.H - 12
        x = max(avail.left() + 4, min(x, avail.right() - self.W - 4))
        y = max(avail.top() + 4, min(y, avail.bottom() - self.H - 4))
        self.move(x, y)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0.5, 0.5, self.W - 1, self.H - 1)
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.setBrush(QColor(20, 21, 24, 200))
        p.drawRoundedRect(rect, 9, 9)

        # Progress bar along the bottom
        bar = QRectF(8, self.H - 8, self.W - 16, 3)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 45))
        p.drawRoundedRect(bar, 1.5, 1.5)
        p.setBrush(QColor("#f39c12") if self.paused else QColor("#e74c3c"))
        p.drawRoundedRect(QRectF(bar.x(), bar.y(), bar.width() * self.percent / 100, 3), 1.5, 1.5)

        # Orange text + bar while paused
        p.setPen(QColor("#f39c12") if self.paused else QColor(255, 255, 255, 235))
        p.setFont(QFont("Segoe UI", 12, QFont.Bold))
        p.drawText(QRectF(0, 2, self.W, self.H - 10), Qt.AlignCenter, f"{self.percent}%")
        p.end()
