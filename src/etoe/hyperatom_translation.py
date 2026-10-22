"""Translate parsed chemical ÆToE notation into semantic hyperatom definitions.

The translator deliberately preserves the source AST and represents unresolved or
ambiguous component references explicitly. It does not silently choose one atom
when several definitions share the same mass.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from .ast import ChemicalGroup, ChemicalNotation, EToEFile, Notation, SourceComment, Structure
from .elements import ElementCatalog
from .parser import EToEParser


HYPERATOM_KIND = "hyperatom"
ELEMENT_TEMPLATE_KIND = "element_template"
ELEMENT_SYMBOL_KIND = "element_symbol"
MOLECULE_KIND = "molecule"
OTHER_KIND = "other"


@dataclass(frozen=True)
class TranslationDiagnostic:
    code: str
    message: str
    source_path: str | None = None
    statement_index: int | None = None
    severity: str = "warning"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "source_path": self.source_path,
            "statement_index": self.statement_index,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class SourceAnnotation:
    """Comment metadata retained from an `.etoe` source file."""

    source_path: str
    text: str
    kind: str
    start: int
    end: int
    line_number: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "text": self.text,
            "kind": self.kind,
            "start": self.start,
            "end": self.end,
            "line_number": self.line_number,
        }


@dataclass
class SemanticComponent:
    """One direct or nested component in a hyperatom's written structure."""

    index: int
    separator: str | None
    canonical: str
    reference_kind: str
    symbol: str | None = None
    subsort: str | None = None
    mass: int | None = None
    mass_origin: str | None = None
    children: tuple["SemanticComponent", ...] = ()
    candidate_ids: tuple[str, ...] = ()
    resolution: str = "not_applicable"

    @property
    def is_structural(self) -> bool:
        return bool(self.children)

    @property
    def canonical_structure(self) -> str:
        """Return this component's deterministic structural token.

        Element symbols are deliberately omitted when an explicit mass is
        present: ``Be-8-(4'4)`` and ``X4-8-(4'4)`` describe the same structural
        configuration for map/index purposes.  The original ``canonical``
        field remains lossless and is never rewritten.
        """
        return _component_text(self)

    def walk(self) -> Iterator["SemanticComponent"]:
        yield self
        for child in self.children:
            yield from child.walk()

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "separator": self.separator,
            "canonical": self.canonical,
            "reference_kind": self.reference_kind,
            "symbol": self.symbol,
            "subsort": self.subsort,
            "mass": self.mass,
            "mass_origin": self.mass_origin,
            "children": [child.to_dict() for child in self.children],
            "candidate_ids": list(self.candidate_ids),
            "resolution": self.resolution,
            "canonical_structure": self.canonical_structure,
        }


@dataclass
class SemanticHyperatom:
    """Semantic record for one top-level chemical statement in a `.etoe` file.

    `atomic_mass` and `primary_mass` mirror the parser's field names verbatim;
    the translator does not reinterpret the second numeric suffix.
    """

    id: str
    kind: str
    canonical: str
    source_path: str
    statement_index: int
    symbol: str | None = None
    subsort: str | None = None
    atomic_mass: int | None = None
    primary_mass: int | None = None
    source_comments: tuple[str, ...] = ()
    matter_level: int | None = None
    syntax_depth: int = 0
    components: tuple[SemanticComponent, ...] = ()
    mass_sum: int | None = None
    mass_balance: str = "not_applicable"
    atomic_level: int | None = None
    atomic_level_source: str | None = None
    structure_text_override: str | None = field(default=None, repr=False, compare=False)
    source_ast: ChemicalNotation | None = field(default=None, repr=False, compare=False)

    @property
    def designation(self) -> str:
        """Compact display label; `canonical` remains the lossless source form."""
        if self.symbol is None:
            return self.canonical
        out = self.symbol
        if self.subsort is not None:
            out += f":{self.subsort}"
        if self.atomic_mass is not None:
            out += f"-{self.atomic_mass}"
        if self.primary_mass is not None:
            out += f"-{self.primary_mass}"
        return out

    @property
    def is_composite(self) -> bool:
        return bool(self.components)

    @property
    def canonical_structure(self) -> str | None:
        """Canonical text key for the hyperatom's own structure.

        The outer parentheses are part of this representation.  A definition
        without an explicit composition has no structure key (``None``),
        rather than being conflated with an explicitly empty structure ``()``.
        """
        if self.structure_text_override is not None:
            return self.structure_text_override
        if self.source_ast is not None and self.source_ast.structure is None and not self.components:
            return None
        if self.source_ast is not None and self.source_ast.structure is not None and not self.components:
            return "()"
        if not self.components:
            return None
        return _components_structure_text(self.components)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "designation": self.designation,
            "canonical": self.canonical,
            "source": {
                "path": self.source_path,
                "statement_index": self.statement_index,
            },
            "symbol": self.symbol,
            "subsort": self.subsort,
            "atomic_mass": self.atomic_mass,
            "primary_mass": self.primary_mass,
            "source_comments": list(self.source_comments),
            "matter_level": self.matter_level,
            "syntax_depth": self.syntax_depth,
            "components": [component.to_dict() for component in self.components],
            "canonical_structure": self.canonical_structure,
            "atomic_level": self.atomic_level,
            "atomic_level_source": self.atomic_level_source,
            "mass_sum": self.mass_sum,
            "mass_balance": self.mass_balance,
        }


