"""Graphviz DOT generation for a semantic ÆToE hyperatom registry.

DOT generation has no Python package dependency. Rendering SVG/PNG/PDF requires
an installed Graphviz executable (for example `dot`).
"""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
from typing import Iterable

from .elements import ElementCatalog
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
from .style import (
    StyleElement,
    StyleSettings,
    chemical_category_slug,
    get_style_settings,
    normalize_mode,
    normalize_target,
)
from .styles.graphviz import ( 
    resolve_graphviz_style,  
    atom_graph_default_nodesep_and_ranksep,
    atom_graph_node_default_width_and_height,
    atom_graph_node_width_and_height,
)


SUPPORTED_LAYOUTS = ("dot", "neato", "fdp", "sfdp", "circo", "twopi")
SUPPORTED_FORMATS = ("dot", "svg", "png", "pdf", "ps", "json")

# ÆToE treats these as independently named chemical elements, not as
# recursively decomposable element templates for numbering/periodic maps.
_NON_INDEXED_ELEMENT_SYMBOLS = frozenset({"H", "D", "T", "Ht"})
_UNIQUE_ELEMENT_SYMBOLS = frozenset({"H", "D", "T", "Ht"})


def _active_style_settings(mode: str | None = None, target: str | None = None) -> StyleSettings:
    """Resolve explicit per-call overrides against the process-wide style settings."""
    current = get_style_settings()
    return StyleSettings(
        mode=normalize_mode(mode, default=current.mode),
        target=normalize_target(target, default=current.target),
    )


