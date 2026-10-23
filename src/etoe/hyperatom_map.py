"""Canonical hyperatom maps with optional runtime patching of missing subatoms.

The map layer is deliberately downstream of parsing and translation.  It
consumes the existing semantic registry, uses canonical structure text for
indexing, preserves ambiguous references, and optionally supplies explicit
runtime placeholders for unresolved mass-bearing subatoms.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from math import log2
from typing import Any, Iterable

from .elements import ElementCatalog
from .hyperatom_translation import (
    HYPERATOM_KIND,
    HyperatomRegistry,
    HyperatomTranslator,
    SemanticComponent,
    SemanticHyperatom,
    TranslationDiagnostic,
    _component_atomic_level,
    _component_atomic_level_options,
    _composition_max_level_options,
    _components_structure_text,
    _infer_atomic_levels,
    _pattern_matches_structure,
)
from .hyperatomic import HyperatomConfig, primary_configuration


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
    by_mass: dict[int, tuple[str, ...]] = field(default_factory=dict)
    by_primary_mass: dict[int, tuple[str, ...]] = field(default_factory=dict)
    primary_hyperatom_ids: tuple[str, ...] = ()
    patched_hyperatoms: tuple[str, ...] = ()

    @property
    def nodes(self) -> tuple[SemanticHyperatom, ...]:
        return self.registry.definitions

    def find_by_structure(self, structure_text: str) -> tuple[SemanticHyperatom, ...]:
        """Return every definition having this canonical structure text."""
        ids = self.by_structure.get(structure_text, ())
        return tuple(self.registry.by_id[item] for item in ids if item in self.registry.by_id)

    def find_by_mass(
        self,
        mass: int | str,
        *,
        primary_only: bool = True,
    ) -> tuple[SemanticHyperatom, ...]:
        """Find hyperatoms by atomic mass, accepting either an integer or decimal text.

        By default, only primary hyperatoms are returned. Pass
        ``primary_only=False`` to search every definition with this mass.
        """
        if isinstance(mass, bool):
            raise TypeError("mass must be a positive integer or decimal string")
        if isinstance(mass, int):
            mass_value = mass
        elif isinstance(mass, str) and mass.strip().isdecimal():
            mass_value = int(mass.strip())
        else:
            raise ValueError(f"invalid atomic mass {mass!r}; expected a positive integer or decimal string")
        if mass_value < 1:
            raise ValueError(f"invalid atomic mass {mass!r}; expected a positive integer or decimal string")
        if not isinstance(primary_only, bool):
            raise TypeError("primary_only must be a bool")
        index = self.by_primary_mass if primary_only else self.by_mass
        ids = index.get(mass_value, ())
        return tuple(self.registry.by_id[item] for item in ids if item in self.registry.by_id)

    def statistics(self) -> dict[str, Any]:
        counts: dict[str, int] = defaultdict(int)
        for edge in self.edges:
            counts[edge.resolution] += 1
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "structural_keys": len(self.by_structure),
            "primary_hyperatoms": len(self.primary_hyperatom_ids),
            "edges_by_resolution": dict(sorted(counts.items())),
            "auto_patch_missing": self.auto_patch_missing,
            "patched_hyperatoms": len(self.patched_hyperatoms),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "etoe.canonical-hyperatom-map.v1",
            "canonicalization": {
                "primary_candidate_rule": "mass-only references and references that describe the primary configuration resolve to primary hyperatoms by mass; references that describe non-primary configurations resolve to non-primary hyperatoms by canonical_structure",
                "unordered_separator": "'",
                "mass_order": "descending; unknown masses last; structural text breaks ties",
                "structural_key": "parenthesized, recursively normalized subatom structure; element symbols omitted for mass-qualified components",
            },
            "statistics": self.statistics(),
            "patched_hyperatoms": list(self.patched_hyperatoms),
            "primary_hyperatom_ids": list(self.primary_hyperatom_ids),
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "by_mass": {str(key): list(value) for key, value in sorted(self.by_mass.items())},
            "by_primary_mass": {str(key): list(value) for key, value in sorted(self.by_primary_mass.items())},
            "by_structure": {key: list(value) for key, value in sorted(self.by_structure.items())},
            "element_catalog": self.registry.element_catalog.to_dict()
            if self.registry.element_catalog is not None else None,
        }


def build_canonical_hyperatom_map(
    registry: HyperatomRegistry,
    *,
    auto_patch_missing: bool = False,
) -> CanonicalHyperatomMap:
    """Build a hyperatom map with unified primary/non-primary linking.

    References without an explicit structure resolve to primary hyperatoms by
    atomic mass. A reference whose explicit structure matches the primary
    configuration for its mass also resolves to the primary candidate by mass.
    References describing a non-primary configuration resolve against
    non-primary definitions using their canonical structure and mass.

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
    _resolve_unified_references(registry)

    patched: list[str] = [
        definition.id for definition in registry.definitions
        if definition.source_path.startswith("<runtime:")
    ]
    if auto_patch_missing:
        patched.extend(_patch_missing_components(registry))
        patched = sorted(set(patched))
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
    by_mass_work: dict[int, list[str]] = defaultdict(list)
    by_primary_mass_work: dict[int, list[str]] = defaultdict(list)
    primary_ids: list[str] = []
    for definition in registry.definitions:
        if definition.atomic_mass is not None:
            by_mass_work[definition.atomic_mass].append(definition.id)
        if _is_primary_hyperatom(definition):
            assert definition.atomic_mass is not None
            by_primary_mass_work[definition.atomic_mass].append(definition.id)
            primary_ids.append(definition.id)
    by_mass = {
        mass: tuple(sorted(ids, key=lambda item: _node_sort_key(registry.by_id[item])))
        for mass, ids in by_mass_work.items()
    }
    by_primary_mass = {
        mass: tuple(sorted(ids, key=lambda item: _node_sort_key(registry.by_id[item])))
        for mass, ids in by_primary_mass_work.items()
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
        by_mass=by_mass,
        by_primary_mass=by_primary_mass,
        primary_hyperatom_ids=tuple(sorted(primary_ids, key=lambda item: _node_sort_key(registry.by_id[item]))),
        patched_hyperatoms=tuple(sorted(patched)),
    )



