# poster-gen

Code-rendered social posters in the editorial collage style — electric field colour,
condensed display type, duotone classical bust, halftone + scanline texture.

Give it a reference image and it adopts that colourway; give it copy and it renders
a 1080×1350 poster (plus a ready-to-upload JPG) into `out/`.

No image model is involved. The photo layer is a real photograph that gets keyed,
duotoned and re-composited with CSS; everything else is type and vector, so the
output stays sharp at any size.

## Setup

```bash
uv sync          # creates .venv with Python 3.14 (pinned in .python-version)
```

## Use

```bash
# render every spec in specs/
uv run poster build

# render one spec
uv run poster build specs/slide-01.json

# adopt the palette of a reference image, then render
uv run poster build --from-ref references/my-reference.jpg

# just extract a palette (writes styles/<name>.json)
uv run poster style references/my-reference.jpg

# key a new photo into a duotone cutout
uv run poster photo path/to/shot.jpg -o assets/photos/cut.png --crop 0.1,0.1,0.9,0.6
```

Outputs land in `out/`:

| file | size | use |
|---|---|---|
| `slide-01-ai-engineering.png` | 2160×2700 | master, retina/print |
| `slide-01-ai-engineering-1080.jpg` | 1080×1350 | Instagram / LinkedIn upload |

## How a render works

1. `specs/*.json` holds the copy, the photo reference and the style to use.
2. `styles/*.json` holds four colours (`bg`, `accent`, `ink`, `paper`) plus texture
   strength. Readable text/line colours are derived from those at render time, so a
   light palette flips the type to dark automatically.
3. The photo is re-keyed into the palette (cached in `assets/photos/cache/`).
4. `templates/slide01.html` is filled with the copy + inlined fonts/images, then
   screenshotted by headless Chrome at 2×.

## Adding a slide

Copy a spec and change the copy — no CSS needed:

```bash
cp specs/slide-01.json specs/slide-02.json
$EDITOR specs/slide-02.json   # change "out", "copy", and the photo if you like
uv run poster build specs/slide-02.json
```

Spec fields: `template`, `out`, `photo`, `style`, `width`, `height`, and `copy`
(any key in `copy` becomes a `{{TOKEN}}` in the template; `index` is a list of
strings rendered as the numbered contents list).

## Reference images

Drop anything you like the look of into `references/` and run
`uv run poster build --from-ref references/that.jpg`. The palette is extracted with
a quantised histogram, so small accents (a lime chip, a red stamp) survive next to a
large flat background.

What transfers automatically: background, accent, ink and paper colours, the type
colour flip, the duotone of the photo, grain strength.

What does **not** transfer: layout and type treatment. Those live in the template —
different compositions (full-bleed photo panels, chip grids, split layouts) are
added as new files in `templates/` and selected per spec via `"template"`.

## Layout

```
src/poster_gen/
  cli.py       build / style / photo commands
  render.py    template fill + headless Chrome screenshot
  palette.py   reference image -> palette + derived text colours
  photo.py     luminance keying -> duotone cutout
templates/     HTML/CSS layouts (slide01.html)
specs/         one JSON per poster
styles/        palettes (default.json)
assets/fonts/  Anton, Bebas Neue, Archivo Black, Barlow Condensed, Playfair Italic
assets/photos/ source photographs (+ cache/)
references/    drop reference images here
out/           rendered posters
```

## Credits

Fonts are SIL Open Font License (Google Fonts). The bust of Julius Caesar is a
public-domain photograph from Wikimedia Commons. Swap in your own photography for
commercial work.
