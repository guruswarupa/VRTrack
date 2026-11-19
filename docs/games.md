# Games

VRTrack feeds OpenTrack, and OpenTrack presents itself to games as a FreeTrack tracker. Any game that supports
FreeTrack or TrackIR head tracking can use it, with no game-side modification.

## Verified

### Euro Truck Simulator 2 / American Truck Simulator

Tested with ETS2.

1. Start OpenTrack and press **Start** (Input *UDP over network*, Output *freetrack 2.0 Enhanced*).
2. Make sure VRTrack is running with the **ETS2** (or **ATS**) profile selected and the phone is tracking.
3. Start the game *after* OpenTrack. The game detects the tracker automatically. If the options menu offers a
   head-tracking setting, leave it enabled.
4. In the cab, sit normally and press Recenter.
5. If left/right or up/down feel reversed, tick **Invert** for that axis on the Tuning page and **Save**. The built-in
   profiles already invert yaw and pitch (that is what a front-facing phone needs).

Tips: ETS2/ATS profiles use a little more yaw sensitivity so you can reach the mirrors without turning far. If the
view sits off to a side, check OpenTrack's filter is **EWMA** — the *Accela* filter exaggerates small head movements and
pushes the camera off-centre.

## Other games (untested)

These support FreeTrack/TrackIR in some form, so they *should* work the same way, but have not been tested with VRTrack.
Check each game's own head-tracking setting.

- Assetto Corsa
- Assetto Corsa Competizione — head-tracking support differs from game to game and version to version; check the game's
  controls/camera options.
- BeamNG.drive
- Microsoft Flight Simulator (may need OpenTrack's SimConnect output instead of FreeTrack)

If a game doesn't see the tracker, open OpenTrack's output settings (the hammer button next to *Output*) and try the
other protocols it offers, or see OpenTrack's own documentation for that game.

## Per-game profiles

VRTrack keeps one profile per game under `%USERPROFILE%\.vrtrack\profiles`. Pick the one you need on the Tuning page;
the choice is remembered. **Duplicate…** creates your own copy.
