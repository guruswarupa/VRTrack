# Protocol

The phone and PC speak a small UDP protocol. The single source of truth is
[`pc/vrtrack/protocol.py`](../pc/vrtrack/protocol.py), mirrored in
[`Protocol.kt`](../android/app/src/main/java/com/vrtrack/tracker/Protocol.kt). Shared fixtures in
[`protocol/test_vectors.json`](../protocol/test_vectors.json) are checked by the test suites on **both** sides, so a
change that breaks compatibility fails CI. Regenerate them with `python tools/gen_vectors.py` after an intentional change.

## Tracking packet (phone → PC, UDP 4243)

Little-endian, fixed 54 bytes:

| Offset | Type | Field |
|---|---|---|
| 0 | `char[4]` | magic `VRTK` |
| 4 | `u8` | version (`1`) |
| 5 | `u8` | flags |
| 6 | `u32` | sequence number (wraps at 2³²) |
| 10 | `u64` | phone monotonic timestamp, microseconds |
| 18 | `f32` | yaw (°) |
| 22 | `f32` | pitch (°) |
| 26 | `f32` | roll (°) |
| 30 | `f32` | x (cm) |
| 34 | `f32` | y (cm) |
| 38 | `f32` | z (cm) |
| 42 | `f32` | gaze X (−1…1, left → right) |
| 46 | `f32` | gaze Y (−1…1, down → up) |
| 50 | `f32` | confidence (0…1 quality estimate) |

Flags: `1` left eye open, `2` right eye open, `4` face tracked, `8` paused, `16` eye tracking enabled.

Pose values are relative to the phone's neutral (calibrated/recentered) position. The PC rejects packets with a bad
magic/version/size or non-finite values, drops late or duplicate sequence numbers (wrap-aware), and counts lost packets.
If a stream is silent for 1 s it is treated as restarted (the phone app restarted).

The original brief's JSON example has the same fields; the binary form is used for size and parsing speed.

## Control (UDP 4244)

| Message | Direction | Meaning |
|---|---|---|
| `VRTD?` | phone → broadcast | "Is there a VRTrack PC here?" Sent on every network interface. |
| `VRTD!` + JSON | PC → phone | `{"name": "...", "dataPort": 4243}` — the phone then streams to that address. |
| `VRTP` + 8 bytes | phone → PC | Ping; payload is the phone's timestamp. |
| `VRTP` + 8 bytes | PC → phone | Pong, identical payload; the phone halves the round trip for the latency display. |

## PC → OpenTrack (UDP 4242)

OpenTrack's native "UDP over network" input: six little-endian doubles — X, Y, Z (cm), Yaw, Pitch, Roll (°). Sent at
120 Hz by default after interpolation and smoothing. OpenTrack then exposes FreeTrack / TrackIR-compatible output.

## Compatibility

Version byte `1` is the only version. A future incompatible change bumps it; receivers ignore other versions.
