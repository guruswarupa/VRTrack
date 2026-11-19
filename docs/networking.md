# Networking

The phone sends small UDP packets (about 54 bytes, 20–30 times a second) to the PC. Everything stays on your local
network; no internet is used.

| What | Port | Direction |
|---|---|---|
| Tracking data | UDP **4243** | phone → PC |
| Discovery and latency ping | UDP **4244** | phone ↔ PC |
| OpenTrack input | UDP **4242** | VRTrack → OpenTrack (same PC, `127.0.0.1`) |

## Option A: same Wi-Fi

Join phone and PC to the same network. Some routers have "AP/client isolation" or a separate guest network that blocks
devices from talking to each other — turn that off or use the same non-guest network.

## Option B: USB tethering (recommended for sim rigs)

Wired, no router, steadier latency.

1. Connect the phone to the PC with a USB data cable.
2. Phone: *Settings → Connections → Mobile Hotspot and Tethering → USB tethering* on.
3. Windows shows a new network adapter (e.g. "Ethernet 3") with an address like `10.x.x.x` or `192.168.42.x`.

The phone finds the PC automatically. VRTrack broadcasts on **every** network interface, including the USB link.

> USB tethering shares the phone's mobile data with the PC. That is not required for VRTrack. If you don't want the PC
> using your data plan, turn off mobile data on the phone — tracking still works.

## Firewall

The Windows installer adds an inbound UDP rule for VRTrack, allowed on any network profile but **only from the local
subnet**. USB-tether and some Wi-Fi networks are classed as *Public* by Windows, which is why the rule isn't limited to
Private networks.

If you installed manually, or the rule is missing, allow it yourself (administrator PowerShell):

```powershell
netsh advfirewall firewall add rule name="VRTrack" dir=in action=allow program="C:\Program Files\VRTrack\VRTrack.exe" protocol=UDP remoteip=localsubnet profile=any
```

(use the path where VRTrack is installed). OpenTrack only receives from VRTrack on the same PC, which doesn't need a
firewall rule; if Windows prompts for OpenTrack, you can decline.

## Entering the PC address manually

Discovery uses a broadcast, which some networks drop. In the desktop app open **Setup** — it lists this PC's addresses
with Copy buttons. In the phone app: **Settings → PC connection → PC address**, paste it, **Apply and test
connection**. Leave the field empty to go back to automatic.

If you have several adapters (VPN, virtual switches), pick the address on the same network as the phone: both must share
the first three numbers (for example `192.168.0.x` and `192.168.0.y`).

## Checking the link

- Phone → **Track** tab: the **PC** tile shows the address and round-trip time (1–5 ms is normal).
- PC → **Dashboard**: *Phone x.x.x.x* chip and the Hz counter. **Setup** has a three-step checklist.
- Wired or Wi-Fi, a healthy link shows *lost 0*.
