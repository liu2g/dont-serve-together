"""Tests for the tolerant INI reader, against synthetic text and the sample clusters."""

from pathlib import Path

from dont_serve_together.cluster.inidata import read_ini

EXAMPLES = Path(__file__).parent / "cluster_examples"


def read_exact(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def test_template_cluster_ini_with_trailing_tabs():
    sections = read_ini(read_exact(EXAMPLES / "Cluster_IslandStart" / "cluster.ini"))
    # The template's [SHARD] block has trailing tabs on the header and key lines.
    assert sections["SHARD"]["shard_enabled"] == "true"
    assert sections["SHARD"]["master_port"] == "10887"
    assert sections["STEAM"]["steam_group_id"] == "12345678"


def test_empty_values_kept_as_empty_strings():
    sections = read_ini(read_exact(EXAMPLES / "Cluster_IslandStart" / "cluster.ini"))
    assert sections["NETWORK"]["cluster_password"] == ""


def test_key_case_preserved():
    sections = read_ini("[Sec]\nCamelKey = Value\n")
    assert sections == {"Sec": {"CamelKey": "Value"}}


def test_non_ascii_values():
    sections = read_ini(read_exact(EXAMPLES / "Cluster_2" / "cluster.ini"))
    assert sections["NETWORK"]["cluster_name"] == "Guest的世界"


def test_all_sample_ini_files_readable():
    for path in sorted(EXAMPLES.glob("*/cluster.ini")) + sorted(EXAMPLES.glob("*/*/server.ini")):
        sections = read_ini(read_exact(path))
        assert sections, f"no sections read from {path}"
