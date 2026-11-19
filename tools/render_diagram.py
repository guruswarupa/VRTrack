"""Render docs/images/architecture.svg to a 2x PNG (needs PySide6; run on a machine with a normal font setup,
not QT_QPA_PLATFORM=offscreen, or the text renders as boxes)."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

root = Path(__file__).resolve().parents[1] / "docs" / "images"
app = QGuiApplication([])
renderer = QSvgRenderer(str(root / "architecture.svg"))
img = QImage(2400, 640, QImage.Format_ARGB32)
img.fill(Qt.transparent)
p = QPainter(img)
p.setRenderHint(QPainter.Antialiasing)
p.setRenderHint(QPainter.TextAntialiasing)
renderer.render(p)
p.end()
img.save(str(root / "architecture.png"))
print("wrote", root / "architecture.png")
