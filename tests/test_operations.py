"""Tests for the pipeline operations: level-settings overwrite and mod-list merge."""

from pathlib import Path

import pytest

from dont_serve_together.cluster.luadata import LuaTable, parse_lua_table, serialize_lua_table
from dont_serve_together.cluster.operations import (
    PickedFileError,
    prepare_level_overwrite,
    prepare_mod_merge,
    write_config_text,
)

EXAMPLES = Path(__file__).parent / "cluster_examples"

IA_MOD_KEYS = ["workshop-1467214795", "workshop-3435352667"]


def read_exact(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def write_exact(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def test_level_overwrite_round_trips_sample():
    source = EXAMPLES / "Cluster_2" / "Caves" / "leveldataoverride.lua"
    assert prepare_level_overwrite(source) == read_exact(source)


def test_level_overwrite_requires_id_and_location(tmp_path):
    picked = tmp_path / "leveldataoverride.lua"
    write_exact(picked, 'return { id="DST_CAVE" }')
    with pytest.raises(PickedFileError, match="location"):
        prepare_level_overwrite(picked)
    write_exact(picked, 'return { location="cave" }')
    with pytest.raises(PickedFileError, match="id"):
        prepare_level_overwrite(picked)


def test_level_overwrite_rejects_unparseable(tmp_path):
    picked = tmp_path / "leveldataoverride.lua"
    write_exact(picked, "this is not lua")
    with pytest.raises(PickedFileError):
        prepare_level_overwrite(picked)


def test_level_overwrite_missing_file(tmp_path):
    with pytest.raises(PickedFileError):
        prepare_level_overwrite(tmp_path / "leveldataoverride.lua")


def test_mod_merge_reproduces_cluster_islandstart():
    # The real use case, reconstructed from the samples: IA-template mods plus
    # Cluster_2's preset mods must yield Cluster_IslandStart's merged file.
    island_text = read_exact(EXAMPLES / "Cluster_IslandStart" / "Island" / "modoverrides.lua")
    island_fields = parse_lua_table(island_text).fields
    ia_only = LuaTable(fields={key: island_fields[key] for key in IA_MOD_KEYS})
    merged = prepare_mod_merge(serialize_lua_table(ia_only), EXAMPLES / "Cluster_2" / "Master" / "modoverrides.lua")
    assert merged == island_text


def test_mod_merge_incoming_wins_in_place(tmp_path):
    original = (
        'return { ["workshop-1"]={ configuration_options={ a=1 }, enabled=true },'
        ' ["workshop-2"]={ configuration_options={  }, enabled=true } }'
    )
    picked = tmp_path / "modoverrides.lua"
    write_exact(
        picked,
        'return { ["workshop-1"]={ configuration_options={ a=2 }, enabled=false },'
        ' ["workshop-3"]={ configuration_options={  }, enabled=true } }',
    )
    merged_fields = parse_lua_table(prepare_mod_merge(original, picked)).fields
    # Colliding key stays in place with the incoming value; new key appends.
    assert list(merged_fields) == ["workshop-1", "workshop-2", "workshop-3"]
    replaced = merged_fields["workshop-1"]
    assert isinstance(replaced, LuaTable)
    assert replaced.fields["enabled"] is False
    assert replaced.fields["configuration_options"] == LuaTable(fields={"a": 2})


def test_mod_merge_preserves_unknown_entry_fields(tmp_path):
    picked = tmp_path / "modoverrides.lua"
    write_exact(picked, 'return { ["workshop-1"]={ enabled=true, extra_field="kept" } }')
    merged_fields = parse_lua_table(prepare_mod_merge("return {  }", picked)).fields
    entry = merged_fields["workshop-1"]
    assert isinstance(entry, LuaTable)
    assert entry.fields["extra_field"] == "kept"


def test_mod_merge_rejects_non_table_entry(tmp_path):
    picked = tmp_path / "modoverrides.lua"
    write_exact(picked, 'return { ["workshop-1"]=true }')
    with pytest.raises(PickedFileError, match="mod list"):
        prepare_mod_merge("return {  }", picked)


def test_mod_merge_rejects_positional_entries(tmp_path):
    picked = tmp_path / "modoverrides.lua"
    write_exact(picked, 'return { "workshop-1" }')
    with pytest.raises(PickedFileError, match="mod list"):
        prepare_mod_merge("return {  }", picked)


def test_write_config_text_exact_bytes(tmp_path):
    target = tmp_path / "modoverrides.lua"
    write_config_text(target, "return {\n  a=1 \n}")
    assert target.read_bytes() == b"return {\n  a=1 \n}"
