#!/usr/bin/env -S uv run

"""Generate a Windows version resource file for PyInstaller from ``pyproject.toml``.

The resulting file is handed to PyInstaller's ``--version-file`` option so the
executable's Properties -> Details tab shows the project's name, version,
author, and license. Only Windows embeds the resource; on other platforms the
option is ignored, so generating the file is harmless there.
"""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path

# Language/codepage pair Windows uses to select the string table:
# US English (0x0409), Unicode (codepage 1200).
TRANSLATION: tuple[int, int] = (0x0409, 1200)


def version_tuple(version: str) -> tuple[int, int, int, int]:
    """Convert a version string into the 4-integer tuple Windows requires.

    Leading numeric release components are kept and padded or truncated to
    length 4. A pre-release or dev suffix (the ``rc1`` in ``0.2.0rc1``) cannot
    be represented in the tuple and is dropped; it stays visible in the
    version resource's string fields.

    Args:
        version: Version string from project metadata, e.g. ``"0.1.0"``.

    Returns:
        Four integers, e.g. ``(0, 1, 0, 0)``.
    """
    parts: list[int] = []
    for component in version.split("."):
        match = re.match(r"\d+", component)
        if match is None:
            break
        parts.append(int(match.group()))
    parts = (parts + [0, 0, 0, 0])[:4]
    return (parts[0], parts[1], parts[2], parts[3])


def generate(pyproject: Path, license_file: Path) -> str:
    """Render ``VSVersionInfo`` text from project metadata.

    Args:
        pyproject: Path to ``pyproject.toml``; supplies every field except the
            copyright notice.
        license_file: Path to the license file whose ``Copyright ...`` line
            becomes ``LegalCopyright``.

    Returns:
        The version-file text in the Python syntax PyInstaller evaluates.
    """
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
    name: str = project["name"]
    version: str = project["version"]
    copyright_line = next(
        (line.strip() for line in license_file.read_text(encoding="utf-8").splitlines() if "Copyright" in line),
        "",
    )
    strings = {
        "ProductName": name,
        "FileDescription": project["description"],
        "FileVersion": version,
        "ProductVersion": version,
        "CompanyName": ", ".join(author["name"] for author in project["authors"]),
        "LegalCopyright": copyright_line,
        "OriginalFilename": f"{name}.exe",
    }
    string_structs = "\n".join(f"                        StringStruct({key!r}, {value!r})," for key, value in strings.items())
    numbers = version_tuple(version)
    table_id = f"{TRANSLATION[0]:04X}{TRANSLATION[1]:04X}"
    return f"""\
VSVersionInfo(
    ffi=FixedFileInfo(
        filevers={numbers},
        prodvers={numbers},
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    {table_id!r},
                    [
{string_structs}
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", {list(TRANSLATION)})]),
    ],
)
"""


def main() -> None:
    """Parse command-line arguments and write the version file."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "dest",
        nargs="?",
        type=Path,
        default=Path("build/file_version_info.txt"),
        help="output path (default: build/file_version_info.txt)",
    )
    args = parser.parse_args()

    dest: Path = args.dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(generate(Path("pyproject.toml"), Path("LICENSE")), encoding="utf-8")
    print(f"Wrote {dest}.")


if __name__ == "__main__":
    main()
