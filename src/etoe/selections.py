"""Automatic catalogues of reusable hyperatom selections.

The catalogs are intentionally built on top of the existing element catalog
and semantic hyperatom registry.  They do not reinterpret ÆToE notation: they
index the symbols, structures, and atomic levels already inferred by the core
translator.  Custom groups are data-driven TOML directories.
"""

from __future__ import annotations

import tomllib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .elements import (
    STANDARD_ELEMENT_ATOMIC_NUMBERS,
    ElementCatalog,
    ElementRecord,
)
from .hyperatom_translation import (
    HYPERATOM_KIND,
    HyperatomRegistry,
    HyperatomTranslator,
    SemanticHyperatom,
)


class SelectionCatalogError(ValueError):
    """Raised when a selection-group folder or its TOML file is invalid."""


@dataclass(frozen=True, slots=True)
class ChemicalCategoryDefinition:
    slug: str
    names: Mapping[str, str]

    def name(self, language: str = "en") -> str:
        language = (language or "en").replace("_", "-").lower()
        candidates = (language, language.split("-", 1)[0], "en", "ru")
        for candidate in candidates:
            if self.names.get(candidate):
                return self.names[candidate]
        return self.slug


# These are mutually exclusive buckets. Halogens and noble gases are split
# out of "nonmetals" so every standard element has exactly one category.
# The categories are a practical classification used for indexing, not a new
# physical postulate of the ÆToE seed.
_CATEGORY_ROWS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("nonmetals", "Неметаллы", "Nonmetals", ("H", "C", "N", "O", "P", "S", "Se")),
    ("alkali-metals", "Щелочные металлы", "Alkali metals", ("Li", "Na", "K", "Rb", "Cs", "Fr")),
    ("alkaline-earth-metals", "Щёлочноземельные металлы", "Alkaline earth metals", ("Be", "Mg", "Ca", "Sr", "Ba", "Ra")),
    ("lanthanoids", "Лантаноиды", "Lanthanoids", ("La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu")),
    ("actinoids", "Актиноиды", "Actinoids", ("Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr")),
    ("transition-metals", "Переходные металлы", "Transition metals", (
        "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
        "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
        "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
        "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn",
    )),
    ("post-transition-metals", "Постпереходные металлы", "Post-transition metals", (
        "Al", "Ga", "In", "Sn", "Tl", "Pb", "Bi", "Nh", "Fl", "Mc", "Lv",
    )),
    ("metalloids", "Полуметаллы", "Metalloids", ("B", "Si", "Ge", "As", "Sb", "Te", "Po")),
    ("halogens", "Галогены", "Halogens", ("F", "Cl", "Br", "I", "At", "Ts")),
    ("noble-gases", "Благородные газы", "Noble gases", ("He", "Ne", "Ar", "Kr", "Xe", "Rn", "Og")),
    ("unknowns", "Анноуны", "Unknowns", ()),
)

CATEGORY_DEFINITIONS: tuple[ChemicalCategoryDefinition, ...] = tuple(
    ChemicalCategoryDefinition(slug, MappingProxyType({"ru": ru, "en": en}))
    for slug, ru, en, _symbols in _CATEGORY_ROWS
)
_CATEGORY_BY_SYMBOL: dict[str, str] = {
    symbol: slug for slug, _ru, _en, symbols in _CATEGORY_ROWS for symbol in symbols
}
if len(_CATEGORY_BY_SYMBOL) != sum(len(row[3]) for row in _CATEGORY_ROWS):  # pragma: no cover - invariant
    raise RuntimeError("Chemical category definitions assign a standard element more than once")
if set(_CATEGORY_BY_SYMBOL) != set(STANDARD_ELEMENT_ATOMIC_NUMBERS):  # pragma: no cover - invariant
    missing = sorted(set(STANDARD_ELEMENT_ATOMIC_NUMBERS) - set(_CATEGORY_BY_SYMBOL))
    extra = sorted(set(_CATEGORY_BY_SYMBOL) - set(STANDARD_ELEMENT_ATOMIC_NUMBERS))
    raise RuntimeError(f"Chemical categories do not cover the periodic table: missing={missing}, extra={extra}")


