"""Session-global start location shared by all file pickers.

Every picker starts browsing at a stored location: initially the game's data
directory for the current platform, then the directory of whatever was last
successfully picked. The value lives for the session only; it is never
persisted to disk.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _default_location() -> Path:
    """Return the DST data directory for the current platform."""
    if sys.platform in {"win32", "darwin"}:
        return Path.home() / "Documents" / "Klei" / "DoNotStarveTogether"
    return Path.home() / ".klei" / "DoNotStarveTogether"


_DEFAULT_LOCATION = _default_location()

_last_picked_dir: Path | None = None


def start_location() -> Path:
    """Return the directory the next file picker should start browsing at.

    Returns:
        The directory of the last successful pick, falling back to the
        platform's game data directory, falling back to the user's home.
    """
    for candidate in (_last_picked_dir, _DEFAULT_LOCATION):
        if candidate is not None and candidate.is_dir():
            return candidate
    return Path.home()


def remember_pick(picked: Path) -> None:
    """Record a successful pick so later pickers resume in its directory.

    Args:
        picked: The file or folder the user picked.
    """
    global _last_picked_dir
    _last_picked_dir = picked.parent
