import time

import pytest

from vrtrack import protocol as P
from vrtrack.controller import Controller
from vrtrack.settings import AppSettings


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("VRTRACK_HOME", str(tmp_path))
    return tmp_path


def pkt(seq, yaw=0.0, flags=P.FLAG_TRACKING):
    return P.TrackingPacket(seq, seq, yaw, 0, 0, 0, 0, 0, flags=flags)


def test_settings_roundtrip_and_validation(home):
    s = AppSettings.load()
    assert s.opentrack_port == 4242 and s.auto_center
    s.opentrack_port = 5000
    s.minimize_to_tray = True
    s.save()
    t = AppSettings.load()
    assert t.opentrack_port == 5000 and t.minimize_to_tray
    AppSettings.path().write_text('{"opentrack_port": 99999999, "auto_center": "yes"}')
    u = AppSettings.load()
    assert u.opentrack_port == 65535 and u.auto_center is True   # clamped / bad type ignored


def test_controller_centres_on_start_and_sends_to_opentrack(home):
    import socket
    ot = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ot.bind(("127.0.0.1", 0))
    ot.settimeout(1.0)
    st = AppSettings(opentrack_port=ot.getsockname()[1], output_rate_hz=200)
    c = Controller(st, data_port=0, control_port=0)
    c.start()
    try:
        for i in range(1, 25):                       # phone reports a constant offset of 30 deg
            c.rx.handle_datagram(pkt(i, yaw=30.0).pack(), ("1.1.1.1", 1))
            time.sleep(0.01)
        data = ot.recv(64)
        import struct
        x, y, z, yaw, pitch, roll = struct.unpack("<6d", data)
        assert abs(yaw) < 0.5                        # auto-centred: offset removed
        assert c.status().link == "connected" and c.status().face
    finally:
        c.stop()


def test_profile_duplicate_and_delete(home):
    c = Controller(AppSettings(), data_port=0, control_port=0)
    try:
        p = c.duplicate_profile("My truck")
        assert "My truck" in c.profiles and (home / "profiles" / "My_truck.json").exists()
        c.select_profile("My truck")
        c.delete_profile("My truck")
        assert "My truck" not in c.profiles and c.proc.profile.name == "General gaming"
        c.profiles["ETS2"].sensitivity["yaw"] = 9.0
        c.delete_profile("ETS2")                       # built-ins reset instead of vanishing
        assert c.profiles["ETS2"].sensitivity["yaw"] == 1.3
    finally:
        c.stop()


def test_paused_stops_output(home):
    c = Controller(AppSettings(), data_port=0, control_port=0)
    c.start()
    try:
        c.set_paused(True)
        c.rx.handle_datagram(pkt(1, yaw=10).pack(), ("1.1.1.1", 1))
        assert c.stage._active is False
    finally:
        c.stop()