class GraphSelectionItem:
    """Common API for items that can feed a selection into Graphviz."""

    directory: Path

    @property
    def output_dir(self) -> Path:
        """Directory for generated files belonging to this selection item."""
        return self.directory

    @property
    def folder(self) -> Path:
        """Alias for :attr:`directory`."""
        return self.directory

    @property
    def symbols(self) -> tuple[str, ...]:
        """Selection tokens accepted by ``hyperatom_graph_to_dot``."""
        raise NotImplementedError

    def symbols_for_graph(self) -> tuple[str, ...]:
        """Return the filter tokens to pass as ``symbols=`` to the graph builder."""
        return self.symbols

    def write_graph(
        self,
        registry: HyperatomRegistry,
        filename: str = "hyperatoms.dot",
        **kwargs: Any,
    ) -> Path:
        """Generate this selection's graph in its own output directory."""
        from .hyperatom_graphviz import write_hyperatom_graph

        return write_hyperatom_graph(
            registry,
            self.output_dir / filename,
            symbols=self.symbols_for_graph(),
            **kwargs,
        )


@dataclass(eq=False, slots=True)
class ChemicalCategory(GraphSelectionItem):
    slug: str
    names: Mapping[str, str]
    directory: Path
    elements: tuple[ElementRecord, ...] = ()
    hyperatoms: tuple[SemanticHyperatom, ...] = ()

    @property
    def name(self) -> str:
        return self.names.get("ru", self.slug)

    def localized_name(self, language: str = "en") -> str:
        language = (language or "en").replace("_", "-").lower()
        for key in (language, language.split("-", 1)[0], "en", "ru"):
            if self.names.get(key):
                return self.names[key]
        return self.slug

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(element.symbol for element in self.elements)

    @property
    def element_symbols(self) -> tuple[str, ...]:
        return self.symbols

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "names": dict(self.names),
            "directory": self.directory.as_posix(),
            "elements": [element.symbol for element in self.elements],
            "hyperatoms": [hyperatom.id for hyperatom in self.hyperatoms],
        }


class ChemicalCategoryCatalog:
    """Build the standard chemical categories from an :class:`ElementCatalog`."""

    def __init__(
        self,
        element_catalog: ElementCatalog,
        registry: HyperatomRegistry | None = None,
        root: str | Path = "data/atom/category",
    ) -> None:
        self.element_catalog = element_catalog
        self.registry = registry
        self.root = Path(root).expanduser().resolve()
        self._items: tuple[ChemicalCategory, ...] = ()
        self._by_slug: dict[str, ChemicalCategory] = {}
        self.refresh()

    @property
    def categories(self) -> tuple[ChemicalCategory, ...]:
        return self._items

    @property
    def items(self) -> tuple[ChemicalCategory, ...]:
        return self._items

    @property
    def slugs(self) -> tuple[str, ...]:
        return tuple(item.slug for item in self._items)

    def get(self, slug: str) -> ChemicalCategory | None:
        return self._by_slug.get(slug.strip())

    def require(self, slug: str) -> ChemicalCategory:
        try:
            return self._by_slug[slug.strip()]
        except (KeyError, AttributeError) as exc:
            raise KeyError(f"Unknown chemical category {slug!r}") from exc

    def refresh(self) -> "ChemicalCategoryCatalog":
        categories: dict[str, ChemicalCategory] = {}
        for definition in CATEGORY_DEFINITIONS:
            directory = self.root / definition.slug
            directory.mkdir(parents=True, exist_ok=True)
            categories[definition.slug] = ChemicalCategory(
                slug=definition.slug,
                names=definition.names,
                directory=directory,
            )

        elements_by_slug: dict[str, list[ElementRecord]] = defaultdict(list)
        for element in self.element_catalog.elements:
            # All project-specific and auxiliary symbols intentionally fall
            # into unknowns until a project explicitly defines richer metadata.
            slug = _CATEGORY_BY_SYMBOL.get(element.symbol, "unknowns") if element.is_standard else "unknowns"
            category = categories[slug]
            object.__setattr__(element, "chemical_category", category)
            elements_by_slug[slug].append(element)
        for slug, items in elements_by_slug.items():
            categories[slug].elements = tuple(items)

        hyperatoms_by_slug: dict[str, list[SemanticHyperatom]] = defaultdict(list)
        if self.registry is not None:
            for obj in self.registry.definitions:
                slug = "unknowns"
                if obj.symbol:
                    element = self.element_catalog.get(obj.symbol)
                    if element is not None and element.chemical_category is not None:
                        slug = element.chemical_category.slug
                obj.chemical_category = categories[slug]
                if obj.kind == HYPERATOM_KIND:
                    hyperatoms_by_slug[slug].append(obj)
        for slug, items in hyperatoms_by_slug.items():
            categories[slug].hyperatoms = tuple(items)

        self._items = tuple(categories[definition.slug] for definition in CATEGORY_DEFINITIONS)
        self._by_slug = categories
        return self

    def __getitem__(self, slug: str) -> ChemicalCategory:
        return self.require(slug)

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "etoe.chemical-categories.v1", "categories": [item.to_dict() for item in self._items]}


