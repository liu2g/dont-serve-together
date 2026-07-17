"""Tests for load_cluster against the three sample clusters."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from dont_serve_together.cluster import ClusterLoadError, load_cluster

EXAMPLES = Path(__file__).parent / "cluster_examples"

IA_MOD_KEYS = ["workshop-1467214795", "workshop-3435352667"]

CLUSTER_2_MOD_KEYS = [
    "workshop-1185229307",
    "workshop-1530801499",
    "workshop-1803285852",
    "workshop-1909182187",
    "workshop-2097358269",
    "workshop-2166704267",
    "workshop-2189004162",
    "workshop-2784048339",
    "workshop-2950657933",
    "workshop-2968712975",
    "workshop-2986515645",
    "workshop-3155066294",
    "workshop-3163270064",
    "workshop-3467205041",
    "workshop-3523647536",
    "workshop-3604214733",
    "workshop-374550642",
    "workshop-378160973",
    "workshop-818739975",
]


def test_cluster_2_preset():
    cluster = load_cluster(EXAMPLES / "Cluster_2")
    assert cluster.name == "Cluster_2"
    assert [shard.name for shard in cluster.shards] == ["Caves", "Master"]

    master = cluster.shard("Master")
    caves = cluster.shard("Caves")
    assert master is not None and caves is not None
    assert cluster.master_shard is master
    assert master.server_ini.shard_name is None
    assert master.server_ini.server_port == 10999
    assert not caves.is_master
    assert caves.server_ini.shard_name == "Caves"
    assert caves.server_ini.shard_id == "3791571480"

    assert master.mod_overrides.keys() == CLUSTER_2_MOD_KEYS
    assert caves.mod_overrides.keys() == CLUSTER_2_MOD_KEYS
    entry = master.mod_overrides.get("workshop-818739975")
    assert entry is not None and entry.enabled
    assert entry.configuration_options.fields == {"DFV_Language": "CN"}

    # No optional root files in a game-UI cluster.
    assert cluster.cluster_token is None
    assert cluster.adminlist is None
    assert cluster.blocklist is None


def test_cluster_islandstart_merged_template():
    cluster = load_cluster(EXAMPLES / "Cluster_IslandStart")
    assert [shard.name for shard in cluster.shards] == ["Caves", "Island", "Master", "Volcano"]

    # The master role belongs to the Island folder, not the folder named Master.
    master_shard = cluster.master_shard
    assert master_shard is not None and master_shard.name == "Island"
    folder_master = cluster.shard("Master")
    assert folder_master is not None and not folder_master.is_master
    assert folder_master.server_ini.shard_name == "Master"
    assert folder_master.server_ini.shard_id == "3"

    # Merged mod list: IA mods first, then the preset's, identical in all shards.
    expected_keys = IA_MOD_KEYS + CLUSTER_2_MOD_KEYS
    for shard in cluster.shards:
        assert shard.mod_overrides.keys() == expected_keys
        assert shard.mod_overrides.entries == cluster.shards[0].mod_overrides.entries

    # Optional root files present in the template-derived cluster.
    assert cluster.cluster_token is not None
    assert cluster.adminlist is not None
    assert cluster.blocklist is not None

    assert cluster.cluster_ini.cluster_name == "Example Cluster"


def test_cluster_3_played_cluster():
    cluster = load_cluster(EXAMPLES / "Cluster_3")
    # Loads cleanly despite save/, backup/, and log files; only real shards found.
    assert [shard.name for shard in cluster.shards] == ["Caves", "Master"]

    # Folder names are labels: Master holds a Shipwrecked world, Caves a Volcano world.
    master = cluster.shard("Master")
    caves = cluster.shard("Caves")
    assert master is not None and caves is not None
    assert master.level_data.location == "shipwrecked"
    assert master.level_data.world_id == "SURVIVAL_SHIPWRECKED_CLASSIC"
    assert caves.level_data.location == "volcanoworld"
    assert cluster.master_shard is master

    assert cluster.cluster_token is None


def test_non_ascii_round_trip():
    assert load_cluster(EXAMPLES / "Cluster_2").cluster_ini.cluster_name == "Guest的世界"
    cluster_3 = load_cluster(EXAMPLES / "Cluster_3")
    assert cluster_3.cluster_ini.cluster_name == "Guest的世界1"
    master = cluster_3.shard("Master")
    assert master is not None
    assert master.level_data.display_name == "海难"


def test_raw_text_is_byte_faithful():
    cluster = load_cluster(EXAMPLES / "Cluster_2")
    # INI files are CRLF; Lua files are LF-only with no trailing newline.
    assert "\r\n" in cluster.cluster_ini.raw_text
    master = cluster.shard("Master")
    assert master is not None
    assert "\r" not in master.mod_overrides.raw_text
    assert master.mod_overrides.raw_text.endswith("}")


def test_loaded_at_is_aware_and_current():
    before = datetime.now().astimezone()
    cluster = load_cluster(EXAMPLES / "Cluster_2")
    after = datetime.now().astimezone()
    assert cluster.loaded_at.tzinfo is not None
    assert before <= cluster.loaded_at <= after
    assert after - before < timedelta(seconds=5)


def test_missing_cluster_ini(tmp_path):
    with pytest.raises(ClusterLoadError, match=r"cluster\.ini"):
        load_cluster(tmp_path)


def test_no_shard_directories(tmp_path):
    (tmp_path / "cluster.ini").write_text("[GAMEPLAY]\ngame_mode = survival\n", encoding="utf-8")
    with pytest.raises(ClusterLoadError, match="no shard directories"):
        load_cluster(tmp_path)


def test_shard_missing_config_file(tmp_path):
    (tmp_path / "cluster.ini").write_text("[GAMEPLAY]\n", encoding="utf-8")
    shard_dir = tmp_path / "Master"
    shard_dir.mkdir()
    (shard_dir / "server.ini").write_text("[SHARD]\nis_master = true\n", encoding="utf-8")
    with pytest.raises(ClusterLoadError, match=r"leveldataoverride\.lua"):
        load_cluster(tmp_path)


def test_not_a_directory(tmp_path):
    with pytest.raises(ClusterLoadError, match="not a directory"):
        load_cluster(tmp_path / "does_not_exist")


def _write_shard(cluster_dir: Path, name: str, mod_text: str) -> None:
    shard = cluster_dir / name
    shard.mkdir()
    (shard / "server.ini").write_text("[SHARD]\nis_master = true\n", encoding="utf-8")
    (shard / "leveldataoverride.lua").write_text(
        'return { id="SURVIVAL_TOGETHER", location="forest" }', encoding="utf-8"
    )
    (shard / "modoverrides.lua").write_text(mod_text, encoding="utf-8")


def test_mismatched_modoverrides_rejected(tmp_path):
    (tmp_path / "cluster.ini").write_text("[GAMEPLAY]\n", encoding="utf-8")
    _write_shard(tmp_path, "Master", 'return { ["workshop-1"]={ enabled=true } }')
    _write_shard(tmp_path, "Caves", 'return { ["workshop-2"]={ enabled=true } }')
    with pytest.raises(ClusterLoadError, match="not byte-identical across shards"):
        load_cluster(tmp_path)


def test_identical_modoverrides_accepted(tmp_path):
    (tmp_path / "cluster.ini").write_text("[GAMEPLAY]\n", encoding="utf-8")
    mod_text = 'return { ["workshop-1"]={ enabled=true } }'
    _write_shard(tmp_path, "Master", mod_text)
    _write_shard(tmp_path, "Caves", mod_text)
    assert len(load_cluster(tmp_path).shards) == 2
