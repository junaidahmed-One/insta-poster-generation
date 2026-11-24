"""Fill a template with a spec + style and screenshot it with headless Chrome."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import subprocess
from pathlib import Path

from .paths import ASSETS, OUT, TEMPLATES, resolve

CHROME = "/usr/bin/google-chrome"

FONT_FILES = {
    "Anton": ("Anton-Regular.ttf", "400", "normal"),
    "Bebas Neue": ("BebasNeue-Regular.ttf", "400", "normal"),
    "Archivo Black": ("ArchivoBlack-Regular.ttf", "400", "normal"),
    "Barlow Condensed": ("BarlowCondensed-Bold.ttf", "700", "normal"),
    "Playfair Display": ("PlayfairDisplay-Italic.ttf", "400 900", "italic"),
}


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def font_css() -> str:
    out = []
    for family, (file, weight, style) in FONT_FILES.items():
        out.append(
            "@font-face{font-family:'%s';src:url('%s') format('truetype');"
            "font-weight:%s;font-style:%s;font-display:block;}"
            % (family, data_uri(ASSETS / "fonts" / file), weight, style)
        )
    return "\n".join(out)


def photo_path(spec: dict, style: dict) -> Path:
    """Resolve the photo, re-keying it into the palette when a raw shot is given."""
    photo = spec["photo"]
    if isinstance(photo, str):
        return resolve(photo)

    from .photo import key_photo, ramp_for_style

    src = resolve(photo["src"])
    ramp = ramp_for_style(style)
    key = "%s|%s|%s|%s" % (src.name, src.stat().st_mtime_ns, photo.get("crop"), ramp)
    digest = hashlib.sha1(key.encode()).hexdigest()[:12]
    cached = resolve("assets/photos/cache") / f"{src.stem}-{digest}.png"
    if not cached.exists():
        key_photo(
            src, cached,
            crop=tuple(photo.get("crop", (0, 0, 1, 1))),
            background=photo.get("background", "dark"),
            ramp=ramp,
        )
    return cached


def photo_aspect(path: Path) -> str:
    from PIL import Image

    with Image.open(path) as im:
        w, h = im.size
    return f"{w}/{h}"


def chip_rows(items: list[str]) -> str:
    return "".join(
        '<span class="chip"><i>%02d</i>%s</span>' % (i, label)
        for i, label in enumerate(items, start=1)
    )


def index_rows(items: list[str]) -> str:
    return "\n    ".join(
        '<div class="idx-row"><span class="n">%02d</span><span class="t">%s</span></div>'
        % (i, label)
        for i, label in enumerate(items, start=1)
    )


def tokens(spec: dict, style: dict) -> dict[str, str]:
    from .palette import derive_roles

    roles = derive_roles(style)
    copy = spec.get("copy", {})
    photo = photo_path(spec, style)

    t = {
        "FONTS": font_css(),
        "PHOTO": data_uri(photo),
        "PHOTO_AR": photo_aspect(photo),
        "BLUE": style["bg"],
        "LIME": style["accent"],
        "NAVY": style["ink"],
        "PAPER": style["paper"],
        "GRAIN": str(style.get("grain", 0.28)),
        "SCAN": str(style.get("scanlines", 0.22)),
        "TEXT": roles["text"],
        "TEXT_SOFT": roles["text_soft"],
        "TEXT_MUTE": roles["text_mute"],
        "LINE": roles["line"],
        "ON_ACCENT": roles["on_accent"],
        "SHADOW": roles["shadow"],
        "INDEX_ITEMS": index_rows(copy.get("index", [])),
        "CHIPS": chip_rows(copy.get("index", [])),
    }
    for key, value in copy.items():
        if key == "index":
            continue
        t[key.upper()] = str(value)
    return t


def fill(template: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        template = template.replace("{{%s}}" % key, value)
    return template


def render(spec: dict, style: dict, *, scale: int = 2, out_name: str | None = None) -> Path:
    template = (TEMPLATES / f"{spec.get('template', 'slide_text')}.html").read_text()
    html = fill(template, tokens(spec, style))

    built = Path("/tmp/opencode/_built.html")
    built.parent.mkdir(parents=True, exist_ok=True)
    built.write_text(html)

    w = int(spec.get("width", 1080))
    h = int(spec.get("height", 1350))
    out = OUT / (out_name or spec["out"])
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--no-sandbox", "--default-background-color=00000000",
        "--virtual-time-budget=3000",
        f"--force-device-scale-factor={scale}",
        f"--window-size={w},{h}",
        f"--screenshot={out}",
        f"file://{built}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"chrome failed:\n{proc.stderr[-2000:]}")

    _export_jpg(out, w, h)
    return out


def render_file(spec_path: str | Path, style_path: str | Path | None = None,
                scale: int = 2, out_name: str | None = None) -> Path:
    from .palette import load_style

    spec_path = resolve(spec_path)
    spec = json.loads(spec_path.read_text())
    style_file = resolve(style_path) if style_path else (resolve(spec["style"]) if spec.get("style") else None)
    return render(spec, load_style(style_file), scale=scale, out_name=out_name)


def _export_jpg(png: Path, w: int, h: int) -> None:
    """Also write a 1x JPG for uploading."""
    from PIL import Image

    im = Image.open(png).convert("RGB")
    if im.size != (w, h):
        im = im.resize((w, h), Image.LANCZOS)
    im.save(png.with_name(png.stem + "-1080.jpg"), quality=93, subsampling=1, optimize=True)