@dataclass(eq=False, slots=True)
class AtomicLevel(GraphSelectionItem):
    level: int
    directory: Path
    hyperatoms: tuple[SemanticHyperatom, ...] = ()

    @property
    def name(self) -> str:
        return str(self.level)

    @property
    def symbols(self) -> tuple[str, ...]:
        # A level selects exact semantic definitions rather than all isotopes
        # of each element. Graph filtering supports canonical notations too.
        return tuple(dict.fromkeys(obj.canonical for obj in self.hyperatoms))

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "directory": self.directory.as_posix(),
            "hyperatoms": [obj.id for obj in self.hyperatoms],
            "symbols": list(self.symbols),
        }


class AtomicLevelCatalog:
    """Index translated hyperatoms by their inferred ``atomic_level``."""

    def __init__(self, registry: HyperatomRegistry, root: str | Path = "data/atom/level") -> None:
        self.registry = registry
        self.root = Path(root).expanduser().resolve()
        self._items: tuple[AtomicLevel, ...] = ()
        self._by_level: dict[int, AtomicLevel] = {}
        self.refresh()

    @property
    def levels(self) -> tuple[AtomicLevel, ...]:
        return self._items

    @property
    def items(self) -> tuple[AtomicLevel, ...]:
        return self._items

    def get(self, level: int) -> AtomicLevel | None:
        return self._by_level.get(int(level))

    def require(self, level: int) -> AtomicLevel:
        result = self.get(level)
        if result is None:
            raise KeyError(f"No hyperatoms indexed at atomic level {level}")
        return result

    def refresh(self) -> "AtomicLevelCatalog":
        by_level: dict[int, list[SemanticHyperatom]] = defaultdict(list)
        for obj in self.registry.definitions:
            if obj.kind == HYPERATOM_KIND and obj.atomic_level is not None:
                if obj.atomic_level < 1:
                    raise SelectionCatalogError(f"Hyperatom {obj.canonical!r} has invalid atomic level {obj.atomic_level}.")
                by_level[obj.atomic_level].append(obj)
        items: list[AtomicLevel] = []
        for level in sorted(by_level):
            directory = self.root / str(level)
            directory.mkdir(parents=True, exist_ok=True)
            sorted_atoms = tuple(sorted(by_level[level], key=lambda obj: (obj.symbol or "", obj.atomic_mass or -1, obj.canonical, obj.id)))
            items.append(AtomicLevel(level=level, directory=directory, hyperatoms=sorted_atoms))
        self._items = tuple(items)
        self._by_level = {item.level: item for item in items}
        return self

    def __getitem__(self, level: int) -> AtomicLevel:
        return self.require(level)

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "etoe.atomic-levels.v1", "levels": [item.to_dict() for item in self._items]}


