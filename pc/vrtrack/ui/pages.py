"""Application pages: Dashboard, Tuning, Setup, About."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from .. import protocol as P
from ..controller import Controller, local_ips
from ..profiles import AXES
from . import theme
from .widgets import AxisMeter, Card, CurvePreview, FloatSlider, HeadView, StatusChip, label

AXIS_LABELS = {"yaw": "Yaw (turn left / right)", "pitch": "Pitch (look up / down)",
               "roll": "Roll (tilt head)", "x": "X (lean left / right)",
               "y": "Y (move up / down)", "z": "Z (lean forward / back)"}


def _page() -> tuple[QWidget, QVBoxLayout]:
    w = QWidget()
    w.setObjectName("page")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(28, 24, 28, 24)
    lay.setSpacing(16)
    return w, lay


def _header(title: str, subtitle: str) -> QVBoxLayout:
    box = QVBoxLayout()
    box.setSpacing(2)
    box.addWidget(label(title, h1=True))
    box.addWidget(label(subtitle, muted=True))
    return box


def _scroll(inner: QWidget) -> QScrollArea:
    s = QScrollArea()
    s.setWidgetResizable(True)
    s.setWidget(inner)
    s.setFrameShape(QScrollArea.NoFrame)
    s.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    s.viewport().setAutoFillBackground(False)
    inner.setAutoFillBackground(False)
    return s


# --------------------------------------------------------------------------------------- Dashboard
class DashboardPage(QWidget):
    def __init__(self, c: Controller):
        super().__init__()
        self.c = c
        w, lay = _page()
        top = QHBoxLayout()
        top.addLayout(_header("Dashboard", "Live tracking from your phone"), 1)
        self.chip_phone = StatusChip("Waiting for phone", theme.WARN)
        self.chip_face = StatusChip("No face", theme.MUTED)
        self.chip_rate = StatusChip("0 Hz", theme.MUTED)
        for chip in (self.chip_phone, self.chip_face, self.chip_rate):
            top.addWidget(chip)
        lay.addLayout(top)

        row = QHBoxLayout()
        row.setSpacing(16)
        card = Card("Head")
        self.head = HeadView()
        card.body.addWidget(self.head, 1)
        row.addWidget(card, 4)

        card2 = Card("Axes", "Phone reading  →  value sent to OpenTrack")
        self.meters: dict[str, AxisMeter] = {}
        for a in AXES:
            unit = "°" if a in ("yaw", "pitch", "roll") else "cm"
            m = AxisMeter(a.capitalize(), unit, 60.0 if unit == "°" else 15.0)
            self.meters[a] = m
            card2.body.addWidget(m)
        self.stats = label("", muted=True, mono=True)
        card2.body.addSpacing(6)
        card2.body.addWidget(self.stats)
        card2.body.addStretch(1)
        row.addWidget(card2, 5)
        lay.addLayout(row, 1)

        actions = QHBoxLayout()
        self.btn_center = QPushButton("Recenter")
        self.btn_center.setProperty("primary", True)
        self.btn_center.setToolTip("Use your current head position as the centre")
        self.btn_center.clicked.connect(c.recenter)
        self.btn_pause = QPushButton("Pause output")
        self.btn_pause.setCheckable(True)
        self.btn_pause.toggled.connect(self._pause)
        actions.addWidget(self.btn_center)
        actions.addWidget(self.btn_pause)
        actions.addStretch(1)
        self.hint = label("", muted=True)
        actions.addWidget(self.hint)
        lay.addLayout(actions)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(w)

    def _pause(self, on: bool) -> None:
        self.c.set_paused(on)
        self.btn_pause.setText("Resume output" if on else "Pause output")

    def refresh(self, s) -> None:
        if s.link == "connected":
            self.chip_phone.set(f"Phone {s.phone_addr}", theme.GOOD)
        else:
            self.chip_phone.set("Waiting for phone", theme.WARN)
        if s.paused:
            self.chip_face.set("Paused", theme.WARN)
        elif s.face:
            self.chip_face.set("Face tracked", theme.GOOD)
        else:
            self.chip_face.set("No face" if s.link == "connected" else "—", theme.MUTED)
        self.chip_rate.set(f"{s.rate_hz:.0f} Hz", theme.GOOD if s.rate_hz >= 15 else theme.WARN if s.rate_hz else theme.MUTED)
        p = self.c.proc.profile
        for a in AXES:
            self.meters[a].rng = max(p.max_value[a], 1.0)
            self.meters[a].set_values(s.raw[a], s.out[a])
        self.head.set_pose(s.out, s.face and not s.paused)
        eyes = ("open" if s.eyes_open else "blink") if s.eyes_enabled else "off"
        self.stats.setText(f"confidence {s.confidence:4.2f}   lost {s.lost}   late {s.late}\n"
                           f"gaze {s.gaze[0]:+.2f} {s.gaze[1]:+.2f}   eyes {eyes}")
        if s.link != "connected":
            self.hint.setText("Open VRTrack on the phone and tap Start tracking")
        elif not s.face and not s.paused:
            self.hint.setText("Phone connected, but it can't see your face")
        else:
            self.hint.setText("")


# --------------------------------------------------------------------------------------- Tuning
class TuningPage(QWidget):
    def __init__(self, c: Controller):
        super().__init__()
        self.c = c
        self._loading = False
        self._dirty = False
        w, lay = _page()
        lay.addLayout(_header("Tuning", "Per-game response. Changes apply instantly; Save keeps them."))

        bar = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.setMinimumWidth(240)
        self.combo.addItems(list(c.profiles))
        self.combo.setCurrentText(c.proc.profile.name)
        self.combo.currentTextChanged.connect(self._select)
        self.btn_save = QPushButton("Save")
        self.btn_save.setProperty("primary", True)
        self.btn_save.clicked.connect(self._save)
        btn_dup = QPushButton("Duplicate…")
        btn_dup.clicked.connect(self._duplicate)
        btn_del = QPushButton("Delete / reset")
        btn_del.setProperty("danger", True)
        btn_del.clicked.connect(self._delete)
        self.dirty_chip = StatusChip("Saved", theme.GOOD)
        for x in (label("Profile", muted=True), self.combo, self.btn_save, btn_dup, btn_del):
            bar.addWidget(x)
        bar.addStretch(1)
        bar.addWidget(self.dirty_chip)
        lay.addLayout(bar)

        body = QHBoxLayout()
        body.setSpacing(16)
        self.axes = QListWidget()
        self.axes.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for a in AXES:
            self.axes.addItem(AXIS_LABELS[a])
        self.axes.setCurrentRow(0)
        self.axes.currentRowChanged.connect(self._axis_changed)
        left = Card("Axis")
        left.body.addWidget(self.axes, 1)
        left.setFixedWidth(240)
        body.addWidget(left)

        right = QVBoxLayout()
        right.setSpacing(16)
        self.axis_card = Card("Yaw")
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        self.s_sens = FloatSlider(0.0, 5.0, 0.05, 2, "×")
        self.s_dead = FloatSlider(0.0, 20.0, 0.1, 1)
        self.s_max = FloatSlider(5.0, 180.0, 1.0, 0)
        self.c_inv = QCheckBox("Invert direction")
        form.addRow(label("Sensitivity", muted=True), self.s_sens)
        form.addRow(label("Dead zone", muted=True), self.s_dead)
        form.addRow(label("Maximum", muted=True), self.s_max)
        form.addRow("", self.c_inv)
        self.axis_card.body.addLayout(form)
        self.curve = CurvePreview()
        self.axis_card.body.addWidget(self.curve)
        right.addWidget(self.axis_card)

        feel = Card("Feel", "Applies to all axes of this profile")
        f2 = QFormLayout()
        f2.setHorizontalSpacing(18)
        f2.setVerticalSpacing(12)
        self.s_smooth = FloatSlider(0.0, 0.95, 0.05, 2)
        self.s_curve = FloatSlider(0.5, 3.0, 0.1, 1)
        f2.addRow(label("Smoothing", muted=True), self.s_smooth)
        f2.addRow(label("Response curve", muted=True), self.s_curve)
        feel.body.addLayout(f2)
        feel.body.addWidget(label("1.0 = linear. Higher values are calmer near the centre and stronger at the edges.",
                                  muted=True, wrap=True))
        right.addWidget(feel)

        eye = Card("Eye gaze", "Adds where you look to the view. Needs eye tracking enabled in the phone app.")
        f3 = QFormLayout()
        self.c_eye = QCheckBox("Add gaze to view")
        self.s_eye = FloatSlider(0.0, 60.0, 1.0, 0)
        f3.addRow(self.c_eye)
        f3.addRow(label("Strength (° at full gaze)", muted=True), self.s_eye)
        eye.body.addLayout(f3)
        right.addWidget(eye)
        right.addStretch(1)
        rw = QWidget()
        rw.setLayout(right)
        body.addWidget(_scroll(rw), 1)
        lay.addLayout(body, 1)

        for sl in (self.s_sens, self.s_dead, self.s_max, self.s_smooth, self.s_curve, self.s_eye):
            sl.valueChanged.connect(self._edited)
        for cb in (self.c_inv, self.c_eye):
            cb.toggled.connect(self._edited)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(w)
        self._load()

    @property
    def axis(self) -> str:
        return AXES[max(0, self.axes.currentRow())]

    def _load(self) -> None:
        self._loading = True
        p, a = self.c.proc.profile, self.axis
        self.axis_card.body.itemAt(0).widget().setText(AXIS_LABELS[a])
        self.s_sens.setValue(p.sensitivity[a])
        self.s_dead.setValue(p.deadzone[a])
        self.s_max.setValue(p.max_value[a])
        self.c_inv.setChecked(bool(p.invert[a]))
        self.s_smooth.setValue(p.smoothing)
        self.s_curve.setValue(p.curve)
        self.c_eye.setChecked(p.eye_tracking)
        self.s_eye.setValue(p.eye_sensitivity)
        self._loading = False
        self._update_curve()

    def _update_curve(self) -> None:
        p, a = self.c.proc.profile, self.axis
        self.curve.set_params(sens=p.sensitivity[a], dead=p.deadzone[a], vmax=p.max_value[a],
                              curve=p.curve, invert=bool(p.invert[a]))

    def _set_dirty(self, d: bool) -> None:
        self._dirty = d
        self.dirty_chip.set("Unsaved changes" if d else "Saved", theme.WARN if d else theme.GOOD)

    def _edited(self, *_):
        if self._loading:
            return
        p, a = self.c.proc.profile, self.axis
        p.sensitivity[a] = self.s_sens.value()
        p.deadzone[a] = self.s_dead.value()
        p.max_value[a] = self.s_max.value()
        p.invert[a] = self.c_inv.isChecked()
        p.smoothing = self.s_smooth.value()
        p.curve = self.s_curve.value()
        p.eye_tracking = self.c_eye.isChecked()
        p.eye_sensitivity = self.s_eye.value()
        self._set_dirty(True)
        self._update_curve()

    def _axis_changed(self, _):
        self._load()

    def _select(self, name: str) -> None:
        if name in self.c.profiles:
            self.c.select_profile(name)
            self._set_dirty(False)
            self._load()

    def _save(self) -> None:
        self.c.save_current()
        self._set_dirty(False)

    def _duplicate(self) -> None:
        name, ok = QInputDialog.getText(self, "Duplicate profile", "Name for the new profile:",
                                        text=f"{self.c.proc.profile.name} copy")
        if ok and name.strip():
            p = self.c.duplicate_profile(name)
            self.combo.blockSignals(True)
            self.combo.addItem(p.name)
            self.combo.setCurrentText(p.name)
            self.combo.blockSignals(False)
            self._select(p.name)

    def _delete(self) -> None:
        name = self.c.proc.profile.name
        if QMessageBox.question(self, "Delete / reset profile",
                                f"Delete '{name}'? Built-in profiles are reset to their defaults.") != QMessageBox.Yes:
            return
        self.c.delete_profile(name)
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItems(list(self.c.profiles))
        self.combo.setCurrentText(self.c.proc.profile.name)
        self.combo.blockSignals(False)
        self._set_dirty(False)
        self._load()

    def refresh(self, s) -> None:
        a = self.axis
        self.curve.set_live((s.raw[a] - self.c.proc.offset(a), s.out[a]) if s.face else None)


# --------------------------------------------------------------------------------------- Setup
class SetupPage(QWidget):
    def __init__(self, c: Controller):
        super().__init__()
        self.c = c
        w, lay = _page()
        lay.addLayout(_header("Setup", "Connect your phone and OpenTrack"))
        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setSpacing(16)

        steps = Card("Checklist")
        self.steps = []
        for text in ("Phone app connected to this PC", "Phone sees your face", "Tracking data is flowing (≥ 15 Hz)"):
            chip = StatusChip(text, theme.MUTED)
            self.steps.append(chip)
            steps.body.addWidget(chip)
        col.addWidget(steps)

        net = Card("This PC", "The phone finds this PC automatically. If it can't, type one of these addresses "
                              "into the phone app (Settings → PC address).")
        self.ip_box = QVBoxLayout()
        net.body.addLayout(self.ip_box)
        self._fill_ips()
        net.body.addWidget(label(f"Ports: UDP {P.DATA_PORT} (tracking) and UDP {P.CONTROL_PORT} (discovery). "
                                 "Allow them in your firewall for private networks.", muted=True, wrap=True))
        btn = QPushButton("Refresh addresses")
        btn.clicked.connect(self._fill_ips)
        net.body.addWidget(btn, 0, Qt.AlignLeft)
        col.addWidget(net)

        ot = Card("OpenTrack output", "In OpenTrack choose Input = “UDP over network” (port below), "
                                      "Output = “freetrack 2.0 Enhanced”, then press Start.")
        f = QFormLayout()
        self.host = QLineEdit(c.settings.opentrack_host)
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(c.settings.opentrack_port)
        f.addRow(label("Host", muted=True), self.host)
        f.addRow(label("Port", muted=True), self.port)
        ot.body.addLayout(f)
        self.host.editingFinished.connect(self._ot)
        self.port.valueChanged.connect(self._ot)
        row = QHBoxLayout()
        self.btn_test = QPushButton("Test OpenTrack output")
        self.btn_test.setToolTip("Sweeps the view left and right for 3 seconds so you can see OpenTrack react")
        self.btn_test.clicked.connect(self._test)
        row.addWidget(self.btn_test)
        row.addStretch(1)
        ot.body.addLayout(row)
        ot.body.addWidget(label("The test sends a manual left-right sweep to OpenTrack only. Tracking itself "
                                "always uses real camera data.", muted=True, wrap=True))
        col.addWidget(ot)

        beh = Card("Behaviour")
        self.c_center = QCheckBox("Centre automatically when tracking starts")
        self.c_center.setChecked(c.settings.auto_center)
        self.c_tray = QCheckBox("Keep running in the system tray when the window is closed")
        self.c_tray.setChecked(c.settings.minimize_to_tray)
        self.c_min = QCheckBox("Start minimised")
        self.c_min.setChecked(c.settings.start_minimized)
        for cb in (self.c_center, self.c_tray, self.c_min):
            beh.body.addWidget(cb)
            cb.toggled.connect(self._beh)
        col.addWidget(beh)
        col.addStretch(1)
        lay.addWidget(_scroll(inner), 1)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(w)

    def _fill_ips(self) -> None:
        while self.ip_box.count():
            it = self.ip_box.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        ips = local_ips() or ["(no network address found)"]
        for ip in ips:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(label(ip, mono=True))
            h.addStretch(1)
            b = QPushButton("Copy")
            b.clicked.connect(lambda _=False, v=ip: QGuiApplication.clipboard().setText(v))
            h.addWidget(b)
            self.ip_box.addWidget(row)

    def _ot(self, *_):
        self.c.set_opentrack_target(self.host.text(), self.port.value())

    def _test(self) -> None:
        self.c.output_test()
        self.btn_test.setEnabled(False)
        QTimer.singleShot(3200, lambda: self.btn_test.setEnabled(True))

    def _beh(self, *_):
        s = self.c.settings
        s.auto_center, s.minimize_to_tray, s.start_minimized = (
            self.c_center.isChecked(), self.c_tray.isChecked(), self.c_min.isChecked())
        s.save()

    def refresh(self, s) -> None:
        ok = (s.link == "connected", s.link == "connected" and s.face, s.rate_hz >= 15)
        for chip, good, text in zip(self.steps, ok, ("Phone app connected to this PC", "Phone sees your face",
                                                     "Tracking data is flowing (≥ 15 Hz)")):
            chip.set(text, theme.GOOD if good else theme.MUTED)


# --------------------------------------------------------------------------------------- About
class AboutPage(QWidget):
    def __init__(self, c: Controller):
        super().__init__()
        w, lay = _page()
        lay.addLayout(_header("About", f"VRTrack {__version__}"))
        card = Card("Phone head tracking for OpenTrack")
        card.body.addWidget(label(
            "Your phone's front camera tracks your head on the phone itself. Only pose numbers are sent over "
            "your local network to this app, which feeds OpenTrack. No video leaves the phone, there are no "
            "accounts, ads or telemetry, and nothing needs the internet.", wrap=True))
        card.body.addWidget(label(f"Network: UDP {P.DATA_PORT} (tracking), UDP {P.CONTROL_PORT} (discovery/ping). "
                                  f"Settings and profiles: ~/.vrtrack", muted=True, wrap=True))
        lay.addWidget(card)
        lay.addStretch(1)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(w)
