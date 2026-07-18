#!/usr/bin/env -S uv run

"""Convert a PNG logo into a multi-resolution Windows ``.ico`` file.

The resulting icon embeds every size PyInstaller and Windows Explorer expect,
so it can be handed to PyInstaller's ``--icon`` option for the executable.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

# Sizes Windows selects between for taskbar, Explorer, and Alt-Tab; 256 is the
# largest an ``.ico`` can hold and PyInstaller downsizes from there as needed.
ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)


def convert(source: Path, dest: Path) -> None:
    """Write ``source`` as a multi-resolution ICO at ``dest``.

    Args:
        source: Path to the source PNG. Should be square with transparency for
            a clean result; non-square input is scaled by Pillow regardless.
        dest: Path to write the ``.ico`` file to.
    """
    with Image.open(source) as image:
        image.convert("RGBA").save(dest, format="ICO", sizes=[(s, s) for s in ICON_SIZES])


def main() -> None:
    """Parse command-line arguments and run the conversion."""
    default_source = Path("assets/logo.png")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=default_source,
        help="source PNG (default: assets/logo.png)",
    )
    parser.add_argument(
        "dest",
        nargs="?",
        type=Path,
        default=None,
        help="output ICO (default: source with an .ico suffix)",
    )
    args = parser.parse_args()

    dest: Path = args.dest if args.dest is not None else args.source.with_suffix(".ico")
    convert(args.source, dest)
    print(f"Wrote {dest} from {args.source} ({', '.join(f'{s}x{s}' for s in ICON_SIZES)}).")


if __name__ == "__main__":
    main()
