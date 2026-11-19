# Calibration and tuning

## Calibrate (phone)

Calibration records your neutral head position so "looking straight ahead" is zero.

1. Phone → **Calibrate** tab → **Start calibration** (tracking must be running).
2. Sit in your normal driving position, look at the monitor, keep your head still. It samples for a couple of seconds.
3. With eye tracking enabled it then asks you to look at the **left**, **right**, **top** and **bottom** edge of the
   monitor (head still) to measure your gaze range.

You rarely need to repeat this. For day-to-day re-zeroing just press **Recenter** — on the phone's Track tab, on the
phone's notification (works with the screen off), in the desktop Dashboard, or `Ctrl+R` in the desktop window.
VRTrack also centres on your current pose every time tracking (re)starts.

## Tune (desktop)

Everything below is per profile and applies instantly; press **Save** to keep it.

| Setting | What it does | Start with |
|---|---|---|
| **Sensitivity** (per axis) | Multiplies head movement. 1.0 = 1:1. | 1.0–1.5 for yaw/pitch |
| **Dead zone** | Ignores movement smaller than this (° or cm) so the view is steady while you steer. | 1° / 0.3 cm |
| **Maximum** | Largest output the axis can produce. | 90° yaw, 60° pitch, 45° roll |
| **Invert** | Reverses direction. | Yaw and pitch on (built-in profiles) |
| **Smoothing** | Low-pass filter. Higher = calmer but laggier. | 0.3–0.5 |
| **Response curve** | 1.0 linear. Above 1 is calmer near the centre and stronger at the edges. | 1.0–1.5 |
| **Eye gaze** | Adds where you look to yaw/pitch; strength in degrees at full gaze. | Off until you want it |

The **curve preview** plots the exact response for the selected axis: the dashed line is 1:1, the yellow dot is your
live head position.

Axes: **yaw** turn left/right, **pitch** look up/down, **roll** tilt, **X** lean sideways, **Y** move up/down,
**Z** lean forward/back. For most games yaw and pitch matter most; if the view shifts when you lean, reduce X/Y/Z
sensitivity or raise their dead zones.

## What the smoothing does

The phone delivers about 20 poses per second. The desktop app sends OpenTrack 120 updates per second by interpolating
between real poses, then applies your smoothing. This removes the "stepping" at the cost of roughly one phone frame
(50–100 ms) of latency. It never extrapolates or invents values: if the face is lost or tracking is paused, nothing is
sent and OpenTrack holds the last pose.

## Getting a higher frame rate

- Turn the phone **screen off** while playing (the live preview costs frame rate; tracking continues).
- Phone → Settings → Camera: **640×480** and **30 fps** are usually best.
- Good, even lighting on your face; avoid a bright window behind you.
- Keep eye tracking off unless you use gaze.

## OpenTrack's own filter

The installer sets OpenTrack's filter to **EWMA**. Don't use *Accela*: it deliberately amplifies small movements and
pushes the view off-centre. VRTrack already smooths and interpolates.
