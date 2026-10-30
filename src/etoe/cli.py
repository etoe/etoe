"""Command-line entry point for the local etoe reference package."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

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

    batch = hyper_sub.add_parser(
        "batch", help="Batch-generate trees, per-symbol periodic maps, and selection hyperatom maps",
    )
    batch.add_argument("--data-root", type=Path, default=Path("data/atom/element"))
    batch.add_argument("--all", dest="all_artifacts", action="store_true",
                       help="Generate all trees, all per-symbol periodic maps, and all hyperatom maps")
    batch.add_argument("--all-trees", action="store_true",
                       help="Generate a tree for every source-defined concrete hyperatom")
    batch.add_argument("--all-periodic-maps", action="store_true",
                       help="Generate a periodic map for every symbol in the element catalog")
    batch.add_argument("--all-hyperatom-maps", action="store_true",
                       help="Generate hyperatom maps for every symbol and every selection catalog")
    batch.add_argument("--mode", choices=STYLE_MODES, default=None, help="Style mode")
    batch.add_argument("--source", choices=STYLE_SOURCES, default=None, help="Style source")
    batch.add_argument("--target", choices=STYLE_TARGETS, default=None, help="Style target")
    batch.add_argument("--layout", choices=("dot", "neato", "fdp", "sfdp", "circo", "twopi"), default="dot")
    batch.add_argument("--format", choices=("dot", "svg", "png", "pdf", "ps", "json"), default=None)
    batch.add_argument("--title", default=None, help="Optional title applied to every generated graph")
    batch.add_argument("--element-names", action="store_true", help="Append localized element names to node labels")
    batch.add_argument("--language", default="en", help="Language tag for element names, e.g. en or ru")
    batch.add_argument("--hide-subelement-numbers", dest="show_subelement_numbers", action="store_false", default=True,
                       help="Hide nonzero subelement numbers in labels")
    batch.add_argument("--full-labels", dest="compact", action="store_false", default=True,
                       help="Use full structural labels and non-compact spacing")
    batch.add_argument("--max-depth", type=_non_negative_int, default=0, metavar="N",
                       help="Maximum depth for generated trees (0 = unlimited)")

    render_3d = hyper_sub.add_parser(
        "render-3d", aliases=["3d"],
        help="Generate hierarchical hyperatom .blend scenes and PNG snapshots in Blender",
    )
    render_3d.add_argument("--data-root", type=Path, default=Path("data/atom/element"))
    render_3d.add_argument("--hyperatom", action="append", default=[], metavar="NOTATION",
                           help="Render one concrete hyperatom; repeat for several (canonical notation or semantic id)")
    render_3d.add_argument("--element", action="append", default=[], metavar="SYMBOL",
                           help="Render every source-defined hyperatom of this element; repeatable")
    render_3d.add_argument("--elements", default="", metavar="SYMBOLS",
                           help="Comma-separated list of chemical element symbols")
    render_3d.add_argument("--category", action="append", default=[], metavar="SLUG",
                           help="Render all hyperatoms of a chemical category; repeatable (e.g. alkali-metals)")
    render_3d.add_argument("--all-elements", action="store_true",
                           help="Render every source-defined hyperatom in data/atom/element")
    render_3d.add_argument("--output", type=Path, default=None,
                           help="Explicit .blend path (only with exactly one --hyperatom)")
    render_3d.add_argument("--output-root", type=Path, default=None,
                           help="Override output root; symbol subdirectories are preserved")
    render_3d.add_argument("--blender", default=os.environ.get("BLENDER", "blender"),
                           help="Blender executable name or path (default: $BLENDER or blender)")
    render_3d.add_argument("--mode", choices=STYLE_MODES, default=None,
                           help="3D theme (default follows ETOE_STYLE_MODE or Light)")
    render_3d.add_argument("--engine", choices=("eevee", "cycles"), default="eevee")
    render_3d.add_argument("--resolution", type=int, default=1200, help="Square PNG resolution in pixels")
    render_3d.add_argument("--samples", type=int, default=64, help="Render samples")
    render_3d.add_argument("--shell-layers", type=int, default=3, help="Illustrative translucent atmosphere layers (1-8)")
    render_3d.add_argument("--max-depth", type=_non_negative_int, default=0, metavar="N",
                           help="Maximum recursive hyperatom depth (0 = unlimited)")
    render_3d.add_argument("--labels", action="store_true", help="Add labels at all hierarchy levels")
    render_3d.add_argument("--transparent-background", action="store_true",
                           help="Render PNG with transparent background")
    render_3d.add_argument("--overwrite", action="store_true", help="Regenerate existing .blend and PNG files")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "parse":
        from .parser import EToEParser
        doc = EToEParser().parse_path(args.path, preserve_comments=args.comments)
        for stmt in doc.statements:
            print(stmt.to_canonical() + ";")
        if args.comments:
            print(f"# comments: {len(doc.comments)}")
        return 0
    if args.command == "check":
        from .parser import EToEParser
        from .validation import validate
        doc = EToEParser().parse_path(args.path)
        result = validate(doc)
        if result.ok:
            print(f"OK: {len(doc.statements)} statement(s)")
            return 0
        for issue in result.issues:
            print(f"ERROR [{issue.code}] {issue.message}")
        return 1
    if args.command == "hyperatoms":
        if args.hyperatoms_command in {"render-3d", "3d"}:
            from .blender3d import BlenderRenderError, run_blender
            from .style import get_style_directory, get_style_settings

            selected_mode = args.mode or get_style_settings().mode
            script_path = Path(__file__).resolve().with_name("blender_render.py")
            script_args = [
                "--data-root", str(args.data_root.expanduser().resolve()),
                "--style-dir", str(get_style_directory()),
                "--mode", selected_mode,
                "--engine", args.engine,
                "--resolution", str(args.resolution),
                "--samples", str(args.samples),
                "--shell-layers", str(args.shell_layers),
                "--max-depth", str(args.max_depth),
            ]
            for selector in args.hyperatom:
                script_args.extend(("--hyperatom", selector))
            for symbol in args.element:
                script_args.extend(("--element", symbol))
            if args.elements:
                script_args.extend(("--elements", args.elements))
            for category in args.category:
                script_args.extend(("--category", category))
            if args.all_elements:
                script_args.append("--all-elements")
            if args.output is not None:
                script_args.extend(("--output", str(args.output.expanduser().resolve())))
            if args.output_root is not None:
                script_args.extend(("--output-root", str(args.output_root.expanduser().resolve())))
            if args.labels:
                script_args.append("--labels")
            if args.transparent_background:
                script_args.append("--transparent-background")
            if args.overwrite:
                script_args.append("--overwrite")
            try:
                return run_blender(args.blender, script_path, script_args)
            except BlenderRenderError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 2

        if args.hyperatoms_command in {"graph", "periodic-map", "hyperatom-map", "tree", "batch"}:
            # Keep visual rendering and generated filenames on the same style tuple.
            configure_styles(mode=args.mode, source=args.source, target=args.target)
        from .parser import EToEParser
        from .hyperatom_translation import HyperatomTranslator

        registry = HyperatomTranslator(EToEParser()).translate_directory(args.data_root)
        stats = registry.statistics()
        if args.hyperatoms_command == "batch":
            selected = (
                args.all_artifacts or args.all_trees or args.all_periodic_maps or args.all_hyperatom_maps
            )
            if not selected:
                print(
                    "ERROR: choose --all, --all-trees, --all-periodic-maps, or --all-hyperatom-maps.",
                    file=sys.stderr,
                )
                return 2

            from .batch_visualization import execute_batch_visualizations, plan_batch_visualizations
            from .hyperatom_map import build_canonical_hyperatom_map

            # Plan from source-defined catalog entries before auto-patching adds
            # synthetic X<n> records to the in-memory element catalog.
            source_definition_count = len(registry.definitions)
            all_artifacts = args.all_artifacts
            plan = plan_batch_visualizations(
                registry,
                element_root=args.data_root,
                all_trees=all_artifacts or args.all_trees,
                all_periodic_maps=all_artifacts or args.all_periodic_maps,
                all_hyperatom_maps=all_artifacts or args.all_hyperatom_maps,
                format=args.format,
                mode=args.mode,
                target=args.target,
            )
            if not plan.jobs:
                print("No visualizations were selected.")
                return 0

            # Resolve references / add in-memory placeholders once for the whole batch.
            # The plan is already fixed, so runtime-only records do not become batch jobs.
            build_canonical_hyperatom_map(registry, auto_patch_missing=True)

            def _progress(index, total, job):
                print(f"[{index}/{total}] {job.kind}: {job.selector} -> {job.output}")

            outputs = execute_batch_visualizations(
                registry,
                plan,
                element_root=args.data_root,
                layout=args.layout,
                format=args.format,
                title=args.title,
                show_element_names=args.element_names,
                language=args.language,
                show_subelement_numbers=args.show_subelement_numbers,
                compact=args.compact,
                mode=args.mode,
                target=args.target,
                max_depth=args.max_depth,
                progress=_progress,
            )
            print(f"Batch complete: {len(outputs)} visualization(s) written or reused.")
            print(json.dumps({**plan.counts(), "source_definitions": source_definition_count}, ensure_ascii=False, indent=2))
            return 0
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