def _dot_value(value: object) -> str:
    """Format a Graphviz attribute value without leaking raw quotes/newlines."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return '"' + _escape(str(value)) + '"'


def _dot_attributes(attributes: dict[str, object]) -> str:
    return ", ".join(f"{key}={_dot_value(value)}" for key, value in attributes.items() if value is not None)


def _graphviz_header(
    graph_name: str,
    title: str | None,
    graph_type: str,
    *,
    mode: str | None = None,
    target: str | None = None,
    nodesep: str | None = None,
    ranksep: str | None = None,
    compact: bool = False,
) -> list[str]:
    """Build graph/node/edge defaults from the selected cascade stylesheet."""
    settings = _active_style_settings(mode, target)
    graph = resolve_graphviz_style(StyleElement.create("graph", classes={f"graph-{graph_type}"}), mode=settings.mode, target=settings.target)
    node = resolve_graphviz_style(StyleElement.create("node"), mode=settings.mode, target=settings.target)
    edge = resolve_graphviz_style(StyleElement.create("edge"), mode=settings.mode, target=settings.target)
    if title:
        graph["label"] = title
    else:
        graph.pop("label", None)
    if nodesep is not None:
        graph["nodesep"] = nodesep
    if ranksep is not None:
        graph["ranksep"] = ranksep
    if compact:
        # Graphviz's default padding and the stylesheet's editorial margins
        # are useful for presentation graphics, but waste pixels in structural
        # diagrams intended to be embedded in books, articles and web pages.
        #graph.update({"pad": "1", "margin": "0", "splines": "line"})
        graph.update({"pad": "0.07", "margin": "0", "splines": "spline"})
        node.update({"margin": "0", "fontsize": 11})
        edge.update({"arrowhead": "none", "arrowsize": 0.45})
    return [
        f"digraph {graph_name} {{",
        f"  graph [{_dot_attributes(graph)}];",
        f"  node [{_dot_attributes(node)}];",
        f"  edge [{_dot_attributes(edge)}];",
    ]


def _atom_level(obj: SemanticHyperatom) -> int:
    """Return the inferred atomic level, bounded for display heuristics.

    ``matter_level`` is a different semantic dimension and must not be used as
    a fallback for atomic level when sizing a graph node.
    """
    value = obj.atomic_level or 1
    return max(1, min(8, int(value)))


def _compact_spacing(level: int) -> tuple[str, str]:
    """Return compact ``(nodesep, ranksep)`` values in inches.

    Both dimensions contract monotonically as the displayed atomic level
    increases.  These are rendering heuristics, not physical constants.
    """
    level = max(1, min(8, int(level)))
    nodesep = max(0.035, 0.17 - 0.019 * (level - 1))
    ranksep = max(0.045, 0.21 - 0.023 * (level - 1))
    return f"{nodesep:.3f}", f"{ranksep:.3f}"


def _compact_node_label(
    obj: SemanticHyperatom,
    *,
    graph_type: str,
    number: int = 0,
    show_subelement_numbers: bool = True,
    tree_root_level: int | None = None,
    depth: int | None = None,
) -> str:
    """Produce short display labels; the full notation remains in tooltips."""

    # Protium is a special case: the mass-qualified form H-1-1 adds no useful
    # information to the picture. In high-level trees, repeated H labels are
    # suppressed entirely, leaving the role-coloured circles as the notation.

    if graph_type == "hyperatom-tree" and (depth or 0) >= 4:
        return ""  
    
    if obj.symbol in _UNIQUE_ELEMENT_SYMBOLS:
        return obj.symbol
    
    symbol = obj.symbol or obj.designation                     

    if graph_type == "periodic-map":
        if (
            show_subelement_numbers
            and number > 0
            and obj.kind == ELEMENT_TEMPLATE_KIND
            and obj.symbol not in _NON_INDEXED_ELEMENT_SYMBOLS
        ):
            return f"{symbol}:{number}"
        return symbol

    # The designation carries an element/isotope identity but deliberately
    # omits the recursive structure, which is already encoded by the edges.
    return obj.designation


def _compact_node_geometry(
    obj: SemanticHyperatom,
    *,
    level: int,
    depth: int = 0,
    tree_root_level: int | None = None,
    label: str | None = None,
    map: bool = False,
) -> dict[str, object]:
    """Return per-node geometry that scales down for higher-level trees."""

    attrs: dict[str, object] = {
        #"margin": "0",
        "fixedsize": True,
        #"fixedsize": False,
        #"style": "filled",
    }    
    if 1:
        w_h = atom_graph_node_default_width_and_height()        
        attrs.update({
            "width": f"{w_h[0]:.3f}",
            "height": f"{w_h[1]:.3f}",              
        })          
        w_h = atom_graph_node_width_and_height(depth, label, map);
        if w_h[0] > 0:
            attrs.update({
                "width": f"{w_h[0]:.3f}",
            })      
        if w_h[1] > 0:
            attrs.update({
                "height": f"{w_h[1]:.3f}",            
            })  
        return attrs                     

    context_level = tree_root_level if tree_root_level is not None else level
    context_level = max(1, min(8, int(context_level)))
    depth = max(0, int(depth))
    fontsize = max(4.0, 8.5 - 0.48 * (context_level - 1) - 0.16 * depth)
    penwidth = max(0.45, 0.95 - 0.055 * (context_level - 1))
    attrs: dict[str, object] = {
        "margin": "0",
        "fontsize": round(fontsize, 2),
        "penwidth": round(penwidth, 2),
    }

    if (
        obj.symbol == "H"
        and obj.kind in {HYPERATOM_KIND, ELEMENT_SYMBOL_KIND, ELEMENT_TEMPLATE_KIND}
        and (obj.atomic_mass in {None, 1})
    ):
        if tree_root_level is None:
            # Maps still need a legible H glyph; the aggressively small empty
            # circles are reserved for repeated Protium in high-level trees.
            diameter = max(0.14, 0.22 - 0.014 * (level - 1))
        elif context_level < 5:
            diameter = max(0.14, 0.22 - 0.014 * (context_level - 1) - 0.005 * depth)
        else:
            diameter = max(0.045, 0.095 - 0.008 * (context_level - 5) - 0.003 * depth)
        attrs.update({
            "width": f"{diameter:.3f}",
            "height": f"{diameter:.3f}",
            "fixedsize": True,
        })
    return attrs


def _style_proxy_node(
    *,
    ambiguous: bool,
    graph_type: str,
    mode: str | None = None,
    target: str | None = None,
) -> dict[str, object]:
    classes = {"proxy", "ambiguous" if ambiguous else "unresolved", f"graph-{graph_type}"}
    return resolve_graphviz_style(
        StyleElement.create("node", classes=classes),
        mode=mode,
        target=target,
    )


def hyperatom_graph_to_dot(
    registry: HyperatomRegistry,
    *,
    include_templates: bool = False,
    symbols: Iterable[str] | None = None,
    title: str | None = None,
    show_element_names: bool = False,
    language: str = "en",
    periodic: bool = False,
    show_subelement_numbers: bool = True,
    mode: str | None = None,
    target: str | None = None,
) -> str:
    """Build a deterministic DOT graph from the translated registry.

    Composition references with one candidate become direct edges. References
    with multiple candidates get an explicit proxy node connected to every
    candidate, so the drawing never pretends an ambiguous link is certain.
    Unresolved mass references also get proxy nodes, preserving the missing
    information visibly. Layout is vertical by default. For a strict periodic
    element map use ``periodic=True`` or :func:`periodic_map_to_dot`; that mode
    includes only chemical-element definitions. ``show_subelement_numbers``
    controls whether nonzero element-substructure indices are shown there.
    """
    if periodic:
        return periodic_map_to_dot(
            registry, symbols=symbols, title=title,
            show_element_names=show_element_names, language=language,
            show_subelement_numbers=show_subelement_numbers,
            mode=mode, target=target,
        )
    selected_symbols = {item.strip() for item in symbols or () if item.strip()}
    allowed_kinds = {HYPERATOM_KIND}
    if include_templates:
        allowed_kinds.update({ELEMENT_TEMPLATE_KIND, ELEMENT_SYMBOL_KIND, MOLECULE_KIND, OTHER_KIND})

    included = {obj.id: obj for obj in registry.definitions if obj.kind in allowed_kinds}
    if selected_symbols:
        # A token may identify either an element (legacy behaviour), a full
        # canonical hyperatom notation, its compact designation, or a semantic ID.
        # This lets level and curated hyperatom-group items select exact objects.
        roots = {
            obj.id for obj in included.values()
            if obj.symbol in selected_symbols
            or obj.designation in selected_symbols
            or obj.canonical in selected_symbols
            or obj.id in selected_symbols
        }
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

    lines = _graphviz_header(
        "hyperatoms", title, "hyperatom-graph", mode=mode, target=target,
    )

    template_ordinals = _template_ordinals(registry.definitions)
    subelement_numbers = build_element_subelement_numbering(registry) if periodic else {}
    for obj in sorted(included.values(), key=lambda value: (value.symbol or "", value.atomic_mass or -1, value.canonical, value.id)):
        label = _node_label(
            obj, template_ordinals, registry.element_catalog,
            show_element_names=show_element_names, language=language,
            periodic=periodic, subelement_number=subelement_numbers.get(obj.id, 0),
            periodic_registry=registry, subelement_numbers=subelement_numbers,
        )
        style = _node_style(obj, graph_type="hyperatom-graph", mode=mode, target=target)
        tooltip = f"{obj.canonical}\nsource={obj.source_path} statement={obj.statement_index}\nkind={obj.kind}"
        attributes = {"label": label, "tooltip": tooltip, **style}
        lines.append(f'  "{obj.id}" [{_dot_attributes(attributes)}];')

    proxy_nodes: dict[str, tuple[str, str]] = {}
    graph_edges: list[str] = []
    for obj in sorted(included.values(), key=lambda value: value.id):
        for component in obj.components:
            if component.reference_kind == "symbol" and not include_templates:
                continue
            candidate_ids = [candidate_id for candidate_id in component.candidate_ids if candidate_id in included]
            if periodic and obj.kind == ELEMENT_TEMPLATE_KIND and component.symbol == obj.symbol:
                # Recursive element references point to the immediately lower
                # subelement, not to themselves or every possible same-symbol template.
                current_number = subelement_numbers.get(obj.id, 0)
                lower = [
                    candidate_id for candidate_id in candidate_ids
                    if subelement_numbers.get(candidate_id, 0) < current_number
                ]
                if lower:
                    immediately_lower = max(subelement_numbers[candidate_id] for candidate_id in lower)
                    candidate_ids = [
                        candidate_id for candidate_id in lower
                        if subelement_numbers.get(candidate_id, 0) == immediately_lower
                    ]
            if len(candidate_ids) == 1:
                graph_edges.append(
                    f'  "{obj.id}" -> "{candidate_ids[0]}" [tooltip="{_escape(component.canonical)}"];'
                )
            elif len(candidate_ids) > 1:
                proxy_id = _proxy_id(obj.id, component)
                proxy_label = _proxy_label(component, len(candidate_ids))
                proxy_nodes[proxy_id] = (proxy_label, f"Ambiguous reference {component.canonical}; candidates={len(candidate_ids)}")
                graph_edges.append(
                    f'  "{obj.id}" -> "{proxy_id}" [tooltip="{_escape(component.canonical)}"];'
                )
                for candidate_id in sorted(candidate_ids):
                    graph_edges.append(
                        f'  "{proxy_id}" -> "{candidate_id}" [style="dashed", color="#98A2B3", label="candidate"];'
                    )
            elif not component.candidate_ids and component.resolution == "unresolved" and _needs_proxy(component, include_templates):
                proxy_id = _proxy_id(obj.id, component)
                proxy_nodes[proxy_id] = (_unresolved_label(component), f"Unresolved reference {component.canonical}")
                graph_edges.append(
                    f'  "{obj.id}" -> "{proxy_id}" [style="dashed", tooltip="{_escape(component.canonical)}"];'
                )

    for proxy_id, (label, tooltip) in sorted(proxy_nodes.items()):
        ambiguous = "candidates=" in tooltip
        style = _style_proxy_node(
            ambiguous=ambiguous, graph_type="hyperatom-graph", mode=mode, target=target,
        )
        lines.append(
            f'  "{proxy_id}" [{_dot_attributes({"label": label, "tooltip": tooltip, **style})}];'
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
    title: str | None = None,
    show_element_names: bool = False,
    language: str = "en",
    periodic: bool = False,
    show_subelement_numbers: bool = True,
    mode: str | None = None,
    target: str | None = None,
) -> Path:
    """Write `.dot` source or render through Graphviz to the requested format."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    chosen_format = (format or ("dot" if output_path.suffix.lower() == ".dot" else output_path.suffix.lower().lstrip("."))).lower()
    if chosen_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported Graphviz format {chosen_format!r}. Choose from {', '.join(SUPPORTED_FORMATS)}.")
    if layout not in SUPPORTED_LAYOUTS:
        raise ValueError(f"Unsupported Graphviz layout {layout!r}. Choose from {', '.join(SUPPORTED_LAYOUTS)}.")
    dot = hyperatom_graph_to_dot(
        registry, include_templates=include_templates, symbols=symbols, title=title,
        show_element_names=show_element_names, language=language, periodic=periodic,
        show_subelement_numbers=show_subelement_numbers, mode=mode, target=target,
    )
    return _write_dot_or_render_ex(dot, output_path, layout=layout, format=chosen_format)



