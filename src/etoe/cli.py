"""Command-line entry point for the local etoe reference package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .parser import EToEParser
from .validation import validate


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="etoe", description="Reference ÆToE parser/validator and hyperatom tools")
    sub = p.add_subparsers(dest="command", required=True)

    parse = sub.add_parser("parse", help="Parse an .etoe file")
    parse.add_argument("path", type=Path)
    parse.add_argument("--comments", action="store_true")

    check = sub.add_parser("check", help="Parse and semantically validate an .etoe file")
    check.add_argument("path", type=Path)

    hyperatoms = sub.add_parser("hyperatoms", help="Translate and graph the hyperatom registry")
    hyper_sub = hyperatoms.add_subparsers(dest="hyperatoms_command", required=True)

    translate = hyper_sub.add_parser("translate", help="Translate data/atom/element/**/*.etoe into semantic JSON")
    translate.add_argument("--data-root", type=Path, default=Path("data/atom/element"))
    translate.add_argument("--output", type=Path, default=Path("build/hyperatoms.semantic.json"))

    graph = hyper_sub.add_parser("graph", help="Generate Graphviz DOT or render SVG/PNG/PDF")
    graph.add_argument("--data-root", type=Path, default=Path("data/atom/element"))
    graph.add_argument("--output", type=Path, default=Path("build/hyperatoms.svg"))
    graph.add_argument("--layout", choices=("dot", "neato", "fdp", "sfdp", "circo", "twopi"), default="dot")
    graph.add_argument("--format", choices=("dot", "svg", "png", "pdf", "ps", "json"), default=None)
    graph.add_argument("--include-templates", action="store_true", help="Include massless element/template statements")
    graph.add_argument("--symbols", default="", help="Optional comma-separated root element symbols, e.g. Fe,Co,Ni")
    graph.add_argument("--title", default="ÆToE semantic hyperatom graph")

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
    if args.command == "hyperatoms":
        from .hyperatom_translation import HyperatomTranslator

        registry = HyperatomTranslator(parser).translate_directory(args.data_root)
        stats = registry.statistics()
        if args.hyperatoms_command == "translate":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(registry.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote {len(registry.definitions)} semantic definition(s) to {args.output}")
            print(json.dumps(stats, ensure_ascii=False, indent=2))
            return 0
        if args.hyperatoms_command == "graph":
            from .hyperatom_graphviz import write_hyperatom_graph

            symbols = [value.strip() for value in args.symbols.split(",") if value.strip()] or None
            output = write_hyperatom_graph(
                registry,
                args.output,
                include_templates=args.include_templates,
                symbols=symbols,
                layout=args.layout,
                format=args.format,
                title=args.title,
            )
            print(f"Wrote Graphviz graph to {output}")
            print(f"Registry source: {len(registry.definitions)} semantic definitions from {registry.source_file_count} files")
            return 0
    return 2
