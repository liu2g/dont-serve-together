"""Parser for the Lua data-literal files used in DST cluster configuration.

Files like ``modoverrides.lua`` and ``leveldataoverride.lua`` are a single
``return { ... }`` expression emitted by Klei's table serializer -- pure data,
no executable code. This module parses exactly that data subset of Lua:
tables, strings, numbers, booleans, and ``--`` line comments. Anything else
(function calls, ``nil``, long strings, ...) is rejected with a
:class:`LuaParseError`.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NUMBER_RE = re.compile(r"-?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?")

_STRING_ESCAPES = {"\\": "\\", '"': '"', "'": "'", "n": "\n", "r": "\r", "t": "\t"}


class LuaParseError(ValueError):
    """Raised when text is not a well-formed Lua data literal.

    Attributes:
        line: 1-based line of the offending position.
        column: 1-based column of the offending position.
    """

    def __init__(self, message: str, line: int, column: int) -> None:
        """Initialize the error with a message and a source position."""
        super().__init__(f"{message} (line {line}, column {column})")
        self.line = line
        self.column = column


class LuaTable(BaseModel):
    """A parsed Lua table: a map part (``fields``) plus an array part (``items``).

    ``{ a=1, "x", ["b"]=2 }`` parses to ``fields={"a": 1, "b": 2}`` and
    ``items=["x"]``.
    """

    model_config = ConfigDict(frozen=True)

    fields: dict[str | int, LuaValue] = Field(default_factory=dict)
    items: list[LuaValue] = Field(default_factory=list)


type LuaValue = str | int | float | bool | LuaTable
"""Any value a Lua data literal can hold."""

LuaTable.model_rebuild()


class TopLevelEntry(BaseModel):
    """One entry of the top-level table, with its exact source-text span.

    ``key`` is ``None`` for positional (array-part) entries. ``source_text``
    is ``text[start:end]``, verbatim -- it lets callers splice original bytes
    (e.g. the ``modoverrides.lua`` merge) instead of re-serializing.
    """

    model_config = ConfigDict(frozen=True)

    key: str | int | None
    value: LuaValue
    start: int
    end: int
    source_text: str


class _Parser:
    """Recursive-descent parser over a single source string."""

    def __init__(self, text: str) -> None:
        self._text = text
        self._pos = 0

    def parse_document(self, record_spans: bool) -> tuple[LuaTable, list[TopLevelEntry]]:
        """Parse ``return { ... }`` plus optional surrounding trivia."""
        self._skip_trivia()
        keyword = _IDENTIFIER_RE.match(self._text, self._pos)
        if keyword is None or keyword.group() != "return":
            raise self._error("expected 'return'")
        self._pos = keyword.end()
        self._skip_trivia()
        table, entries = self._parse_table(record_spans=record_spans)
        self._skip_trivia()
        if self._pos != len(self._text):
            raise self._error("unexpected content after the top-level table")
        return table, entries

    def _parse_table(self, record_spans: bool = False) -> tuple[LuaTable, list[TopLevelEntry]]:
        if not self._starts_with("{"):
            raise self._error("expected '{'")
        self._pos += 1
        fields: dict[str | int, LuaValue] = {}
        items: list[LuaValue] = []
        entries: list[TopLevelEntry] = []
        while True:
            self._skip_trivia()
            if self._starts_with("}"):
                self._pos += 1
                break
            start = self._pos
            key, value = self._parse_entry()
            end = self._pos
            if key is None:
                items.append(value)
            else:
                fields[key] = value
            if record_spans:
                entries.append(
                    TopLevelEntry(key=key, value=value, start=start, end=end, source_text=self._text[start:end])
                )
            self._skip_trivia()
            if self._starts_with(",") or self._starts_with(";"):
                self._pos += 1
            elif not self._starts_with("}"):
                raise self._error("expected ',' or '}' after table entry")
        return LuaTable(fields=fields, items=items), entries

    def _parse_entry(self) -> tuple[str | int | None, LuaValue]:
        if self._starts_with("["):
            self._pos += 1
            self._skip_trivia()
            key = self._parse_value()
            if isinstance(key, bool) or not isinstance(key, str | int):
                raise self._error("table key must be a string or an integer")
            self._skip_trivia()
            self._expect("]")
            self._skip_trivia()
            self._expect("=")
            self._skip_trivia()
            return key, self._parse_value()
        name = _IDENTIFIER_RE.match(self._text, self._pos)
        if name is not None:
            saved = self._pos
            self._pos = name.end()
            self._skip_trivia()
            if self._starts_with("="):
                self._pos += 1
                self._skip_trivia()
                return name.group(), self._parse_value()
            self._pos = saved
        return None, self._parse_value()

    def _parse_value(self) -> LuaValue:
        if self._pos >= len(self._text):
            raise self._error("unexpected end of input")
        char = self._text[self._pos]
        if char == "{":
            table, _ = self._parse_table()
            return table
        if char in {'"', "'"}:
            return self._parse_string()
        number = _NUMBER_RE.match(self._text, self._pos)
        if number is not None:
            self._pos = number.end()
            literal = number.group()
            return float(literal) if any(c in literal for c in ".eE") else int(literal)
        word = _IDENTIFIER_RE.match(self._text, self._pos)
        if word is not None:
            if word.group() == "true":
                self._pos = word.end()
                return True
            if word.group() == "false":
                self._pos = word.end()
                return False
            raise self._error(f"unsupported bare word {word.group()!r} (only data literals are supported)")
        raise self._error(f"unexpected character {char!r}")

    def _parse_string(self) -> str:
        quote = self._text[self._pos]
        self._pos += 1
        pieces: list[str] = []
        while True:
            if self._pos >= len(self._text):
                raise self._error("unterminated string")
            char = self._text[self._pos]
            if char == quote:
                self._pos += 1
                return "".join(pieces)
            if char == "\n":
                raise self._error("unterminated string")
            if char == "\\":
                escape = self._text[self._pos + 1 : self._pos + 2]
                if escape not in _STRING_ESCAPES:
                    raise self._error(f"unsupported escape sequence '\\{escape}'")
                pieces.append(_STRING_ESCAPES[escape])
                self._pos += 2
            else:
                pieces.append(char)
                self._pos += 1

    def _skip_trivia(self) -> None:
        text = self._text
        while self._pos < len(text):
            if text[self._pos] in " \t\r\n":
                self._pos += 1
            elif text.startswith("--", self._pos):
                newline = text.find("\n", self._pos)
                self._pos = len(text) if newline == -1 else newline + 1
            else:
                break

    def _starts_with(self, token: str) -> bool:
        return self._text.startswith(token, self._pos)

    def _expect(self, token: str) -> None:
        if not self._starts_with(token):
            raise self._error(f"expected {token!r}")
        self._pos += len(token)

    def _error(self, message: str) -> LuaParseError:
        line = self._text.count("\n", 0, self._pos) + 1
        column = self._pos - self._text.rfind("\n", 0, self._pos)
        return LuaParseError(message, line, column)


def parse_lua_table(text: str) -> LuaTable:
    """Parse a ``return { ... }`` Lua data literal.

    Args:
        text: Full file content.

    Returns:
        The top-level table.

    Raises:
        LuaParseError: If ``text`` is not a well-formed Lua data literal.
    """
    table, _ = _Parser(text).parse_document(record_spans=False)
    return table


def parse_top_level_entries(text: str) -> list[TopLevelEntry]:
    """Parse a ``return { ... }`` literal, keeping each top-level entry's source span.

    Args:
        text: Full file content.

    Returns:
        The top-level table's entries in file order, each carrying its exact
        source text (used by the ``modoverrides.lua`` merge to splice original
        bytes).

    Raises:
        LuaParseError: If ``text`` is not a well-formed Lua data literal.
    """
    _, entries = _Parser(text).parse_document(record_spans=True)
    return entries
