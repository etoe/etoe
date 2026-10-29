"""Batch planning and execution for data-driven atom visualizations.

The planner only discovers inputs and computes output paths. It does not build
DOT strings or invoke Graphviz, which makes it safe to use for previews and
unit tests. Actual rendering happens only when :func:`execute_batch_jobs` is
called by the CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .elements import ElementCatalog
from .filenames import (
    DEFAULT_VISUAL_FORMAT,
    standard_hyperatom_path,
    standard_named_path,
    standard_selection_path,
)
from .hyperatom_translation import HYPERATOM_KIND, HyperatomRegistry, SemanticHyperatom
from .selections import AtomSelectionCatalog, GraphSelectionItem

BatchJobKind = Literal["hyperatom-tree", "periodic-map", "hyperatom-map"]


@dataclass(frozen=True, slots=True)
class BatchVisualizationJob:
    """One deterministic visualization task in a batch."""

    kind: BatchJobKind
    selector: str
    output: Path
    symbols: tuple[str, ...] | None = None
    hyperatom: SemanticHyperatom | None = None
    selection: GraphSelectionItem | None = None


@dataclass(frozen=True, slots=True)
class BatchVisualizationPlan:
    """Batch jobs grouped by the requested artifact families."""

    jobs: tuple[BatchVisualizationJob, ...]

    def counts(self) -> dict[str, int]:
        counts = {"hyperatom-tree": 0, "periodic-map": 0, "hyperatom-map": 0}
        for job in self.jobs:
            counts[job.kind] += 1
        counts["total"] = len(self.jobs)
        return counts


def plan_batch_visualizations(
    registry: HyperatomRegistry,
    *,
    element_root: str | Path = "data/atom/element",
    all_trees: bool = False,
    all_periodic_maps: bool = False,
    all_hyperatom_maps: bool = False,
    format: str | None = None,
    mode: str | None = None,
    target: str | None = None,
) -> BatchVisualizationPlan:
    """Plan visualizations for every selected catalog item.

    ``all_trees`` makes one occurrence tree for every concrete hyperatom
    defined by source files. ``all_periodic_maps`` makes a periodic map for
    every symbol in the element catalog. ``all_hyperatom_maps`` makes a map
    for every symbol and for every available selection (chemical category,
    atomic level, custom element group, and custom hyperatom group).

    Runtime placeholders added by ``build_canonical_hyperatom_map`` are
    intentionally excluded from the tree list because they are not source
    definitions under ``data/atom``.
    """
    if not (all_trees or all_periodic_maps or all_hyperatom_maps):
        return BatchVisualizationPlan(())

    root = Path(element_root).expanduser().resolve()
    visual_format = (format or DEFAULT_VISUAL_FORMAT).lower().lstrip(".")
    jobs: list[BatchVisualizationJob] = []

    if all_trees:
        hyperatoms = sorted(
            (
                obj for obj in registry.definitions
                if obj.kind == HYPERATOM_KIND and not obj.source_path.startswith("<runtime:")
            ),
            key=lambda obj: (obj.symbol or "", obj.atomic_mass or -1, obj.canonical, obj.id),
        )
        for obj in hyperatoms:
            output = standard_hyperatom_path(
                obj, element_root=root, artifact="tree", format=visual_format,
                mode=mode, target=target,
            )
            jobs.append(BatchVisualizationJob(
                kind="hyperatom-tree", selector=obj.canonical, output=output, hyperatom=obj,
            ))

    catalog = AtomSelectionCatalog(root, registry=registry) if all_hyperatom_maps else None
    if all_periodic_maps:
        # Periodic-only batches need the element catalog, not the sibling group
        # TOML catalogs; don't make a periodic-map command depend on selections.
        element_catalog = (
            catalog.element_catalog if catalog is not None
            else (registry.element_catalog or ElementCatalog(root))
        )
        for element in sorted(element_catalog.elements, key=lambda item: item.symbol):
            output = standard_named_path(
                element.directory, f"{element.symbol}-periodic-map", "periodic-map",
                format=visual_format, mode=mode, target=target,
            )
            jobs.append(BatchVisualizationJob(
                kind="periodic-map", selector=element.symbol, symbols=(element.symbol,), output=output,
            ))

    if all_hyperatom_maps:
        assert catalog is not None
        for element in sorted(catalog.element_catalog.elements, key=lambda item: item.symbol):
            output = standard_named_path(
                element.directory, f"{element.symbol}-hyperatom-map", "hyperatom-map",
                format=visual_format, mode=mode, target=target,
            )
            jobs.append(BatchVisualizationJob(
                kind="hyperatom-map", selector=element.symbol, symbols=(element.symbol,), output=output,
            ))

        selections: list[GraphSelectionItem] = []
        selections.extend(catalog.categories.items)
        selections.extend(catalog.levels.items)
        selections.extend(catalog.element_groups.items)
        selections.extend(catalog.hyperatom_groups.items)
        for selection in sorted(
            selections,
            key=lambda item: (item.directory.as_posix(), item.directory.name),
        ):
            tokens = tuple(selection.symbols_for_graph())
            if not tokens:
                continue
            output = standard_selection_path(
                selection, artifact="hyperatom-map", format=visual_format,
                mode=mode, target=target,
            )
            label = getattr(selection, "slug", None) or getattr(selection, "name", None) or selection.directory.name
            jobs.append(BatchVisualizationJob(
                kind="hyperatom-map", selector=str(label), symbols=tokens,
                output=output, selection=selection,
            ))

    # Catch accidental overwrites before the first artifact is generated.
    by_output: dict[Path, BatchVisualizationJob] = {}
    for job in jobs:
        previous = by_output.get(job.output)
        if previous is not None:
            raise ValueError(
                f"Batch output collision at {job.output}: "
                f"{previous.kind} ({previous.selector}) and {job.kind} ({job.selector})."
            )
        by_output[job.output] = job

    return BatchVisualizationPlan(tuple(jobs))


def execute_batch_visualizations(
    registry: HyperatomRegistry,
    plan: BatchVisualizationPlan,
    *,
    element_root: str | Path = "data/atom/element",
    layout: str = "dot",
    format: str | None = None,
    title: str | None = None,
    show_element_names: bool = False,
    language: str = "en",
    show_subelement_numbers: bool = True,
    compact: bool = True,
    mode: str | None = None,
    target: str | None = None,
    max_depth: int = 0,
    progress: Any = None,
) -> tuple[Path, ...]:
    """Execute a precomputed plan through the normal incremental writers.

    This function deliberately has no custom renderer: all output is passed
    through the same writers and incremental manifests as single-item CLI
    requests. Use ``format="dot"`` to execute the pipeline without starting
    Graphviz.
    """
    from .hyperatom_graphviz import write_hyperatom_map, write_hyperatom_tree, write_periodic_map

    outputs: list[Path] = []
    total = len(plan.jobs)
    for index, job in enumerate(plan.jobs, start=1):
        if progress is not None:
            progress(index, total, job)
        common = {
            "element_root": element_root,
            "layout": layout,
            "format": format,
            "title": title,
            "show_element_names": show_element_names,
            "language": language,
            "show_subelement_numbers": show_subelement_numbers,
            "compact": compact,
            "mode": mode,
            "target": target,
        }
        if job.kind == "hyperatom-tree":
            assert job.hyperatom is not None
            output = write_hyperatom_tree(
                registry, job.hyperatom, job.output, max_depth=max_depth, **common,
            )
        elif job.kind == "periodic-map":
            output = write_periodic_map(
                registry, job.output, symbols=job.symbols, **common,
            )
        else:
            output = write_hyperatom_map(
                registry, job.output, symbols=job.symbols, **common,
            )
        outputs.append(Path(output))
    return tuple(outputs)


__all__ = [
    "BatchVisualizationJob",
    "BatchVisualizationPlan",
    "execute_batch_visualizations",
    "plan_batch_visualizations",
]
