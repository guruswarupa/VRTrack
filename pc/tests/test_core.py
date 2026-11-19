import json
import socket
import struct
import time

from vrtrack import protocol as P
from vrtrack.opentrack import pack_opentrack
from vrtrack.processing import Processor, shape_axis
from vrtrack.profiles import Profile, load_profiles, save_profile
from vrtrack.receiver import Receiver


def pkt(seq=1, yaw=0.0, flags=P.FLAG_TRACKING, **kw):
    return P.TrackingPacket(seq, 1000, yaw, kw.get("pitch", 0), 0, 0, 0, 0, flags=flags)


def test_roundtrip_and_size():
    p = P.TrackingPacket(7, 123456, 1.5, -2.5, 3.5, 4, 5, 6, 0.1, -0.2, 0.9,
                         P.FLAG_TRACKING | P.FLAG_LEFT_OPEN)
    b = p.pack()
    assert len(b) == P.PACKET_SIZE == 54
    q = P.TrackingPacket.unpack(b)
    assert q.seq == 7 and q.tracking and q.left_open and not q.right_open
    assert abs(q.yaw - 1.5) < 1e-6 and abs(q.gaze_y + 0.2) < 1e-6


def test_rejects_garbage():
    assert P.TrackingPacket.unpack(b"hello") is None
    bad = bytearray(pkt().pack()); bad[0] = 0
    assert P.TrackingPacket.unpack(bytes(bad)) is None
    nan = P.TrackingPacket(1, 1, float("nan"), 0, 0, 0, 0, 0).pack()
    assert P.TrackingPacket.unpack(nan) is None


def test_seq_wrap():
    assert P.seq_is_newer(5, 4)
    assert not P.seq_is_newer(4, 5) and not P.seq_is_newer(5, 5)
    assert P.seq_is_newer(0, 0xFFFFFFFF)


def test_opentrack_format():
    b = pack_opentrack(1, 2, 3, 4, 5, 6)
    assert struct.unpack("<6d", b) == (1, 2, 3, 4, 5, 6)


def test_shape_axis():
    assert shape_axis(0.5, 1, 1, 90, 1, False) == 0
    assert shape_axis(11, 1, 1, 90, 1, False) == 10
    assert shape_axis(-11, 1, 1, 90, 1, True) == 10
    assert shape_axis(200, 2, 0, 90, 1, False) == 90  # clamped


def test_processor_recenter_pause_loss():
    pr = Processor(Profile(smoothing=0.0))
    assert pr.process(pkt(yaw=20))["yaw"] == 19.0   # 1 deg dead zone
    pr.recenter()
    assert pr.process(pkt(yaw=20))["yaw"] == 0.0
    assert pr.process(pkt(yaw=30, flags=0)) is None  # lost face -> nothing sent
    pr.paused = True
    assert pr.process(pkt(yaw=30)) is None


def test_smoothing_converges():
    pr = Processor(Profile(smoothing=0.5))
    pr.profile.deadzone = {k: 0 for k in pr.profile.deadzone}
    first = pr.process(pkt(yaw=0))["yaw"]
    v = [pr.process(pkt(yaw=10))["yaw"] for _ in range(20)]
    assert first == 0 and 0 < v[0] < 10 and abs(v[-1] - 10) < 0.01


def test_eye_gaze_only_when_enabled():
    p = Profile(smoothing=0.0, eye_tracking=True, eye_sensitivity=10)
    pr = Processor(p)
    g = P.TrackingPacket(1, 1, 0, 0, 0, 0, 0, 0, gaze_x=0.5,
                         flags=P.FLAG_TRACKING | P.FLAG_EYES_ENABLED)
    assert pr.process(g)["yaw"] == 5.0
    g.flags = P.FLAG_TRACKING
    assert pr.process(g)["yaw"] == 0.0