@dataclass(eq=False, slots=True)
class ElementGroup(GraphSelectionItem):
    name: str
    directory: Path
    declared_symbols: tuple[str, ...]
    elements: tuple[ElementRecord, ...]
    hyperatoms: tuple[SemanticHyperatom, ...] = ()
    metadata_file: Path | None = None

    @property
    def symbols(self) -> tuple[str, ...]:
        return self.declared_symbols

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "directory": self.directory.as_posix(),
            "metadata_file": self.metadata_file.as_posix() if self.metadata_file else None,
            "symbols": list(self.symbols),
            "hyperatoms": [obj.id for obj in self.hyperatoms],
        }


@dataclass(eq=False, slots=True)
class HyperatomGroup(GraphSelectionItem):
    name: str
    directory: Path
    declared_hyperatoms: tuple[str, ...]
    hyperatoms: tuple[SemanticHyperatom, ...]
    metadata_file: Path | None = None

    @property
    def symbols(self) -> tuple[str, ...]:
        # Each token is the lossless canonical notation of a concrete object.
        return tuple(obj.canonical for obj in self.hyperatoms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "directory": self.directory.as_posix(),
            "metadata_file": self.metadata_file.as_posix() if self.metadata_file else None,
            "hyperatoms": [obj.canonical for obj in self.hyperatoms],
            "hyperatom_ids": [obj.id for obj in self.hyperatoms],
        }


class _TomlGroupCatalog:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()

    def _folders(self) -> tuple[Path, ...]:
        if not self.root.exists():
            return ()
        if not self.root.is_dir():
            raise NotADirectoryError(self.root)
        return tuple(sorted(
            (path for path in self.root.iterdir() if path.is_dir() and not path.name.startswith((".", "_"))),
            key=lambda path: path.name,
        ))

    def _read_group_file(self, folder: Path, preferred_name: str) -> tuple[Path, dict[str, Any]]:
        preferred = folder / preferred_name
        if preferred.is_file():
            metadata_file = preferred
        else:
            files = sorted(folder.glob("*.toml"))
            if len(files) != 1:
                raise SelectionCatalogError(
                    f"Group folder {folder} must contain {preferred_name!r} or exactly one TOML file; found {len(files)}."
                )
            metadata_file = files[0]
        try:
            with metadata_file.open("rb") as handle:
                raw = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise SelectionCatalogError(f"Cannot load selection group metadata {metadata_file}: {exc}") from exc
        if not isinstance(raw, dict):  # pragma: no cover - tomllib returns dict
            raise SelectionCatalogError(f"Root of {metadata_file} must be a TOML table.")
        return metadata_file, raw


