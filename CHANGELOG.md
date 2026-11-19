# Changelog

## 0.1.0 — first release

- Android app: CameraX + MediaPipe Face Landmarker head pose (yaw/pitch/roll/x/y/z), optional gaze and blink,
  calibration wizard, foreground service that keeps tracking with the screen off, lock-screen notification with
  Recenter/Pause/Stop, portrait and landscape, onboarding.
- Desktop app (PySide6): Dashboard, Tuning (per-axis sensitivity, dead zone, maximum, invert, curve preview, smoothing,
  eye gaze, saved per-game profiles), Setup (checklist, PC addresses, OpenTrack output, output test), system tray.
- OpenTrack output at 120 Hz with interpolation between real poses.
- Automatic PC discovery on every network interface (Wi-Fi and USB tethering), latency display, reconnection.
- Windows installer that also installs and pre-configures OpenTrack and opens the firewall for the phone.
- CI (tests, lint, builds) and tag-driven releases for Windows, Linux and Android.
