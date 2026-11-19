"""Stamp a release version into the desktop app.

    python tools/set_version.py 1.2.3        (a leading "v" is accepted)

The Android version is passed to Gradle instead (-PversionName / -PversionCode), see release.yml.
"""
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit(__doc__)
version = sys.argv[1].lstrip("v")
if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.]+)?", version):
    raise SystemExit(f"not a semantic version: {version!r}")
p = Path(__file__).resolve().parents[1] / "pc" / "vrtrack" / "__init__.py"
text = p.read_text(encoding="utf-8")
new, n = re.subn(r'__version__ = "[^"]*"', f'__version__ = "{version}"', text)
if n != 1:
    raise SystemExit("could not find __version__")
p.write_text(new, encoding="utf-8")
print(f"vrtrack {version}")
