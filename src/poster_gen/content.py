"""Parse a content file into poster copy.

Accepts either a simple `key: value` file or loose markdown:

    title: AI Engineering in 5 Slides
    kicker: A practical guide for builders
    list: Models, Context, Evals, Agents, Cost

    --- or ---

    # AI Engineering in 5 Slides
    A practical guide for builders
    - Models
    - Context
    Most teams can ship a demo...
"""

from __future__ import annotations

import re
from pathlib import Path

KEYS = {
    "title", "kicker", "deck", "list", "cta", "stamp", "rail_left",
    "rail_mid", "index_head", "tag", "swipe",
}


def parse(src: str | Path) -> dict:
    """Return a dict with at least `title`; other keys are optional."""
    try:
        path = Path(src)
        text = path.read_text() if path.is_file() else str(src)
    except OSError:
        text = str(src)
    lines = [ln.rstrip() for ln in text.splitlines()]

    data: dict[str, str] = {}
    bullets: list[str] = []
    paragraphs: list[str] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^([a-z_]+)\s*:\s*(.+)$", line, re.I)
        if m and m.group(1).lower() in KEYS:
            data[m.group(1).lower()] = m.group(2).strip()
            continue
        if line.startswith("# "):
            data.setdefault("title", line[2:].strip())
            continue
        if line.startswith("## "):
            data.setdefault("kicker", line[3:].strip())
            continue
        if re.match(r"^[-*]\s+", line):
            bullets.append(re.sub(r"^[-*]\s+", "", line).strip())
            continue
        paragraphs.append(line)

    if "title" not in data:
        if paragraphs:
            data["title"] = paragraphs.pop(0)
        elif bullets:
            data["title"] = bullets.pop(0)
        else:
            raise ValueError("content needs a title")

    # a short opening line is a subtitle, not body copy
    if "kicker" not in data and paragraphs:
        first = paragraphs[0]
        if len(first.split()) <= 9 and not first.endswith("."):
            data["kicker"] = paragraphs.pop(0)

    if "deck" not in data and paragraphs:
        data["deck"] = " ".join(paragraphs)

    items = bullets
    if not items and data.get("list"):
        items = [s.strip() for s in re.split(r"[,;]", data["list"]) if s.strip()]

    return {
        "title": data["title"],
        "kicker": data.get("kicker", ""),
        "deck": data.get("deck", ""),
        "list": items,
        "stamp": data.get("stamp", "01 / 05"),
        "rail_left": data.get("rail_left", "Field Notes"),
        "rail_mid": data.get("rail_mid", "2026"),
        "index_head": data.get("index_head", "In this set"),
        "swipe": data.get("swipe", "Swipe"),
    }


def slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:60] or "poster"


def to_copy(content: dict) -> dict:
    """Map parsed content onto the generic template's tokens."""
    deck = content["deck"]
    first = deck.split(". ")[0].strip()
    lead = (first + ".") if first and not first.endswith(".") else first
    sub = content["kicker"] or content["rail_mid"]

    return {
        "rail_left": content["rail_left"],
        "rail_mid": content["rail_mid"],
        "stamp": content["stamp"],
        "kicker": content["kicker"],
        "title": content["title"],
        "deck": content["deck"],
        "index_head": content["index_head"],
        "index": content["list"],
        "bar_lead": lead or content["title"],
        "bar_sub": sub,
        "swipe": content["swipe"],
    }
