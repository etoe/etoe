"""Element metadata catalog for ÆToE element data directories.

An element is discovered from ``<data_root>/<SYMBOL>/`` when that directory
contains at least one ``.etoe`` file or a matching ``<SYMBOL>.toml`` metadata
file. Metadata is deliberately kept outside Python code so project-specific
symbols can be added without changing the grammar or package implementation.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterator, Mapping


# Ordered by IUPAC atomic number. Kept in etoe so the catalog can classify
# standard symbols without making periodictable a mandatory dependency.
_STANDARD_ELEMENT_ROWS: tuple[tuple[str, str], ...] = (
    ("H", "hydrogen"), ("He", "helium"), ("Li", "lithium"), ("Be", "beryllium"),
    ("B", "boron"), ("C", "carbon"), ("N", "nitrogen"), ("O", "oxygen"),
    ("F", "fluorine"), ("Ne", "neon"), ("Na", "sodium"), ("Mg", "magnesium"),
    ("Al", "aluminum"), ("Si", "silicon"), ("P", "phosphorus"), ("S", "sulfur"),
    ("Cl", "chlorine"), ("Ar", "argon"), ("K", "potassium"), ("Ca", "calcium"),
    ("Sc", "scandium"), ("Ti", "titanium"), ("V", "vanadium"), ("Cr", "chromium"),
    ("Mn", "manganese"), ("Fe", "iron"), ("Co", "cobalt"), ("Ni", "nickel"),
    ("Cu", "copper"), ("Zn", "zinc"), ("Ga", "gallium"), ("Ge", "germanium"),
    ("As", "arsenic"), ("Se", "selenium"), ("Br", "bromine"), ("Kr", "krypton"),
    ("Rb", "rubidium"), ("Sr", "strontium"), ("Y", "yttrium"), ("Zr", "zirconium"),
    ("Nb", "niobium"), ("Mo", "molybdenum"), ("Tc", "technetium"), ("Ru", "ruthenium"),
    ("Rh", "rhodium"), ("Pd", "palladium"), ("Ag", "silver"), ("Cd", "cadmium"),
    ("In", "indium"), ("Sn", "tin"), ("Sb", "antimony"), ("Te", "tellurium"),
    ("I", "iodine"), ("Xe", "xenon"), ("Cs", "cesium"), ("Ba", "barium"),
    ("La", "lanthanum"), ("Ce", "cerium"), ("Pr", "praseodymium"), ("Nd", "neodymium"),
    ("Pm", "promethium"), ("Sm", "samarium"), ("Eu", "europium"), ("Gd", "gadolinium"),
    ("Tb", "terbium"), ("Dy", "dysprosium"), ("Ho", "holmium"), ("Er", "erbium"),
    ("Tm", "thulium"), ("Yb", "ytterbium"), ("Lu", "lutetium"), ("Hf", "hafnium"),
    ("Ta", "tantalum"), ("W", "tungsten"), ("Re", "rhenium"), ("Os", "osmium"),
    ("Ir", "iridium"), ("Pt", "platinum"), ("Au", "gold"), ("Hg", "mercury"),
    ("Tl", "thallium"), ("Pb", "lead"), ("Bi", "bismuth"), ("Po", "polonium"),
    ("At", "astatine"), ("Rn", "radon"), ("Fr", "francium"), ("Ra", "radium"),
    ("Ac", "actinium"), ("Th", "thorium"), ("Pa", "protactinium"), ("U", "uranium"),
    ("Np", "neptunium"), ("Pu", "plutonium"), ("Am", "americium"), ("Cm", "curium"),
    ("Bk", "berkelium"), ("Cf", "californium"), ("Es", "einsteinium"), ("Fm", "fermium"),
    ("Md", "mendelevium"), ("No", "nobelium"), ("Lr", "lawrencium"), ("Rf", "rutherfordium"),
    ("Db", "dubnium"), ("Sg", "seaborgium"), ("Bh", "bohrium"), ("Hs", "hassium"),
    ("Mt", "meitnerium"), ("Ds", "darmstadtium"), ("Rg", "roentgenium"), ("Cn", "copernicium"),
    ("Nh", "nihonium"), ("Fl", "flerovium"), ("Mc", "moscovium"), ("Lv", "livermorium"),
    ("Ts", "tennessine"), ("Og", "oganesson"),
)

STANDARD_ELEMENT_NAMES: Mapping[str, str] = MappingProxyType(dict(_STANDARD_ELEMENT_ROWS))
STANDARD_ELEMENT_ATOMIC_NUMBERS: Mapping[str, int] = MappingProxyType(
    {symbol: atomic_number for atomic_number, (symbol, _name) in enumerate(_STANDARD_ELEMENT_ROWS, start=1)}
)
STANDARD_ELEMENT_SYMBOLS = frozenset(STANDARD_ELEMENT_NAMES)
ELEMENT_KINDS = frozenset({"standard", "custom", "auxiliary"})
_SYMBOL_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")


class ElementCatalogError(ValueError):
    """Raised when an element directory or its TOML metadata is invalid."""


@dataclass(frozen=True, slots=True)
class ElementRecord:
    """Metadata describing one symbol known to an :class:`ElementCatalog`.

    ``kind`` describes the role of the symbol in ÆToE (``standard``,
    ``custom`` or ``auxiliary``); it is distinct from the syntactic kind of a
    particular definition such as a hyperatom or element template.
    """

    symbol: str
    kind: str
    names: Mapping[str, str]
    role: str
    directory: Path
    metadata_file: Path | None = None
    description: str | None = None
    atomic_number: int | None = None
    aliases: tuple[str, ...] = ()
    metadata: Mapping[str, Any] | None = None
    # Runtime link populated by ChemicalCategoryCatalog.refresh().
    chemical_category: "ChemicalCategory | None" = field(default=None, compare=False, repr=False)
    # Optional category slug explicitly declared in the element TOML.
    # Kept separate from the runtime object so metadata works before any
    # selection catalog has been constructed.
    declared_chemical_category: str | None = None

    @property
    def category(self) -> "ChemicalCategory | None":
        """Return the runtime chemical-category link, when a selection catalog is built."""
        return self.chemical_category

    def name(self, language: str = "en") -> str:
        """Return the best available localized name, falling back to English/symbol.

        Language tags are case-insensitive and ``ru_RU`` is normalized to
        ``ru-RU``. If the requested locale is missing, the base language is
        tried, then English, then the symbol itself.
        """
        requested = _normalize_language(language)
        candidates = [requested]
        base_language = requested.split("-", 1)[0]
        if base_language not in candidates:
            candidates.append(base_language)
        if "en" not in candidates:
            candidates.append("en")
        for candidate in candidates:
            value = self.names.get(candidate)
            if value:
                return value
        if self.kind == "standard" and "en" in candidates:
            return STANDARD_ELEMENT_NAMES.get(self.symbol, self.symbol)
        return self.symbol

    @property
    def is_standard(self) -> bool:
        return self.kind == "standard"

    @property
    def is_custom(self) -> bool:
        return self.kind == "custom"

    @property
    def is_auxiliary(self) -> bool:
        return self.kind == "auxiliary"

    def to_dict(self, *, relative_to: str | Path | None = None) -> dict[str, Any]:
        directory = self.directory
        metadata_file = self.metadata_file
        if relative_to is not None:
            base = Path(relative_to).expanduser().resolve()
            try:
                directory_value = directory.resolve().relative_to(base).as_posix()
            except ValueError:
                directory_value = directory.as_posix()
            if metadata_file is None:
                metadata_value = None
            else:
                try:
                    metadata_value = metadata_file.resolve().relative_to(base).as_posix()
                except ValueError:
                    metadata_value = metadata_file.as_posix()
        else:
            directory_value = directory.as_posix()
            metadata_value = metadata_file.as_posix() if metadata_file else None
        return {
            "symbol": self.symbol,
            "kind": self.kind,
            "role": self.role,
            "names": dict(self.names),
            "description": self.description,
            "atomic_number": self.atomic_number,
            "aliases": list(self.aliases),
            "directory": directory_value,
            "metadata_file": metadata_value,
            "metadata": _plain_data(dict(self.metadata or {})),
            "chemical_category": (
                self.declared_chemical_category
                or getattr(self.chemical_category, "slug", None)
            ),
        }


class ElementCatalog:
    """Discover element symbols and metadata from ``data/atom/element``.

    Each immediate child directory is treated as a symbol folder when it
    contains ``.etoe`` source files or a matching ``<SYMBOL>.toml`` file.
    The TOML file is optional and lives next to that symbol's ``.etoe`` files.

    Classification rules:

    * No TOML + one of the 118 IUPAC symbols: ``standard``.
    * No TOML + another symbol: ``auxiliary``.
    * TOML with explicit ``kind``: the declared kind is used.
    * TOML without ``kind``: known standard symbols remain ``standard``;
      other symbols default to ``custom``.

    ``data_root`` defaults to the repository-style path relative to the
    current working directory. It can be explicitly set for other projects.
    """

    def __init__(self, data_root: str | Path = "data/atom/element") -> None:
        self.root = Path(data_root).expanduser().resolve()
        if not self.root.exists():
            raise FileNotFoundError(self.root)
        if not self.root.is_dir():
            raise NotADirectoryError(self.root)
        self._elements: tuple[ElementRecord, ...] = ()
        self._by_symbol: dict[str, ElementRecord] = {}
        # Runtime auxiliaries live only in this catalog instance. They are
        # never materialized as folders or files under the user's data root.
        self._runtime_elements: dict[str, ElementRecord] = {}
        self.refresh()

    @property
    def elements(self) -> tuple[ElementRecord, ...]:
        """All discovered elements in deterministic periodic-table-first order."""
        return self._elements

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(element.symbol for element in self._elements)

    def get(self, symbol: str) -> ElementRecord | None:
        """Return the record for an exact, case-sensitive symbol, if present."""
        return self._by_symbol.get(symbol.strip())

    def require(self, symbol: str) -> ElementRecord:
        """Return a record or raise :class:`KeyError` for an unknown symbol."""
        result = self.get(symbol)
        if result is None:
            raise KeyError(f"Unknown ÆToE element symbol {symbol!r} in {self.root}")
        return result

    def by_kind(self, kind: str) -> tuple[ElementRecord, ...]:
        if kind not in ELEMENT_KINDS:
            raise ValueError(f"Unknown element kind {kind!r}; expected one of {', '.join(sorted(ELEMENT_KINDS))}.")
        return tuple(element for element in self._elements if element.kind == kind)

    def register_runtime_auxiliary(
        self,
        symbol: str,
        *,
        atomic_level: int,
        description: str | None = None,
    ) -> ElementRecord:
        """Register a virtual auxiliary hyperatom element in this catalog.

        This method is intended for synthetic ``X<n>`` elements created by
        automatic hyperatom-map patching. It updates lookup/serialization
        immediately but does not write anything to disk.
        """
        normalized = symbol.strip() if isinstance(symbol, str) else ""
        if not _SYMBOL_RE.fullmatch(normalized):
            raise ElementCatalogError(f"Invalid runtime auxiliary symbol {symbol!r}.")
        if atomic_level < 1:
            raise ElementCatalogError("Runtime auxiliary atomic_level must be >= 1.")
        existing = self._by_symbol.get(normalized)
        if existing is not None:
            if existing.metadata and existing.metadata.get("runtime") is True:
                existing_level = existing.metadata.get("atomic_level")
                if existing_level != atomic_level:
                    raise ElementCatalogError(
                        f"Runtime auxiliary {normalized!r} already has atomic level {existing_level}, "
                        f"not {atomic_level}."
                    )
                return existing
            raise ElementCatalogError(
                f"Runtime auxiliary symbol {normalized!r} conflicts with an existing catalog element."
            )

        record = ElementRecord(
            symbol=normalized,
            kind="auxiliary",
            names=MappingProxyType({
                "en": f"Auxiliary hyperatom, atomic level {atomic_level}",
                "ru": f"Вспомогательный гиператом, атомный уровень {atomic_level}",
            }),
            role="runtime_auxiliary_hyperatom",
            directory=self.root / normalized,
            metadata_file=None,
            description=description or "Runtime-generated placeholder for a missing subatom hyperatom.",
            atomic_number=None,
            aliases=(),
            metadata=MappingProxyType({
                "runtime": True,
                "atomic_level": atomic_level,
                "generated_by": "etoe.hyperatom_map",
            }),
        )
        self._runtime_elements[normalized] = record
        self.refresh()
        return self._by_symbol[normalized]

    def refresh(self) -> "ElementCatalog":
        """Rescan the directory, picking up newly created folders and TOML files."""
        found: list[ElementRecord] = []
        for directory in sorted(self.root.iterdir(), key=lambda path: path.name):
            if not directory.is_dir() or directory.name.startswith((".", "_")):
                continue
            symbol = directory.name
            metadata_file = directory / f"{symbol}.toml"
            source_exists = next(directory.rglob("*.etoe"), None) is not None
            if not source_exists and not metadata_file.is_file():
                continue
            if not _SYMBOL_RE.fullmatch(symbol):
                raise ElementCatalogError(
                    f"Element folder {directory} has invalid symbol {symbol!r}; "
                    "use a letter followed by letters, digits or underscores."
                )
            found.append(_load_element_record(directory, metadata_file if metadata_file.is_file() else None))

        by_symbol = {element.symbol: element for element in found}
        if len(by_symbol) != len(found):  # Defensive; normal folder names are unique.
            raise ElementCatalogError(f"Duplicate element symbols discovered in {self.root}")

        # Runtime definitions remain visible across refreshes unless a real
        # on-disk definition has claimed the same symbol. Registration itself
        # refuses such conflicts, so this only handles later filesystem edits.
        for symbol, element in self._runtime_elements.items():
            by_symbol.setdefault(symbol, element)
        found = list(by_symbol.values())

        def sort_key(element: ElementRecord) -> tuple[int, int, str]:
            if element.kind == "standard" and element.atomic_number is not None:
                return (0, element.atomic_number, element.symbol)
            kind_order = {"custom": 1, "auxiliary": 2, "standard": 0}[element.kind]
            return (kind_order, 0, element.symbol)

        self._elements = tuple(sorted(found, key=sort_key))
        self._by_symbol = by_symbol
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "etoe.element-catalog.v1",
            "root": self.root.as_posix(),
            "count": len(self._elements),
            "counts_by_kind": {
                kind: sum(element.kind == kind for element in self._elements)
                for kind in ("standard", "custom", "auxiliary")
            },
            "elements": [element.to_dict(relative_to=self.root) for element in self._elements],
        }

    def __getitem__(self, symbol: str) -> ElementRecord:
        return self.require(symbol)

    def __contains__(self, symbol: object) -> bool:
        return isinstance(symbol, str) and symbol in self._by_symbol

    def __iter__(self) -> Iterator[ElementRecord]:
        return iter(self._elements)

    def __len__(self) -> int:
        return len(self._elements)

    def __repr__(self) -> str:
        return f"ElementCatalog(root={str(self.root)!r}, elements={len(self)})"


def default_element_catalog(data_root: str | Path = "data/atom/element") -> ElementCatalog:
    """Create an uncached catalog using the default project data location."""
    return ElementCatalog(data_root)


def _load_element_record(directory: Path, metadata_file: Path | None) -> ElementRecord:
    symbol = directory.name
    raw: dict[str, Any] = {}
    if metadata_file is not None:
        try:
            with metadata_file.open("rb") as handle:
                loaded = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ElementCatalogError(f"Cannot load element metadata {metadata_file}: {exc}") from exc
        if not isinstance(loaded, dict):  # tomllib currently always returns dict; validates the contract.
            raise ElementCatalogError(f"Element metadata root must be a TOML table: {metadata_file}")
        raw = loaded

    declared_symbol = raw.get("symbol", symbol)
    if not isinstance(declared_symbol, str) or declared_symbol != symbol:
        raise ElementCatalogError(
            f"Metadata symbol in {metadata_file} must match its directory symbol {symbol!r}; "
            f"received {declared_symbol!r}."
        )

    if "kind" in raw:
        kind = raw["kind"]
    elif metadata_file is not None and symbol not in STANDARD_ELEMENT_SYMBOLS:
        kind = "custom"
    elif symbol in STANDARD_ELEMENT_SYMBOLS:
        kind = "standard"
    else:
        kind = "auxiliary"
    if not isinstance(kind, str) or kind not in ELEMENT_KINDS:
        raise ElementCatalogError(
            f"Invalid kind in {metadata_file or directory}: {kind!r}; "
            f"expected one of {', '.join(sorted(ELEMENT_KINDS))}."
        )

    role = raw.get("role")
    if role is None:
        role = {"standard": "chemical_element", "custom": "theoretical_element", "auxiliary": "auxiliary"}[kind]
    if not isinstance(role, str) or not role.strip():
        raise ElementCatalogError(f"Field 'role' in {metadata_file} must be a non-empty string.")

    description = raw.get("description")
    if description is not None and not isinstance(description, str):
        raise ElementCatalogError(f"Field 'description' in {metadata_file} must be a string.")

    chemical_category_value = raw.get("chemical_category")
    if chemical_category_value is None:
        declared_chemical_category = None
    elif (
        not isinstance(chemical_category_value, str)
        or not chemical_category_value.strip()
    ):
        raise ElementCatalogError(
            f"Field 'chemical_category' in {metadata_file} must be a non-empty category slug."
        )
    else:
        declared_chemical_category = chemical_category_value.strip()

    names_value = raw.get("names", {})
    if not isinstance(names_value, dict):
        raise ElementCatalogError(f"Field 'names' in {metadata_file} must be a TOML table.")
    names: dict[str, str] = {}
    for language, value in names_value.items():
        if not isinstance(language, str) or not isinstance(value, str) or not value.strip():
            raise ElementCatalogError(
                f"Every entry in [names] in {metadata_file} must map a locale to a non-empty string."
            )
        names[_normalize_language(language)] = value.strip()
    # Convenient shorthand for a single English name.
    simple_name = raw.get("name")
    if simple_name is not None:
        if not isinstance(simple_name, str) or not simple_name.strip():
            raise ElementCatalogError(f"Field 'name' in {metadata_file} must be a non-empty string.")
        names.setdefault("en", simple_name.strip())

    aliases_value = raw.get("aliases", [])
    if not isinstance(aliases_value, list) or any(not isinstance(alias, str) or not alias.strip() for alias in aliases_value):
        raise ElementCatalogError(f"Field 'aliases' in {metadata_file} must be an array of non-empty strings.")

    metadata_value = raw.get("metadata", {})
    if not isinstance(metadata_value, dict):
        raise ElementCatalogError(f"Field 'metadata' in {metadata_file} must be a TOML table.")
    reserved = {
        "symbol", "kind", "role", "description", "names", "name",
        "aliases", "metadata", "chemical_category",
    }
    metadata: dict[str, Any] = dict(metadata_value)
    # Preserve additional fields so projects can extend metadata incrementally.
    metadata.update({key: value for key, value in raw.items() if key not in reserved})

    atomic_number = STANDARD_ELEMENT_ATOMIC_NUMBERS.get(symbol) if kind == "standard" else None
    return ElementRecord(
        symbol=symbol,
        kind=kind,
        names=MappingProxyType(names),
        role=role.strip(),
        directory=directory.resolve(),
        metadata_file=metadata_file.resolve() if metadata_file else None,
        description=description.strip() if isinstance(description, str) else None,
        atomic_number=atomic_number,
        aliases=tuple(alias.strip() for alias in aliases_value),
        metadata=MappingProxyType(metadata),
        declared_chemical_category=declared_chemical_category,
    )


def _normalize_language(language: str) -> str:
    if not isinstance(language, str) or not language.strip():
        return "en"
    return language.strip().replace("_", "-").lower()


def _plain_data(value: Any) -> Any:
    """Convert TOML container values into ordinary JSON-compatible containers."""
    if isinstance(value, dict):
        return {str(key): _plain_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_data(item) for item in value]
    return value
