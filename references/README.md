# references/

Drop reference images here — posters, screenshots, album covers, anything whose
colour direction you want to borrow.

```bash
uv run poster build --from-ref references/your-image.jpg
```

This extracts a palette into `styles/<name>.json` and renders every spec with it.

Tips:
- Designed graphics (posters, decks, UI) work far better than photographs.
- 3–6 distinct colours give the cleanest result; muddy images produce muddy palettes.
- Reuse a palette later with `--style styles/<name>.json`.