def _group_payload(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = raw.get("group")
    return nested if isinstance(nested, Mapping) else raw


def _string_list(raw: Mapping[str, Any], fields: Sequence[str], metadata_file: Path) -> tuple[str, ...]:
    payload = _group_payload(raw)
    value: Any = None
    for field_name in fields:
        if field_name in payload:
            value = payload[field_name]
            break
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        expected = " or ".join(repr(field_name) for field_name in fields)
        raise SelectionCatalogError(f"{metadata_file} must define {expected} as an array of non-empty strings.")
    result = tuple(item.strip() for item in value)
    if len(set(result)) != len(result):
        raise SelectionCatalogError(f"{metadata_file} contains duplicate entries in {fields[0]!r}.")
    return result


class ElementGroupCatalog(_TomlGroupCatalog):
    """Read custom chemical-element groups from ``data/atom/groupel/<name>``."""

    def __init__(
        self,
        element_catalog: ElementCatalog,
        registry: HyperatomRegistry | None = None,
        root: str | Path = "data/atom/groupel",
    ) -> None:
        super().__init__(root)
        self.element_catalog = element_catalog
        self.registry = registry
        self._items: tuple[ElementGroup, ...] = ()
        self._by_name: dict[str, ElementGroup] = {}
        self.refresh()

    @property
    def groups(self) -> tuple[ElementGroup, ...]:
        return self._items

    @property
    def items(self) -> tuple[ElementGroup, ...]:
        return self._items

    def get(self, name: str) -> ElementGroup | None:
        return self._by_name.get(name.strip())

    def require(self, name: str) -> ElementGroup:
        result = self.get(name)
        if result is None:
            raise KeyError(f"Unknown chemical-element group {name!r}")
        return result

    def refresh(self) -> "ElementGroupCatalog":
        items: list[ElementGroup] = []
        for folder in self._folders():
            metadata_file, raw = self._read_group_file(folder, "groupel.toml")
            payload = _group_payload(raw)
            declared_name = payload.get("name", folder.name)
            if not isinstance(declared_name, str) or not declared_name.strip():
                raise SelectionCatalogError(f"Group name in {metadata_file} must be a non-empty string.")
            symbols = _string_list(raw, ("elements", "symbols"), metadata_file)
            missing = [symbol for symbol in symbols if self.element_catalog.get(symbol) is None]
            if missing:
                raise SelectionCatalogError(f"Unknown element symbol(s) in {metadata_file}: {', '.join(missing)}.")
            elements = tuple(self.element_catalog.require(symbol) for symbol in symbols)
            hyperatoms = tuple(
                obj for obj in (self.registry.definitions if self.registry else ())
                if obj.kind == HYPERATOM_KIND and obj.symbol in set(symbols)
            )
            items.append(ElementGroup(
                name=declared_name.strip(), directory=folder, declared_symbols=symbols,
                elements=elements, hyperatoms=hyperatoms, metadata_file=metadata_file,
            ))
        names = [item.name for item in items]
        if len(names) != len(set(names)):
            raise SelectionCatalogError("Chemical-element group names must be unique.")
        self._items = tuple(items)
        self._by_name = {item.name: item for item in items}
        return self

    def __getitem__(self, name: str) -> ElementGroup:
        return self.require(name)

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "etoe.element-groups.v1", "groups": [item.to_dict() for item in self._items]}


class HyperatomGroupCatalog(_TomlGroupCatalog):
    """Read concrete hyperatom groups from ``data/atom/group/<name>``."""

    def __init__(self, registry: HyperatomRegistry, root: str | Path = "data/atom/group") -> None:
        super().__init__(root)
        self.registry = registry
        self._items: tuple[HyperatomGroup, ...] = ()
        self._by_name: dict[str, HyperatomGroup] = {}
        self.refresh()

    @property
    def groups(self) -> tuple[HyperatomGroup, ...]:
        return self._items

    @property
    def items(self) -> tuple[HyperatomGroup, ...]:
        return self._items

    def get(self, name: str) -> HyperatomGroup | None:
        return self._by_name.get(name.strip())

    def require(self, name: str) -> HyperatomGroup:
        result = self.get(name)
        if result is None:
            raise KeyError(f"Unknown hyperatom group {name!r}")
        return result

    def refresh(self) -> "HyperatomGroupCatalog":
        candidates_by_text: dict[str, list[SemanticHyperatom]] = defaultdict(list)
        for obj in self.registry.definitions:
            if obj.kind == HYPERATOM_KIND:
                for value in {obj.id, obj.designation, obj.canonical}:
                    candidates_by_text[value].append(obj)
        items: list[HyperatomGroup] = []
        for folder in self._folders():
            metadata_file, raw = self._read_group_file(folder, "group.toml")
            payload = _group_payload(raw)
            declared_name = payload.get("name", folder.name)
            if not isinstance(declared_name, str) or not declared_name.strip():
                raise SelectionCatalogError(f"Group name in {metadata_file} must be a non-empty string.")
            designations = _string_list(raw, ("hyperatoms", "atoms", "symbols"), metadata_file)
            resolved: list[SemanticHyperatom] = []
            for designation in designations:
                exact = [obj for obj in self.registry.definitions if obj.kind == HYPERATOM_KIND and obj.canonical == designation]
                options = exact or candidates_by_text.get(designation, [])
                unique = {obj.id: obj for obj in options}
                if not unique:
                    raise SelectionCatalogError(
                        f"Hyperatom {designation!r} from {metadata_file} was not found in the translated registry."
                    )
                if len(unique) > 1:
                    raise SelectionCatalogError(
                        f"Hyperatom selector {designation!r} in {metadata_file} is ambiguous; use its full canonical notation."
                    )
                resolved.append(next(iter(unique.values())))
            items.append(HyperatomGroup(
                name=declared_name.strip(), directory=folder, declared_hyperatoms=designations,
                hyperatoms=tuple(resolved), metadata_file=metadata_file,
            ))
        names = [item.name for item in items]
        if len(names) != len(set(names)):
            raise SelectionCatalogError("Hyperatom group names must be unique.")
        self._items = tuple(items)
        self._by_name = {item.name: item for item in items}
        return self

    def __getitem__(self, name: str) -> HyperatomGroup:
        return self.require(name)

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "etoe.hyperatom-groups.v1", "groups": [item.to_dict() for item in self._items]}


