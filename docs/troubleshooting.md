# Troubleshooting

Start with the desktop app's **Setup** page: its checklist shows which link is broken (phone connected → face seen →
data flowing).

## The phone says "Searching…" and never finds the PC

- Is the VRTrack desktop app running? (Window or system-tray icon.)
- Same network? Phone and PC must share the first three numbers of their addresses. A PC with several adapters (VPN,
  Hyper-V) may have an address on the wrong network — use the one on the phone's network.
- **USB tethering:** make sure tethering is on and Windows shows the new adapter. VRTrack broadcasts on every interface,
  so this works without extra steps.
- Firewall: see [networking](networking.md#firewall). Re-run the installer to restore the rule.
- Wi-Fi "AP isolation" / guest network blocks device-to-device traffic. Use the main network.
- Type the PC address into the phone: **Settings → PC connection**.

## The phone is connected, but the desktop says "Waiting for phone"

Two copies of VRTrack can be running and fighting over the ports; one of them receives the data and the other shows
nothing. Quit all VRTrack windows and tray icons (check Task Manager for `VRTrack.exe` / `pythonw.exe`) and start one.

If you restarted the phone app, the desktop picks the new stream up after about a second. If not, restart the desktop app.

## OpenTrack shows zeros / no movement

- VRTrack desktop must show *Phone … Hz*. Fix that first.
- In VRTrack → **Setup** → OpenTrack output: host `127.0.0.1`, port `4242`, and OpenTrack's *UDP over network* input
  must use the same port (its settings → hammer button next to *Input*).
- Press OpenTrack's **Start**. Use **Setup → Test OpenTrack output**: the *Game data* numbers should sweep left/right for
  3 seconds. If they do, the PC side works and the phone is the issue; if not, check the port.

## The game doesn't react

- Start OpenTrack (and press Start) **before** launching the game.
- Output must be **freetrack 2.0 Enhanced**. Run OpenTrack and the game at the same privilege level (both normal, or both
  as administrator).
- Close TrackIR software if installed; only one tracker program can talk to a game.
- Some games need head tracking enabled in their own options.

## The view sits turned to one side / camera is far off-centre

- Press **Recenter** while looking straight ahead.
- OpenTrack's filter must be **EWMA**, not *Accela* (Accela exaggerates small movements ~5×). The installer sets EWMA.
- Check the OpenTrack *Raw tracker data* vs *Game data* rows: they should be similar in size.

## Left/right or up/down are reversed

Tick **Invert** for that axis on the Tuning page and **Save**. The built-in profiles invert yaw and pitch. Roll or X may
need inverting too depending on the game.

## The view is choppy / laggy

- Turn the phone screen off (preview costs frame rate). Check the desktop Hz counter: around 20 is normal with the screen
  off; ~10–14 with the live preview showing.
- Phone → Settings → Camera: 640×480, 30 fps.
- Raise lighting; low light lowers the camera's frame rate.
- Lower Smoothing on the Tuning page.
- Over Wi-Fi, USB tethering is steadier.

## Tracking stops after a while or when the screen turns off

Some phones kill background apps. Phone → Settings → *Keep tracking in the background* → open battery settings and set
VRTrack to **Unrestricted / Don't optimise**. Keep the phone plugged in; the camera is power-hungry.

## "Face: Not seen"

- Whole face in view, eyes visible, even lighting, no strong backlight. Masks and hands over the face stop tracking —
  nothing is sent while the face is lost, so the game view just holds its last pose.
- Move the phone so your face is in the middle third of the preview.

## The camera preview is black or sideways

Fully close and reopen the phone app. The app rotates frames to match the phone's orientation; if you turn the phone
mid-session, it re-adapts within a moment.

## Android refuses to install the APK

Allow installs from the app you opened it with (Settings → Apps → Special access → Install unknown apps). If you had a
debug-signed build and the new one is release-signed (or vice versa), uninstall the old one first.

## Windows warns about an unknown publisher / SmartScreen

The installer isn't code-signed yet. Choose *More info → Run anyway*. Verify the download against the `.sha256` file on the
release page if you want to be sure.

## Reset everything

Close VRTrack and delete `%USERPROFILE%\.vrtrack` (settings and profiles). On the phone: Settings → Apps → VRTrack →
Storage → Clear data.
