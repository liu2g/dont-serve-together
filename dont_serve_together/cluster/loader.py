"""Loading a cluster directory from disk into the in-memory model."""

from __future__ import annotations

from pathlib import Path

from dont_serve_together.cluster.inidata import IniParseError, read_ini
from dont_serve_together.cluster.luadata import (
    LuaParseError,
    LuaTable,
    TopLevelEntry,
    parse_lua_table,
    parse_top_level_entries,
)
from dont_serve_together.cluster.model import (
    Cluster,
    ClusterIni,
    LevelData,
    ModEntry,
    ModOverrides,
    ServerIni,
    Shard,
)

_CLUSTER_INI = "cluster.ini"
_SERVER_INI = "server.ini"
_LEVEL_DATA = "leveldataoverride.lua"
_MOD_OVERRIDES = "modoverrides.lua"


class ClusterLoadError(Exception):
    """Raised when a directory cannot be loaded as a DST cluster."""


def load_cluster(path: Path) -> Cluster:
    """Load the cluster directory at ``path`` into a read-only snapshot.

    Shards are the subdirectories that contain a ``server.ini``; everything
    else (runtime ``save/``, ``backup/``, logs, stray files) is ignored.

    Args:
        path: The cluster directory.

    Returns:
        The loaded cluster, shards sorted by folder name.

    Raises:
        ClusterLoadError: If ``path`` is not a cluster directory, a required
            file is missing or unreadable, or a config file fails to parse.
    """
    root = Path(path).resolve()
    if not root.is_dir():
        raise ClusterLoadError(f"not a directory: {root}")

    cluster_ini_path = root / _CLUSTER_INI
    if not cluster_ini_path.is_file():
        raise ClusterLoadError(f"missing {_CLUSTER_INI} in {root}")
    cluster_ini_text = _read_text(cluster_ini_path)
    cluster_ini = ClusterIni(
        path=cluster_ini_path, raw_text=cluster_ini_text, sections=_parse_ini(cluster_ini_text, cluster_ini_path)
    )

    shard_dirs = sorted(
        (child for child in root.iterdir() if child.is_dir() and (child / _SERVER_INI).is_file()),
        key=lambda child: child.name.lower(),
    )
    if not shard_dirs:
        raise ClusterLoadError(f"no shard directories (subdirectories with {_SERVER_INI}) in {root}")

    return Cluster(
        path=root,
        name=root.name,
        cluster_ini=cluster_ini,
        shards=[_load_shard(shard_dir) for shard_dir in shard_dirs],
        cluster_token=_optional_file(root / "cluster_token.txt"),
        adminlist=_optional_file(root / "adminlist.txt"),
        blocklist=_optional_file(root / "blocklist.txt"),
    )


def _load_shard(path: Path) -> Shard:
    for required in (_LEVEL_DATA, _MOD_OVERRIDES):
        if not (path / required).is_file():
            raise ClusterLoadError(f"shard {path}: missing {required}")

    server_ini_path = path / _SERVER_INI
    server_ini_text = _read_text(server_ini_path)
    server_ini = ServerIni(
        path=server_ini_path, raw_text=server_ini_text, sections=_parse_ini(server_ini_text, server_ini_path)
    )

    level_data_path = path / _LEVEL_DATA
    level_data_text = _read_text(level_data_path)
    level_data = LevelData(
        path=level_data_path, raw_text=level_data_text, table=_parse_lua(level_data_text, level_data_path)
    )

    mod_overrides_path = path / _MOD_OVERRIDES
    mod_overrides_text = _read_text(mod_overrides_path)
    try:
        top_level_entries = parse_top_level_entries(mod_overrides_text)
    except LuaParseError as exc:
        raise ClusterLoadError(f"{mod_overrides_path}: {exc}") from exc
    mod_overrides = ModOverrides(
        path=mod_overrides_path,
        raw_text=mod_overrides_text,
        entries=[_build_mod_entry(entry, mod_overrides_path) for entry in top_level_entries],
    )

    return Shard(
        name=path.name, path=path, server_ini=server_ini, level_data=level_data, mod_overrides=mod_overrides
    )


def _build_mod_entry(entry: TopLevelEntry, file: Path) -> ModEntry:
    if not isinstance(entry.key, str):
        raise ClusterLoadError(f"{file}: mod entry key {entry.key!r} is not a string")
    if not isinstance(entry.value, LuaTable):
        raise ClusterLoadError(f"{file}: mod entry {entry.key!r} is not a table")
    configuration_options = entry.value.fields.get("configuration_options")
    return ModEntry(
        key=entry.key,
        enabled=entry.value.fields.get("enabled") is True,
        configuration_options=(
            configuration_options if isinstance(configuration_options, LuaTable) else LuaTable()
        ),
        source_text=entry.source_text,
    )


def _read_text(path: Path) -> str:
    """Read a file as UTF-8 with newlines preserved exactly (no translation)."""
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return handle.read()
    except OSError as exc:
        raise ClusterLoadError(f"{path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ClusterLoadError(f"{path}: not valid UTF-8 ({exc})") from exc


def _parse_ini(text: str, path: Path) -> dict[str, dict[str, str]]:
    try:
        return read_ini(text)
    except IniParseError as exc:
        raise ClusterLoadError(f"{path}: {exc}") from exc


def _parse_lua(text: str, path: Path) -> LuaTable:
    try:
        return parse_lua_table(text)
    except LuaParseError as exc:
        raise ClusterLoadError(f"{path}: {exc}") from exc


def _optional_file(path: Path) -> Path | None:
    return path if path.is_file() else None
