"""Public parser API for canonical ÆToE notation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TextIO

from lark import Lark
from lark.exceptions import UnexpectedCharacters, UnexpectedInput

from .ast import EToEFile, Notation, SourceComment
from .transformer import EToETransformer

_GRAMMAR = Path(__file__).with_name("grammar.lark").read_text(encoding="utf-8")
_COMMENT_RE = re.compile(r"(?P<hash>#[^\r\n]*)|(?P<slash>//[^\r\n]*)|(?P<block>/\*(?s:.*?)\*/)")


class EToEParser:
    """LALR parser for the canonical ÆToE grammar."""

    def __init__(self) -> None:
        self._parser = Lark(
            _GRAMMAR,
            parser="earley",
            lexer="dynamic",
            ambiguity="resolve",
            start="start",
            maybe_placeholders=False,
            propagate_positions=True,
        )

    def parse_file(self, text: str, *, preserve_comments: bool = False) -> EToEFile:
        tree = self._parser.parse(text)
        result = EToETransformer().transform(tree)
        if not isinstance(result, EToEFile):
            raise TypeError(f"Unexpected transformer result: {type(result)!r}")
        if preserve_comments:
            result = EToEFile(result.statements, _extract_comments(text))
        return result

    def parse_statement(self, text: str) -> Notation:
        source = text.strip()
        if not source.endswith(";"):
            source += ";"
        result = self.parse_file(source)
        if len(result.statements) != 1:
            raise ValueError("Expected exactly one ÆToE statement")
        return result.statements[0]

    def parse_path(self, path: str | Path, *, preserve_comments: bool = False) -> EToEFile:
        return self.parse_file(Path(path).read_text(encoding="utf-8"), preserve_comments=preserve_comments)


def parse_file(text_or_stream_or_path, *, preserve_comments: bool = False) -> EToEFile:
    parser = EToEParser()
    if isinstance(text_or_stream_or_path, (str, Path)) and isinstance(text_or_stream_or_path, Path):
        return parser.parse_path(text_or_stream_or_path, preserve_comments=preserve_comments)
    if hasattr(text_or_stream_or_path, "read"):
        return parser.parse_file(text_or_stream_or_path.read(), preserve_comments=preserve_comments)
    return parser.parse_file(str(text_or_stream_or_path), preserve_comments=preserve_comments)


def parse_statement(text: str) -> Notation:
    return EToEParser().parse_statement(text)


def _extract_comments(text: str) -> tuple[SourceComment, ...]:
    return tuple(SourceComment(m.group(0), m.lastgroup or "unknown", m.start(), m.end()) for m in _COMMENT_RE.finditer(text))
