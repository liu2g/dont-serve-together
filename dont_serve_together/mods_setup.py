"""Checking and populating the game's ``dedicated_server_mods_setup.lua``.

The program never downloads mods itself: the game server runs this file on
boot and downloads every mod passed to ``ServerModSetup``. This module reads
the file with a comment-aware text scan (the file is arbitrary user-editable
Lua, so anything short of a Lua interpreter is an approximation by design),
compares the ids against a cluster's enabled workshop mods, and appends
``ServerModSetup`` lines for the missing ones. The file belongs to the game
install, not to a cluster, so nothing here touches the cluster model.

The game directory is session state: an override set from the UI's
"Set Game Directory" command, falling back to the platform's default Steam
install location. It is never persisted to disk.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from enum import Enum, auto
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from dont_serve_together.cluster import Cluster, ModEntry

MODS_SETUP_NAME = "dedicated_server_mods_setup.lua"


class ModsSetupError(Exception):
    """Raised when ``dedicated_server_mods_setup.lua`` cannot be read or appended to."""


def _default_game_directory() -> Path:
    """Return the platform's default Steam install location of the game."""
    if sys.platform == "win32":
        return Path("C:/Program Files (x86)/Steam/steamapps/common/Don't Starve Together")
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Steam/steamapps/common/Don't Starve Together"
    return Path.home() / ".steam/steam/steamapps/common/Don't Starve Together"


_DEFAULT_GAME_DIRECTORY = _default_game_directory()

_game_directory_override: Path | None = None


def set_game_directory(path: Path) -> None:
    """Set the session's game directory (accepted as picked, no validation).

    Args:
        path: The folder the user picked as the game directory.
    """
    global _game_directory_override
    _game_directory_override = path


def game_directory() -> Path:
    """Return the session's game directory: the override, else the platform default."""
    return _game_directory_override or _DEFAULT_GAME_DIRECTORY


def mods_setup_path() -> Path:
    """Return the session's path of ``dedicated_server_mods_setup.lua``."""
    return game_directory() / "mods" / MODS_SETUP_NAME


class ModsSetupStatus(Enum):
    """Outcome of reading ``dedicated_server_mods_setup.lua``."""

    OK = auto()
    """The file was read; ``missing_ids`` is meaningful."""

    FILE_MISSING = auto()
    """No file at the expected path -- likely a wrong game directory."""

    UNREADABLE = auto()
    """The file exists but could not be read; ``error`` has the reason."""


class ModsSetupCheck(BaseModel):
    """Result of checking a cluster's mods against ``dedicated_server_mods_setup.lua``.

    Produced alongside every cluster load/reload; a missing or unreadable file
    is a status, never an exception, because it must surface as a warning.
    """

    model_config = ConfigDict(frozen=True)

    path: Path
    status: ModsSetupStatus
    missing_ids: list[str] = []
    error: str | None = None

    @property
    def offers_populate(self) -> bool:
        """Whether the populate action applies: the file was read and mods are missing."""
        return self.status is ModsSetupStatus.OK and bool(self.missing_ids)


# The stock file's commented-out examples must not count as installed, so
# comments are stripped before matching. Only basic --[[ ]] block comments are
# recognized (no long-bracket --[==[ ]==] forms).
_BLOCK_COMMENT = re.compile(r"--\[\[.*?\]\]", re.DOTALL)
_LINE_COMMENT = re.compile(r"--[^\n]*")
_SERVER_MOD_SETUP = re.compile(r"""\bServerModSetup\s*\(\s*(["'])(\d+)\1\s*\)""")

_WORKSHOP_KEY = re.compile(r"workshop-(\d+)")


def parse_installed_mod_ids(text: str) -> set[str]:
    """Extract the workshop ids passed to ``ServerModSetup`` in the file text.

    ``ServerModCollectionSetup`` calls are ignored: a collection's contents
    cannot be known without the Steam network.

    Args:
        text: The ``dedicated_server_mods_setup.lua`` content.

    Returns:
        The set of mod ids (bare digits, no ``workshop-`` prefix).
    """
    stripped = _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub(" ", text))
    return {match.group(2) for match in _SERVER_MOD_SETUP.finditer(stripped)}


