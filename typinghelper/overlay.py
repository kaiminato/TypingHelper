"""Big translucent, click-through countdown number shown in the middle of the screen."""
from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
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
