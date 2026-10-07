from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QMessageBox,
    QSlider,
    QSpinBox,
    QWidget,
)

from .config import Settings
from .hotkey import Hotkey
from .theme import dark_title_bar


def _spin(lo: int, hi: int, value: int, suffix: str = "") -> QSpinBox:
    sb = QSpinBox()
    sb.setRange(lo, hi)
    sb.setValue(value)
    if suffix:
        sb.setSuffix(suffix)
    sb.setFixedWidth(120)
    return sb


def _range_row(a: QSpinBox, b: QSpinBox = None) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(a)
    if b is not None:
        lay.addWidget(QLabel("~"))
        lay.addWidget(b)
    lay.addStretch(1)
    return w


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None, on_opacity=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self._on_opacity = on_opacity
        s = settings

        self.key_min = _spin(1, 10000, s.key_delay_min, " ms")
        self.key_max = _spin(1, 10000, s.key_delay_max, " ms")
        self.line_min = _spin(0, 60000, s.line_delay_min, " ms")
        self.line_max = _spin(0, 60000, s.line_delay_max, " ms")
        self.typo_min = _spin(0, 1000, s.typos_min)
        self.typo_max = _spin(0, 1000, s.typos_max)
        self.countdown = _spin(0, 30, s.countdown, " s")
        self.hide = QCheckBox("Hide window while typing")
        self.hide.setChecked(s.hide_while_typing)
        self.stop_key_starts = QCheckBox("F9 also starts typing the clipboard (F9 = start / stop)")
        self.stop_key_starts.setChecked(s.stop_key_starts)
        self.keep_text = QCheckBox("Keep text after typing finishes")
        self.keep_text.setChecked(s.keep_text)
        self.skip_indent = QCheckBox("Skip leading spaces after Enter (for auto-indenting editors)")
        self.skip_indent.setChecked(s.skip_indent)
        self.hotkey = QKeySequenceEdit(QKeySequence(s.start_hotkey))
        self.hotkey.setMaximumSequenceLength(1)
        self.hotkey.setClearButtonEnabled(True)
        self.hotkey.setFixedWidth(200)
        self.hotkey.setToolTip("Click, then press the key combination. Clear it to disable.")
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(30, 100)
        self.opacity.setValue(s.opacity)
        if on_opacity:
            self.opacity.valueChanged.connect(lambda v: on_opacity(v / 100))

        form = QFormLayout(self)
        form.addRow("Typing speed (per key):", _range_row(self.key_min, self.key_max))
        form.addRow("Next line wait:", _range_row(self.line_min, self.line_max))
        form.addRow("Typos per 1000 chars:", _range_row(self.typo_min, self.typo_max))
        form.addRow("Start countdown:", _range_row(self.countdown))
        form.addRow("Type clipboard hotkey:", _range_row(self.hotkey))
        form.addRow("Window opacity:", self.opacity)
        form.addRow(self.hide)
        form.addRow(self.stop_key_starts)
        form.addRow(self.keep_text)
        form.addRow(self.skip_indent)
        hint = QLabel("Hotkeys:  F8 = pause / resume,  F9 = stop")
        hint.setStyleSheet("color: #7f838a;")
        form.addRow(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self._restore_defaults)
        form.addRow(buttons)

    def showEvent(self, event) -> None:
        dark_title_bar(self)
        super().showEvent(event)

    def _restore_defaults(self) -> None:
        d = Settings()
        self.key_min.setValue(d.key_delay_min)
        self.key_max.setValue(d.key_delay_max)
        self.line_min.setValue(d.line_delay_min)
        self.line_max.setValue(d.line_delay_max)
        self.typo_min.setValue(d.typos_min)
        self.typo_max.setValue(d.typos_max)
        self.countdown.setValue(d.countdown)
        self.opacity.setValue(d.opacity)
        self.hide.setChecked(d.hide_while_typing)
        self.keep_text.setChecked(d.keep_text)
        self.stop_key_starts.setChecked(d.stop_key_starts)
        self.skip_indent.setChecked(d.skip_indent)
        self.hotkey.setKeySequence(QKeySequence(d.start_hotkey))

    def _hotkey_text(self) -> str:
        return self.hotkey.keySequence().toString(QKeySequence.PortableText)

    def accept(self) -> None:
        text = self._hotkey_text()
        if text and Hotkey.parse(text) is None:
            QMessageBox.warning(
                self,
                "Hotkey",
                f'"{text}" can\'t be used as a hotkey.\n\n'
                "Use Ctrl / Shift / Alt / Win with a letter, digit or F-key "
                "(e.g. Ctrl+Shift+V), or a plain F-key.",
            )
            return
        super().accept()

    def result_settings(self) -> Settings:
        def ordered(a: QSpinBox, b: QSpinBox):
            return min(a.value(), b.value()), max(a.value(), b.value())

        kmin, kmax = ordered(self.key_min, self.key_max)
        lmin, lmax = ordered(self.line_min, self.line_max)
        tmin, tmax = ordered(self.typo_min, self.typo_max)
        return Settings(
            key_delay_min=kmin,
            key_delay_max=kmax,
            line_delay_min=lmin,
            line_delay_max=lmax,
            typos_min=tmin,
            typos_max=tmax,
            hide_while_typing=self.hide.isChecked(),
            keep_text=self.keep_text.isChecked(),
            stop_key_starts=self.stop_key_starts.isChecked(),
            skip_indent=self.skip_indent.isChecked(),
            countdown=self.countdown.value(),
            opacity=self.opacity.value(),
            start_hotkey=self._hotkey_text(),
        )
