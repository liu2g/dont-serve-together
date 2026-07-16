"""The two pipeline operations: level-settings overwrite and mod-list merge.

Both operations take a user-picked file, validate it structurally
(loader-level checks only -- no deeper schema, in particular no world-type
check), and produce the exact text the UI previews in the diff view and
writes on Apply. All produced text comes from the Klei-style serializer
(parse -> model -> serialize); nothing is spliced from the original files.
"""

from __future__ import annotations

from pathlib import Path

from dont_serve_together.cluster.luadata import (
    LuaParseError,
    LuaTable,
    LuaValue,
    parse_lua_table,
    serialize_lua_table,
)


class PickedFileError(Exception):
    """Raised when a user-picked file is not valid for the chosen operation."""


def prepare_level_overwrite(picked: Path) -> str:
    """Build the replacement ``leveldataoverride.lua`` text from a picked file.

    Nothing from the shard's original file is carried over: the picked file is
    parsed and re-serialized, and the result replaces the original wholesale.

    Args:
        picked: The user-picked ``leveldataoverride.lua``.

    Returns:
        The serialized replacement text.

    Raises:
        PickedFileError: If the file is unreadable, fails to parse, or lacks
            string ``id`` and ``location`` fields.
    """
    table = _parse_picked(picked)
    for field in ("id", "location"):
        if not isinstance(table.fields.get(field), str):
            raise PickedFileError(f"{picked}: not a level settings file (no string {field!r} field)")
    return serialize_lua_table(table)


def prepare_mod_merge(original_text: str, picked: Path) -> str:
    """Build the merged ``modoverrides.lua`` text for the whole cluster.

    Incoming entries win: an entry whose key already exists replaces the
    original entry in place (keeping the diff aligned), and entries with new
    keys are appended at the end in the picked file's order.

    Args:
        original_text: The cluster's current ``modoverrides.lua`` content
            (already validated by the loader).
        picked: The user-picked ``modoverrides.lua`` to merge in.

    Returns:
        The serialized merged text, to be written to every shard.

    Raises:
        PickedFileError: If the picked file is unreadable, fails to parse, or
            has a top-level entry that is not a string key mapped to a table.
    """
    incoming = _parse_picked(picked)
    if incoming.items:
        raise PickedFileError(f"{picked}: not a mod list file (has entries without keys)")
    for key, value in incoming.fields.items():
        if not isinstance(key, str) or not isinstance(value, LuaTable):
            raise PickedFileError(
                f"{picked}: not a mod list file (entry {key!r} is not a string key mapped to a table)"
            )

    merged: dict[str | int, LuaValue] = dict(parse_lua_table(original_text).fields)
    # dict.update gives exactly the decided merge: existing keys keep their
    # position with the incoming value, new keys append at the end.
    merged.update(incoming.fields)
    return serialize_lua_table(LuaTable(fields=merged))


def write_config_text(path: Path, text: str) -> None:
    """Write config text exactly as given (UTF-8, no BOM, no newline translation).

    Args:
        path: The file to overwrite.
        text: The exact content to write.

    Raises:
        OSError: If the file cannot be written.
    """
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _parse_picked(path: Path) -> LuaTable:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            text = handle.read()
    except OSError as exc:
        raise PickedFileError(f"{path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise PickedFileError(f"{path}: not valid UTF-8 ({exc})") from exc
    try:
        return parse_lua_table(text)
    except LuaParseError as exc:
        raise PickedFileError(f"{path}: {exc}") from exc