def _has_runtime_patch(component: SemanticComponent, registry: HyperatomRegistry) -> bool:
    """Whether a component already points to a persistent in-memory placeholder."""
    return component.resolution == "patched" and any(
        candidate_id in registry.by_id
        and registry.by_id[candidate_id].source_path.startswith("<runtime:")
        for candidate_id in component.candidate_ids
    )


def _is_primary_hyperatom(definition: SemanticHyperatom) -> bool:
    """Classify a definition using the exact primary-sequence rule in EToE.md.

    A definition is primary iff its canonical structural configuration equals
    the primary sequence configuration for the same atomic mass. The base
    mass-one hyperatom is primary without an explicit composition. This
    structural comparison classifies nodes; the unified resolver uses mass
    lookups for primary references and canonical structures for non-primary ones.
    """
    if (
        definition.kind != HYPERATOM_KIND
        or definition.atomic_mass is None
        or definition.source_path.startswith("<runtime:")
    ):
        return False
    mass = definition.atomic_mass
    if mass == 1:
        return not definition.components
    structure_text = definition.canonical_structure
    if structure_text is None:
        return False
    try:
        actual = HyperatomConfig.from_structure(structure_text)
        expected = primary_configuration(mass)
    except (TypeError, ValueError):
        return False
    return actual.key == expected.key


