"""Builds the real window offscreen and drives it with real packets (skipped if PySide6 is missing)."""
import os
import socket
import time

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from vrtrack import protocol as P  # noqa: E402
from vrtrack.controller import Controller  # noqa: E402
from vrtrack.settings import AppSettings  # noqa: E402
from vrtrack.ui import theme  # noqa: E402
from vrtrack.ui.app import MainWindow  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(theme.STYLESHEET)
    return a


def test_all_pages_render_and_react_to_live_data(app, tmp_path, monkeypatch):
    monkeypatch.setenv("VRTRACK_HOME", str(tmp_path))
    c = Controller(AppSettings(), data_port=0, control_port=0)
    c.start()
    try:
        w = MainWindow(c)
        w.show()
        dport = c.rx._socks[0].getsockname()[1]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for i in range(1, 30):
            s.sendto(P.TrackingPacket(i, i, 10, 5, 0, 0, 0, 0, confidence=0.9,
                                      flags=P.FLAG_TRACKING).pack(), ("127.0.0.1", dport))
            time.sleep(0.01)
        for k in range(4):
            w._goto(k)
            for _ in range(5):
                app.processEvents()
            assert not w.grab().isNull()
        dash = w.pages[0]
        assert "Phone" in dash.chip_phone._text and "Face" in dash.chip_face._text
        w.close()
    finally:
        c.stop()
