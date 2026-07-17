"""Tests for the dedicated_server_mods_setup.lua check and populate logic."""

import shutil
from pathlib import Path

import pytest

from dont_serve_together import mods_setup
from dont_serve_together.cluster import LuaTable, ModEntry, load_cluster
from dont_serve_together.mods_setup import (
    MODS_SETUP_NAME,
    ModsSetupError,
    ModsSetupStatus,
    append_missing_mods,
    check_mods_setup,
    enabled_workshop_ids,
    parse_installed_mod_ids,
)

EXAMPLES = Path(__file__).parent / "cluster_examples"
SETUP_FILE = Path(__file__).parent / "game_dir_example" / "mods" / MODS_SETUP_NAME

# The stock fixture installs exactly the two IA mods (the ids appended after
# Klei's stock comments); its commented-out examples must never count.
STOCK_IDS = {"1467214795", "3435352667"}
COMMENTED_EXAMPLE_IDS = {"350811795", "379114180"}


def _entry(key: str, enabled: bool = True) -> ModEntry:
    return ModEntry(key=key, enabled=enabled, configuration_options=LuaTable(), source_text="")


# --- parse_installed_mod_ids ---


def test_parse_stock_fixture():
    text = SETUP_FILE.read_text(encoding="utf-8", newline="")
    assert parse_installed_mod_ids(text) == STOCK_IDS
    assert parse_installed_mod_ids(text).isdisjoint(COMMENTED_EXAMPLE_IDS)


def test_parse_quote_styles_and_whitespace():
    text = "ServerModSetup( '123' )\nServerModSetup  (\"456\")\nServerModSetup(\"789')"
    assert parse_installed_mod_ids(text) == {"123", "456"}


def test_parse_line_comments_stripped():
    text = '--ServerModSetup("111")\nServerModSetup("222") --ServerModSetup("333")'
    assert parse_installed_mod_ids(text) == {"222"}


def test_parse_block_comments_stripped():
    text = '--[[\nServerModSetup("111")\n]]\nServerModSetup("222")'
    assert parse_installed_mod_ids(text) == {"222"}


def test_parse_collections_ignored():
    assert parse_installed_mod_ids('ServerModCollectionSetup("999")') == set()


def test_parse_other_function_names_ignored():
    assert parse_installed_mod_ids('MyServerModSetup("777")') == set()


# --- enabled_workshop_ids ---


def test_enabled_workshop_ids_filters_and_dedups():
    entries = [
        _entry("workshop-2"),
        _entry("workshop-1"),
        _entry("workshop-3", enabled=False),
        _entry("my-local-mod"),
        _entry("workshop-2"),
    ]
    assert enabled_workshop_ids(entries) == ["2", "1"]


# --- check_mods_setup ---


def test_check_island_start_against_stock():
    island = load_cluster(EXAMPLES / "Cluster_IslandStart")
    cluster_2 = load_cluster(EXAMPLES / "Cluster_2")
    check = check_mods_setup(island, SETUP_FILE)

    assert check.status is ModsSetupStatus.OK
    assert check.offers_populate
    # The IA mods are installed by the stock fixture; what's missing is exactly
    # the merged-in preset's mod list, in modoverrides entry order.
    assert check.missing_ids == enabled_workshop_ids(cluster_2.shards[0].mod_overrides.entries)
    assert len(check.missing_ids) == 19
    assert STOCK_IDS.isdisjoint(check.missing_ids)


def test_check_missing_file(tmp_path: Path):
    island = load_cluster(EXAMPLES / "Cluster_IslandStart")
    check = check_mods_setup(island, tmp_path / MODS_SETUP_NAME)
    assert check.status is ModsSetupStatus.FILE_MISSING
    assert not check.offers_populate


def test_check_unreadable_file(tmp_path: Path):
    island = load_cluster(EXAMPLES / "Cluster_IslandStart")
    target = tmp_path / MODS_SETUP_NAME
    target.write_bytes(b"\xff\xfe\x00ServerModSetup")
    check = check_mods_setup(island, target)
    assert check.status is ModsSetupStatus.UNREADABLE
    assert check.error is not None and "UTF-8" in check.error
    assert not check.offers_populate


# --- append_missing_mods ---


def test_append_to_stock_copy(tmp_path: Path):
    island = load_cluster(EXAMPLES / "Cluster_IslandStart")
    target = tmp_path / MODS_SETUP_NAME
    shutil.copyfile(SETUP_FILE, target)
    original = target.read_bytes()
    missing = check_mods_setup(island, target).missing_ids

    assert append_missing_mods(island, target) == len(missing)

    data = target.read_bytes()
    assert data.startswith(original)  # a true append: existing bytes untouched
    expected_block = "\r\n" + "\r\n".join(f'ServerModSetup("{mod_id}")' for mod_id in missing)
    assert data[len(original) :] == expected_block.encode("ascii")
    assert not data.endswith(b"\n")  # the stock convention: no trailing newline

    after = check_mods_setup(island, target)
    assert after.status is ModsSetupStatus.OK and after.missing_ids == []
    assert append_missing_mods(island, target) == 0
    assert target.read_bytes() == data


def test_append_matches_lf_style(tmp_path: Path):
    cluster_2 = load_cluster(EXAMPLES / "Cluster_2")
    target = tmp_path / MODS_SETUP_NAME
    target.write_bytes(b'ServerModSetup("999")\n')

    count = append_missing_mods(cluster_2, target)

    ids = enabled_workshop_ids(cluster_2.shards[0].mod_overrides.entries)
    assert count == len(ids)
    expected = b'ServerModSetup("999")\n' + "\n".join(f'ServerModSetup("{mod_id}")' for mod_id in ids).encode()
    assert target.read_bytes() == expected


def test_append_missing_file_raises(tmp_path: Path):
    island = load_cluster(EXAMPLES / "Cluster_IslandStart")
    with pytest.raises(ModsSetupError):
        append_missing_mods(island, tmp_path / MODS_SETUP_NAME)


# --- session game directory ---


def test_game_directory_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mods_setup, "_game_directory_override", None)
    assert mods_setup.game_directory() == mods_setup._DEFAULT_GAME_DIRECTORY

    mods_setup.set_game_directory(tmp_path)
    assert mods_setup.game_directory() == tmp_path
    assert mods_setup.mods_setup_path() == tmp_path / "mods" / MODS_SETUP_NAME

    # The default-path wiring is exercised against the override, never a real install.
    island = load_cluster(EXAMPLES / "Cluster_IslandStart")
    assert check_mods_setup(island).status is ModsSetupStatus.FILE_MISSING
