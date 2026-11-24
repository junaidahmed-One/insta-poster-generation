"""Extract a usable style (palette + texture) from a reference image.

Drop any poster/screenshot you like into references/ and run:

    uv run poster style references/whatever.jpg

Colours are found with a quantised histogram + peak merging rather than k-means,
so small but important accents (a lime chip, a red stamp) survive next to a large
flat background. The result is a style JSON the renderer consumes, so a new
reference gives you the same colourway without touching CSS.
"""

from __future__ import annotations

import colorsys
import json
from pathlib import Path

import numpy as np
from PIL import Image

BITS = 4                      # 16 levels per channel
MIN_SHARE = 0.002             # a colour must cover 0.2% of the frame
MERGE_DIST = 38 / 255         # peaks closer than this collapse into one


def extract_style(src: Path, name: str | None = None) -> dict:
    im = Image.open(src).convert("RGB")
    im.thumbnail((420, 420), Image.LANCZOS)
    px = np.asarray(im, np.float32).reshape(-1, 3) / 255.0

    centres, shares = _peaks(px)
    lum = centres @ np.array([0.2126, 0.7152, 0.0722], np.float32)

    order = np.argsort(-shares)
    bg = int(order[0])

    solid = [i for i in order if shares[i] > 0.01] or list(order)
    ink = int(min(solid, key=lambda i: lum[i]))
    paper = int(max(solid, key=lambda i: lum[i]))

    bg_h, bg_s, _ = _hsv(centres[bg])
    candidates = [
        i for i in order
        if i not in (bg, ink, paper) and 0.10 < lum[i] < 0.93
    ] or [i for i in order if i != bg]

    def accent_score(i: int) -> float:
        h, s, _ = _hsv(centres[i])
        hue_gap = min(abs(h - bg_h), 1 - abs(h - bg_h)) * 360
        separation = 1.0 if (hue_gap > 28 or bg_s < 0.15) else 0.12
        return s * separation * (shares[i] ** 0.2)

    accent = int(max(candidates, key=accent_score))

    return {
        "name": name or src.stem,
        "source": str(src),
        "bg": _hex(centres[bg]),
        "accent": _hex(centres[accent]),
        "ink": _hex(centres[ink]),
        "paper": _hex(centres[paper]),
        "palette": [_hex(centres[i]) for i in order],
        "grain": round(_grain(im), 3),
        "scanlines": 0.22,
    }


def _peaks(px: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Quantised histogram -> merged colour peaks, most common first."""
    q = np.clip((px * ((1 << BITS) - 1)).round().astype(np.int32), 0, (1 << BITS) - 1)
    key = (q[:, 0] << (2 * BITS)) | (q[:, 1] << BITS) | q[:, 2]
    counts = np.bincount(key, minlength=1 << (3 * BITS))

    sums = np.zeros((len(counts), 3), np.float64)
    for c in range(3):
        sums[:, c] = np.bincount(key, weights=px[:, c], minlength=len(counts))

    total = len(px)
    keep = np.flatnonzero(counts > MIN_SHARE * total)
    keep = keep[np.argsort(-counts[keep])]

    centres: list[np.ndarray] = []
    weights: list[float] = []
    for b in keep:
        colour = sums[b] / counts[b]
        for i, c in enumerate(centres):
            if np.abs(colour - c).max() < MERGE_DIST:
                w = weights[i] + counts[b]
                centres[i] = (c * weights[i] + colour * counts[b]) / w
                weights[i] = w
                break
        else:
            centres.append(colour)
            weights.append(float(counts[b]))

    centres = np.array(centres, np.float32)
    shares = np.array(weights, np.float32) / total
    return centres, shares


def _grain(im: Image.Image) -> float:
    """Rough texture estimate: high-frequency energy -> grain strength."""
    g = np.asarray(im.convert("L"), np.float32) / 255.0
    dx = np.abs(np.diff(g, axis=1)).mean()
    dy = np.abs(np.diff(g, axis=0)).mean()
    return float(np.clip(0.12 + (dx + dy) * 6.0, 0.12, 0.42))


def _hsv(rgb: np.ndarray) -> tuple[float, float, float]:
    return colorsys.rgb_to_hsv(*(float(np.clip(c, 0, 1)) for c in rgb))


def _hex(rgb: np.ndarray) -> str:
    r, g, b = (np.clip(rgb, 0, 1) * 255).round().astype(int)
    return f"#{r:02X}{g:02X}{b:02X}"


def derive_roles(style: dict) -> dict:
    """Work out readable text/line colours for a palette.

    A reference with a light background needs dark type, so these are computed
    from the palette instead of being hard-coded in the template.
    """
    bg = _rgb(style["bg"])
    ink = _rgb(style["ink"])
    paper = _rgb(style["paper"])
    accent = _rgb(style["accent"])

    text = _rgb(style["text"]) if style.get("text") else (ink if _lum(bg) > 0.55 else paper)
    on_accent = ink if _lum(accent) > 0.5 else paper

    return {
        "text": _css(text, 1),
        "text_soft": _css(text, 0.90),
        "text_mute": _css(text, 0.58),
        "line": _css(text, 0.30),
        "on_accent": _css(on_accent, 1),
        "shadow": _css(ink, 0.22 if _lum(bg) < 0.55 else 0.14),
    }


def _rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def _lum(rgb: tuple[int, int, int]) -> float:
    r, g, b = (c / 255 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _css(rgb: tuple[int, int, int], alpha: float) -> str:
    r, g, b = rgb
    return f"rgba({r},{g},{b},{alpha})" if alpha < 1 else f"#{r:02X}{g:02X}{b:02X}"


def save_style(style: dict, dst: Path) -> Path:
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(style, indent=2) + "\n")
    return dst


def load_style(src: Path | None) -> dict:
    from .paths import STYLES

    path = Path(src) if src else STYLES / "default.json"
    return json.loads(path.read_text())
