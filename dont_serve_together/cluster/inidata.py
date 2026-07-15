"""Tolerant, read-only reader for DST INI files (``cluster.ini``, ``server.ini``).

The game's INI files are simple ``[SECTION]`` / ``key = value`` text, but real
files are sloppy: trailing tabs on section headers and values (the IA
template's ``[SHARD]`` block), empty values (``cluster_password = ``), and
non-ASCII UTF-8 values. This reader tolerates all of that and preserves key
case. INI files are never written -- they are copied whole.
"""

from __future__ import annotations

import configparser


class IniParseError(ValueError):
    """Raised when text cannot be read as an INI file."""


class _CaseSensitiveParser(configparser.ConfigParser):
    """ConfigParser that keeps option names exactly as written."""

    def optionxform(self, optionstr: str) -> str:
        """Return the option name unchanged (no lowercasing)."""
        return optionstr


def read_ini(text: str) -> dict[str, dict[str, str]]:
    """Parse INI text into a plain ``{section: {key: value}}`` mapping.

    Args:
        text: Full file content.

    Returns:
        Sections in file order, each mapping keys (case preserved) to values
        (surrounding whitespace stripped; empty values become ``""``).

    Raises:
        IniParseError: If the text is not readable as an INI file.
    """
    parser = _CaseSensitiveParser(interpolation=None, strict=False)
    try:
        parser.read_string(text.lstrip("\N{ZERO WIDTH NO-BREAK SPACE}"))
    except configparser.Error as exc:
        raise IniParseError(str(exc)) from exc
    return {section: dict(parser[section]) for section in parser.sections()}
