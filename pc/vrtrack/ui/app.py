"""Main window, tray icon and GUI entry point."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QStackedWidget,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..controller import Controller
from ..settings import AppSettings
from . import theme
from .pages import AboutPage, DashboardPage, SetupPage, TuningPage
from .widgets import label


def make_icon() -> QIcon:
    """The VRTrack app icon (bundled with the package; also used for the tray)."""
    path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
    return QIcon(str(path)) if path.exists() else QIcon()


class MainWindow(QMainWindow):
    NAV = (("Dashboard", DashboardPage), ("Tuning", TuningPage), ("Setup", SetupPage), ("About", AboutPage))

    def __init__(self, controller: Controller):
        super().__init__()
        self.c = controller
        self.setWindowTitle("VRTrack")
        self.setWindowIcon(make_icon())
        self.resize(1080, 720)
        self.setMinimumSize(900, 620)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(200)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 18, 14, 14)
        sl.setSpacing(4)
        sl.addWidget(label("VRTrack", h2=True))
        sl.addWidget(label("Head tracking for OpenTrack", muted=True))
        sl.addSpacing(18)
        self.stack = QStackedWidget()
        self.pages = []
        self.nav = []
        for i, (name, cls) in enumerate(self.NAV):
            page = cls(controller)
            self.pages.append(page)
            self.stack.addWidget(page)
            b = QToolButton()
            b.setObjectName("nav")
            b.setText(name)
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.setToolButtonStyle(Qt.ToolButtonTextOnly)
            b.setSizePolicy(b.sizePolicy().horizontalPolicy(), b.sizePolicy().verticalPolicy())
            b.setMinimumWidth(170)
            b.clicked.connect(lambda _=False, k=i: self.stack.setCurrentIndex(k))
            sl.addWidget(b)
            self.nav.append(b)
        self.nav[0].setChecked(True)
        sl.addStretch(1)
        self.foot = label(f"v{__version__}", muted=True)
        sl.addWidget(self.foot)
        h.addWidget(side)
        h.addWidget(self.stack, 1)

        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.c.recenter)
        for i in range(4):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda k=i: self._goto(k))

        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(make_icon(), self)
            m = QMenu()
            for text, fn in (("Show VRTrack", self._show), ("Recenter", self.c.recenter)):
                a = QAction(text, m)
                a.triggered.connect(fn)
                m.addAction(a)
            self.act_pause = QAction("Pause output", m, checkable=True)
            self.act_pause.toggled.connect(self.c.set_paused)
            m.addAction(self.act_pause)
            m.addSeparator()
            q = QAction("Quit", m)
            q.triggered.connect(self._quit)
            m.addAction(q)
            self.tray.setContextMenu(m)
            self.tray.activated.connect(lambda r: self._show() if r == QSystemTrayIcon.Trigger else None)
            self.tray.show()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)
        self._quitting = False

    def _goto(self, k: int) -> None:
        self.nav[k].setChecked(True)
        self.stack.setCurrentIndex(k)

    def _tick(self) -> None:
        s = self.c.status()
        cur = self.pages[self.stack.currentIndex()]
        cur.refresh(s) if hasattr(cur, "refresh") else None
        if self.tray:
            self.tray.setToolTip(f"VRTrack — {'tracking' if s.face else 'waiting'}")

    def _show(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        self._quitting = True
        self.close()

    def closeEvent(self, e):
        if self.c.settings.minimize_to_tray and self.tray and not self._quitting:
            self.hide()
            e.ignore()
            return
        self.timer.stop()
        self.c.stop()
        if self.tray:
            self.tray.hide()
        e.accept()
        QApplication.quit()


def run_gui(args) -> int:
    app = QApplication(sys.argv[:1])
    app.setApplicationName("VRTrack")
    app.setStyleSheet(theme.STYLESHEET)
    settings = AppSettings.load()
    if getattr(args, "profile", None):
        settings.profile = args.profile
    settings.opentrack_host = getattr(args, "opentrack_host", None) or settings.opentrack_host
    settings.opentrack_port = getattr(args, "opentrack_port", None) or settings.opentrack_port
    c = Controller(settings)
    c.start()
    w = MainWindow(c)
    if getattr(args, "minimized", False) or settings.start_minimized:
        if w.tray:
            pass                 # lives in the tray
        else:
            w.showMinimized()
    else:
        w.show()
    return app.exec()
