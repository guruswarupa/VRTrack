"""Download the MediaPipe Face Landmarker model into the Android assets (checksum-verified).

    python tools/fetch_model.py

The model is Google's `face_landmarker.task` (float16), Apache-2.0. It is not committed to git.
"""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
DEST = Path(__file__).resolve().parents[1] / "android" / "app" / "src" / "main" / "assets" / "face_landmarker.task"


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    if DEST.exists() and digest(DEST) == SHA256:
        print("model already present and verified")
        return 0
    DEST.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {URL}")
    urllib.request.urlretrieve(URL, DEST)
    got = digest(DEST)
    if got != SHA256:
        DEST.unlink(missing_ok=True)
        print(f"checksum mismatch: expected {SHA256}, got {got}", file=sys.stderr)
        return 1
    print(f"saved {DEST} ({DEST.stat().st_size // 1024} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
