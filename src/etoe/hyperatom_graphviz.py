"""Graphviz DOT generation for a semantic ÆToE hyperatom registry.

DOT generation has no Python package dependency. Rendering SVG/PNG/PDF requires
an installed Graphviz executable (for example `dot`).
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
from typing import Iterable

from .hyperatom_translation import (
    ELEMENT_SYMBOL_KIND,
    ELEMENT_TEMPLATE_KIND,
    HYPERATOM_KIND,
    MOLECULE_KIND,
    OTHER_KIND,
    HyperatomRegistry,
    SemanticComponent,
    SemanticHyperatom,
)


SUPPORTED_LAYOUTS = ("dot", "neato", "fdp", "sfdp", "circo", "twopi")
SUPPORTED_FORMATS = ("dot", "svg", "png", "pdf", "ps", "json")


def hyperatom_graph_to_dot(
    registry: HyperatomRegistry,
    *,
    include_templates: bool = False,
    symbols: Iterable[str] | None = None,
    title: str = "ÆToE semantic hyperatom graph",
) -> str:
    """Build a deterministic DOT graph from the translated registry.

    Composition references with one candidate become direct edges. References
    with multiple candidates get an explicit proxy node connected to every
    candidate, so the drawing never pretends an ambiguous link is certain.
    Unresolved mass references also get proxy nodes, preserving the missing
    information visibly.
    """
    selected_symbols = {item.strip() for item in symbols or () if item.strip()}
    allowed_kinds = {HYPERATOM_KIND}
    if include_templates:
        allowed_kinds.update({ELEMENT_TEMPLATE_KIND, ELEMENT_SYMBOL_KIND, MOLECULE_KIND, OTHER_KIND})

    included = {obj.id: obj for obj in registry.definitions if obj.kind in allowed_kinds}
    if selected_symbols:
        roots = {obj.id for obj in included.values() if obj.symbol in selected_symbols}
        closure = set(roots)
        queue = list(roots)
        while queue:
            current = registry.by_id[queue.pop()]
            for component in current.components:
                if component.reference_kind == "symbol" and not include_templates:
                    continue
                for candidate_id in component.candidate_ids:
                    candidate = registry.by_id.get(candidate_id)
                    if candidate is not None and candidate.kind in allowed_kinds and candidate_id not in closure:
                        closure.add(candidate_id)
                        queue.append(candidate_id)
        included = {object_id: obj for object_id, obj in included.items() if object_id in closure}

    if not included:
        requested = ", ".join(sorted(selected_symbols)) if selected_symbols else "the requested registry"
        raise ValueError(f"No graphable hyperatom definitions found for {requested}.")

    lines = [
        "digraph hyperatoms {",
        f'  graph [rankdir="LR", bgcolor="white", pad="0.25", nodesep="0.22", ranksep="0.55", splines="spline", labelloc="t", labeljust="l", label="{_escape(title)}", fontsize="15", fontname="Helvetica-Bold"];',
        '  node [fontname="Helvetica", fontsize="9", margin="0.08,0.05", style="filled,rounded", color="#667085", penwidth="1.0"];',
        '  edge [fontname="Helvetica", fontsize="8", color="#667085", arrowsize="0.65"];',
    ]

    template_ordinals = _template_ordinals(included.values())
    for obj in sorted(included.values(), key=lambda value: (value.symbol or "", value.atomic_mass or -1, value.canonical, value.id)):
        label = _node_label(obj, template_ordinals)
        shape, fill, fontcolor = _node_style(obj)
        tooltip = f"{obj.canonical}\\nsource={obj.source_path} statement={obj.statement_index}\\nkind={obj.kind}"
        lines.append(
            f'  "{obj.id}" [label="{_escape(label)}", tooltip="{_escape(tooltip)}", '
            f'shape="{shape}", fillcolor="{fill}", fontcolor="{fontcolor}"];'
        )

    proxy_nodes: dict[str, tuple[str, str]] = {}
    graph_edges: list[str] = []
    for obj in sorted(included.values(), key=lambda value: value.id):
        for component in obj.components:
            if component.reference_kind == "symbol" and not include_templates:
                continue
            candidate_ids = [candidate_id for candidate_id in component.candidate_ids if candidate_id in included]
            if len(candidate_ids) == 1:
                edge_label = component.separator or "contains"
                graph_edges.append(
                    f'  "{obj.id}" -> "{candidate_ids[0]}" [label="{_escape(edge_label)}", tooltip="{_escape(component.canonical)}"];'
                )
            elif len(candidate_ids) > 1:
                proxy_id = _proxy_id(obj.id, component)
                proxy_label = _proxy_label(component, len(candidate_ids))
                proxy_nodes[proxy_id] = (proxy_label, f"Ambiguous reference {component.canonical}; candidates={len(candidate_ids)}")
                edge_label = component.separator or "contains"
                graph_edges.append(
                    f'  "{obj.id}" -> "{proxy_id}" [label="{_escape(edge_label)}", tooltip="{_escape(component.canonical)}"];'
                )
                for candidate_id in sorted(candidate_ids):
                    graph_edges.append(
                        f'  "{proxy_id}" -> "{candidate_id}" [style="dashed", color="#98A2B3", label="candidate"];'
                    )
            elif not component.candidate_ids and component.resolution == "unresolved" and _needs_proxy(component, include_templates):
                proxy_id = _proxy_id(obj.id, component)
                proxy_nodes[proxy_id] = (_unresolved_label(component), f"Unresolved reference {component.canonical}")
                edge_label = component.separator or "contains"
                graph_edges.append(
                    f'  "{obj.id}" -> "{proxy_id}" [label="{_escape(edge_label)}", style="dashed", tooltip="{_escape(component.canonical)}"];'
                )

    for proxy_id, (label, tooltip) in sorted(proxy_nodes.items()):
        ambiguous = "candidates=" in tooltip
        fill = "#FFF2CC" if ambiguous else "#FEE4E2"
        color = "#B54708" if ambiguous else "#B42318"
        lines.append(
            f'  "{proxy_id}" [label="{_escape(label)}", tooltip="{_escape(tooltip)}", '
            f'shape="diamond", style="filled", fillcolor="{fill}", color="{color}", fontsize="8"];'
        )
    lines.extend(graph_edges)
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_hyperatom_graph(
    registry: HyperatomRegistry,
    output: str | Path,
    *,
    include_templates: bool = False,
    symbols: Iterable[str] | None = None,
    layout: str = "dot",
    format: str | None = None,
    title: str = "ÆToE semantic hyperatom graph",
) -> Path:
    """Write `.dot` source or render through Graphviz to the requested format."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    chosen_format = (format or ("dot" if output_path.suffix.lower() == ".dot" else output_path.suffix.lower().lstrip("."))).lower()
    if chosen_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported Graphviz format {chosen_format!r}. Choose from {', '.join(SUPPORTED_FORMATS)}.")
    if layout not in SUPPORTED_LAYOUTS:
        raise ValueError(f"Unsupported Graphviz layout {layout!r}. Choose from {', '.join(SUPPORTED_LAYOUTS)}.")
    dot = hyperatom_graph_to_dot(registry, include_templates=include_templates, symbols=symbols, title=title)
    if chosen_format == "dot":
        if output_path.suffix.lower() != ".dot":
            output_path = output_path.with_suffix(".dot")
        output_path.write_text(dot, encoding="utf-8")
        return output_path

    executable = shutil.which(layout)
    if executable is None:
        raise RuntimeError(
            f"Graphviz layout executable '{layout}' was not found. Install Graphviz or request format='dot'."
        )
    command = [executable, f"-T{chosen_format}", "-o", str(output_path)]
    result = subprocess.run(command, input=dot, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"Graphviz rendering failed: {detail}")
    return output_path


