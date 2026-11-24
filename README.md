# poster-gen

Code-rendered social posters. Write content, optionally point at a reference image,
get a 1080×1350 poster in `out/` (plus a ready-to-upload JPG).

Two things adapt to what you write:

- **Typography** — the headline is measured in the browser and shrunk until it fits,
  so titles of any length work.
- **Visual theme** — a keyword matcher picks a palette, a figure and a texture set
  from `themes/`, so a finance post does not look like a tech post.

No image model is involved. The photo layer is a real photograph that gets keyed,
duotoned and re-composited with CSS; everything else is type and vector.

## Setup

```bash
uv sync          # .venv on Python 3.14 (pinned in .python-version)
```

## Make a poster from content

```bash
uv run poster make content/ai-engineering.md
uv run poster make content/pricing-leaks.md --ref references/some-poster.jpg
uv run poster make content/ai-engineering.md --theme culture --out my-post
uv run poster themes          # list available themes
```

Output: `out/<slug>.png` (2160×2700) + `out/<slug>-1080.jpg`, and the resolved
spec is saved to `specs/<slug>.json` so the render is reproducible.

### Content format

Either markdown or `key: value`. Both of these work:

```markdown
# AI Engineering in 5 Slides

A practical guide for builders

- Models
- Context
- Evals
- Agents
- Cost

Most teams can ship a demo. Few build a system.
```

```text
title: AI Engineering in 5 Slides
kicker: A practical guide for builders
list: Models, Context, Evals, Agents, Cost
deck: Most teams can ship a demo. Few build a system.
```

A short first paragraph is treated as the subtitle; the rest becomes body copy.
Bullets become the numbered chip list. Nothing is mandatory except a title.

### How the theme is chosen

Each file in `themes/` declares keywords. The title counts triple, the kicker double,
the deck and list once. Highest score wins; no match falls back to `tech`.

| theme | direction | figure |
|---|---|---|
| `tech` | electric blue / lime | Caesar bust |
| `finance` | deep green / gold | Cicero bust |
| `culture` | oxblood / cream | Diocletian bust |
| `science` | teal / amber | Diocletian bust |

A theme supplies `bg`, `accent`, `ink`, `paper`, grain + scanline strength, and which
photograph to key. Text colours are derived from the palette, so a light background
flips the type to dark automatically.

## Reference images

```bash
uv run poster make content/x.md --ref references/that.jpg   # borrow the palette
uv run poster style references/that.jpg                     # just extract a palette
```

Palette extraction uses a quantised histogram, so small accents (a lime chip, a red
stamp) survive next to a large flat background. A reference overrides the theme's
colours but keeps its figure and texture.

## Other commands

```bash
uv run poster build                          # re-render every spec in specs/
uv run poster build specs/slide-01.json      # one spec
uv run poster photo shot.jpg -o cut.png --crop 0.1,0.1,0.9,0.6   # key a photo
```

## Templates

- `templates/slide_text.html` — the generic layout used by `make`: auto-fitted
  headline, deck, chip list, figure, footer bar.
- `templates/slide01.html` — the hand-tuned cover (the "AI / ENGINEERING / in 5 SLIDES"
  stack). Fixed sizes, so use it only for content shaped like that.

## What is automatic, and what is not

Automatic: palette, figure, texture, headline fitting, deck/chip layout, JPG export.

Not automatic: composition. Both templates place text left and the figure bottom-right.
If a reference has a fundamentally different layout (full-bleed photo, split panels,
chip grid), that needs a new template file — the colour/photo/copy pipeline will then
work with it unchanged.

## Layout

```
src/poster_gen/
  cli.py       make / build / style / photo / themes
  content.py   content file -> copy tokens
  theme.py     keyword scoring -> theme
  render.py    template fill + headless Chrome screenshot
  palette.py   reference image -> palette + derived text colours
  photo.py     luminance keying -> duotone cutout
templates/     HTML/CSS layouts
themes/        palette + figure + texture per subject
content/       example content files
specs/         one JSON per rendered poster
assets/        fonts, source photos, key cache
references/    drop reference images here
out/           rendered posters
```

## Credits

Fonts are SIL Open Font License (Google Fonts). The busts are public-domain
photographs from Wikimedia Commons. Swap in your own photography for commercial work.
