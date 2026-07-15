"""Cluster scaffold: in-memory representation of DST cluster directories.

``load_cluster`` reads a cluster directory into a read-only snapshot of frozen
Pydantic models. Config files are kept whole (exact raw text) with light
parsed views on top; only the important keys are typed.
"""

from dont_serve_together.cluster.inidata import IniParseError, read_ini
from dont_serve_together.cluster.loader import ClusterLoadError, load_cluster
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
    ConfigFile,
    IniFile,
    LevelData,
    ModEntry,
    ModOverrides,
    ServerIni,
    Shard,
)

__all__ = [
    "Cluster",
    "ClusterIni",
    "ClusterLoadError",
    "ConfigFile",
    "IniFile",
    "IniParseError",
    "LevelData",
    "LuaParseError",
    "LuaTable",
    "ModEntry",
    "ModOverrides",
    "ServerIni",
    "Shard",
    "TopLevelEntry",
    "load_cluster",
    "parse_lua_table",
    "parse_top_level_entries",
    "read_ini",
]
