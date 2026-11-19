# VRTrack desktop app

Receives head-tracking data from the VRTrack Android app and feeds [OpenTrack](https://github.com/opentrack/opentrack).

```bash
python -m pip install -e ".[dev]"
python -m vrtrack            # GUI
python -m vrtrack --headless # console only
python -m pytest
```

Full documentation: see the [repository README](../README.md) and [docs/](../docs/).
