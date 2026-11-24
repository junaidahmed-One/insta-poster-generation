"""Pick a visual theme for a piece of content.

Scoring is deliberately simple and explainable: each theme declares keywords,
the title counts triple, the kicker double, the rest single. Highest score wins,
ties fall back to `tech`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .paths import ROOT

THEMES = ROOT / "themes"
DEFAULT = "tech"


def load_themes() -> dict[str, dict]:
    out = {}
    for path in sorted(THEMES.glob("*.json")):
        theme = json.loads(path.read_text())
        out[theme["name"]] = theme
    return out


def score(content: dict, theme: dict) -> float:
    fields = {
        "title": 3.0,
        "kicker": 2.0,
        "deck": 1.0,
        "list": 1.0,
    }
    text = {
        "title": content.get("title", ""),
        "kicker": content.get("kicker", ""),
        "deck": content.get("deck", ""),
        "list": " ".join(content.get("list", [])),
    }
    total = 0.0
    for key, weight in fields.items():
        haystack = text[key].lower()
        for kw in theme.get("keywords", []):
            if re.search(r"\b%s\b" % re.escape(kw), haystack):
                total += weight
    return total


def pick(content: dict, name: str | None = None) -> tuple[dict, dict[str, float]]:
    themes = load_themes()
    if name:
        if name not in themes:
            raise KeyError(f"unknown theme '{name}', have: {', '.join(themes)}")
        return themes[name], {name: 1.0}

    scores = {n: score(content, t) for n, t in themes.items()}
    best = max(scores, key=lambda n: scores[n])
    if scores[best] == 0:
        best = DEFAULT
    return themes[best], scores
