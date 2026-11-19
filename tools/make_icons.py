"""Generate every app icon from one source image.

    python tools/make_icons.py [path/to/source.png]

Outputs
  assets/branding/icon-1024.png                      master (rounded square, transparent corners)
  pc/vrtrack/assets/icon.png, icon.ico               desktop app + installer
  android/app/src/main/res/mipmap-*/ic_launcher*.png legacy launcher icons
  android/app/src/main/res/mipmap-*/ic_launcher_foreground.png   adaptive icon layer
  android/app/src/main/res/drawable-nodpi/ic_launcher_bg.png     (flat colour is used instead; see values/)
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC_DEFAULT = ROOT / "assets" / "branding" / "icon-source.png"
CORNER_RATIO = 0.225   # corner radius of the artwork's rounded square, as a fraction of its width


def crop_to_artwork(im: Image.Image) -> Image.Image:
    """The source is a rounded-square icon on a black backdrop: crop to the icon's bounds."""
    rgb = im.convert("RGB")
    gray = rgb.convert("L").point(lambda v: 255 if v > 22 else 0)
    box = gray.getbbox()
    if not box:
        raise SystemExit("could not find the icon artwork in the source image")
    l, t, r, b = box
    side = max(r - l, b - t)
    cx, cy = (l + r) // 2, (t + b) // 2
    box = (cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side)
    return rgb.crop(box)


def rounded(im: Image.Image, size: int) -> Image.Image:
    """Resize and apply an anti-aliased rounded-square alpha mask."""
    im = im.resize((size, size), Image.LANCZOS).convert("RGBA")
    s = 4
    mask = Image.new("L", (size * s, size * s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size * s - 1, size * s - 1),
                                           radius=int(size * s * CORNER_RATIO), fill=255)
    im.putalpha(mask.resize((size, size), Image.LANCZOS))
    return im


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC_DEFAULT
    art = crop_to_artwork(Image.open(src))
    master = rounded(art, 1024)

    brand = ROOT / "assets" / "branding"
    brand.mkdir(parents=True, exist_ok=True)
    if not SRC_DEFAULT.exists() or src != SRC_DEFAULT:
        Image.open(src).convert("RGB").save(SRC_DEFAULT)
    master.save(brand / "icon-1024.png")

    # ---- desktop
    pc = ROOT / "pc" / "vrtrack" / "assets"
    pc.mkdir(parents=True, exist_ok=True)
    rounded(art, 256).save(pc / "icon.png")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    master.resize((256, 256), Image.LANCZOS).save(pc / "icon.ico", sizes=[(s, s) for s in sizes])
    master.resize((256, 256), Image.LANCZOS).save(brand / "icon.ico", sizes=[(s, s) for s in sizes])
    # installer wizard images (Inno Setup: 164x314 side panel, 55x55 small)
    panel = Image.new("RGB", (164, 314), (6, 14, 28))
    panel.paste(rounded(art, 140), (12, 20), rounded(art, 140))
    panel.save(brand / "installer-side.bmp")
    rounded(art, 55).convert("RGB").save(brand / "installer-small.bmp")

    # ---- android
    res = ROOT / "android" / "app" / "src" / "main" / "res"
    dens = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
    for name, k in dens.items():
        d = res / f"mipmap-{name}"
        d.mkdir(parents=True, exist_ok=True)
        legacy = round(48 * k)
        rounded(art, legacy).save(d / "ic_launcher.png")
        # round launcher: circle crop of the artwork
        circ = art.resize((legacy, legacy), Image.LANCZOS).convert("RGBA")
        m = Image.new("L", (legacy * 4, legacy * 4), 0)
        ImageDraw.Draw(m).ellipse((0, 0, legacy * 4 - 1, legacy * 4 - 1), fill=255)
        circ.putalpha(m.resize((legacy, legacy), Image.LANCZOS))
        circ.save(d / "ic_launcher_round.png")
        # adaptive foreground: 108dp canvas, artwork inside the 72dp safe zone
        canvas = round(108 * k)
        fg = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
        inner = round(72 * k)
        art_fg = rounded(art, inner)
        fg.paste(art_fg, ((canvas - inner) // 2, (canvas - inner) // 2), art_fg)
        fg.save(d / "ic_launcher_foreground.png")
    print("icons written")


if __name__ == "__main__":
    main()
