"""Command-line entry point for the local etoe reference package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .parser import EToEParser
from .validation import validate
from .style import MODES as STYLE_MODES, SOURCES as STYLE_SOURCES, TARGETS as STYLE_TARGETS, configure_styles


def _non_negative_int(value: str) -> int:
    """Parse a non-negative integer CLI option."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


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

    hyper_map = hyper_sub.add_parser("map", help="Build a canonical text-indexed hyperatom map as JSON")
    hyper_map.add_argument("--data-root", type=Path, default=Path("data/atom/element"))
    hyper_map.add_argument("--output", type=Path, default=Path("build/hyperatoms.map.json"))
    hyper_map.add_argument("--auto-patch-missing", action="store_true", help="Add runtime X<n> placeholders for missing mass-bearing subatoms")

    graph = hyper_sub.add_parser("graph", help="Generate Graphviz DOT or render SVG/PNG/PDF")
    graph.add_argument("--data-root", type=Path, default=Path("data/atom/element"))
    graph.add_argument("--output", type=Path, default=None, help="Output path (defaults to the standard filename)")
    graph.add_argument("--mode", choices=STYLE_MODES, default=None, help="Style mode (default follows ETOE_STYLE_MODE)")
    graph.add_argument("--source", choices=STYLE_SOURCES, default=None, help="Style source (default follows ETOE_STYLE_SOURCE)")
    graph.add_argument("--target", choices=STYLE_TARGETS, default=None, help="Style target (default follows ETOE_STYLE_TARGET)")
    graph.add_argument("--layout", choices=("dot", "neato", "fdp", "sfdp", "circo", "twopi"), default="dot")
    graph.add_argument("--format", choices=("dot", "svg", "png", "pdf", "ps", "json"), default=None)
    graph.add_argument("--include-templates", action="store_true", help="Include massless element/template statements")
    graph.add_argument(
        "--auto-patch-missing",
        action="store_true",
        help="Add runtime X<n> auxiliary hyperatoms for unresolved mass-bearing subatoms",
    )
    graph.add_argument("--symbols", default="", help="Optional comma-separated root element symbols, e.g. Fe,Co,Ni")
    graph.add_argument("--title", default=None, help="Optional graph title (omitted by default to save space)")
    graph.add_argument("--element-names", action="store_true", help="Append localized element names to node labels")
    graph.add_argument("--language", default="en", help="Language tag for element names, e.g. en or ru")

    periodic = hyper_sub.add_parser("periodic-map", help="Generate a vertically oriented periodic map with numbered subelements")
    periodic.add_argument("--data-root", type=Path, default=Path("data/atom/element"))
    periodic.add_argument("--output", type=Path, default=None, help="Output path (defaults to the standard filename)")
    periodic.add_argument("--mode", choices=STYLE_MODES, default=None, help="Style mode (default follows ETOE_STYLE_MODE)")
    periodic.add_argument("--source", choices=STYLE_SOURCES, default=None, help="Style source (default follows ETOE_STYLE_SOURCE)")
    periodic.add_argument("--target", choices=STYLE_TARGETS, default=None, help="Style target (default follows ETOE_STYLE_TARGET)")
    periodic.add_argument("--layout", choices=("dot", "neato", "fdp", "sfdp", "circo", "twopi"), default="dot")
    periodic.add_argument("--format", choices=("dot", "svg", "png", "pdf", "ps", "json"), default=None)
    periodic.add_argument("--symbols", default="", help="Optional comma-separated root element symbols, e.g. He,Li,Be")
    periodic.add_argument("--title", default=None, help="Optional graph title (omitted by default to save space)")
    periodic.add_argument("--element-names", action="store_true", help="Append localized element names to node labels")
    periodic.add_argument("--language", default="en", help="Language tag for element names, e.g. en or ru")
    periodic.add_argument("--hide-subelement-numbers", dest="show_subelement_numbers", action="store_false", default=True,
                          help="Hide nonzero subelement numbers in element labels")
    periodic.add_argument("--full-labels", dest="compact", action="store_false", default=True,
                          help="Use full structural labels and non-compact spacing")

    hyperatom_map = hyper_sub.add_parser("hyperatom-map", help="Generate a map containing concrete hyperatoms only")
    hyperatom_map.add_argument("--data-root", type=Path, default=Path("data/atom/element"))
    hyperatom_map.add_argument("--output", type=Path, default=None, help="Output path (defaults to the standard filename)")
    hyperatom_map.add_argument("--mode", choices=STYLE_MODES, default=None, help="Style mode (default follows ETOE_STYLE_MODE)")
    hyperatom_map.add_argument("--source", choices=STYLE_SOURCES, default=None, help="Style source (default follows ETOE_STYLE_SOURCE)")
    hyperatom_map.add_argument("--target", choices=STYLE_TARGETS, default=None, help="Style target (default follows ETOE_STYLE_TARGET)")
    hyperatom_map.add_argument("--layout", choices=("dot", "neato", "fdp", "sfdp", "circo", "twopi"), default="dot")
    hyperatom_map.add_argument("--format", choices=("dot", "svg", "png", "pdf", "ps", "json"), default=None)
    hyperatom_map.add_argument("--symbols", default="", help="Optional comma-separated selectors, e.g. He or He-5-(4'1)")
    hyperatom_map.add_argument("--title", default=None, help="Optional graph title (omitted by default to save space)")
    hyperatom_map.add_argument("--element-names", action="store_true", help="Append localized element names to node labels")
    hyperatom_map.add_argument("--language", default="en", help="Language tag for element names, e.g. en or ru")
    hyperatom_map.add_argument("--hide-subelement-numbers", dest="show_subelement_numbers", action="store_false", default=True,
                               help="Hide nonzero subelement numbers in hyperatom labels")
    hyperatom_map.add_argument("--full-labels", dest="compact", action="store_false", default=True,
                               help="Use full structural labels and non-compact spacing")

    tree = hyper_sub.add_parser("tree", help="Expand one concrete hyperatom into an occurrence tree")
    tree.add_argument("hyperatom", help="Canonical hyperatom notation or semantic ID, e.g. He-5-(4'1)")
    tree.add_argument("--data-root", type=Path, default=Path("data/atom/element"))
    tree.add_argument("--output", type=Path, default=None, help="Output path (defaults to the standard filename)")
    tree.add_argument("--mode", choices=STYLE_MODES, default=None, help="Style mode (default follows ETOE_STYLE_MODE)")
    tree.add_argument("--source", choices=STYLE_SOURCES, default=None, help="Style source (default follows ETOE_STYLE_SOURCE)")
    tree.add_argument("--target", choices=STYLE_TARGETS, default=None, help="Style target (default follows ETOE_STYLE_TARGET)")
    tree.add_argument("--layout", choices=("dot", "neato", "fdp", "sfdp", "circo", "twopi"), default="dot")
    tree.add_argument("--format", choices=("dot", "svg", "png", "pdf", "ps", "json"), default=None)
    tree.add_argument("--title", default=None, help="Optional graph title (omitted by default to save space)")
    tree.add_argument("--element-names", action="store_true", help="Append localized element names to node labels")
    tree.add_argument("--language", default="en", help="Language tag for element names, e.g. en or ru")
    tree.add_argument("--hide-subelement-numbers", dest="show_subelement_numbers", action="store_false", default=True,
                      help="Hide nonzero subelement numbers in hyperatom labels")
    tree.add_argument("--full-labels", dest="compact", action="store_false", default=True,
                      help="Use full structural labels and non-compact spacing")
    tree.add_argument(
        "--max-depth", type=_non_negative_int, default=0, metavar="N",
        help="Limit tree depth from the root (0 = unlimited; root depth is 0)",
    )

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
        if args.hyperatoms_command in {"graph", "periodic-map", "hyperatom-map", "tree"}:
            # Keep visual rendering and generated filenames on the same style tuple.
            configure_styles(mode=args.mode, source=args.source, target=args.target)
        from .hyperatom_translation import HyperatomTranslator

        registry = HyperatomTranslator(parser).translate_directory(args.data_root)
        stats = registry.statistics()
        if args.hyperatoms_command == "translate":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(registry.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote {len(registry.definitions)} semantic definition(s) to {args.output}")
            print(json.dumps(stats, ensure_ascii=False, indent=2))
            return 0
        if args.hyperatoms_command == "map":
            from .hyperatom_map import build_canonical_hyperatom_map

            canonical_map = build_canonical_hyperatom_map(
                registry,
                auto_patch_missing=args.auto_patch_missing,
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(canonical_map.to_dict(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Wrote canonical hyperatom map with {len(canonical_map.nodes)} node(s) to {args.output}")
            print(json.dumps(canonical_map.statistics(), ensure_ascii=False, indent=2))
            return 0
        if args.hyperatoms_command == "periodic-map":
            from .hyperatom_map import build_canonical_hyperatom_map
            from .hyperatom_graphviz import write_periodic_map

            canonical_map = build_canonical_hyperatom_map(registry, auto_patch_missing=True)            

            symbols = [value.strip() for value in args.symbols.split(",") if value.strip()] or None
            output = write_periodic_map(
                registry,
                args.output,
                element_root=args.data_root,
                symbols=symbols,
                layout=args.layout,
                format=args.format,
                title=args.title,
                show_element_names=args.element_names,
                language=args.language,
                show_subelement_numbers=args.show_subelement_numbers,
                compact=args.compact,
            )
            print(f"Wrote Graphviz periodic map to {output}")
            print(json.dumps(stats, ensure_ascii=False, indent=2))
            return 0
        if args.hyperatoms_command == "hyperatom-map":
            from .hyperatom_map import build_canonical_hyperatom_map            
            from .hyperatom_graphviz import write_hyperatom_map

            canonical_map = build_canonical_hyperatom_map(registry, auto_patch_missing=True)                

            symbols = [value.strip() for value in args.symbols.split(",") if value.strip()] or None
            output = write_hyperatom_map(
                registry,
                args.output,
                element_root=args.data_root,
                symbols=symbols,
                layout=args.layout,
                format=args.format,
                title=args.title,
                show_element_names=args.element_names,
                language=args.language,
                show_subelement_numbers=args.show_subelement_numbers,
                compact=args.compact,
            )
            print(f"Wrote Graphviz hyperatom map to {output}")
            print(json.dumps(stats, ensure_ascii=False, indent=2))
            return 0
        if args.hyperatoms_command == "tree":
            from .hyperatom_map import build_canonical_hyperatom_map            
            from .hyperatom_graphviz import write_hyperatom_tree

            canonical_map = build_canonical_hyperatom_map(registry, auto_patch_missing=True)                

            output = write_hyperatom_tree(
                registry,
                args.hyperatom,
                args.output,
                element_root=args.data_root,
                layout=args.layout,
                format=args.format,
                title=args.title,
                show_element_names=args.element_names,
                language=args.language,
                show_subelement_numbers=args.show_subelement_numbers,
                compact=args.compact,
                max_depth=args.max_depth,
            )
            print(f"Wrote Graphviz hyperatom tree to {output}")
            return 0
        if args.hyperatoms_command == "graph":
            from .hyperatom_graphviz import write_hyperatom_graph
            from .hyperatom_map import build_canonical_hyperatom_map

            symbols = [value.strip() for value in args.symbols.split(",") if value.strip()] or None
            source_definition_count = len(registry.definitions)
            canonical_map = build_canonical_hyperatom_map(
                registry,
                auto_patch_missing=args.auto_patch_missing,
            )
            output = write_hyperatom_graph(
                registry,
                args.output,
                element_root=args.data_root,
                include_templates=args.include_templates,
                symbols=symbols,
                layout=args.layout,
                format=args.format,
                title=args.title,
                show_element_names=args.element_names,
                language=args.language,
            )
            print(f"Wrote Graphviz graph to {output}")
            print(
                f"Registry source: {source_definition_count} semantic definitions from {registry.source_file_count} files; "
                f"runtime additions: {len(registry.definitions) - source_definition_count}"
            )
            print(json.dumps(canonical_map.statistics(), ensure_ascii=False, indent=2))
            return 0
    return 2