def _template_ordinals(objects: Iterable[SemanticHyperatom]) -> dict[str, int]:
    grouped: dict[str, list[SemanticHyperatom]] = {}
    for obj in objects:
        if obj.kind == ELEMENT_TEMPLATE_KIND and obj.symbol:
            grouped.setdefault(obj.symbol, []).append(obj)
    result: dict[str, int] = {}
    for symbol, items in grouped.items():
        for index, obj in enumerate(sorted(items, key=lambda value: (value.canonical, value.id)), start=1):
            result[obj.id] = index
    return result


def _node_label(obj: SemanticHyperatom, template_ordinals: dict[str, int]) -> str:
    if obj.kind == HYPERATOM_KIND:
        return obj.designation
    if obj.kind == ELEMENT_TEMPLATE_KIND:
        ordinal = template_ordinals.get(obj.id, 1)
        return f"{obj.symbol} · template {ordinal}"
    if obj.kind == ELEMENT_SYMBOL_KIND:
        return str(obj.symbol or obj.canonical)
    if obj.kind == MOLECULE_KIND:
        return obj.designation + " · molecule"
    return obj.designation


def _node_style(obj: SemanticHyperatom) -> tuple[str, str, str]:
    if obj.kind == HYPERATOM_KIND:
        return "box", "#E8F1FB", "#17365D"
    if obj.kind == ELEMENT_TEMPLATE_KIND:
        return "hexagon", "#E7F6EC", "#155B35"
    if obj.kind == ELEMENT_SYMBOL_KIND:
        return "ellipse", "#F2F4F7", "#344054"
    if obj.kind == MOLECULE_KIND:
        return "component", "#F4EBFF", "#5925DC"
    return "box", "#F2F4F7", "#344054"


def _needs_proxy(component: SemanticComponent, include_templates: bool) -> bool:
    if component.reference_kind == "symbol":
        return include_templates
    return component.reference_kind in {"mass", "group", "explicit_object", "other"}


def _proxy_label(component: SemanticComponent, count: int) -> str:
    if component.mass is not None:
        return f"mass {component.mass}\nambiguous ×{count}"
    if component.symbol:
        return f"{component.symbol}\nambiguous ×{count}"
    return f"reference\nambiguous ×{count}"


def _unresolved_label(component: SemanticComponent) -> str:
    if component.mass is not None:
        return f"mass {component.mass}\nunresolved"
    if component.symbol:
        return f"{component.symbol}\nunresolved"
    return f"{component.canonical}\nunresolved"


def _proxy_id(parent_id: str, component: SemanticComponent) -> str:
    digest = sha256(f"{parent_id}\0{component.index}\0{component.canonical}".encode("utf-8")).hexdigest()[:12]
    return f"ref_{digest}"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")
