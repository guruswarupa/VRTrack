"""Reusable widgets."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from ..processing import shape_axis
from . import theme


def label(text: str = "", *, muted=False, h1=False, h2=False, mono=False, wrap=False) -> QLabel:
    lb = QLabel(text)
    for k, v in (("muted", muted), ("h1", h1), ("h2", h2), ("mono", mono)):
        if v:
            lb.setProperty(k, True)
    lb.setWordWrap(wrap)
    return lb


class Card(QFrame):
    def __init__(self, title: str = "", subtitle: str = ""):
        super().__init__()
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 16, 18, 16)
        self.body.setSpacing(10)
        if title:
            self.body.addWidget(label(title, h2=True))
        if subtitle:
            self.body.addWidget(label(subtitle, muted=True, wrap=True))


class StatusChip(QWidget):
    """Small pill: coloured dot + text."""

    def __init__(self, text="", color=theme.MUTED):
        super().__init__()
        self._text, self._color = text, QColor(color)
        self.setFixedHeight(30)
        self.set(text, color)

    def set(self, text: str, color: str) -> None:
        self._text, self._color = text, QColor(color)
        fm = self.fontMetrics()
        self.setFixedWidth(fm.horizontalAdvance(text) + 44)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.setBrush(QColor(theme.SURFACE_2))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        p.setBrush(self._color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(15, r.height() / 2 + 0.5), 4.5, 4.5)
        p.setPen(QColor(theme.TEXT))
        p.drawText(QRectF(28, 0, r.width() - 30, r.height() + 1), Qt.AlignVCenter | Qt.AlignLeft, self._text)


class HeadView(QWidget):
    """Front view of a head: rotates with roll, nose dot shows yaw/pitch, whole head shifts with x/y."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(260, 260)
        self.pose = {k: 0.0 for k in ("yaw", "pitch", "roll", "x", "y", "z")}
        self.active = False

    def set_pose(self, pose: dict, active: bool) -> None:
        self.pose, self.active = pose, active
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base = min(w, h)
        col = QColor(theme.ACCENT if self.active else theme.MUTED)
        # reference rings
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.setBrush(Qt.NoBrush)
        for k in (0.46, 0.34):
            p.drawEllipse(QPointF(cx, cy), base * k, base * k)
        p.drawLine(QPointF(cx - base * 0.46, cy), QPointF(cx + base * 0.46, cy))
        p.drawLine(QPointF(cx, cy - base * 0.46), QPointF(cx, cy + base * 0.46))
        # head
        scale = max(0.7, min(1.4, 1 + self.pose["z"] / 60.0))
        p.save()
        p.translate(cx + self.pose["x"] * 3.0, cy - self.pose["y"] * 3.0)
        p.rotate(self.pose["roll"])
        p.scale(scale, scale)
        rx, ry = base * 0.19, base * 0.25
        p.setPen(QPen(col, 2.5))
        p.setBrush(QColor(col.red(), col.green(), col.blue(), 28))
        p.drawEllipse(QPointF(0, 0), rx, ry)
        # eyes follow yaw/pitch a little for depth
        ox = math.sin(math.radians(self.pose["yaw"])) * rx * 0.9
        oy = -math.sin(math.radians(self.pose["pitch"])) * ry * 0.9
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        for ex in (-rx * 0.38, rx * 0.38):
            p.drawEllipse(QPointF(ex + ox * 0.5, -ry * 0.2 + oy * 0.5), 4.5, 4.5)
        pen = QPen(col, 3, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(ox, oy - ry * 0.05), QPointF(ox * 1.1, oy + ry * 0.2))   # nose
        p.restore()
        # yaw / pitch arc labels
        p.setPen(QColor(theme.MUTED))
        f = QFont(self.font())
        f.setPointSize(9)
        p.setFont(f)
        p.drawText(QRectF(0, h - 22, w, 18), Qt.AlignCenter,
                   f"yaw {self.pose['yaw']:+.0f}°   pitch {self.pose['pitch']:+.0f}°   roll {self.pose['roll']:+.0f}°")


