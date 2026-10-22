"""Canonical hyperatom maps with optional runtime patching of missing subatoms.

The map layer is deliberately downstream of parsing and translation.  It
consumes the existing semantic registry, uses canonical structure text for
indexing, preserves ambiguous references, and optionally supplies explicit
runtime placeholders for unresolved mass-bearing subatoms.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from math import log2
from typing import Any, Iterable

from .elements import ElementCatalog
from .hyperatom_translation import (
    HYPERATOM_KIND,
    HyperatomRegistry,
    SemanticComponent,
    SemanticHyperatom,
    TranslationDiagnostic,
    _component_atomic_level,
    _component_atomic_level_options,
    _composition_max_level_options,
    _components_structure_text,
    _infer_atomic_levels,
)


@dataclass(frozen=True, slots=True)
class HyperatomMapEdge:
    """A component reference from one hyperatom to zero or more candidates."""

    source_id: str
    component_index: int
    component_text: str
    canonical_structure: str
    target_ids: tuple[str, ...]
    target_structure_texts: tuple[str | None, ...]
    resolution: str
    auto_patched: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "component_index": self.component_index,
            "component_text": self.component_text,
            "canonical_structure": self.canonical_structure,
            "target_ids": list(self.target_ids),
            "target_structure_texts": list(self.target_structure_texts),
            "resolution": self.resolution,
            "auto_patched": self.auto_patched,
        }


@dataclass
class CanonicalHyperatomMap:
    """Canonical structural index and component links for a hyperatom registry."""

    registry: HyperatomRegistry
    auto_patch_missing: bool
    edges: tuple[HyperatomMapEdge, ...]
    by_structure: dict[str, tuple[str, ...]]
    patched_hyperatoms: tuple[str, ...] = ()

    @property
    def nodes(self) -> tuple[SemanticHyperatom, ...]:
        return self.registry.definitions

    def find_by_structure(self, structure_text: str) -> tuple[SemanticHyperatom, ...]:
        """Return every definition having this canonical structure text."""
        ids = self.by_structure.get(structure_text, ())
        return tuple(self.registry.by_id[item] for item in ids if item in self.registry.by_id)

    def statistics(self) -> dict[str, Any]:
        counts: dict[str, int] = defaultdict(int)
        for edge in self.edges:
            counts[edge.resolution] += 1
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "structural_keys": len(self.by_structure),
            "edges_by_resolution": dict(sorted(counts.items())),
            "auto_patch_missing": self.auto_patch_missing,
            "patched_hyperatoms": len(self.patched_hyperatoms),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "etoe.canonical-hyperatom-map.v1",
            "canonicalization": {
                "unordered_separator": "'",
                "mass_order": "descending; unknown masses last; structural text breaks ties",
                "structural_key": "parenthesized, recursively normalized subatom structure; element symbols omitted for mass-qualified components",
            },
            "statistics": self.statistics(),
            "patched_hyperatoms": list(self.patched_hyperatoms),
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "by_structure": {key: list(value) for key, value in sorted(self.by_structure.items())},
            "element_catalog": self.registry.element_catalog.to_dict()
            if self.registry.element_catalog is not None else None,
        }


def build_canonical_hyperatom_map(
    registry: HyperatomRegistry,
    *,
    auto_patch_missing: bool = False,
) -> CanonicalHyperatomMap:
    """Build a structure-indexed map from a translated hyperatom registry.

    With ``auto_patch_missing=True``, each unresolved mass-bearing component
    that has no candidate is bound to a synthetic hyperatom ``X<n>-mass``.
    ``n`` is inferred from a complete nested structure where possible. For a
    mass-only reference with no structural evidence, the primary-sequence level
    ``floor(log2(mass)) + 1`` is used as an explicitly recorded fallback; the
    seed does not determine a unique atom level from mass alone for arbitrary
    non-primary configurations.

    Ambiguous references are intentionally left ambiguous and are not patched.
    Runtime ``X<n>`` records are added to the in-memory ElementCatalog only;
    no source or metadata files are written to disk.
    """
    _infer_atomic_levels(registry)
    patched: list[str] = []
    if auto_patch_missing:
        patched = _patch_missing_components(registry)
        _infer_atomic_levels(registry)

    by_structure_work: dict[str, list[str]] = defaultdict(list)
    for definition in registry.definitions:
        structure_text = definition.canonical_structure
        if structure_text is not None:
            by_structure_work[structure_text].append(definition.id)
    by_structure = {
        key: tuple(sorted(ids, key=lambda item: _node_sort_key(registry.by_id[item])))
        for key, ids in by_structure_work.items()
    }

    edges: list[HyperatomMapEdge] = []
    for definition in sorted(registry.definitions, key=_node_sort_key):
        for component in definition.components:
            candidate_ids = tuple(sorted(
                (candidate_id for candidate_id in component.candidate_ids if candidate_id in registry.by_id),
                key=lambda item: _node_sort_key(registry.by_id[item]),
            ))
            edges.append(HyperatomMapEdge(
                source_id=definition.id,
                component_index=component.index,
                component_text=component.canonical,
                canonical_structure=component.canonical_structure,
                target_ids=candidate_ids,
                target_structure_texts=tuple(
                    registry.by_id[target_id].canonical_structure for target_id in candidate_ids
                ),
                resolution=component.resolution,
                auto_patched=component.resolution == "patched",
            ))

    return CanonicalHyperatomMap(
        registry=registry,
        auto_patch_missing=auto_patch_missing,
        edges=tuple(edges),
        by_structure=by_structure,
        patched_hyperatoms=tuple(sorted(patched)),
    )


def _patch_missing_components(registry: HyperatomRegistry) -> list[str]:
    """Create/reuse X<n> definitions for unresolved concrete subatoms."""
    catalog = registry.element_catalog
    if catalog is None:
        catalog = ElementCatalog(registry.root)
        registry.element_catalog = catalog

    # Work in reverse nesting order so the structure of an enclosing synthetic
    # node already carries any runtime target IDs needed by its children.
    all_components: list[tuple[SemanticHyperatom, SemanticComponent, tuple[SemanticComponent, ...]]] = []
    for definition in registry.definitions:
        for component in _walk_component_context(definition.components):
            all_components.append((definition, component[0], component[1]))
    all_components.sort(key=lambda entry: _component_depth(entry[1]), reverse=True)

    deduplicated: dict[tuple[int, int, str | None], SemanticHyperatom] = {}
    patched_ids: list[str] = []
    diagnostics = list(registry.diagnostics)
    for parent, component, siblings in all_components:
        if component.candidate_ids or component.mass is None or component.reference_kind == "primitive":
            continue
        level, level_source = _infer_missing_level(component, parent, siblings, registry)
        symbol = f"X{level}"
        catalog.register_runtime_auxiliary(
            symbol,
            atomic_level=level,
            description=f"Runtime-only auxiliary element for unresolved atomic level {level} subatoms.",
        )
        nested_text = _declared_nested_structure(component)
        key = (level, component.mass, nested_text)
        synthetic = deduplicated.get(key)
        if synthetic is None:
            structure_key = nested_text
            digest = sha256(f"{symbol}\0{component.mass}\0{structure_key or ''}".encode("utf-8")).hexdigest()[:16]
            object_id = f"runtime_ha_{digest}"
            cloned_components = deepcopy(component.children) if component.children else ()
            mass_sum = None
            mass_balance = "not_applicable"
            if cloned_components:
                child_masses = [child.mass for child in cloned_components]
                if all(value is not None for value in child_masses):
                    mass_sum = sum(value for value in child_masses if value is not None)
                    mass_balance = "consistent" if mass_sum == component.mass else "mismatch"
                else:
                    mass_balance = "unknown"
            canonical = f"{symbol}-{component.mass}"
            if structure_key is not None:
                canonical += f"-{structure_key}"
            synthetic = SemanticHyperatom(
                id=object_id,
                kind=HYPERATOM_KIND,
                canonical=canonical,
                source_path=f"<runtime:{symbol}>",
                statement_index=-1,
                symbol=symbol,
                atomic_mass=component.mass,
                primary_mass=None,
                source_comments=(),
                matter_level=5,
                syntax_depth=_component_depth(component),
                components=cloned_components,
                mass_sum=mass_sum,
                mass_balance=mass_balance,
                atomic_level=level,
                atomic_level_source=level_source,
                structure_text_override=structure_key,
                source_ast=None,
            )
            deduplicated[key] = synthetic
            registry.add_definition(synthetic)
            patched_ids.append(synthetic.id)
            diagnostics.append(TranslationDiagnostic(
                code="auto-patched-missing-subatom",
                message=(f"Unresolved component {component.canonical!r} in {parent.canonical!r} was bound to "
                         f"runtime auxiliary {canonical!r} (atomic level {level}; level source: {level_source})."),
                source_path=parent.source_path,
                statement_index=parent.statement_index,
                severity="info",
            ))
        component.candidate_ids = (synthetic.id,)
        component.resolution = "patched"

    registry.diagnostics = tuple(diagnostics)
    return patched_ids


def _walk_component_context(
    components: Iterable[SemanticComponent],
) -> Iterable[tuple[SemanticComponent, tuple[SemanticComponent, ...]]]:
    values = tuple(components)
    for component in values:
        yield component, values
        yield from _walk_component_context(component.children)


def _declared_nested_structure(component: SemanticComponent) -> str | None:
    if component.children:
        return _components_structure_text(component.children)
    # Distinguish a deliberately empty structure (``mass-()``) from a
    # mass-only reference. ``canonical`` is kept in the source's original form.
    if component.canonical.rstrip().endswith("()"):
        return "()"
    return None


def _infer_missing_level(
    component: SemanticComponent,
    parent: SemanticHyperatom,
    siblings: tuple[SemanticComponent, ...],
    registry: HyperatomRegistry,
) -> tuple[int, str]:
    if component.children:
        child_options = [
            _component_atomic_level_options(child, registry) for child in component.children
        ]
        if child_options and all(options is not None for options in child_options):
            possible_maxima = _composition_max_level_options(
                [options for options in child_options if options is not None]
            )
            if len(possible_maxima) == 1:
                return next(iter(possible_maxima)) + 1, "nested_structure"
    if component.mass == 1:
        return 1, "protium_base"
    if parent.atomic_level is not None and parent.atomic_level > 1:
        return parent.atomic_level - 1, "parent_context_fallback"

    # The seed gives an exact mass->level formula for the *primary* sequence,
    # not for arbitrary configurations. Use it only as an explicit fallback.
    mass = component.mass
    if mass is not None and mass > 0:
        return int(log2(mass)) + 1, "primary_mass_fallback"

    sibling_levels = [
        level for sibling in siblings
        if (level := _component_atomic_level(sibling, registry)) is not None
    ]
    return (max(sibling_levels) if sibling_levels else 1), "sibling_context_fallback"


def _component_depth(component: SemanticComponent) -> int:
    if not component.children:
        return 1
    return 1 + max(_component_depth(child) for child in component.children)


def _node_sort_key(node: SemanticHyperatom) -> tuple[Any, ...]:
    return (
        node.atomic_level if node.atomic_level is not None else 10**9,
        node.atomic_mass if node.atomic_mass is not None else 10**9,
        node.symbol or "",
        node.canonical_structure or "",
        node.canonical,
        node.id,
    )


__all__ = [
    "CanonicalHyperatomMap",
    "HyperatomMapEdge",
    "build_canonical_hyperatom_map",
]