@dataclass
class HyperatomRegistry:
    """A semantic index over translated `.etoe` element files."""

    root: str
    source_file_count: int
    statement_count: int
    definitions: tuple[SemanticHyperatom, ...]
    diagnostics: tuple[TranslationDiagnostic, ...] = ()
    source_annotations: tuple[SourceAnnotation, ...] = ()
    element_catalog: ElementCatalog | None = field(default=None, repr=False, compare=False)
    by_id: dict[str, SemanticHyperatom] = field(init=False, repr=False)
    by_symbol: dict[str, tuple[SemanticHyperatom, ...]] = field(init=False, repr=False)
    by_mass: dict[int, tuple[SemanticHyperatom, ...]] = field(init=False, repr=False)
    by_symbol_mass: dict[tuple[str, int], tuple[SemanticHyperatom, ...]] = field(init=False, repr=False)
    by_structure: dict[str, tuple[SemanticHyperatom, ...]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._reindex()

    def _reindex(self) -> None:
        """Rebuild all indexes after adding runtime-generated definitions."""
        self.by_id = {obj.id: obj for obj in self.definitions}
        by_symbol: dict[str, list[SemanticHyperatom]] = defaultdict(list)
        by_mass: dict[int, list[SemanticHyperatom]] = defaultdict(list)
        by_symbol_mass: dict[tuple[str, int], list[SemanticHyperatom]] = defaultdict(list)
        by_structure: dict[str, list[SemanticHyperatom]] = defaultdict(list)
        for obj in self.definitions:
            if obj.symbol:
                by_symbol[obj.symbol].append(obj)
                if obj.atomic_mass is not None:
                    by_symbol_mass[(obj.symbol, obj.atomic_mass)].append(obj)
            if obj.atomic_mass is not None:
                by_mass[obj.atomic_mass].append(obj)
            if obj.canonical_structure is not None:
                by_structure[obj.canonical_structure].append(obj)
        self.by_symbol = {key: tuple(value) for key, value in by_symbol.items()}
        self.by_mass = {key: tuple(value) for key, value in by_mass.items()}
        self.by_symbol_mass = {key: tuple(value) for key, value in by_symbol_mass.items()}
        self.by_structure = {key: tuple(value) for key, value in by_structure.items()}

    def add_definition(self, definition: SemanticHyperatom) -> None:
        """Add a generated hyperatom and keep the registry indexes coherent."""
        if definition.id in self.by_id:
            raise ValueError(f"Duplicate semantic hyperatom id {definition.id!r}")
        self.definitions = (*self.definitions, definition)
        self._reindex()

    def get(self, object_id: str) -> SemanticHyperatom | None:
        return self.by_id.get(object_id)

    def iter_components(self) -> Iterator[tuple[SemanticHyperatom, SemanticComponent]]:
        for definition in self.definitions:
            for component in definition.components:
                yield definition, component
                for nested in component.walk():
                    if nested is not component:
                        yield definition, nested

    def statistics(self) -> dict[str, Any]:
        kind_counts = Counter(obj.kind for obj in self.definitions)
        mass_counts = Counter(c.resolution for _, c in self.iter_components() if c.reference_kind != "group")
        balances = Counter(obj.mass_balance for obj in self.definitions if obj.mass_balance != "not_applicable")
        return {
            "root": self.root,
            "source_files": self.source_file_count,
            "source_statements": self.statement_count,
            "source_comments": len(self.source_annotations),
            "semantic_definitions": len(self.definitions),
            "definitions_by_kind": dict(sorted(kind_counts.items())),
            "definitions_by_matter_level": dict(sorted(Counter(str(obj.matter_level) for obj in self.definitions).items())),
            "max_syntax_depth": max((obj.syntax_depth for obj in self.definitions), default=0),
            "definitions_by_atomic_level": dict(sorted(Counter(
                str(obj.atomic_level) for obj in self.definitions if obj.atomic_level is not None
            ).items())),
            "component_references_by_resolution": dict(sorted(mass_counts.items())),
            "mass_balance": dict(sorted(balances.items())),
            "diagnostics_by_code": dict(sorted(Counter(d.code for d in self.diagnostics).items())),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "etoe.semantic-hyperatoms.v1",
            "root": self.root,
            "statistics": self.statistics(),
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "source_annotations": [annotation.to_dict() for annotation in self.source_annotations],
            "element_catalog": self.element_catalog.to_dict() if self.element_catalog is not None else None,
            "definitions": [definition.to_dict() for definition in self.definitions],
        }


class HyperatomTranslationError(ValueError):
    """Raised when an element data directory cannot be translated."""


class HyperatomTranslator:
    """Parse ÆToE element files and resolve component definitions into an index."""

    def __init__(
        self,
        parser: EToEParser | None = None,
        element_catalog: ElementCatalog | None = None,
    ) -> None:
        self.parser = parser or EToEParser()
        # When omitted, a fresh catalog is created for each translated root so
        # filesystem changes and local project metadata are picked up naturally.
        self.element_catalog = element_catalog

    def translate_directory(self, root: str | Path) -> HyperatomRegistry:
        root_argument = Path(root).expanduser()
        root_path = root_argument.resolve()
        if not root_path.exists():
            raise FileNotFoundError(root_path)
        if not root_path.is_dir():
            raise NotADirectoryError(root_path)
        files = sorted(root_path.rglob("*.etoe"))
        if not files:
            raise HyperatomTranslationError(f"No .etoe files found under {root_path}")
        element_catalog = self.element_catalog or ElementCatalog(root_path)

        diagnostics: list[TranslationDiagnostic] = []
        definitions: list[SemanticHyperatom] = []
        source_annotations: list[SourceAnnotation] = []
        statement_count = 0
        duplicate_occurrences: Counter[tuple[str, str]] = Counter()

        for file_path in files:
            relative_path = file_path.relative_to(root_path).as_posix()
            try:
                source_text = file_path.read_text(encoding="utf-8")
                document: EToEFile = self.parser.parse_file(source_text, preserve_comments=True)
            except Exception as exc:
                raise HyperatomTranslationError(f"Could not parse {file_path}: {exc}") from exc
            statement_count += len(document.statements)
            statement_end_offsets = _top_level_statement_end_offsets(source_text)
            line_starts = _line_start_offsets(source_text)
            comment_text_by_statement: dict[int, list[str]] = defaultdict(list)
            for comment in document.comments:
                line_number = bisect_right(line_starts, comment.start)
                source_annotations.append(SourceAnnotation(
                    source_path=relative_path,
                    text=comment.text,
                    kind=comment.kind,
                    start=comment.start,
                    end=comment.end,
                    line_number=line_number,
                ))
                preceding_statement = bisect_right(statement_end_offsets, comment.start) - 1
                if preceding_statement >= 0 and preceding_statement < len(document.statements):
                    end_offset = statement_end_offsets[preceding_statement] - 1
                    if bisect_right(line_starts, end_offset) == line_number:
                        comment_text_by_statement[preceding_statement].append(comment.text)
            if len(statement_end_offsets) != len(document.statements):
                diagnostics.append(TranslationDiagnostic(
                    "statement-offset-mismatch",
                    f"The source scanner found {len(statement_end_offsets)} top-level terminator(s) for "
                    f"{len(document.statements)} parsed statement(s); statement-level comment association may be incomplete.",
                    relative_path,
                ))
            folder_symbol = file_path.parent.name
            for statement_index, statement in enumerate(document.statements):
                if not isinstance(statement, ChemicalNotation):
                    diagnostics.append(TranslationDiagnostic(
                        "unsupported-root-statement",
                        f"Statement {statement_index} is {type(statement).__name__}, not chemical notation; skipped.",
                        relative_path,
                        statement_index,
                    ))
                    continue
                canonical = statement.to_canonical()
                occurrence_key = (relative_path, canonical)
                duplicate_number = duplicate_occurrences[occurrence_key]
                duplicate_occurrences[occurrence_key] += 1
                object_id = "ha_" + sha256(
                    f"{relative_path}\0{canonical}\0{duplicate_number}".encode("utf-8")
                ).hexdigest()[:16]
                kind = _kind_for(statement, folder_symbol)
                components = _components_from_structure(statement.structure) if statement.structure else ()
                node = SemanticHyperatom(
                    id=object_id,
                    kind=kind,
                    canonical=canonical,
                    source_path=relative_path,
                    statement_index=statement_index,
                    symbol=statement.symbol,
                    subsort=statement.subsort,
                    atomic_mass=statement.atomic_mass,
                    primary_mass=statement.primary_mass,
                    source_comments=tuple(comment_text_by_statement.get(statement_index, ())),
                    matter_level=_matter_level(kind),
                    syntax_depth=_notation_depth(statement),
                    components=components,
                    source_ast=statement,
                )
                definitions.append(node)
                if statement.symbol and folder_symbol != statement.symbol:
                    diagnostics.append(TranslationDiagnostic(
                        "folder-symbol-mismatch",
                        f"Containing directory is '{folder_symbol}', notation symbol is '{statement.symbol}'.",
                        relative_path,
                        statement_index,
                    ))

        registry = HyperatomRegistry(
            # Keep the caller's root path for portable JSON exports; individual
            # source_path fields are always relative to this directory.
            root=root_argument.as_posix(),
            source_file_count=len(files),
            statement_count=statement_count,
            definitions=tuple(definitions),
            diagnostics=tuple(diagnostics),
            source_annotations=tuple(source_annotations),
            element_catalog=element_catalog,
        )
        self._resolve_references(registry)
        self._check_mass_balance(registry)
        _infer_atomic_levels(registry)
        return registry

    def _resolve_references(self, registry: HyperatomRegistry) -> None:
        diagnostics = list(registry.diagnostics)
        for definition in registry.definitions:
            for component in definition.components:
                self._resolve_component(component, registry)
                for nested in component.walk():
                    if nested is component:
                        continue
                    self._resolve_component(nested, registry)
                    if nested.resolution in {"ambiguous", "unresolved"} and nested.reference_kind not in {"group", "primitive"}:
                        diagnostics.append(_resolution_diagnostic(definition, nested))
                if component.resolution in {"ambiguous", "unresolved"} and component.reference_kind not in {"group", "primitive"}:
                    diagnostics.append(_resolution_diagnostic(definition, component))
        registry.diagnostics = tuple(diagnostics)

    @staticmethod
    def _resolve_component(component: SemanticComponent, registry: HyperatomRegistry) -> None:
        candidates: Sequence[SemanticHyperatom] = ()
        if component.reference_kind in {"mass", "group"} and component.mass is not None:
            candidates = registry.by_mass.get(component.mass, ())
            if component.children:
                expected_structure = _components_structure_text(component.children)
                # Fast exact match against canonical structure text. Fall back
                # to recursive partial-pattern matching because omitted
                # descendants intentionally act as wildcards in ÆToE.
                exact = tuple(obj for obj in candidates if obj.canonical_structure == expected_structure)
                partial = tuple(
                    obj for obj in candidates
                    if obj.source_ast is not None and obj.source_ast.structure is not None
                    and _pattern_matches_structure(component.children, obj.source_ast.structure)
                )
                candidates = tuple({obj.id: obj for obj in (*exact, *partial)}.values())
        elif component.reference_kind == "symbol" and component.symbol:
            candidates = tuple(
                obj for obj in registry.by_symbol.get(component.symbol, ())
                if obj.atomic_mass is None and obj.source_ast is not None and obj.source_ast.structure is not None
            )
            if component.subsort is not None:
                candidates = tuple(obj for obj in candidates if obj.subsort == component.subsort)
            if component.children:
                expected_structure = _components_structure_text(component.children)
                exact = tuple(obj for obj in candidates if obj.canonical_structure == expected_structure)
                partial = tuple(
                    obj for obj in candidates if obj.source_ast is not None and obj.source_ast.structure is not None
                    and _pattern_matches_structure(component.children, obj.source_ast.structure)
                )
                candidates = tuple({obj.id: obj for obj in (*exact, *partial)}.values())
            if not candidates and not component.children:
                candidates = tuple(
                    obj for obj in registry.by_symbol.get(component.symbol, ())
                    if obj.atomic_mass is None and obj.kind == ELEMENT_SYMBOL_KIND
                    and (component.subsort is None or obj.subsort == component.subsort)
                )
        elif component.reference_kind == "explicit_object" and component.symbol and component.mass is not None:
            candidates = registry.by_symbol_mass.get((component.symbol, component.mass), ())
            if component.children:
                expected_structure = _components_structure_text(component.children)
                exact = tuple(obj for obj in candidates if obj.canonical_structure == expected_structure)
                partial = tuple(
                    obj for obj in candidates if obj.source_ast is not None and obj.source_ast.structure is not None
                    and _pattern_matches_structure(component.children, obj.source_ast.structure)
                )
                candidates = tuple({obj.id: obj for obj in (*exact, *partial)}.values())
        # Built-in primitives are retained as syntax but are not mapped to a fabricated atom.
        component.candidate_ids = tuple(sorted(obj.id for obj in candidates))
        if not candidates:
            component.resolution = "unresolved"
        elif len(candidates) == 1:
            component.resolution = "unique"
        else:
            component.resolution = "ambiguous"

    @staticmethod
    def _check_mass_balance(registry: HyperatomRegistry) -> None:
        diagnostics = list(registry.diagnostics)
        for definition in registry.definitions:
            if definition.atomic_mass is None or not definition.components:
                continue
            masses = [component.mass for component in definition.components]
            if any(value is None for value in masses):
                definition.mass_sum = None
                definition.mass_balance = "unknown"
                continue
            definition.mass_sum = sum(value for value in masses if value is not None)
            if definition.mass_sum == definition.atomic_mass:
                definition.mass_balance = "consistent"
            else:
                definition.mass_balance = "mismatch"
                diagnostics.append(TranslationDiagnostic(
                    "mass-balance-mismatch",
                    f"{definition.canonical}: direct component mass sum is {definition.mass_sum}, "
                    f"but the declared mass is {definition.atomic_mass}.",
                    definition.source_path,
                    definition.statement_index,
                ))
        registry.diagnostics = tuple(diagnostics)


def _line_start_offsets(text: str) -> list[int]:
    return [0] + [index + 1 for index, char in enumerate(text) if char == "\n"]


def _top_level_statement_end_offsets(text: str) -> list[int]:
    """Find top-level semicolon terminators while respecting comments/strings."""
    offsets: list[int] = []
    index = 0
    depth = 0
    in_string = False
    escaped = False
    line_comment = False
    block_comment = False
    while index < len(text):
        char = text[index]
        next_two = text[index:index + 2]
        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if next_two == "*/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if next_two == "/*":
            block_comment = True
            index += 2
            continue
        if char == "#" or next_two == "//":
            line_comment = True
            index += 1 if char == "#" else 2
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth = max(0, depth - 1)
        elif char == ";" and depth == 0:
            offsets.append(index + 1)
        index += 1
    return offsets


def _matter_level(kind: str) -> int | None:
    # Files under data/atom/element describe the chemical/atom stair (E5).
    # Unknown-symbol molecule notations remain E6 instead of being recast.
    if kind in {HYPERATOM_KIND, ELEMENT_TEMPLATE_KIND, ELEMENT_SYMBOL_KIND}:
        return 5
    if kind == MOLECULE_KIND:
        return 6
    return None


def _notation_depth(node: Notation) -> int:
    """Return written nesting depth, not a claimed physical hierarchy level."""
    if isinstance(node, ChemicalGroup):
        children = [_notation_depth(child) for child in node.structure.objects]
        return 1 + max(children, default=0)
    if isinstance(node, ChemicalNotation) and node.structure is not None:
        children = [_notation_depth(child) for child in node.structure.objects]
        return 1 + max(children, default=0)
    return 0


def _kind_for(node: ChemicalNotation, folder_symbol: str | None = None) -> str:
    # Legacy ÆToE data contains project-specific element symbols (for example
    # `Nm` and `X`) that the generic grammar correctly classifies as identifiers
    # rather than IUPAC symbols. In the element-data tree, the containing folder
    # is the authoritative hint that such a symbol is an element record.
    belongs_to_element_file = bool(node.symbol and folder_symbol and node.symbol == folder_symbol)
    if node.atomic_mass is not None:
        return HYPERATOM_KIND if node.kind == "element" or belongs_to_element_file else MOLECULE_KIND
    if node.structure is not None:
        return ELEMENT_TEMPLATE_KIND if node.kind == "element" or belongs_to_element_file else MOLECULE_KIND
    if node.kind == "element" or belongs_to_element_file:
        return ELEMENT_SYMBOL_KIND
    return MOLECULE_KIND if node.kind == "molecule" else OTHER_KIND


def _component_text(component: SemanticComponent) -> str:
    """Serialize a component as a normalized, structure-oriented text token."""
    nested = _components_structure_text(component.children) if component.children else None
    if component.reference_kind == "group":
        return nested or "()"
    if component.reference_kind == "mass":
        mass_text = str(component.mass) if component.mass is not None else component.canonical
        return f"{mass_text}-{nested}" if nested else mass_text
    if component.reference_kind == "explicit_object":
        # A mass-qualified object is structurally comparable across element
        # symbols. The symbol is kept in the lossless source field instead.
        base = str(component.mass) if component.mass is not None else (component.symbol or component.canonical)
        if component.mass is None and component.subsort is not None:
            base += f":{component.subsort}"
        return f"{base}-{nested}" if nested else base
    if component.reference_kind == "symbol":
        base = component.symbol or component.canonical
        if component.subsort is not None:
            base += f":{component.subsort}"
        return f"{base}-{nested}" if nested else base
    if component.reference_kind == "primitive":
        base = str(component.mass) if component.mass is not None else component.canonical
        return f"{base}-{nested}" if nested else base
    return f"{component.canonical}-{nested}" if nested else component.canonical


def _components_structure_text(components: Sequence[SemanticComponent]) -> str:
    """Textual structural key with canonical sibling order and multiplicity."""
    if not components:
        return "()"
    pieces: list[str] = []
    for index, component in enumerate(components):
        if index:
            pieces.append(component.separator or "'")
        pieces.append(_component_text(component))
    return "(" + "".join(pieces) + ")"


def _component_mass_sort_key(component: SemanticComponent) -> tuple[Any, ...]:
    mass = component.mass
    return (
        mass is None,
        -(mass or 0),
        component.canonical_structure,
        component.canonical,
    )


def _components_from_structure(structure: Structure | None) -> tuple[SemanticComponent, ...]:
    if structure is None:
        return ()
    components: list[SemanticComponent] = []
    for index, notation in enumerate(structure.objects):
        separator = structure.separators[index - 1] if index > 0 and index - 1 < len(structure.separators) else None
        components.append(_component_from_notation(notation, index, separator))

    # Apostrophe-joined siblings are an unordered multiset in ÆToE. Canonical
    # storage sorts those siblings by descending known mass, while leaving
    # mixed/other separators order-sensitive until their semantics are defined.
    if len(components) <= 1 or all(separator == "'" for separator in structure.separators):
        components.sort(key=_component_mass_sort_key)
        for index, component in enumerate(components):
            component.index = index
            component.separator = None if index == 0 else "'"
    return tuple(components)


def _component_from_notation(node: Notation, index: int, separator: str | None) -> SemanticComponent:
    if isinstance(node, ChemicalGroup):
        children = _components_from_structure(node.structure)
        child_masses = [child.mass for child in children]
        inferred_mass = sum(child_masses) if child_masses and all(m is not None for m in child_masses) else None
        return SemanticComponent(
            index=index,
            separator=separator,
            canonical=node.to_canonical(),
            reference_kind="group",
            mass=inferred_mass,
            mass_origin="inferred_sum" if inferred_mass is not None else None,
            children=children,
        )
    if isinstance(node, ChemicalNotation):
        children = _components_from_structure(node.structure)
        if node.kind == "mass":
            return SemanticComponent(index, separator, node.to_canonical(), "mass", mass=node.atomic_mass,
                                     mass_origin="explicit", children=children)
        if node.kind in {"protium_core", "proton", "neutron"}:
            return SemanticComponent(index, separator, node.to_canonical(), "primitive", mass=node.atomic_mass,
                                     mass_origin="explicit" if node.atomic_mass is not None else None, children=children)
        if node.atomic_mass is not None and node.symbol:
            return SemanticComponent(index, separator, node.to_canonical(), "explicit_object", node.symbol,
                                     node.subsort, node.atomic_mass, "explicit", children)
        return SemanticComponent(index, separator, node.to_canonical(), "symbol", node.symbol,
                                 node.subsort, node.atomic_mass, "explicit" if node.atomic_mass is not None else None, children)
    return SemanticComponent(index, separator, node.to_canonical(), "other")


def _structure_signature_from_ast(structure: Structure) -> tuple[Any, ...]:
    result = []
    for index, child in enumerate(structure.objects):
        separator = structure.separators[index - 1] if index > 0 and index - 1 < len(structure.separators) else None
        result.append((separator, _notation_signature(child)))
    return tuple(result)


def _notation_signature(node: Notation) -> tuple[Any, ...]:
    if isinstance(node, ChemicalGroup):
        return ("group", _structure_signature_from_ast(node.structure))
    if isinstance(node, ChemicalNotation):
        if node.kind == "mass":
            return ("mass", node.atomic_mass, _structure_signature_from_ast(node.structure) if node.structure else ())
        if node.atomic_mass is not None:
            return ("object", node.symbol, node.subsort, node.atomic_mass,
                    _structure_signature_from_ast(node.structure) if node.structure else ())
        return (node.kind, node.symbol, node.subsort,
                _structure_signature_from_ast(node.structure) if node.structure else ())
    return (type(node).__name__, node.to_canonical())


def _component_structure_signature(component: SemanticComponent) -> tuple[Any, ...]:
    return tuple((child.separator, _component_signature(child)) for child in component.children)


def _component_signature(component: SemanticComponent) -> tuple[Any, ...]:
    if component.reference_kind == "group":
        return ("group", _component_structure_signature(component))
    if component.reference_kind == "mass":
        return ("mass", component.mass, _component_structure_signature(component) if component.children else ())
    if component.reference_kind == "explicit_object":
        return ("object", component.symbol, component.subsort, component.mass,
                _component_structure_signature(component) if component.children else ())
    return (component.reference_kind, component.symbol, component.subsort,
            _component_structure_signature(component) if component.children else ())


def _pattern_matches_structure(pattern: tuple[SemanticComponent, ...], actual: Structure) -> bool:
    """Match an explicit structural pattern without inventing missing detail.

    Omitted descendants act as wildcards: `96-(48'48)` specifies the direct
    composition of a mass-96 object, but does not claim each mass-48 child is
    elementary. The seed also defines apostrophe-joined direct subobjects as an
    unordered multiset, so those siblings are matched independent of order
    while retaining multiplicity. Other/mixed separators remain order-sensitive
    until their semantics are specified.
    """
    if len(pattern) != len(actual.objects):
        return False
    pattern_is_apostrophe_multiset = all(
        item.separator == "'" for item in pattern[1:]
    )
    actual_is_apostrophe_multiset = all(separator == "'" for separator in actual.separators)
    if pattern_is_apostrophe_multiset and actual_is_apostrophe_multiset:
        return _match_unordered_notations(pattern, actual.objects)

    for index, (wanted, found) in enumerate(zip(pattern, actual.objects)):
        actual_separator = actual.separators[index - 1] if index > 0 and index - 1 < len(actual.separators) else None
        if wanted.separator != actual_separator or not _pattern_matches_notation(wanted, found):
            return False
    return True


def _match_unordered_notations(pattern: tuple[SemanticComponent, ...], actual: Sequence[Notation]) -> bool:
    """Find a one-to-one matching, so duplicate equal subobjects keep multiplicity."""
    if len(pattern) != len(actual):
        return False

    def match_next(pattern_index: int, remaining_indexes: tuple[int, ...]) -> bool:
        if pattern_index == len(pattern):
            return not remaining_indexes
        wanted = pattern[pattern_index]
        for actual_index in remaining_indexes:
            if not _pattern_matches_notation(wanted, actual[actual_index]):
                continue
            rest = tuple(index for index in remaining_indexes if index != actual_index)
            if match_next(pattern_index + 1, rest):
                return True
        return False

    return match_next(0, tuple(range(len(actual))))


def _pattern_matches_notation(pattern: SemanticComponent, actual: Notation) -> bool:
    if pattern.reference_kind == "group":
        if isinstance(actual, ChemicalGroup):
            return _pattern_matches_structure(pattern.children, actual.structure)
        if isinstance(actual, ChemicalNotation) and actual.structure is not None:
            return _pattern_matches_structure(pattern.children, actual.structure)
        return False
    if not isinstance(actual, ChemicalNotation):
        return False
    if pattern.reference_kind == "mass":
        actual_mass = actual.atomic_mass
        if actual_mass != pattern.mass:
            return False
        if pattern.children:
            return actual.structure is not None and _pattern_matches_structure(pattern.children, actual.structure)
        return True
    if pattern.reference_kind == "explicit_object":
        if actual.symbol != pattern.symbol or actual.atomic_mass != pattern.mass:
            return False
        if pattern.subsort is not None and actual.subsort != pattern.subsort:
            return False
        if pattern.children:
            return actual.structure is not None and _pattern_matches_structure(pattern.children, actual.structure)
        return True
    if pattern.reference_kind == "symbol":
        if actual.symbol != pattern.symbol:
            return False
        if pattern.subsort is not None and actual.subsort != pattern.subsort:
            return False
        if pattern.children:
            return actual.structure is not None and _pattern_matches_structure(pattern.children, actual.structure)
        return True
    if pattern.reference_kind == "primitive":
        return actual.to_canonical() == pattern.canonical
    return actual.to_canonical() == pattern.canonical


def _resolution_diagnostic(definition: SemanticHyperatom, component: SemanticComponent) -> TranslationDiagnostic:
    if component.resolution == "ambiguous":
        message = (f"Component '{component.canonical}' in {definition.canonical} has "
                   f"{len(component.candidate_ids)} candidate definitions; ambiguity preserved.")
        code = "ambiguous-component-reference"
    else:
        message = f"Component '{component.canonical}' in {definition.canonical} has no matching definition."
        code = "unresolved-component-reference"
    return TranslationDiagnostic(code, message, definition.source_path, definition.statement_index)


def _component_atomic_level(component: SemanticComponent, registry: HyperatomRegistry) -> int | None:
    """Infer a component's atom level from explicit structure or resolved nodes."""
    options = _component_atomic_level_options(component, registry)
    return next(iter(options)) if options is not None and len(options) == 1 else None


def _component_atomic_level_options(
    component: SemanticComponent,
    registry: HyperatomRegistry,
) -> set[int] | None:
    """Return possible levels without collapsing known ambiguity prematurely."""
    candidates = [registry.by_id[candidate_id] for candidate_id in component.candidate_ids
                  if candidate_id in registry.by_id]
    if candidates and len(candidates) == len(component.candidate_ids):
        levels = [candidate.atomic_level for candidate in candidates]
        if all(level is not None for level in levels):
            return {level for level in levels if level is not None}
    if component.children:
        child_options = [_component_atomic_level_options(child, registry) for child in component.children]
        if child_options and all(options is not None for options in child_options):
            maxima = _composition_max_level_options([options for options in child_options if options is not None])
            return {level + 1 for level in maxima}
    if component.mass == 1:
        # Mass-1 atoms are the base objects in the primary atom hierarchy.
        return {1}
    return None


def _composition_max_level_options(level_options: Sequence[set[int]]) -> set[int]:
    """Possible values of max(child levels), without Cartesian-product growth."""
    if not level_options:
        return set()
    candidates = set().union(*level_options)
    return {
        level for level in candidates
        if all(min(options) <= level for options in level_options)
        and any(level in options for options in level_options)
    }


def _infer_atomic_levels(registry: HyperatomRegistry) -> None:
    """Infer atom levels using the seed's L(comp)=1+max(L(subatom)) rule.

    Only levels entailed by the available composition are assigned.  A
    mass-only component that has no definition does not magically acquire a
    structural level here; the opt-in runtime patcher records its fallback
    inference separately.
    """
    for definition in registry.definitions:
        if definition.kind == HYPERATOM_KIND and definition.atomic_mass == 1 and not definition.components:
            definition.atomic_level = 1
            definition.atomic_level_source = "protium_base"

    # Since definitions are not guaranteed to be listed by level or mass,
    # iterate to a fixed point. In ordinary cases this converges in a handful
    # of passes, while the bound also protects against malformed cycles.
    for _ in range(len(registry.definitions) + 1):
        changed = False
        for definition in registry.definitions:
            if definition.atomic_level is not None or not definition.components:
                continue
            component_options = [
                _component_atomic_level_options(component, registry) for component in definition.components
            ]
            if component_options and all(options is not None for options in component_options):
                possible_maxima = _composition_max_level_options(
                    [options for options in component_options if options is not None]
                )
                if len(possible_maxima) == 1:
                    definition.atomic_level = next(iter(possible_maxima)) + 1
                    definition.atomic_level_source = "structure"
                    changed = True
        if not changed:
            break


def translate_hyperatoms(
    root: str | Path,
    *,
    parser: EToEParser | None = None,
    element_catalog: ElementCatalog | None = None,
) -> HyperatomRegistry:
    """Convenience API for translating chemical `.etoe` files and metadata."""
    return HyperatomTranslator(parser, element_catalog=element_catalog).translate_directory(root)
