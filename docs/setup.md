# Setup guide

About five minutes. You need: a Windows PC (Linux works too, see the end), an Android phone (8.0+) with a front camera,
and a way to connect them: the same Wi-Fi network **or** a USB cable (USB tethering).

## 1. Install on the PC (Windows)

1. Download `VRTrack-Setup-x.y.z.exe` from the Releases page and run it. It needs administrator rights.
2. Click through the wizard. The installer:
   - installs **VRTrack**,
   - installs **OpenTrack** (the official release, silently, if you don't have it yet),
   - adds a Windows Firewall rule so your phone can reach VRTrack (local network only),
   - pre-configures OpenTrack: Input **UDP over network**, Output **freetrack 2.0 Enhanced**, Filter **EWMA**.
     If you already use OpenTrack with your own profile, yours is left alone and a ready-made `VRTrack.ini` profile
     is added next to it (in `Documents\opentrack-2.3`).
3. Leave "Launch VRTrack" ticked and finish.

> Already have OpenTrack? The installer detects it and skips that step.

## 2. Install the app on the phone

1. Download `VRTrack-x.y.z-android.apk` on the phone (or copy it over) and open it.
2. Android will ask to allow installs from that source (browser / files app). Allow it once.
3. Open **VRTrack** and read the three intro screens. Tap **Allow and continue** and grant the **camera** and
   **notification** permissions. Both stay on the phone.

## 3. Connect the phone and PC

Pick one:

- **Same Wi-Fi.** Join both to the same network. Nothing else to do.
- **USB tethering** (lowest latency, no router needed). Plug the phone into the PC, then on the phone:
  *Settings → Connections → Mobile Hotspot and Tethering → USB tethering*.

The phone finds the PC by itself. On the phone's **Track** tab the **PC** tile turns green and shows the PC's address
and the round-trip time. If it stays on *Searching…*, see [networking](networking.md) — you can also type the PC's
address under **Settings → PC connection** (the desktop app shows it under **Setup**).

## 4. Start OpenTrack

1. Open **OpenTrack** from the Start menu.
2. Check the three boxes read **UDP over network**, **freetrack 2.0 Enhanced**, **EWMA** (the installer sets this).
3. Press **Start**. Leave OpenTrack running.

You must press **Start** each session, and start OpenTrack **before** the game so the game can find it.

## 5. Start tracking

1. Mount the phone below or beside your monitor, facing you, so your whole face is in view. Portrait or landscape both
   work — the app follows the phone's orientation.
2. In the phone app tap **Start tracking**. You should see your face with landmarks and **Face: Tracked**.
3. On the PC, the VRTrack window's **Dashboard** shows the head moving. In OpenTrack the *Raw tracker data* numbers move.
4. Sit in your normal driving position, look at the screen and press **Recenter** (phone, PC window, or the phone's
   notification). VRTrack also centres automatically each time tracking starts.

**Turn the phone screen off** if you like — tracking keeps going, and with the screen off it runs faster (the camera
preview costs frame rate).

## 6. Start your game

See [games](games.md). For Euro Truck Simulator 2: start OpenTrack (Start pressed), launch the game, sit in the cab
and look around.

## 7. Tune it

Open the desktop app's **Tuning** page, pick the profile for your game and adjust sensitivity, dead zone and
smoothing while you watch the live curve. Press **Save**. Details: [tuning](tuning.md).

## Optional: eye tracking

Phone app → **Settings → Tracking → Eye tracking**, then restart tracking and run **Calibrate** (it then also asks you to
look at the left/right/top/bottom of the monitor). In the desktop app tick *Add gaze to view* on the Tuning page.
Head tracking works fine without it.

## Linux

Download the `.tar.gz`, extract, run `VRTrack/VRTrack`. Install OpenTrack separately and set it up as in step 4
(Input *UDP over network*, port 4242). Open UDP ports 4243 and 4244 in your firewall.

## Updating and uninstalling

- **Update:** run the newer installer; it upgrades in place and keeps your profiles (stored in `%USERPROFILE%\.vrtrack`).
- **Uninstall:** *Settings → Apps → VRTrack*. This removes VRTrack and its firewall rule. OpenTrack is left installed;
  remove it separately if you want.
