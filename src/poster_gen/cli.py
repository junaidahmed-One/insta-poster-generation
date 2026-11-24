"""Command line interface.

    uv run poster build                 # render every spec in specs/
    uv run poster build specs/x.json    # render one spec
    uv run poster style references/ref.jpg   # reference image -> style json
    uv run poster photo shot.jpg --crop 0.1,0.1,0.9,0.6   # photo -> duotone cutout
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .paths import SPECS, STYLES, resolve


def cmd_build(args: argparse.Namespace) -> int:
    from .render import render

    style_path = args.style
    if args.from_ref:
        from .palette import extract_style, save_style

        ref = resolve(args.from_ref)
        style = extract_style(ref)
        style_path = save_style(style, STYLES / f"{style['name']}.json")
        print(
            f"style: bg={style['bg']} accent={style['accent']} "
            f"ink={style['ink']} paper={style['paper']}"
        )

    if args.all or not args.specs:
        specs = sorted(SPECS.glob("*.json"))
    else:
        specs = [resolve(s) for s in args.specs]

    if not specs:
        print("no specs found in specs/", file=sys.stderr)
        return 1

    for spec in specs:
        out = render(spec, style_path=style_path, scale=args.scale, out_name=args.out)
        print(f"{out.relative_to(resolve('.'))}  ({out.stat().st_size // 1024} KB)")
    return 0


def cmd_style(args: argparse.Namespace) -> int:
    from .palette import extract_style, save_style

    src = resolve(args.reference)
    style = extract_style(src, name=args.name)
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="poster", description="Code-rendered social posters")
    sub = p.add_subparsers(dest="cmd", required=True)

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

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
