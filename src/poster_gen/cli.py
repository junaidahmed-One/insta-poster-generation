"""Command line interface.

    uv run poster make content/ai-engineering.md          # content -> poster
    uv run poster make content/x.md --ref references/y.jpg
    uv run poster build                                  # render specs/
    uv run poster style references/ref.jpg               # reference -> style json
    uv run poster photo shot.jpg -o cut.png              # photo -> duotone cutout
"""

from __future__ import annotations

import argparse
import json
import sys

from .paths import SPECS, STYLES, resolve


def cmd_make(args: argparse.Namespace) -> int:
    from . import content as content_mod
    from .palette import extract_style, load_style, save_style
    from .render import render
    from .theme import pick

    data = content_mod.parse(args.content)
    theme, scores = pick(data, args.theme)

    if args.ref:
        style = extract_style(resolve(args.ref))
        save_style(style, STYLES / f"{style['name']}.json")
        source = f"reference {args.ref}"
    else:
        style = {**theme["palette"], **theme["texture"]}
        source = f"theme {theme['name']}"

    name = args.out or content_mod.slug(data["title"])
    spec = {
        "template": args.template or "slide_text",
        "out": f"{name}.png",
        "photo": theme["figure"],
        "width": 1080,
        "height": 1350,
        "copy": content_mod.to_copy(data),
    }

    out = render(spec, style)
    (SPECS / f"{name}.json").write_text(json.dumps(spec, indent=2) + "\n")

    ranked = ", ".join(f"{k}={v:g}" for k, v in sorted(scores.items(), key=lambda kv: -kv[1])[:3])
    print(f"theme  {theme['name']}  ({source}; {ranked})")
    print(f"spec   specs/{name}.json")
    print(f"out    {out.relative_to(resolve('.'))}  ({out.stat().st_size // 1024} KB)")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    from .render import render_file

    style_path = args.style
    if args.from_ref:
        from .palette import extract_style, save_style

        style = extract_style(resolve(args.from_ref))
        style_path = save_style(style, STYLES / f"{style['name']}.json")
        print(
            f"style: bg={style['bg']} accent={style['accent']} "
            f"ink={style['ink']} paper={style['paper']}"
        )

    specs = sorted(SPECS.glob("*.json")) if (args.all or not args.specs) else [resolve(s) for s in args.specs]
    if not specs:
        print("no specs found in specs/", file=sys.stderr)
        return 1

    for spec in specs:
        out = render_file(spec, style_path=style_path, scale=args.scale, out_name=args.out)
        print(f"{out.relative_to(resolve('.'))}  ({out.stat().st_size // 1024} KB)")
    return 0


def cmd_style(args: argparse.Namespace) -> int:
    from .palette import extract_style, save_style

    style = extract_style(resolve(args.reference), name=args.name)
    dst = resolve(args.out) if args.out else STYLES / f"{style['name']}.json"
    save_style(style, dst)
    print(f"{dst}  bg={style['bg']} accent={style['accent']} ink={style['ink']} paper={style['paper']}")
    return 0


def cmd_photo(args: argparse.Namespace) -> int:
    from .photo import key_photo

    crop = tuple(float(v) for v in args.crop.split(","))
    if len(crop) != 4:
        print("--crop wants 4 comma-separated floats", file=sys.stderr)
        return 1
    dst = resolve(args.out)
    key_photo(
        resolve(args.source), dst,
        crop=crop,
        background=args.background,
        ramp=(args.shadow, args.light),
    )
    print(dst)
    return 0


def cmd_themes(args: argparse.Namespace) -> int:
    from .theme import load_themes

    for name, theme in load_themes().items():
        palette = theme["palette"]
        print(f"{name:10s} {theme['label']:28s} bg={palette['bg']} accent={palette['accent']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="poster", description="Code-rendered social posters")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("make", help="content file -> poster")
    m.add_argument("content", help="markdown or key: value file")
    m.add_argument("--ref", help="reference image to borrow the palette from")
    m.add_argument("--theme", help="force a theme instead of detecting one")
    m.add_argument("--template", default="slide_text", help="template name (default slide_text)")
    m.add_argument("--out", help="output name (default: slug of the title)")
    m.set_defaults(func=cmd_make)

    b = sub.add_parser("build", help="render specs to out/")
    b.add_argument("specs", nargs="*", help="spec files (default: all of specs/)")
    b.add_argument("--all", action="store_true", help="render every spec in specs/")
    b.add_argument("--style", help="style json to override the spec's style")
    b.add_argument("--from-ref", metavar="IMAGE",
                   help="extract a palette from a reference image, then render with it")
    b.add_argument("--out", help="output filename override")
    b.add_argument("--scale", type=int, default=2, help="device pixel ratio (default 2)")
    b.set_defaults(func=cmd_build)

    s = sub.add_parser("style", help="extract a palette from a reference image")
    s.add_argument("reference")
    s.add_argument("-o", "--out")
    s.add_argument("-n", "--name")
    s.set_defaults(func=cmd_style)

    ph = sub.add_parser("photo", help="key a photo into a duotone cutout")
    ph.add_argument("source")
    ph.add_argument("-o", "--out", required=True)
    ph.add_argument("--crop", default="0,0,1,1", help="l,t,r,b as 0-1 fractions")
    ph.add_argument("--background", choices=["dark", "light"], default="dark")
    ph.add_argument("--shadow", default="#283FA0")
    ph.add_argument("--light", default="#F4F1E8")
    ph.set_defaults(func=cmd_photo)

    t = sub.add_parser("themes", help="list available themes")
    t.set_defaults(func=cmd_themes)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