def periodic_map_to_dot(
    registry: HyperatomRegistry,
    *,
    symbols: Iterable[str] | None = None,
    title: str | None = None,
    show_element_names: bool = False,
    language: str = "en",
    show_subelement_numbers: bool = True,
    compact: bool = True,
    mode: str | None = None,
    target: str | None = None,
) -> str:
    """Build a vertical map containing chemical-element definitions only.

    Concrete hyperatoms are deliberately excluded. Edges connect element
    templates/symbols to their element subcomponents; H, D, T and Ht are
    treated as standalone named elements for numbering (their label stays at
    index zero), while any source-template components remain visible as edges.
    By default, labels and layout are compact and no graph title is emitted;
    pass ``compact=False`` for detailed structural labels.
    """
    selected = {item.strip() for item in symbols or () if item.strip()}
    element_kinds = {ELEMENT_TEMPLATE_KIND, ELEMENT_SYMBOL_KIND}
    elements = {
        obj.id: obj for obj in registry.definitions
        if obj.kind in element_kinds
    }
    if selected:
        roots = {
            obj.id for obj in elements.values()
            if obj.symbol in selected or obj.canonical in selected
            or obj.designation in selected or obj.id in selected
        }
        included_ids = set(roots)
        queue = list(sorted(roots))
        while queue:
            current = registry.by_id[queue.pop()]
            # These symbols are not assigned subelement indices, but their
            # source templates can still have meaningful structural edges
            # (for example D -> H). Continue traversal so those child elements
            # are included in a selected periodic map.
            for component in current.components:
                for candidate_id in component.candidate_ids:
                    candidate = elements.get(candidate_id)
                    if candidate is None:
                        continue
                    if candidate.id not in included_ids:
                        included_ids.add(candidate.id)
                        queue.append(candidate.id)
        elements = {item: obj for item, obj in elements.items() if item in included_ids}
    if not elements:
        requested = ", ".join(sorted(selected)) if selected else "the requested registry"
        raise ValueError(f"No chemical-element definitions found for {requested}.")

    numbers = build_element_subelement_numbering(registry)
    max_level = max((_atom_level(obj) for obj in elements.values()), default=1)
    nodesep, ranksep = _compact_spacing(max_level) if compact else (None, None)
    lines = _graphviz_header(
        "periodic_map", title, "periodic-map", mode=mode, target=target,
        nodesep=nodesep, ranksep=ranksep, compact=compact,
    )
    ordered = sorted(
        elements.values(),
        key=lambda obj: (obj.symbol or "", numbers.get(obj.id, 0), obj.canonical, obj.id),
    )
    for obj in ordered:
        number = numbers.get(obj.id, 0)
        label = (
            _compact_node_label(
                obj, graph_type="periodic-map", number=number,
                show_subelement_numbers=show_subelement_numbers,
            )
            if compact else _periodic_label(
                obj, number, registry, numbers,
                show_subelement_numbers=show_subelement_numbers,
            )
        )
        if show_element_names and registry.element_catalog is not None and obj.symbol:
            element = registry.element_catalog.get(obj.symbol)
            if element is not None:
                localized = element.name(language)
                if localized and localized != obj.symbol:
                    label += f"\n{localized}"
        style = _node_style(obj, graph_type="periodic-map", mode=mode, target=target)
        tooltip = f"{obj.canonical}\nsource={obj.source_path} statement={obj.statement_index}\nkind={obj.kind}"
        attributes = {"label": label, "tooltip": tooltip, **style}
        if compact:
            attributes.update(_compact_node_geometry(obj, level=_atom_level(obj), label=label, map=True))
        lines.append(f'  "{obj.id}" [{_dot_attributes(attributes)}];')

    # Do not de-duplicate edges by (parent, child, symbol): each entry in
    # ``obj.components`` is a separate subatom occurrence. In particular,
    # D-(H'H) contributes two D -> H edges and Ht-(H'H'H) contributes three.
    # The graph is intentionally non-strict so Graphviz preserves parallel
    # edges between the same pair of element nodes.
    edges: list[tuple[str, str, str, int]] = []
    for obj in ordered:
        # Independent element symbols keep index 0, but their structural
        # component edges remain visible: D -> H (twice), T -> D/H, Ht -> H (thrice).
        parent_number = numbers.get(obj.id, 0)
        for component in obj.components:
            targets = [
                candidate_id for candidate_id in component.candidate_ids
                if candidate_id in elements
            ]
            if component.symbol == obj.symbol and obj.kind == ELEMENT_TEMPLATE_KIND:
                lower = [
                    target for target in targets
                    if numbers.get(target, 0) < parent_number
                ]
                if lower:
                    lowest_step = max(numbers.get(target, 0) for target in lower)
                    targets = [target for target in lower if numbers.get(target, 0) == lowest_step]
                else:
                    # No lower same-symbol template means this isn't a link
                    # to a valid lower subelement (or this source is the base).
                    targets = []
            for target_id in targets:
                edges.append((obj.id, target_id, component.canonical, component.index))
    for source_id, target_id, component_text, occurrence_index in sorted(edges):
        lines.append(
            f'  "{source_id}" -> "{target_id}" '
            f'[tooltip="{_escape(component_text)} (occurrence {occurrence_index + 1})"];'
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_periodic_map(
    registry: HyperatomRegistry,
    output: str | Path,
    *,
    symbols: Iterable[str] | None = None,
    layout: str = "dot",
    format: str | None = None,
    title: str | None = None,
    show_element_names: bool = False,
    language: str = "en",
    show_subelement_numbers: bool = True,
    compact: bool = True,
    mode: str | None = None,
    target: str | None = None,
) -> Path:
    """Write a periodic map as DOT or render it using an installed Graphviz layout."""
    output_path = Path(output)
    chosen_format = (format or ("dot" if output_path.suffix.lower() == ".dot" else output_path.suffix.lower().lstrip("."))).lower()
    if chosen_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported Graphviz format {chosen_format!r}. Choose from {', '.join(SUPPORTED_FORMATS)}.")
    if layout not in SUPPORTED_LAYOUTS:
        raise ValueError(f"Unsupported Graphviz layout {layout!r}. Choose from {', '.join(SUPPORTED_LAYOUTS)}.")
    dot = periodic_map_to_dot(
        registry, symbols=symbols, title=title,
        show_element_names=show_element_names, language=language,
        show_subelement_numbers=show_subelement_numbers, compact=compact,
        mode=mode, target=target,
    )
    return _write_dot_or_render_ex(dot, output_path, layout=layout, format=chosen_format)


def hyperatom_map_to_dot(
    registry: HyperatomRegistry,
    *,
    symbols: Iterable[str] | None = None,
    title: str | None = None,
    show_element_names: bool = False,
    language: str = "en",
    show_subelement_numbers: bool = True,
    compact: bool = True,
    mode: str | None = None,
    target: str | None = None,
) -> str:
    """Build a vertical map whose graph nodes are concrete hyperatoms only.

    Candidate ambiguity is represented by direct edges to each concrete
    hyperatom candidate, not by proxy nodes. Unresolved subatoms have no edge,
    because the map's nodes are exclusively concrete hyperatom definitions.
    Compact mode labels atoms with short designations and leaves structure to
    the edges; full canonical notations remain in tooltips.
    """
    selected = {item.strip() for item in symbols or () if item.strip()}
    atoms = {obj.id: obj for obj in registry.definitions if obj.kind == HYPERATOM_KIND}
    if selected:
        roots = {
            obj.id for obj in atoms.values()
            if obj.symbol in selected or obj.canonical in selected
            or obj.designation in selected or obj.id in selected
        }
        included_ids = set(roots)
        queue = list(sorted(roots))
        while queue:
            current = registry.by_id[queue.pop()]
            for component in current.components:
                for candidate_id in component.candidate_ids:
                    if candidate_id in atoms and candidate_id not in included_ids:
                        included_ids.add(candidate_id)
                        queue.append(candidate_id)
        atoms = {item: obj for item, obj in atoms.items() if item in included_ids}
    if not atoms:
        requested = ", ".join(sorted(selected)) if selected else "the requested registry"
        raise ValueError(f"No concrete hyperatom definitions found for {requested}.")

    numbers = build_element_subelement_numbering(registry)
    max_level = max((_atom_level(obj) for obj in atoms.values()), default=1)
    nodesep, ranksep = _compact_spacing(max_level) if compact else (None, None)
    lines = _graphviz_header(
        "hyperatom_map", title, "hyperatom-map", mode=mode, target=target,
        nodesep=nodesep, ranksep=ranksep, compact=compact,
    )
    ordered = sorted(atoms.values(), key=lambda obj: (obj.symbol or "", numbers.get(obj.id, 0), obj.atomic_mass or -1, obj.canonical, obj.id))
    for obj in ordered:
        label = (
            _compact_node_label(obj, graph_type="hyperatom-map")
            if compact else _periodic_label(
                obj, numbers.get(obj.id, 0), registry, numbers,
                show_subelement_numbers=show_subelement_numbers,
            )
        )
        if show_element_names and registry.element_catalog is not None and obj.symbol:
            element = registry.element_catalog.get(obj.symbol)
            if element is not None:
                localized = element.name(language)
                if localized and localized != obj.symbol:
                    label += f"\n{localized}"
        style = _node_style(obj, graph_type="hyperatom-map", mode=mode, target=target)
        tooltip = f"{obj.canonical}\nsource={obj.source_path} statement={obj.statement_index}\nkind={obj.kind}"
        attributes = {"label": label, "tooltip": tooltip, **style}
        if compact:
            attributes.update(_compact_node_geometry(obj, level=_atom_level(obj), label=label, map=True))
        lines.append(f'  "{obj.id}" [{_dot_attributes(attributes)}];')

    # Preserve every component occurrence, including parallel edges to the same
    # child definition; the graph is deliberately non-strict.
    edges: list[tuple[str, str, str, int]] = []
    for obj in ordered:
        for component in obj.components:
            for target_id in component.candidate_ids:
                if target_id in atoms:
                    edges.append((obj.id, target_id, component.canonical, component.index))
    for source_id, target_id, component_text, occurrence_index in sorted(edges):
        lines.append(
            f'  "{source_id}" -> "{target_id}" '
            f'[tooltip="{_escape(component_text)} (occurrence {occurrence_index + 1})"];'
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_hyperatom_map(
    registry: HyperatomRegistry,
    output: str | Path,
    *,
    symbols: Iterable[str] | None = None,
    layout: str = "dot",
    format: str | None = None,
    title: str | None = None,
    show_element_names: bool = False,
    language: str = "en",
    show_subelement_numbers: bool = True,
    compact: bool = True,
    mode: str | None = None,
    target: str | None = None,
) -> Path:
    """Write a hyperatom map as DOT or render it through Graphviz."""
    output_path = Path(output)
    chosen_format = (format or ("dot" if output_path.suffix.lower() == ".dot" else output_path.suffix.lower().lstrip("."))).lower()
    if chosen_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported Graphviz format {chosen_format!r}. Choose from {', '.join(SUPPORTED_FORMATS)}.")
    if layout not in SUPPORTED_LAYOUTS:
        raise ValueError(f"Unsupported Graphviz layout {layout!r}. Choose from {', '.join(SUPPORTED_LAYOUTS)}.")
    dot = hyperatom_map_to_dot(
        registry, symbols=symbols, title=title,
        show_element_names=show_element_names, language=language,
        show_subelement_numbers=show_subelement_numbers, compact=compact,
        mode=mode, target=target,
    )
    return _write_dot_or_render_ex(dot, output_path, layout=layout, format=chosen_format)


def build_element_subelement_numbering(registry: HyperatomRegistry) -> dict[str, int]:
    """Return stable, automatically inferred subelement numbers by object ID.

    The base objects are element-template statements. Their direct component
    symbols form a structural signature, so isotope-specific hyperatoms with
    the same signature inherit the template's number. Signatures are grouped
    per element; structurally identical alternatives share one number. The
    ordering is bottom-up: non-recursive templates precede templates that
    contain their own element symbol, and children of greater structural depth
    sort after shallower children. Elements without components are numbered 0.

    H, D, T and Ht are kept at zero because ÆToE treats them as independently
    named elements rather than indexed subelements. This affects labels only;
    their structural components still produce periodic-map edges (for example
    D -> H). This indexing convention is inferred from `.etoe` and is not a
    new physical assertion in the ÆToE seed.
    """
    templates = {
        obj.id: obj for obj in registry.definitions
        if obj.kind == ELEMENT_TEMPLATE_KIND and obj.symbol
        and obj.symbol not in _NON_INDEXED_ELEMENT_SYMBOLS
    }
    if not templates:
        return {obj.id: 0 for obj in registry.definitions}

    signatures = {object_id: _component_symbol_signature(obj, registry) for object_id, obj in templates.items()}
    self_recursive = {
        object_id: obj.symbol in signatures[object_id]
        for object_id, obj in templates.items()
    }

    # Cross-element template dependencies are collapsed into strongly connected
    # components first. This guarantees a finite, deterministic depth even if
    # custom data contains mutually recursive element templates.
    dependencies: dict[str, set[str]] = {object_id: set() for object_id in templates}
    for object_id, obj in templates.items():
        for component in obj.components:
            for candidate_id in component.candidate_ids:
                candidate = templates.get(candidate_id)
                if candidate is not None and candidate.symbol != obj.symbol:
                    dependencies[object_id].add(candidate_id)
    component_of, components = _strongly_connected_components(dependencies)
    component_dependencies: dict[int, set[int]] = {i: set() for i in range(len(components))}
    for parent_id, child_ids in dependencies.items():
        parent_component = component_of[parent_id]
        for child_id in child_ids:
            child_component = component_of[child_id]
            if child_component != parent_component:
                component_dependencies[parent_component].add(child_component)

    depth_memo: dict[int, int] = {}
    def component_depth(index: int) -> int:
        if index not in depth_memo:
            children = component_dependencies[index]
            depth_memo[index] = 1 + max((component_depth(child) for child in children), default=0)
        return depth_memo[index]

    external_depth = {
        object_id: component_depth(component_of[object_id])
        for object_id in templates
    }
    # A recursive template is a parent of at least one lower template of the
    # same symbol. Use the shallowest non-recursive sibling as its lower anchor.
    effective_depth = dict(external_depth)
    for object_id, obj in templates.items():
        if not self_recursive[object_id]:
            continue
        lower_siblings = [
            external_depth[other_id]
            for other_id, other in templates.items()
            if other.symbol == obj.symbol and other_id != object_id and not self_recursive[other_id]
        ]
        if lower_siblings:
            effective_depth[object_id] = max(external_depth[object_id], min(lower_siblings) + 1)

    groups_by_symbol: dict[str, dict[tuple[str, ...], list[str]]] = defaultdict(lambda: defaultdict(list))
    for object_id, obj in templates.items():
        groups_by_symbol[obj.symbol][signatures[object_id]].append(object_id)

    template_number: dict[str, int] = {}
    number_by_signature: dict[tuple[str, tuple[str, ...]], int] = {}
    for symbol, grouped in groups_by_symbol.items():
        ordered_signatures = sorted(
            grouped,
            key=lambda signature: (
                any(part == symbol for part in signature),
                min(effective_depth[item] for item in grouped[signature]),
                min(external_depth[item] for item in grouped[signature]),
                signature,
                min(templates[item].canonical for item in grouped[signature]),
            ),
        )
        for number, signature in enumerate(ordered_signatures, start=1):
            number_by_signature[(symbol, signature)] = number
            for object_id in grouped[signature]:
                template_number[object_id] = number

    result: dict[str, int] = {object_id: 0 for object_id in registry.by_id}
    result.update(template_number)
    by_symbol_max: dict[str, int] = {
        symbol: max(number_by_signature[(symbol, signature)] for signature in signatures_for_symbol)
        for symbol, signatures_for_symbol in (
            (symbol, grouped.keys()) for symbol, grouped in groups_by_symbol.items()
        )
    }
    for obj in registry.definitions:
        if (obj.kind != HYPERATOM_KIND or not obj.symbol or not obj.components
                or obj.symbol in _NON_INDEXED_ELEMENT_SYMBOLS):
            continue
        signature = _component_symbol_signature(obj, registry)
        number = number_by_signature.get((obj.symbol, signature))
        if number is None:
            # Preserve the fact that an explicit composition has subelements,
            # even when a future/custom definition has no matching template.
            number = by_symbol_max.get(obj.symbol, 0) + 1
        result[obj.id] = number
    return result


# Concise alias for callers that think of the result as a numbering operation.
number_element_subelements = build_element_subelement_numbering


def hyperatom_tree_to_dot(
    registry: HyperatomRegistry,
    hyperatom: str | SemanticHyperatom,
    *,
    title: str | None = None,
    show_element_names: bool = False,
    language: str = "en",
    show_subelement_numbers: bool = True,
    compact: bool = True,
    mode: str | None = None,
    target: str | None = None,
) -> str:
    """Build a vertical occurrence tree for one concrete hyperatom.

    Unlike a map, the same definition used twice in a composition is emitted
    as two distinct occurrence nodes. If a component has multiple concrete
    hyperatom candidates, each is expanded as a separate possible branch.
    Non-hyperatom templates and unresolved references do not become graph nodes.
    Compact mode is the default; Protium labels are hidden in trees rooted at
    atomic level 5 or above, and node geometry scales with root level and depth.
    """
    root = _resolve_hyperatom(registry, hyperatom)
    root_level = _atom_level(root)
    #nodesep, ranksep = _compact_spacing(root_level) if compact else ("0.12", "0.28")
    nodesep, ranksep = atom_graph_default_nodesep_and_ranksep()
    numbering = build_element_subelement_numbering(registry)
    lines = _graphviz_header(
        "hyperatom_tree", title, "hyperatom-tree",
        mode=mode, target=target, nodesep=nodesep, ranksep=ranksep,
        compact=compact,
    )
    counter = 0
    edge_lines: list[str] = []

    def add_occurrence(
        obj: SemanticHyperatom,
        occurrence_id: str,
        ancestors: tuple[str, ...],
        *,
        position: str = "tree-root",
        parent_style: dict[str, object] | None = None,
        depth: int = 0,
    ) -> None:
        nonlocal counter
        label = (
            _compact_node_label(
                obj, graph_type="hyperatom-tree", tree_root_level=root_level, depth=depth,
            )
            if compact else _periodic_label(
                obj, numbering.get(obj.id, 0), registry, numbering,
                show_subelement_numbers=show_subelement_numbers,
            )
        )
        if show_element_names and registry.element_catalog is not None and obj.symbol:
            element = registry.element_catalog.get(obj.symbol)
            if element is not None:
                localized = element.name(language)
                if localized and localized != obj.symbol:
                    label += f"\n{localized}"
        style = _node_style(
            obj, graph_type="hyperatom-tree", position=position,
            mode=mode, target=target, parent_style=parent_style,
        )
        if compact:
            style.update(_compact_node_geometry(
                obj, level=_atom_level(obj), depth=depth,
                tree_root_level=root_level, label=label
            ))
        tooltip = f"{obj.canonical}\nsource={obj.source_path} statement={obj.statement_index}"
        lines.append(
            f'  "{occurrence_id}" [{_dot_attributes({"label": label, "tooltip": tooltip, **style})}];'
        )
        for component in obj.components:
            # A hyperatom tree contains only concrete hyperatom occurrences.
            # Element templates and unresolved references are not graph nodes.
            targets = [
                registry.by_id[item]
                for item in component.candidate_ids
                if item in registry.by_id and registry.by_id[item].kind == HYPERATOM_KIND
            ]
            if len(obj.components) == 1:
                child_position = "only-subatom"
            elif component.index == 0:
                child_position = "first-subatom"
            elif component.index == 1:
                child_position = "second-subatom"
            else:
                child_position = f"subatom-{component.index + 1}"
            for child_obj in targets:
                counter += 1
                child_id = f"occ_{counter}"
                edge_lines.append(
                    f'  "{occurrence_id}" -> "{child_id}" [tooltip="{_escape(component.canonical)}"];'
                )
                if child_obj.id in ancestors:
                    # A pathological cyclic structure must not unfold forever.
                    cycle_label = (
                        _compact_node_label(
                            child_obj, graph_type="hyperatom-tree",
                            tree_root_level=root_level, depth=depth,
                        )
                        if compact else _periodic_label(
                            child_obj, numbering.get(child_obj.id, 0), registry, numbering,
                            show_subelement_numbers=show_subelement_numbers,
                        )
                    ) + "\n(cycle)"
                    cycle_style = _node_style(
                        child_obj, graph_type="hyperatom-tree", position=child_position,
                        mode=mode, target=target, parent_style=style,
                    )
                    if compact:
                        cycle_style.update(_compact_node_geometry(
                            child_obj, level=_atom_level(child_obj), depth=depth + 1,
                            tree_root_level=root_level,
                        ))
                    lines.append(
                        f'  "{child_id}" [{_dot_attributes({"label": cycle_label, "tooltip": f"Cycle cut at {child_obj.canonical}", **cycle_style})}];'
                    )
                else:
                    add_occurrence(
                        child_obj, child_id, (*ancestors, child_obj.id),
                        position=child_position, parent_style=style, depth=depth + 1,
                    )

    add_occurrence(root, "occ_0", (root.id,))
    lines.extend(edge_lines)
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_hyperatom_tree(
    registry: HyperatomRegistry,
    hyperatom: str | SemanticHyperatom,
    output: str | Path,
    *,
    layout: str = "dot",
    format: str | None = None,
    title: str | None = None,
    show_element_names: bool = False,
    language: str = "en",
    show_subelement_numbers: bool = True,
    compact: bool = True,
    mode: str | None = None,
    target: str | None = None,
) -> Path:
    """Write a hyperatom tree as DOT or render it using Graphviz."""
    output_path = Path(output)
    chosen_format = (format or ("dot" if output_path.suffix.lower() == ".dot" else output_path.suffix.lower().lstrip("."))).lower()
    if chosen_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported Graphviz format {chosen_format!r}. Choose from {', '.join(SUPPORTED_FORMATS)}.")
    if layout not in SUPPORTED_LAYOUTS:
        raise ValueError(f"Unsupported Graphviz layout {layout!r}. Choose from {', '.join(SUPPORTED_LAYOUTS)}.")
    dot = hyperatom_tree_to_dot(
        registry, hyperatom, title=title,
        show_element_names=show_element_names, language=language,
        show_subelement_numbers=show_subelement_numbers, compact=compact,
        mode=mode, target=target,
    )
    return _write_dot_or_render_ex(dot, output_path, layout=layout, format=chosen_format)


def _write_dot_or_render(dot: str, output: Path, *, layout: str, format: str) -> Path:
    output_path = output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if format == "dot":
        if output_path.suffix.lower() != ".dot":
            output_path = output_path.with_suffix(".dot")
        output_path.write_text(dot, encoding="utf-8")
        return output_path
    executable = shutil.which(layout)
    if executable is None:
        raise RuntimeError(
            f"Graphviz layout executable '{layout}' was not found. Install Graphviz or request format='dot'."
        )
    command = [executable, f"-T{format}", "-o", str(output_path)]
    result = subprocess.run(command, input=dot, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"Graphviz rendering failed: {detail}")
    return output_path

def _write_dot_or_render_ex(dot: str, output: Path, *, layout: str, format: str) -> Path:
    output_path = output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    fmt = format.lower()
    
    if fmt == "dot":
        if output_path.suffix.lower() != ".dot":
            output_path = output_path.with_suffix(".dot")
        output_path.write_text(dot, encoding="utf-8")
        return output_path

    executable = shutil.which(layout)
    if executable is None:
        raise RuntimeError(
            f"Graphviz layout executable '{layout}' was not found. Install Graphviz or request format='dot'."
        )

    # Проверяем условие использования cairosvg для растровых форматов
    val = os.environ.get("ETOE_GRAPHVIZ_CAIROSVG", "").lower()
    use_cairosvg = ( 
        val not in ("", "0", "false", "off")
        and fmt in ("png", "jpg", "jpeg")
    )
    
    cairosvg_available = False
    if use_cairosvg:
        try:
            import cairosvg  # noqa: F401
            cairosvg_available = True
        except ImportError:
            pass

    if use_cairosvg and cairosvg_available:
        import cairosvg
        
        # Создаем временный файл для SVG, сгенерированного через Graphviz
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_svg:
            tmp_svg_path = Path(tmp_svg.name)
            
        try:
            # Рендерим dot в svg через Graphviz
            command = [executable, "-Tsvg", "-o", str(tmp_svg_path)]
            result = subprocess.run(command, input=dot, text=True, capture_output=True, check=False)
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
                raise RuntimeError(f"Graphviz SVG rendering failed: {detail}")
            
            if fmt == "png":
                # Конвертируем SVG во временный PNG через cairosvg
                cairosvg.svg2png(url=str(tmp_svg_path), write_to=str(output_path))
            else:
                # Для jpg/jpeg конвертируем сначала в png-буфер/файл, затем сохраняем через Pillow в jpeg
                from PIL import Image
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png:
                    tmp_png_path = Path(tmp_png.name)
                try:
                    cairosvg.svg2png(url=str(tmp_svg_path), write_to=str(tmp_png_path))
                    with Image.open(tmp_png_path) as img:
                        # JPEG не поддерживает прозрачность, заменяем альфа-канал на белый фон
                        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                            background = Image.new("RGB", img.size, (255, 255, 255))
                            background.paste(img, mask=img.convert("RGBA"))
                            img = background
                        else:
                            img = img.convert("RGB")
                        img.save(output_path, "JPEG")
                finally:
                    if tmp_png_path.exists():
                        tmp_png_path.unlink()
        finally:
            if tmp_svg_path.exists():
                tmp_svg_path.unlink()
                
        return output_path

    # Стандартный путь прямой генерации через Graphviz
    command = [executable, f"-T{format}", "-o", str(output_path)]
    result = subprocess.run(command, input=dot, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"Graphviz rendering failed: {detail}")
    return output_path


def _resolve_hyperatom(
    registry: HyperatomRegistry,
    hyperatom: str | SemanticHyperatom,
) -> SemanticHyperatom:
    if isinstance(hyperatom, SemanticHyperatom):
        result = registry.by_id.get(hyperatom.id)
        if result is None:
            raise ValueError("The supplied hyperatom does not belong to this registry.")
    elif isinstance(hyperatom, str) and hyperatom.strip():
        token = hyperatom.strip()
        result = registry.by_id.get(token)
        if result is None:
            candidates = [obj for obj in registry.definitions if obj.canonical == token]
            if not candidates:
                candidates = [obj for obj in registry.definitions if obj.designation == token]
            if len(candidates) != 1:
                if not candidates:
                    raise KeyError(f"No hyperatom matching {token!r} exists in this registry.")
                raise ValueError(f"Hyperatom selector {token!r} is ambiguous; use a canonical notation or semantic ID.")
            result = candidates[0]
    else:
        raise TypeError("hyperatom must be a non-empty canonical notation, semantic ID, or SemanticHyperatom")
    if result.kind != HYPERATOM_KIND:
        raise ValueError(f"{result.canonical!r} is not a concrete hyperatom definition.")
    return result


def _component_symbol_signature(obj: SemanticHyperatom, registry: HyperatomRegistry) -> tuple[str, ...]:
    return _components_symbol_signature(obj.components, registry)


def _components_symbol_signature(components: Iterable[SemanticComponent], registry: HyperatomRegistry) -> tuple[str, ...]:
    symbols: list[str] = []
    for component in components:
        if component.symbol:
            symbols.append(component.symbol)
            continue
        candidate_symbols = sorted({
            candidate.symbol for candidate_id in component.candidate_ids
            if (candidate := registry.by_id.get(candidate_id)) is not None and candidate.symbol
        })
        if len(candidate_symbols) == 1:
            symbols.append(candidate_symbols[0])
        elif candidate_symbols:
            # Keep the alternatives stable; this cannot accidentally match an
            # ordinary single-element child signature.
            symbols.append("{" + "|".join(candidate_symbols) + "}")
        elif component.mass is not None:
            symbols.append(f"mass:{component.mass}")
        else:
            symbols.append(f"ref:{component.canonical_structure}")
    return tuple(sorted(symbols))


def _strongly_connected_components(graph: dict[str, set[str]]) -> tuple[dict[str, int], tuple[tuple[str, ...], ...]]:
    """Tarjan SCCs for a small deterministic dependency graph."""
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    output: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal index
        indexes[node] = lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(graph.get(node, ())):
            if target not in indexes:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indexes[target])
        if lowlinks[node] == indexes[node]:
            members: list[str] = []
            while True:
                target = stack.pop()
                on_stack.remove(target)
                members.append(target)
                if target == node:
                    break
            output.append(tuple(sorted(members)))

    for node in sorted(graph):
        if node not in indexes:
            visit(node)
    component_of = {node: i for i, members in enumerate(output) for node in members}
    return component_of, tuple(output)

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


def _node_label(
    obj: SemanticHyperatom,
    template_ordinals: dict[str, int],
    element_catalog: ElementCatalog | None = None,
    *,
    show_element_names: bool = False,
    language: str = "en",
    periodic: bool = False,
    subelement_number: int = 0,
    periodic_registry: HyperatomRegistry | None = None,
    subelement_numbers: dict[str, int] | None = None,
) -> str:
    if periodic:
        label = _periodic_label(obj, subelement_number, periodic_registry, subelement_numbers)
    elif obj.kind == HYPERATOM_KIND:
        label = obj.designation
    elif obj.kind == ELEMENT_TEMPLATE_KIND:
        ordinal = template_ordinals.get(obj.id, 1)
        label = f"{obj.symbol} · template {ordinal}"
    elif obj.kind == ELEMENT_SYMBOL_KIND:
        label = str(obj.symbol or obj.canonical)
    elif obj.kind == MOLECULE_KIND:
        label = obj.designation + " · molecule"
    else:
        label = obj.designation

    if show_element_names and element_catalog is not None and obj.symbol:
        element = element_catalog.get(obj.symbol)
        if element is not None:
            localized_name = element.name(language)
            if localized_name and localized_name != obj.symbol:
                label += f"\n{localized_name}"
    return label



def _periodic_label(
    obj: SemanticHyperatom,
    number: int,
    registry: HyperatomRegistry | None = None,
    subelement_numbers: dict[str, int] | None = None,
    *,
    show_subelement_numbers: bool = True,
) -> str:
    """Format an element or hyperatom with optional subelement indices."""
    symbol = obj.symbol
    if not symbol:
        return obj.canonical
    if obj.kind in {ELEMENT_TEMPLATE_KIND, ELEMENT_SYMBOL_KIND} and symbol in _NON_INDEXED_ELEMENT_SYMBOLS:
        return symbol
    shown_number = number if show_subelement_numbers else 0
    suffix = f":{shown_number}" if shown_number > 0 else ""
    if obj.kind == ELEMENT_TEMPLATE_KIND:
        tail = obj.canonical[len(symbol):] if obj.canonical.startswith(symbol) else ""
        # A recursive template should name the lower same-symbol subelement
        # explicitly, e.g. He:2-(He:1'H), without changing source notation.
        if show_subelement_numbers and registry is not None and subelement_numbers is not None and number > 0:
            for component in obj.components:
                if component.symbol != symbol or component.canonical != symbol:
                    continue
                lower_numbers = [
                    subelement_numbers.get(candidate_id, 0)
                    for candidate_id in component.candidate_ids
                    if candidate_id in registry.by_id
                    and registry.by_id[candidate_id].kind == ELEMENT_TEMPLATE_KIND
                    and subelement_numbers.get(candidate_id, 0) < number
                ]
                if lower_numbers:
                    child_number = max(lower_numbers)
                    tail = re.sub(
                        rf"\b{re.escape(symbol)}\b",
                        f"{symbol}:{child_number}",
                        tail,
                    )
        return symbol + suffix + tail
    if obj.kind == HYPERATOM_KIND:
        tail = obj.canonical[len(symbol):] if obj.canonical.startswith(symbol) else ""
        return symbol + suffix + tail
    if obj.kind == ELEMENT_SYMBOL_KIND:
        return symbol
    if obj.kind == MOLECULE_KIND:
        return symbol + suffix + " · molecule"
    return obj.designation

def _node_style(
    obj: SemanticHyperatom,
    *,
    graph_type: str,
    position: str | None = None,
    mode: str | None = None,
    target: str | None = None,
    parent_style: dict[str, object] | None = None,
) -> dict[str, object]:
    """Resolve a semantic node through the shared Graphviz cascade.

    Chemical categories come from the translator's runtime category link when
    available, falling back to the package's canonical periodic-table mapping.
    Special Protium positional selectors are applied after category selectors.
    """
    classes: set[str] = {f"graph-{graph_type}"}
    if obj.kind == HYPERATOM_KIND:
        classes.add("hyperatom")
    elif obj.kind == ELEMENT_TEMPLATE_KIND:
        classes.update({"element", "element-template"})
    elif obj.kind == ELEMENT_SYMBOL_KIND:
        classes.update({"element", "element-symbol"})
    elif obj.kind == MOLECULE_KIND:
        classes.add("molecule")
    else:
        classes.add("other")

    symbol = obj.symbol
    if symbol:
        classes.add(f"symbol-{symbol}")
    category = getattr(getattr(obj, "chemical_category", None), "slug", None)
    category = category or chemical_category_slug(symbol)
    classes.update({"chemical", f"category-{category}"})
    if position:
        classes.add(f"position-{position}")

    element = StyleElement.create(
        "node",
        classes=classes,
        attributes={
            "kind": obj.kind,
            "symbol": symbol or "",
            "chemical_category": category,
            "graph_type": graph_type,
            "position": position or "",
            "atomic_mass": obj.atomic_mass if obj.atomic_mass is not None else "",
        },
    )
    return resolve_graphviz_style(
        element, mode=mode, target=target, parent=parent_style,
    )

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
