"""Tests for the Lua data-literal parser and serializer, against synthetic snippets and the sample clusters."""

from pathlib import Path

import pytest

from dont_serve_together.cluster.luadata import (
    LuaParseError,
    LuaTable,
    parse_lua_table,
    parse_top_level_entries,
    serialize_lua_table,
)

EXAMPLES = Path(__file__).parent / "cluster_examples"

SAMPLE_LUA_FILES = sorted(EXAMPLES.glob("*/*/leveldataoverride.lua")) + sorted(EXAMPLES.glob("*/*/modoverrides.lua"))


def read_exact(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def test_scalars():
    table = parse_lua_table('return { a=1, b=-10, c=0.7, d=true, e=false, f="x" }')
    assert table.fields == {"a": 1, "b": -10, "c": 0.7, "d": True, "e": False, "f": "x"}
    assert table.items == []


def test_nested_tables_and_lists():
    table = parse_lua_table('return { list={ "a", "b" }, nested={ x={ y=1 } } }')
    assert table.fields["list"] == LuaTable(items=["a", "b"])
    assert table.fields["nested"] == LuaTable(fields={"x": LuaTable(fields={"y": 1})})


def test_non_ascii_keys_and_values():
    table = parse_lua_table('return { ["世界设置"]=false, desc="标准《饥荒》体验。" }')
    assert table.fields["世界设置"] is False
    assert table.fields["desc"] == "标准《饥荒》体验。"


def test_empty_string_key():
    table = parse_lua_table('return { [""]=0 }')
    assert table.fields[""] == 0


def test_empty_table_klei_style():
    table = parse_lua_table("return { t={  } }")
    assert table.fields["t"] == LuaTable()


def test_string_quotes_and_escapes():
    table = parse_lua_table("return { s='a\\'b', t=\"line\\nbreak\" }")
    assert table.fields["s"] == "a'b"
    assert table.fields["t"] == "line\nbreak"


def test_line_comments_skipped():
    table = parse_lua_table("return { -- comment\n  a=1, -- trailing\n}")
    assert table.fields == {"a": 1}


def test_trailing_separator_allowed():
    assert parse_lua_table("return { a=1, }").fields == {"a": 1}


@pytest.mark.parametrize(
    "text",
    [
        "{ a=1 }",  # missing return
        "return { a= }",  # missing value
        "return { a=1 } garbage",  # trailing content
        'return { s="unterminated }',
        "return { a=nil }",  # nil is not data
        "return { a=1 b=2 }",  # missing separator
    ],
)
def test_parse_errors(text):
    with pytest.raises(LuaParseError):
        parse_lua_table(text)


def test_parse_error_position():
    with pytest.raises(LuaParseError) as excinfo:
        parse_lua_table("return {\n  a=@\n}")
    assert excinfo.value.line == 2
    assert excinfo.value.column == 5


@pytest.mark.parametrize("path", SAMPLE_LUA_FILES, ids=lambda p: str(p.relative_to(EXAMPLES)))
def test_parses_all_sample_lua_files(path):
    table = parse_lua_table(read_exact(path))
    assert table.fields or table.items


def test_serialize_empty_table():
    assert serialize_lua_table(LuaTable()) == "return {  }"


def test_serialize_scalars_inline():
    text = 'return { a=1, b=-10, c=0.7, d=true, e=false, f="x" }'
    assert serialize_lua_table(parse_lua_table(text)) == text


def test_serialize_key_quoting():
    text = 'return { [""]=0, ["世界设置"]=false, ["workshop-1"]={  }, plain=1 }'
    assert serialize_lua_table(parse_lua_table(text)) == text


def test_serialize_keyword_key_is_bracketed():
    assert serialize_lua_table(LuaTable(fields={"end": 1})) == 'return { ["end"]=1 }'


def test_serialize_string_escapes():
    table = LuaTable(fields={"s": 'a"b\\c\nd'})
    assert serialize_lua_table(table) == 'return { s="a\\"b\\\\c\\nd" }'


def test_serialize_items_before_fields():
    assert serialize_lua_table(LuaTable(fields={"a": 1}, items=["x"])) == 'return { "x", a=1 }'


def test_serialize_multiline_when_long():
    # Long tables break into Klei's multi-line form: 2-space indent, a trailing
    # space before every closing brace, short subtables inline, no re-sorting.
    text = (
        "return {\n"
        '  zebra="first because insertion order is preserved",\n'
        "  alpha={\n"
        "    long_key_number_one=1111111,\n"
        "    long_key_number_two=2222222,\n"
        "    long_key_number_three=3333333 \n"
        "  },\n"
        "  small={ 1, 2 } \n"
        "}"
    )
    assert serialize_lua_table(parse_lua_table(text)) == text


@pytest.mark.parametrize("path", SAMPLE_LUA_FILES, ids=lambda p: str(p.relative_to(EXAMPLES)))
def test_serializer_round_trips_all_sample_lua_files(path):
    text = read_exact(path)
    assert serialize_lua_table(parse_lua_table(text)) == text


def test_top_level_entries_spans_are_verbatim():
    text = read_exact(EXAMPLES / "Cluster_2" / "Master" / "modoverrides.lua")
    entries = parse_top_level_entries(text)
    assert len(entries) == 19
    assert entries[0].key == "workshop-1185229307"
    previous_end = 0
    for entry in entries:
        assert entry.start >= previous_end
        assert text[entry.start : entry.end] == entry.source_text
        assert entry.source_text.startswith(f'["{entry.key}"]')
        assert isinstance(entry.value, LuaTable)
        assert entry.value.fields.get("enabled") is True
        previous_end = entry.end
