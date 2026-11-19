"""Regenerate protocol/test_vectors.json (the shared Python <-> Kotlin wire-format fixtures)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pc"))
from vrtrack import protocol as P  # noqa: E402

CASES = [
    dict(name="neutral", seq=0, timestamp_us=0, yaw=0, pitch=0, roll=0, x=0, y=0, z=0, gaze_x=0, gaze_y=0, confidence=0, flags=0),
    dict(name="tracking", seq=1, timestamp_us=123456789, yaw=12.5, pitch=-7.25, roll=3.0, x=1.5, y=-2.5, z=10.0,
         gaze_x=0.25, gaze_y=-0.5, confidence=0.98,
         flags=P.FLAG_TRACKING | P.FLAG_LEFT_OPEN | P.FLAG_RIGHT_OPEN | P.FLAG_EYES_ENABLED),
    dict(name="paused_seq_wrap", seq=4294967295, timestamp_us=9007199254740991, yaw=-90, pitch=60, roll=-45, x=-20, y=20, z=-20,
         gaze_x=1, gaze_y=-1, confidence=1.0, flags=P.FLAG_PAUSED),
]

out = []
for c in CASES:
    pkt = P.TrackingPacket(c["seq"], c["timestamp_us"], c["yaw"], c["pitch"], c["roll"], c["x"], c["y"], c["z"],
                           c["gaze_x"], c["gaze_y"], c["confidence"], c["flags"])
    out.append({**c, "hex": pkt.pack().hex()})
(ROOT / "protocol" / "test_vectors.json").write_text(json.dumps({"packet_size": P.PACKET_SIZE, "cases": out}, indent=2))
print("wrote", len(out), "vectors")