def test_profiles_roundtrip(tmp_path):
    p = Profile(name="My Game: v2", smoothing=0.7)
    p.invert["yaw"] = True
    save_profile(p, tmp_path)
    loaded = load_profiles(tmp_path)
    assert loaded["My Game: v2"].smoothing == 0.7 and loaded["My Game: v2"].invert["yaw"] is True
    assert {"Assetto Corsa", "Assetto Corsa Competizione", "ETS2", "ATS", "General gaming"} <= set(loaded)


def test_receiver_udp_end_to_end():
    got = []
    rx = Receiver(got.append, data_port=0, control_port=0)
    # bind ephemeral ports: start manually to learn them
    rx.start()
    dport = rx._socks[0].getsockname()[1]
    cport = rx._socks[1].getsockname()[1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for seq in (1, 2, 5, 4, 6):  # 3 missing, 4 late
        s.sendto(pkt(seq=seq).pack(), ("127.0.0.1", dport))
    s.sendto(b"junk", ("127.0.0.1", dport))
    time.sleep(0.4)
    assert [g.seq for g in got] == [1, 2, 5, 6]
    assert rx.lost == 2 and rx.out_of_order == 1 and rx.invalid == 1 and rx.connected
    # discovery + ping
    s.settimeout(1)
    s.sendto(P.DISCOVER_REQUEST, ("127.0.0.1", cport))
    data, _ = s.recvfrom(256)
    assert data.startswith(P.DISCOVER_REPLY_PREFIX)
    assert json.loads(data[5:])["dataPort"] == dport
    s.sendto(b"VRTP12345678", ("127.0.0.1", cport))
    assert s.recvfrom(256)[0] == b"VRTP12345678"
    rx.stop()


def test_phone_restart_resets_sequence():
    got = []
    rx = Receiver(got.append, data_port=0, control_port=0)
    rx.handle_datagram(pkt(seq=5000).pack(), ("1.2.3.4", 1))
    rx.handle_datagram(pkt(seq=1).pack(), ("1.2.3.4", 1))      # restart right away: still "late"
    assert rx.out_of_order == 1 and len(got) == 1
    rx.last_rx_time -= 2.0                                      # stream went silent
    rx.handle_datagram(pkt(seq=1).pack(), ("1.2.3.4", 1))      # app restarted: accepted
    assert [g.seq for g in got] == [5000, 1]


def test_output_stage_interpolates_and_stops():
    from vrtrack.processing import OutputStage
    sent = []
    pr = Processor(Profile(smoothing=0.0))
    st = OutputStage(pr, lambda *a: sent.append(a), rate_hz=200)
    st.start()
    z = {k: 0.0 for k in ("yaw", "pitch", "roll", "x", "y", "z")}
    st.push(dict(z, yaw=0.0)); time.sleep(0.1)
    st.push(dict(z, yaw=10.0)); time.sleep(0.2)
    yaws = [a[3] for a in sent]
    assert len(yaws) > 20                                  # far more than the 2 poses pushed
    mid = [y for y in yaws if 0.5 < y < 9.5]
    assert mid, "should pass through intermediate values (no stepping)"
    assert abs(yaws[-1] - 10.0) < 0.5 and max(yaws) <= 10.0 + 1e-6   # never overshoots
    n = len(sent); st.push(None); time.sleep(0.1)
    assert len(sent) <= n + 1                              # stops sending when lost/paused
    st.stop()


def test_shared_wire_vectors():
    """The Android app is tested against the same file; both must produce identical bytes."""
    import json
    from pathlib import Path
    data = json.loads((Path(__file__).resolve().parents[2] / "protocol" / "test_vectors.json").read_text())
    assert data["packet_size"] == P.PACKET_SIZE
    for c in data["cases"]:
        pkt = P.TrackingPacket(c["seq"], c["timestamp_us"], c["yaw"], c["pitch"], c["roll"], c["x"], c["y"],
                               c["z"], c["gaze_x"], c["gaze_y"], c["confidence"], c["flags"])
        assert pkt.pack().hex() == c["hex"], c["name"]
        back = P.TrackingPacket.unpack(bytes.fromhex(c["hex"]))
        assert back is not None and back.seq == c["seq"] and back.flags == c["flags"]