def enabled_workshop_ids(entries: Iterable[ModEntry]) -> list[str]:
    """Return the numeric workshop ids of the enabled mod entries, in entry order.

    Keys not shaped ``workshop-<digits>`` (e.g. local mods) are skipped:
    ``ServerModSetup`` cannot download them.

    Args:
        entries: Mod entries from a ``modoverrides.lua``.

    Returns:
        The deduplicated ids of the enabled workshop mods.
    """
    ids: list[str] = []
    for entry in entries:
        match = _WORKSHOP_KEY.fullmatch(entry.key)
        if entry.enabled and match is not None and match.group(1) not in ids:
            ids.append(match.group(1))
    return ids


def check_mods_setup(cluster: Cluster, path: Path | None = None) -> ModsSetupCheck:
    """Check the cluster's enabled workshop mods against the setup file.

    Args:
        cluster: The loaded cluster.
        path: The setup file; defaults to the session's :func:`mods_setup_path`.

    Returns:
        The check result; missing and unreadable files become statuses.
    """
    target = path if path is not None else mods_setup_path()
    if not target.is_file():
        return ModsSetupCheck(path=target, status=ModsSetupStatus.FILE_MISSING)
    try:
        text = _read_text(target)
    except ModsSetupError as exc:
        return ModsSetupCheck(path=target, status=ModsSetupStatus.UNREADABLE, error=str(exc))
    return ModsSetupCheck(path=target, status=ModsSetupStatus.OK, missing_ids=_missing_ids(cluster, text))


def append_missing_mods(cluster: Cluster, path: Path | None = None) -> int:
    """Append ``ServerModSetup`` lines for the cluster's missing mods.

    The file is re-read immediately before appending, so a stale load-time
    snapshot cannot cause duplicates; only ids still missing are written, in
    ``modoverrides.lua`` entry order. The write is a true append -- existing
    content is never rewritten -- using the file's own line-ending style and
    leaving no trailing newline, the stock file's convention.

    Args:
        cluster: The loaded cluster.
        path: The setup file; defaults to the session's :func:`mods_setup_path`.

    Returns:
        The number of mods appended (0 if none were missing).

    Raises:
        ModsSetupError: If the file is missing, unreadable, or cannot be
            appended to.
    """
    target = path if path is not None else mods_setup_path()
    if not target.is_file():
        raise ModsSetupError(f"{target}: file not found")
    text = _read_text(target)
    missing = _missing_ids(cluster, text)
    if not missing:
        return 0
    try:
        with target.open("a", encoding="utf-8", newline="") as handle:
            handle.write(_append_block(text, missing))
    except OSError as exc:
        raise ModsSetupError(f"{target}: {exc}") from exc
    return len(missing)


def _missing_ids(cluster: Cluster, text: str) -> list[str]:
    """Return the cluster's enabled workshop ids that ``text`` does not install.

    ``modoverrides.lua`` is byte-identical across shards (loader-enforced), so
    the first shard's entries are the cluster's mod list.
    """
    installed = parse_installed_mod_ids(text)
    cluster_ids = enabled_workshop_ids(cluster.shards[0].mod_overrides.entries)
    return [mod_id for mod_id in cluster_ids if mod_id not in installed]


def _append_block(existing: str, ids: list[str]) -> str:
    """Build the text to append: one ``ServerModSetup`` line per id."""
    newline = "\r\n" if "\r\n" in existing else "\n"
    lines = newline.join(f'ServerModSetup("{mod_id}")' for mod_id in ids)
    prefix = newline if existing and not existing.endswith("\n") else ""
    return prefix + lines


def _read_text(path: Path) -> str:
    """Read the setup file exactly (UTF-8, newlines preserved, no translation).

    Raises:
        ModsSetupError: If the file cannot be read or is not valid UTF-8.
    """
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return handle.read()
    except OSError as exc:
        raise ModsSetupError(f"{path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ModsSetupError(f"{path}: not valid UTF-8 ({exc})") from exc
