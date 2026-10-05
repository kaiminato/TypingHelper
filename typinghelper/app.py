import sys

from pynput import keyboard
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .config import Settings
from .icons import BUSY_COLOR, IDLE_COLOR, status_icon
from .overlay import CountdownOverlay
from .settings_dialog import SettingsDialog
from .theme import apply_dark_theme, dark_title_bar
from .typer import TypingWorker

PAUSE_KEY = keyboard.Key.f8
STOP_KEY = keyboard.Key.f9


class Bridge(QObject):
    """Carries events from background threads into the Qt thread."""
    progress = Signal(int, int)
    finished = Signal(str)
    hotkey = Signal(str)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = Settings.load()
        self.worker = None
        self.hidden_by_us = False
        self.countdown_left = 0
        self.quitting = False

        self.bridge = Bridge()
        self.bridge.progress.connect(self._on_progress)
        self.bridge.finished.connect(self._on_finished)
        self.bridge.hotkey.connect(self._on_hotkey)

        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self._countdown_tick)

        self.icon_idle = status_icon(IDLE_COLOR)
        self.icon_busy = status_icon(BUSY_COLOR)
        self.overlay = CountdownOverlay()

        self._build_ui()
        self._build_tray()
        self._start_hotkeys()
        self._set_state("idle")

    # ---------- UI ----------
    def _build_ui(self) -> None:
        self.setWindowTitle("Typing Helper")
        self.setWindowIcon(self.icon_idle)
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setWindowOpacity(self.settings.opacity / 100)
        self.resize(420, 300)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Paste or write the text to type here…")

        self.status = QLabel()
        self.status.setStyleSheet("color: #7f838a;")

        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙")
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setStyleSheet("font-size: 16px;")
        self.settings_btn.clicked.connect(self.open_settings)

        self.start_btn = QPushButton("Start")
        self.start_btn.setMinimumWidth(90)
        self.start_btn.clicked.connect(self.toggle_start)

        bottom = QHBoxLayout()
        bottom.addWidget(self.status, 1)
        bottom.addWidget(self.settings_btn)
        bottom.addWidget(self.start_btn)

        lay = QVBoxLayout(self)
        lay.addWidget(self.editor)
        lay.addLayout(bottom)

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.icon_idle, self)
        menu = QMenu()
        self.act_show = QAction("Show / Hide", self, triggered=self.toggle_visible)
        self.act_start = QAction("Start", self, triggered=self.toggle_start)
        self.act_pause = QAction("Pause (F8)", self, triggered=self.toggle_pause)
        act_settings = QAction("Settings…", self, triggered=self.open_settings)
        act_quit = QAction("Quit", self, triggered=self.quit)
        for a in (self.act_show, self.act_start, self.act_pause, act_settings):
            menu.addAction(a)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.toggle_visible() if reason == QSystemTrayIcon.Trigger else None
        )
        self.tray.show()

    def _start_hotkeys(self) -> None:
        def on_press(key):
            if key == PAUSE_KEY:
                self.bridge.hotkey.emit("pause")
            elif key == STOP_KEY:
                self.bridge.hotkey.emit("stop")

        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.daemon = True
        self.listener.start()

    # ---------- state ----------
    def _set_state(self, state: str, msg: str = "") -> None:
        self.state = state
        busy = state != "idle"
        icon = self.icon_busy if busy else self.icon_idle
        self.tray.setIcon(icon)
        self.setWindowIcon(icon)
        self.start_btn.setText("Stop" if busy else "Start")
        self.act_start.setText("Stop (F9)" if busy else "Start")
        self.act_pause.setEnabled(state in ("typing", "paused"))
        self.act_pause.setText("Resume (F8)" if state == "paused" else "Pause (F8)")
        self.editor.setReadOnly(busy)
        self.settings_btn.setEnabled(not busy)
        default = {
            "idle": "Idle",
            "countdown": "Starting…",
            "typing": "Typing…  (F8 pause, F9 stop)",
            "paused": "Paused  (F8 resume, F9 stop)",
        }[state]
        text = msg or default
        self.status.setText(text)
        self.tray.setToolTip(f"Typing Helper — {text}")

    # ---------- actions ----------
    def toggle_visible(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show_window()

    def show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_start(self) -> None:
        if self.state == "idle":
            self.start()
        else:
            self.stop()

    def start(self) -> None:
        text = self.editor.toPlainText()
        if not text:
            self._set_state("idle", "Nothing to type.")
            return
        self.hidden_by_us = False
        if self.settings.hide_while_typing and self.isVisible():
            self.hide()
            self.hidden_by_us = True
        self.countdown_left = self.settings.countdown
        self._set_state("countdown")
        self._countdown_tick(first=True)
        if self.state == "countdown" and self.countdown_left >= 0:
            self.countdown_timer.start()

    def _countdown_tick(self, first: bool = False) -> None:
        if not first:
            self.countdown_left -= 1
        if self.countdown_left > 0:
            self._set_state(
                "countdown", f"Starting in {self.countdown_left}…  click into the target window"
            )
            self.overlay.show_number(self.countdown_left)
            return
        self.countdown_timer.stop()
        self.overlay.stop()
        self.countdown_left = -1
        if self.isVisible() and self.isActiveWindow():
            self._finish_ui("Focus is on Typing Helper — click into the target window first.")
            return
        self.worker = TypingWorker(
            self.editor.toPlainText(),
            self.settings,
            self.bridge.progress.emit,
            self.bridge.finished.emit,
        )
        self._set_state("typing")
        self.worker.start()

    def stop(self) -> None:
        if self.state == "countdown":
            self.countdown_timer.stop()
            self.overlay.stop()
            self._finish_ui("Cancelled.")
        elif self.worker:
            self.worker.stop()

    def toggle_pause(self) -> None:
        if self.worker and self.state in ("typing", "paused"):
            paused = self.worker.toggle_pause()
            self._set_state("paused" if paused else "typing")

    def open_settings(self) -> None:
        if self.state != "idle":
            return
        previous_opacity = self.windowOpacity()
        dlg = SettingsDialog(self.settings, self, on_opacity=self.setWindowOpacity)
        if dlg.exec():
            self.settings = dlg.result_settings()
            self.settings.save()
            self.setWindowOpacity(self.settings.opacity / 100)
        else:
            self.setWindowOpacity(previous_opacity)

    def quit(self) -> None:
        self.quitting = True
        if self.worker:
            self.worker.stop()
        self.listener.stop()
        self.tray.hide()
        QApplication.quit()

    # ---------- callbacks ----------
    def _on_hotkey(self, name: str) -> None:
        if name == "stop" and self.state != "idle":
            self.stop()
        elif name == "pause":
            self.toggle_pause()

    def _on_progress(self, done: int, total: int) -> None:
        if self.state == "typing":
            pct = done * 100 // max(total, 1)
            self.status.setText(f"Typing {done}/{total} ({pct}%)  F8 pause, F9 stop")
            self.tray.setToolTip(f"Typing Helper — typing {pct}%")

    def _on_finished(self, reason: str) -> None:
        self.worker = None
        self._finish_ui(reason[:1].upper() + reason[1:] + ("" if reason.startswith("error") else "."))

    def _finish_ui(self, msg: str) -> None:
        self._set_state("idle", msg)
        if self.hidden_by_us:
            self.hidden_by_us = False
            self.show_window()

    def showEvent(self, event) -> None:
        dark_title_bar(self)
        super().showEvent(event)

    def closeEvent(self, event) -> None:
        if self.quitting:
            event.accept()
            return
        event.ignore()
        self.hide()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apply_dark_theme(app)
    win = MainWindow()
    win.show()
    return app.exec()