class AtomSelectionCatalog:
    """Convenience facade that builds all four selection catalogs together.

    ``element_root`` points at ``data/atom/element``; the sibling ``category``,
    ``level``, ``groupel``, and ``group`` directories are inferred from it.
    """

    def __init__(
        self,
        element_root: str | Path | None = None,
        *,
        registry: HyperatomRegistry | None = None,
        element_catalog: ElementCatalog | None = None,
    ) -> None:
        inferred_root = element_root
        if inferred_root is None:
            if element_catalog is not None:
                inferred_root = element_catalog.root
            elif registry is not None and registry.element_catalog is not None:
                inferred_root = registry.element_catalog.root
            else:
                inferred_root = "data/atom/element"
        self.element_root = Path(inferred_root).expanduser().resolve()
        self.data_root = self.element_root.parent
        self.element_catalog = element_catalog or (
            registry.element_catalog if registry is not None and registry.element_catalog is not None
            else ElementCatalog(self.element_root)
        )
        self.registry = registry or HyperatomTranslator(element_catalog=self.element_catalog).translate_directory(self.element_root)
        self.categories = ChemicalCategoryCatalog(self.element_catalog, self.registry, self.data_root / "category")
        self.levels = AtomicLevelCatalog(self.registry, self.data_root / "level")
        self.element_groups = ElementGroupCatalog(self.element_catalog, self.registry, self.data_root / "groupel")
        self.hyperatom_groups = HyperatomGroupCatalog(self.registry, self.data_root / "group")

    @property
    def category_catalog(self) -> ChemicalCategoryCatalog:
        return self.categories

    @property
    def level_catalog(self) -> AtomicLevelCatalog:
        return self.levels

    @property
    def groupel_catalog(self) -> ElementGroupCatalog:
        return self.element_groups

    @property
    def group_catalog(self) -> HyperatomGroupCatalog:
        return self.hyperatom_groups

    def refresh(self) -> "AtomSelectionCatalog":
        """Refresh element links and reread all group folders/TOML files."""
        self.element_catalog.refresh()
        # Refresh the category links before re-resolving the TOML groups.
        self.categories.refresh()
        self.levels.refresh()
        self.element_groups.refresh()
        self.hyperatom_groups.refresh()
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "etoe.atom-selection-catalogs.v1",
            "chemical_categories": self.categories.to_dict(),
            "atomic_levels": self.levels.to_dict(),
            "element_groups": self.element_groups.to_dict(),
            "hyperatom_groups": self.hyperatom_groups.to_dict(),
        }