def _resolve_unified_references(registry: HyperatomRegistry) -> None:
    """Resolve component links by mass for primary, structure for non-primary.

    The intended reference class is derived from the reference itself:
    a mass-only token denotes the primary candidate for that mass; a nested
    structure equal to the primary configuration denotes the same primary
    candidate. A non-primary nested structure is matched against non-primary
    definitions using canonical structural text, with the translator's
    recursive partial-pattern semantics retained.
    """
    primary_lists: dict[int, list[SemanticHyperatom]] = defaultdict(list)
    non_primary_by_mass: dict[int, list[SemanticHyperatom]] = defaultdict(list)
    for definition in registry.definitions:
        if definition.atomic_mass is None or definition.kind != HYPERATOM_KIND:
            continue
        if _is_primary_hyperatom(definition):
            primary_lists[definition.atomic_mass].append(definition)
        elif not definition.source_path.startswith("<runtime:"):
            non_primary_by_mass[definition.atomic_mass].append(definition)

    primary_by_mass = {
        mass: tuple(sorted(nodes, key=_node_sort_key))
        for mass, nodes in primary_lists.items()
    }
    non_primary_by_mass_sorted = {
        mass: tuple(sorted(nodes, key=_node_sort_key))
        for mass, nodes in non_primary_by_mass.items()
    }

    for definition in registry.definitions:
        for root_component in definition.components:
            for component in root_component.walk():
                if _has_runtime_patch(component, registry):
                    continue
                if component.reference_kind in {"mass", "group"} and component.mass is not None:
                    if _component_requests_primary_by_mass(component):
                        candidates = primary_by_mass.get(component.mass, ())
                    else:
                        candidates = _match_non_primary_structure(
                            component,
                            non_primary_by_mass_sorted.get(component.mass, ()),
                        )
                    _set_component_candidates(component, candidates)
                elif component.reference_kind == "explicit_object" and component.mass is not None:
                    # An explicit symbol remains a constraint. Its structure
                    # selects the primary-by-mass or non-primary-by-structure
                    # branch, but never discards the symbol constraint itself.
                    symbol_candidates = tuple(
                        node for node in registry.by_symbol_mass.get(
                            (component.symbol or "", component.mass), ()
                        )
                        if node.kind == HYPERATOM_KIND
                    )
                    if _component_requests_primary_by_mass(component):
                        candidates = tuple(
                            node for node in symbol_candidates if _is_primary_hyperatom(node)
                        )
                    else:
                        candidates = _match_non_primary_structure(
                            component,
                            tuple(node for node in symbol_candidates if not _is_primary_hyperatom(node)),
                        )
                    _set_component_candidates(component, candidates)
                else:
                    # Keep existing behavior for symbol/template and primitive
                    # references; this helper only defines mass-qualified links.
                    HyperatomTranslator._resolve_component(component, registry)


def _component_requests_primary_by_mass(component: SemanticComponent) -> bool:
    """Whether this mass-bearing reference describes the primary configuration.

    A mass-only reference is intentionally a lookup key for the primary
    sequence. If structure is provided, it selects that branch only when its
    canonical structural text equals the primary configuration for the mass.
    """
    if not component.children:
        # An explicitly empty structure is distinguishable from a bare mass.
        if not component.canonical.rstrip().endswith("()"):
            return True
        return component.mass == 1 and _is_primary_reference_structure(component)
    return _is_primary_reference_structure(component)


def _is_primary_reference_structure(component: SemanticComponent) -> bool:
    if component.mass is None or not component.children:
        return False
    try:
        expected = primary_configuration(component.mass)
    except (TypeError, ValueError):
        return False
    # A mass-one primary is a primitive reference, not a composed structure.
    expected_text = f"({expected.canonical})" if isinstance(expected, HyperatomConfig) else None
    return expected_text is not None and _components_structure_text(component.children) == expected_text


def _match_non_primary_structure(
    component: SemanticComponent,
    candidates: Iterable[SemanticHyperatom],
) -> tuple[SemanticHyperatom, ...]:
    """Match a non-primary reference's explicit structure against candidates."""
    values = tuple(candidates)
    if not component.children:
        # Empty structures do not have a child pattern; compare their canonical
        # representation directly where an explicit () was written.
        if component.canonical.rstrip().endswith("()"):
            return tuple(node for node in values if node.canonical_structure == "()")
        return ()
    expected_structure = _components_structure_text(component.children)
    exact = tuple(node for node in values if node.canonical_structure == expected_structure)
    partial = tuple(
        node for node in values
        if node.source_ast is not None and node.source_ast.structure is not None
        and _pattern_matches_structure(component.children, node.source_ast.structure)
    )
    unique = {node.id: node for node in (*exact, *partial)}
    return tuple(sorted(unique.values(), key=_node_sort_key))


def _set_component_candidates(
    component: SemanticComponent,
    candidates: Iterable[SemanticHyperatom],
) -> None:
    values = tuple(candidates)
    component.candidate_ids = tuple(sorted(node.id for node in values))
    if not values:
        component.resolution = "unresolved"
    elif len(values) == 1:
        component.resolution = "unique"
    else:
        component.resolution = "ambiguous"


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
