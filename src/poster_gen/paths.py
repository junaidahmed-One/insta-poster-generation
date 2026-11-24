from pathlib import Path

# src/poster_gen/paths.py -> project root
ROOT = Path(__file__).resolve().parents[2]

TEMPLATES = ROOT / "templates"
SPECS = ROOT / "specs"
STYLES = ROOT / "styles"
ASSETS = ROOT / "assets"
OUT = ROOT / "out"


def resolve(p: str | Path) -> Path:
    """Resolve a path relative to the project root."""
    p = Path(p)
    return p if p.is_absolute() else (ROOT / p)
