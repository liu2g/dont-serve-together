"""In-memory representation of a DST cluster directory (the "cluster scaffold").

Following the whole-files-first principle, every config file is held as its
exact raw text (the opaque unit that gets copied or replaced whole), with a
light parsed view on top. Only the important keys get typed accessors: the mod
list, the master role and shard name/id, the world identity, and the cluster
name. All models are frozen -- a loaded cluster is a read-only snapshot.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from dont_serve_together.cluster.luadata import LuaTable


class ConfigFile(BaseModel):
    """A cluster config file kept whole, with its exact text."""

    model_config = ConfigDict(frozen=True)

    path: Path
    raw_text: str


class IniFile(ConfigFile):
    """An INI config file with a parsed read-only view."""

    sections: dict[str, dict[str, str]]

    def get(self, section: str, key: str, default: str | None = None) -> str | None:
        """Return the value of ``key`` in ``section``, or ``default`` if absent."""
        return self.sections.get(section, {}).get(key, default)


class ClusterIni(IniFile):
    """The cluster-wide ``cluster.ini``."""

    @property
    def cluster_name(self) -> str | None:
        """The cluster's display name (``[NETWORK] cluster_name``)."""
        return self.get("NETWORK", "cluster_name")


class ServerIni(IniFile):
    """A shard's ``server.ini``: master/slave role and port wiring."""

    @property
    def is_master(self) -> bool:
        """Whether this shard is the cluster's master (``[SHARD] is_master``)."""
        return (self.get("SHARD", "is_master") or "").lower() == "true"

    @property
    def shard_name(self) -> str | None:
        """The shard's wire name (``[SHARD] name``); master shards have none."""
        return self.get("SHARD", "name")

    @property
    def shard_id(self) -> str | None:
        """The shard's wire id (``[SHARD] id``); master shards have none."""
        return self.get("SHARD", "id")

    @property
    def server_port(self) -> int | None:
        """The shard's game port (``[NETWORK] server_port``), if a valid integer."""
        value = self.get("NETWORK", "server_port")
        try:
            return int(value) if value else None
        except ValueError:
            return None


class LevelData(ConfigFile):
    """A shard's ``leveldataoverride.lua``: world type and world-gen settings."""

    table: LuaTable

    def _str_field(self, key: str) -> str | None:
        value = self.table.fields.get(key)
        return value if isinstance(value, str) else None

    @property
    def world_id(self) -> str | None:
        """The world preset id (``id``), e.g. ``SURVIVAL_SHIPWRECKED_CLASSIC``."""
        return self._str_field("id")

    @property
    def location(self) -> str | None:
        """The world location (``location``): forest, cave, shipwrecked, volcanoworld, ..."""
        return self._str_field("location")

    @property
    def display_name(self) -> str | None:
        """The world's display name (``name``)."""
        return self._str_field("name")


class ModEntry(BaseModel):
    """One mod entry of a ``modoverrides.lua``.

    ``source_text`` is the entry's exact source span, kept so the merge can
    splice original bytes instead of re-serializing.
    """

    model_config = ConfigDict(frozen=True)

    key: str
    enabled: bool
    configuration_options: LuaTable
    source_text: str


class ModOverrides(ConfigFile):
    """A shard's ``modoverrides.lua``: the ordered mod list."""

    entries: list[ModEntry]

    def keys(self) -> list[str]:
        """Return the mod keys (``workshop-<id>``) in file order."""
        return [entry.key for entry in self.entries]

    def get(self, key: str) -> ModEntry | None:
        """Return the entry with the given mod key, or ``None`` if absent."""
        for entry in self.entries:
            if entry.key == key:
                return entry
        return None


class Shard(BaseModel):
    """One shard directory of a cluster.

    ``name`` is the folder label only -- it never implies the master role or
    the world type (see ``server_ini.is_master`` / ``level_data.location``).
    """

    model_config = ConfigDict(frozen=True)

    name: str
    path: Path
    server_ini: ServerIni
    level_data: LevelData
    mod_overrides: ModOverrides

    @property
    def is_master(self) -> bool:
        """Whether this shard is the cluster's master."""
        return self.server_ini.is_master


class Cluster(BaseModel):
    """A cluster directory loaded into memory as a read-only snapshot.

    Optional root files (``cluster_token``, ``adminlist``, ``blocklist``) are
    recorded as paths only; their content is out of scope and they are copied
    whole by the pipeline.
    """

    model_config = ConfigDict(frozen=True)

    path: Path
    name: str
    cluster_ini: ClusterIni
    shards: list[Shard]
    cluster_token: Path | None = None
    adminlist: Path | None = None
    blocklist: Path | None = None

    def shard(self, name: str) -> Shard | None:
        """Return the shard whose folder is named ``name``, or ``None`` if absent."""
        for shard in self.shards:
            if shard.name == name:
                return shard
        return None

    @property
    def master_shard(self) -> Shard | None:
        """The shard whose ``server.ini`` declares ``is_master = true``."""
        for shard in self.shards:
            if shard.is_master:
                return shard
        return None