class AxisMeter(QWidget):
    """Horizontal centred bar: shows a value within +-range, with raw marker."""

    def __init__(self, name: str, unit: str, rng: float):
        super().__init__()
        self.name, self.unit, self.rng = name, unit, rng
        self.value = 0.0
        self.raw = 0.0
        self.setFixedHeight(30)

    def set_values(self, raw: float, out: float) -> None:
        self.raw, self.value = raw, out
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        label_w, val_w = 56, 120
        bar = QRectF(label_w, h / 2 - 4, w - label_w - val_w, 8)
        p.setPen(QColor(theme.MUTED))
        p.drawText(QRectF(0, 0, label_w, h), Qt.AlignVCenter, self.name)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.SURFACE_2))
        p.drawRoundedRect(bar, 4, 4)
        mid = bar.center().x()
        frac = max(-1.0, min(1.0, self.value / self.rng))
        p.setBrush(QColor(theme.ACCENT))
        fill = QRectF(min(mid, mid + frac * bar.width() / 2), bar.top(), abs(frac) * bar.width() / 2, bar.height())
        p.drawRoundedRect(fill, 4, 4)
        p.setPen(QPen(QColor(theme.MUTED), 1))
        p.drawLine(QPointF(mid, bar.top() - 3), QPointF(mid, bar.bottom() + 3))
        p.setPen(QColor(theme.TEXT))
        f = QFont("Cascadia Mono, Consolas, monospace")
        f.setPointSize(9)
        p.setFont(f)
        p.drawText(QRectF(w - val_w + 8, 0, val_w - 8, h), Qt.AlignVCenter | Qt.AlignRight,
                   f"{self.raw:+7.1f} → {self.value:+7.1f}")


class CurvePreview(QWidget):
    """Plots game output vs head input for one axis, using the real shaping function."""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(190)
        self.params = dict(sens=1.0, dead=1.0, vmax=90.0, curve=1.0, invert=False)
        self.live = None

    def set_params(self, **kw) -> None:
        self.params.update(kw)
        self.update()

    def set_live(self, value) -> None:
        self.live = value
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(34, 10, -10, -24)
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.setBrush(QColor(theme.SURFACE_2))
        p.drawRoundedRect(r, 8, 8)
        vmax = max(self.params["vmax"], 1.0)
        span = vmax * 1.2   # input range drawn
        for k in range(-2, 3):
            x = r.center().x() + k * r.width() / 4
            y = r.center().y() + k * r.height() / 4
            p.setPen(QPen(QColor(theme.BORDER), 1, Qt.DotLine))
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        # identity reference
        p.setPen(QPen(QColor(theme.MUTED), 1, Qt.DashLine))
        p.drawLine(QPointF(r.left(), r.bottom()), QPointF(r.right(), r.top()))
        path = QPainterPath()
        n = 160
        for i in range(n + 1):
            xin = -span + 2 * span * i / n
            yout = shape_axis(xin, self.params["sens"], self.params["dead"], vmax,
                              self.params["curve"], self.params["invert"])
            px = r.center().x() + xin / span * r.width() / 2
            py = r.center().y() - max(-span, min(span, yout)) / span * r.height() / 2
            (path.moveTo if i == 0 else path.lineTo)(px, py)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(theme.ACCENT), 2.5))
        p.drawPath(path)
        if self.live is not None:
            xin, yout = self.live
            px = r.center().x() + max(-span, min(span, xin)) / span * r.width() / 2
            py = r.center().y() - max(-span, min(span, yout)) / span * r.height() / 2
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.WARN))
            p.drawEllipse(QPointF(px, py), 5, 5)
        p.setPen(QColor(theme.MUTED))
        p.drawText(QRectF(0, self.height() - 20, self.width(), 18), Qt.AlignCenter, "head movement  →  game view")


class FloatSlider(QWidget):
    """Slider + spin box kept in sync; emits valueChanged(float)."""
    valueChanged = Signal(float)

    def __init__(self, lo: float, hi: float, step: float = 0.1, decimals: int = 2, suffix: str = ""):
        super().__init__()
        self._scale = 10 ** decimals
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(round(lo * self._scale), round(hi * self._scale))
        self.spin = QDoubleSpinBox()
        self.spin.setRange(lo, hi)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(decimals)
        self.spin.setSuffix(suffix)
        self.spin.setFixedWidth(92)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(self.slider, 1)
        lay.addWidget(self.spin)
        self.slider.valueChanged.connect(self._from_slider)
        self.spin.valueChanged.connect(self._from_spin)

    def _from_slider(self, v):
        val = v / self._scale
        self.spin.blockSignals(True)
        self.spin.setValue(val)
        self.spin.blockSignals(False)
        self.valueChanged.emit(val)

    def _from_spin(self, val):
        self.slider.blockSignals(True)
        self.slider.setValue(round(val * self._scale))
        self.slider.blockSignals(False)
        self.valueChanged.emit(val)

    def setValue(self, val: float) -> None:
        self.slider.blockSignals(True)
        self.spin.blockSignals(True)
        self.slider.setValue(round(val * self._scale))
        self.spin.setValue(val)
        self.slider.blockSignals(False)
        self.spin.blockSignals(False)

    def value(self) -> float:
        return self.spin.value()
