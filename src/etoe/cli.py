"""Command-line entry point for the local etoe reference package."""

from __future__ import annotations

import argparse
from pathlib import Path

from .parser import EToEParser
from .validation import validate


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="etoe", description="Reference ÆToE parser/validator")
    sub = p.add_subparsers(dest="command", required=True)

    parse = sub.add_parser("parse", help="Parse an .etoe file")
    parse.add_argument("path", type=Path)
    parse.add_argument("--comments", action="store_true")

    check = sub.add_parser("check", help="Parse and semantically validate an .etoe file")
    check.add_argument("path", type=Path)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    parser = EToEParser()
    if args.command == "parse":
        doc = parser.parse_path(args.path, preserve_comments=args.comments)
        for stmt in doc.statements:
            print(stmt.to_canonical() + ";")
        if args.comments:
            print(f"# comments: {len(doc.comments)}")
        return 0
    if args.command == "check":
        doc = parser.parse_path(args.path)
        result = validate(doc)
        if result.ok:
            print(f"OK: {len(doc.statements)} statement(s)")
            return 0
        for issue in result.issues:
            print(f"ERROR [{issue.code}] {issue.message}")
        return 1
    return 2
