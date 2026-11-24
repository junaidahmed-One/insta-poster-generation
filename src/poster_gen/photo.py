"""Turn a photograph into a poster-ready duotone cutout.

Works best on subjects shot against a flat background (dark or light). The
background is keyed by luminance, then the subject is remapped onto a two-colour
ramp so it reads as a screen print rather than a photo.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

# how a photo gets keyed, per background type
PRESETS = {
    "dark": dict(lo=26, span=55, gamma=0.90),
    "light": dict(lo=196, span=-55, gamma=0.90),
}


def key_photo(
    src: Path,
    dst: Path,
    *,
    crop: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0),
    background: str = "dark",
    ramp: tuple[str, str] = ("#283FA0", "#F4F1E8"),
    max_size: int = 1600,
) -> Path:
    """Key `src`, tint it with `ramp`, and write a transparent PNG to `dst`."""
    im = Image.open(src).convert("RGB")
    im = ImageOps.exif_transpose(im)
    w, h = im.size
    im = im.crop((
        int(crop[0] * w), int(crop[1] * h),
        int(crop[2] * w), int(crop[3] * h),
    ))
    im.thumbnail((max_size, max_size), Image.LANCZOS)
    im = im.filter(ImageFilter.MedianFilter(3))

    arr = np.asarray(im, np.float32)
    lum = arr.max(axis=2)  # max channel keeps dark veining in the marble
    lum = np.asarray(
        Image.fromarray(lum.astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)),
        np.float32,
    )

    p = PRESETS[background]
    span = p["span"] if p["span"] > 0 else abs(p["span"])
    if background == "dark":
        alpha = np.clip((lum - p["lo"]) / span, 0, 1) ** p["gamma"]
        t = np.clip((lum - 40) / 150.0, 0, 1)
    else:
        alpha = np.clip((p["lo"] - lum) / span, 0, 1) ** p["gamma"]
        t = 1.0 - np.clip((lum - 40) / 150.0, 0, 1)

    shadow = np.array(_hex(ramp[0]), np.float32)
    light = np.array(_hex(ramp[1]), np.float32)
    rgb = shadow + (light - shadow) * t[..., None]

    rgba = np.dstack([rgb, alpha[..., None] * 255]).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")
    out = out.crop(out.getbbox())

    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)
    return dst


def ramp_for_style(style: dict) -> tuple[str, str]:
    """Duotone ramp derived from a palette: shadow = bg pulled toward ink."""
    bg = _hex(style["bg"])
    ink = _hex(style["ink"])
    light = _hex(style.get("text") or style["paper"])
    # on a light field the figure needs a darker shadow end to keep contrast
    lum = (0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2]) / 255
    w = 0.62 if lum > 0.55 else 0.40
    lo = tuple(round(b * (1 - w) + i * w) for b, i in zip(bg, ink))
    return ("#%02X%02X%02X" % lo, "#%02X%02X%02X" % light)


def _hex(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
