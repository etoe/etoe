"""Unified experimental generators and analysis tools for ÆToE hyperatoms.

This module contains two equivalent binary-generation strategies:

* :class:`MassIndexedGenerator` builds candidates by target atomic mass.
* :class:`LevelIndexedGenerator` reproduces the old ÆToE object-oriented
  level-by-level traversal.

Both strategies use the same immutable structural data model, canonical
unordered sibling representation, structural identity, family/kind labels,
text serializers, text-list comparison helpers, and combinatorial count
calculators.

The implementation is deliberately explicit about the distinction between
an unrestricted combinatorial binary universe and any later physical
admissibility policy.  Special non-binary configurations such as Ht-3 are
represented by the common data model but are generated through a separate
special-configuration hook.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from math import floor, log2
from typing import Literal, Union


SEQUENCE_PRIMARY = "primary"
SEQUENCE_DOUBLE = "double"
SEQUENCE_TRIPLE = "triple"

COMPOSITION_PRIMARY = "primary"
COMPOSITION_SECONDARY = "secondary"
COMPOSITION_TERTIARY = "tertiary"

KIND_MAGIC = "magic"
KIND_NUMBERED = "numbered"
KIND_SECONDARY = "secondary"
KIND_TERTIARY = "tertiary"

# Historical API aliases.  The canonical terminology is now Primary/Double/Triple
# for sequences and Primary/Secondary/Tertiary for composition classes.
FAMILY_PRIMARY = SEQUENCE_PRIMARY
FAMILY_BASIC = SEQUENCE_DOUBLE
FAMILY_EXTRA = SEQUENCE_TRIPLE
KIND_BASIC = KIND_SECONDARY
KIND_EXTRA = KIND_TERTIARY

# Deprecated spelling aliases retained so existing callers still import.
SEQUENCE_BASIC = SEQUENCE_DOUBLE
SEQUENCE_EXTRA = SEQUENCE_TRIPLE

Family = Literal["primary", "double", "triple"]
CompositionType = Literal["primary", "secondary", "tertiary"]
ConfigKind = Literal["magic", "numbered", "secondary", "tertiary"]


@dataclass(frozen=True, slots=True)
class HyperatomRef:
    """Reference to a primary hyperatom by primary number/mass."""

    number: int

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("hyperatom reference number must be positive")

    @property
    def mass(self) -> int:
        return self.number

    @property
    def hyper_level(self) -> int:
        return primary_hyper_level(self.number)

    @property
    def atomic_level(self) -> int:
        return self.hyper_level + 1

    @property
    def canonical(self) -> str:
        return str(self.number)

    @property
    def key(self) -> tuple:
        return ("ref", self.number)


Subatom = Union[HyperatomRef, "HyperatomConfig"]


@dataclass(frozen=True, slots=True)
class HyperatomConfig:
    """Immutable canonical structural configuration.

    Immediate siblings are an unordered multiset: order is semantically
    irrelevant, but multiplicity is preserved.  Primary children can be
    represented by :class:`HyperatomRef`; non-primary children are embedded
    as explicit nested :class:`HyperatomConfig` values.
    """

    children: tuple[Subatom, ...]

    def __post_init__(self) -> None:
        if not self.children:
            raise ValueError("a hyperatom configuration needs at least one child")
        ordered = tuple(sorted(self.children, key=_subatom_sort_key, reverse=True))
        if ordered != self.children:
            object.__setattr__(self, "children", ordered)

    @classmethod
    def compose(cls, *children: Subatom) -> "HyperatomConfig":
        return cls(tuple(children))

    @property
    def arity(self) -> int:
        return len(self.children)

    @property
    def mass(self) -> int:
        return sum(child.mass for child in self.children)

    @property
    def hyper_level(self) -> int:
        return 1 + max(child.hyper_level for child in self.children)

    @property
    def atomic_level(self) -> int:
        return self.hyper_level + 1

    @property
    def canonical(self) -> str:
        return "'".join(_render_subatom(child) for child in self.children)

    @property
    def key(self) -> tuple:
        return ("config", tuple(child.key for child in self.children))

    def __str__(self) -> str:
        return self.canonical

    @classmethod
    def from_structure(cls, text: str) -> "HyperatomConfig | HyperatomRef":
        parser = _StructureParser(text)
        value = parser.parse_expr()
        parser.skip_ws()
        if parser.pos != len(parser.text):
            raise ValueError(f"unexpected input at offset {parser.pos}: {text!r}")
        return value


def _subatom_sort_key(node: Subatom) -> tuple[int, str]:
    return (node.mass, node.canonical)


def _render_subatom(node: Subatom) -> str:
    if isinstance(node, HyperatomRef):
        return node.canonical
    return f"({node.canonical})"


class _StructureParser:
    """Small parser for structure expressions such as ``(3'1)'1``."""

    def __init__(self, text: str) -> None:
        self.text = text.strip()
        self.pos = 0

    def skip_ws(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def parse_expr(self) -> Subatom:
        self.skip_ws()
        first = self.parse_term()
        children: list[Subatom] = [first]
        while True:
            self.skip_ws()
            if self.pos >= len(self.text) or self.text[self.pos] != "'":
                break
            self.pos += 1
            children.append(self.parse_term())
        if len(children) == 1:
            return first
        return HyperatomConfig.compose(*children)

    def parse_term(self) -> Subatom:
        self.skip_ws()
        if self.pos >= len(self.text):
            raise ValueError("expected integer or parenthesized configuration")
        if self.text[self.pos] == "(":
            self.pos += 1
            value = self.parse_expr()
            self.skip_ws()
            if self.pos >= len(self.text) or self.text[self.pos] != ")":
                raise ValueError("missing ')' in configuration")
            self.pos += 1
            return value
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self.pos += 1
        if start == self.pos:
            raise ValueError(f"expected positive integer at offset {self.pos}")
        value = int(self.text[start:self.pos])
        if value < 1:
            raise ValueError("reference number must be positive")
        return HyperatomRef(value)


@dataclass(frozen=True, slots=True)
class SequenceItem:
    """Common record used by both generation strategies.

    ``category`` is the historical family field retained for API compatibility:
    Primary/Double/Triple sequence membership is stored in ``category``.
    ``kind`` stores the Primary subtypes ``magic``/``numbered`` or the
    Secondary/Tertiary composition classes.
    """

    period: int
    config: HyperatomConfig | HyperatomRef
    category: str
    kind: str | None = None
    source: str | None = None

    @property
    def mass(self) -> int:
        return self.config.mass

    @property
    def canonical(self) -> str:
        return self.config.canonical

    @property
    def hyper_level(self) -> int:
        return self.config.hyper_level

    @property
    def atomic_level(self) -> int:
        return self.hyper_level + 1

    @property
    def designation(self) -> str:
        return short_designation(self.config)

    @property
    def family(self) -> str:
        return self.category

    @property
    def sequence(self) -> str:
        """Inclusive sequence membership: Primary, Double, or Triple."""
        return self.category

    @property
    def composition_type(self) -> str:
        """Structural composition class: Primary, Secondary, or Tertiary."""
        return composition_type(self.config)


Admissibility = Callable[[int, Subatom, Subatom], bool]


def always_admissible(_: int, __: Subatom, ___: Subatom) -> bool:
    return True


def is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def primary_kind(n: int) -> str:
    return KIND_MAGIC if is_power_of_two(n) else KIND_NUMBERED


def composition_type(config: HyperatomConfig | HyperatomRef) -> str:
    """Return the semantic composition class Primary, Secondary, or Tertiary.

    Primary status has semantic precedence over the concrete representation: a
    primary configuration such as ``P_2 = (1'1)`` is still Primary even when
    stored internally as an explicit structural configuration.

    Among non-primary configurations, Secondary means that every immediate
    subatom is a primary reference.  This includes n-ary special forms such as
    ``(1'1'1)``.  Tertiary is the remaining class.  The three classes are
    exhaustive and pairwise disjoint.
    """
    if config.key == primary_configuration(config.mass).key:
        return COMPOSITION_PRIMARY
    if isinstance(config, HyperatomConfig) and all(
        isinstance(child, HyperatomRef) for child in config.children
    ):
        return COMPOSITION_SECONDARY
    return COMPOSITION_TERTIARY


def primary_hyper_level(n: int) -> int:
    """Zero-based structural level of primary configuration P_n."""
    if n < 1:
        raise ValueError("n must be positive")
    if n == 1:
        return 0
    return floor(log2(n - 1)) + 1


def primary_atomic_level(n: int) -> int:
    return primary_hyper_level(n) + 1


def primary_period(n: int) -> int:
    """Chemical-style period number used by the periodic-list examples."""
    return primary_atomic_level(n)


def recursive_primary_definition(n: int) -> tuple[int, int]:
    """Return primary child numbers for primary configuration P_n."""
    if n < 2:
        raise ValueError("n must be >= 2")
    p = 2 ** floor(log2(n - 1))
    return p, n - p


def compose(left: Subatom, right: Subatom) -> HyperatomConfig:
    return HyperatomConfig.compose(left, right)


def item_subatom(item: SequenceItem) -> Subatom:
    """Use a primary mass reference, but retain explicit non-primary structure."""
    if item.category == FAMILY_PRIMARY:
        return HyperatomRef(item.mass)
    return item.config


def primary_configuration(n: int) -> HyperatomConfig | HyperatomRef:
    """Construct the canonical primary configuration without a generator state."""
    if n < 1:
        raise ValueError("n must be positive")
    if n == 1:
        return HyperatomRef(1)
    p, q = recursive_primary_definition(n)
    return compose(HyperatomRef(p), HyperatomRef(q))


def _is_same_key(a: Subatom, b: Subatom) -> bool:
    return a.key == b.key


class BaseHyperatomicGenerator:
    """Shared primary construction and family-level helper interface."""

    def primary(self, max_mass: int) -> Mapping[int, HyperatomConfig | HyperatomRef]:
        raise NotImplementedError

    def double(self, max_mass: int) -> Mapping[int, tuple[HyperatomConfig | HyperatomRef, ...]]:
        raise NotImplementedError

    def triple(self, max_mass: int) -> Mapping[int, tuple[HyperatomConfig | HyperatomRef, ...]]:
        raise NotImplementedError

    # Historical aliases.
    def basic(self, max_mass: int) -> Mapping[int, tuple[HyperatomConfig | HyperatomRef, ...]]:
        return self.double(max_mass)

    def extra(self, max_mass: int) -> Mapping[int, tuple[HyperatomConfig | HyperatomRef, ...]]:
        return self.triple(max_mass)

    def is_primary(self, config: HyperatomConfig | HyperatomRef) -> bool:
        return config.key == primary_configuration(config.mass).key

    def primary_reference(self, mass: int) -> HyperatomRef:
        if mass < 1:
            raise ValueError("mass must be positive")
        self.primary(mass)
        return HyperatomRef(mass)

    def secondary(self, max_mass: int) -> Mapping[int, tuple[HyperatomConfig | HyperatomRef, ...]]:
        data = self.double(max_mass)
        return {
            n: tuple(config for config in data[n] if composition_type(config) == COMPOSITION_SECONDARY)
            for n in range(1, max_mass + 1)
        }

    def tertiary(self, max_mass: int) -> Mapping[int, tuple[HyperatomConfig | HyperatomRef, ...]]:
        data = self.triple(max_mass)
        return {
            n: tuple(config for config in data[n] if composition_type(config) == COMPOSITION_TERTIARY)
            for n in range(1, max_mass + 1)
        }

    def primary_sequence(self, max_mass: int, *, source: str | None = None) -> tuple[SequenceItem, ...]:
        p = self.primary(max_mass)
        return tuple(
            SequenceItem(primary_period(n), p[n], FAMILY_PRIMARY, primary_kind(n), source)
            for n in range(1, max_mass + 1)
        )

    def double_sequence(self, max_mass: int, *, source: str | None = None) -> tuple[SequenceItem, ...]:
        data = self.double(max_mass)
        return tuple(
            SequenceItem(
                primary_period(n),
                config,
                SEQUENCE_PRIMARY if self.is_primary(config) else SEQUENCE_DOUBLE,
                primary_kind(n) if self.is_primary(config) else KIND_SECONDARY,
                source,
            )
            for n in range(1, max_mass + 1)
            for config in data[n]
        )

    def triple_sequence(self, max_mass: int, *, source: str | None = None) -> tuple[SequenceItem, ...]:
        data = self.triple(max_mass)
        double_data = self.double(max_mass)
        double_keys_by_mass = {
            n: {config.key for config in double_data[n]}
            for n in range(1, max_mass + 1)
        }
        result: list[SequenceItem] = []
        for n in range(1, max_mass + 1):
            for config in data[n]:
                primary = self.is_primary(config)
                double = config.key in double_keys_by_mass[n]
                category = (
                    SEQUENCE_PRIMARY if primary
                    else SEQUENCE_DOUBLE if double
                    else SEQUENCE_TRIPLE
                )
                kind = (
                    primary_kind(n) if primary
                    else KIND_SECONDARY if double
                    else KIND_TERTIARY
                )
                result.append(SequenceItem(primary_period(n), config, category, kind, source))
        return tuple(result)

    def secondary_new(self, max_mass: int, *, source: str | None = None) -> tuple[SequenceItem, ...]:
        return tuple(
            item for item in self.double_sequence(max_mass, source=source)
            if item.category == SEQUENCE_DOUBLE and item.composition_type == COMPOSITION_SECONDARY
        )

    def tertiary_new(self, max_mass: int, *, source: str | None = None) -> tuple[SequenceItem, ...]:
        return tuple(
            item for item in self.triple_sequence(max_mass, source=source)
            if item.category == SEQUENCE_TRIPLE and item.composition_type == COMPOSITION_TERTIARY
        )

    # Historical method aliases.
    def basic_sequence(self, max_mass: int, *, source: str | None = None) -> tuple[SequenceItem, ...]:
        return self.double_sequence(max_mass, source=source)

    def extra_sequence(self, max_mass: int, *, source: str | None = None) -> tuple[SequenceItem, ...]:
        return self.triple_sequence(max_mass, source=source)

    def basic_new(self, max_mass: int, *, source: str | None = None) -> tuple[SequenceItem, ...]:
        return self.secondary_new(max_mass, source=source)

    def extra_new(self, max_mass: int, *, source: str | None = None) -> tuple[SequenceItem, ...]:
        return self.tertiary_new(max_mass, source=source)


class MassIndexedGenerator(BaseHyperatomicGenerator):
    """Generate binary families by target mass.

    This is the mass-indexed strategy used by the newer experimental module.
    """

    def __init__(
        self,
        *,
        basic_admissible: Admissibility = always_admissible,
        extra_admissible: Admissibility = always_admissible,
        recursive_extra: bool = False,
    ) -> None:
        self.basic_admissible = basic_admissible
        self.extra_admissible = extra_admissible
        self.recursive_extra = recursive_extra
        self._primary: dict[int, HyperatomConfig | HyperatomRef] = {1: HyperatomRef(1)}
        self._basic: dict[int, tuple[HyperatomConfig | HyperatomRef, ...]] = {
            1: (HyperatomRef(1),)
        }
        self._extra: dict[int, tuple[HyperatomConfig | HyperatomRef, ...]] = {
            1: (HyperatomRef(1),)
        }

    def primary(self, max_mass: int) -> Mapping[int, HyperatomConfig | HyperatomRef]:
        if max_mass < 1:
            return {}
        for n in range(2, max_mass + 1):
            if n in self._primary:
                continue
            p, q = recursive_primary_definition(n)
            self._primary[n] = compose(HyperatomRef(p), HyperatomRef(q))
        return dict(self._primary)

    def double(self, max_mass: int) -> Mapping[int, tuple[HyperatomConfig | HyperatomRef, ...]]:
        if max_mass < 1:
            return {}
        self.primary(max_mass)
        for n in range(2, max_mass + 1):
            if n in self._basic:
                continue
            pool = [HyperatomRef(m) for m in range(1, n)]
            out: list[HyperatomConfig | HyperatomRef] = []
            seen: set[tuple] = set()
            for left, right in _binary_candidates_by_mass(pool, n):
                config = compose(left, right)
                if self.is_primary(config):
                    allowed = True
                else:
                    allowed = self.basic_admissible(n, left, right)
                if not allowed or config.key in seen:
                    continue
                seen.add(config.key)
                out.append(config)
            primary = self._primary[n]
            if primary.key not in seen:
                out.append(primary)
            out.sort(key=_config_order_key, reverse=True)
            self._basic[n] = tuple(out)
        return dict(self._basic)

    def triple(self, max_mass: int) -> Mapping[int, tuple[HyperatomConfig | HyperatomRef, ...]]:
        if max_mass < 1:
            return {}
        self.double(max_mass)
        for n in range(2, max_mass + 1):
            if n in self._extra:
                continue
            pool: list[Subatom] = []
            source = self._extra if self.recursive_extra else self._basic
            for m in range(1, n):
                for config in source.get(m, ()):
                    pool.append(HyperatomRef(m) if self.is_primary(config) else config)
            out: list[HyperatomConfig | HyperatomRef] = []
            seen: set[tuple] = set()
            double_keys = {config.key for config in self._basic.get(n, ())}
            for left, right in _binary_candidates_by_mass(pool, n):
                config = compose(left, right)
                kind = composition_type(config)
                if kind == COMPOSITION_PRIMARY:
                    allowed = True
                elif kind == COMPOSITION_SECONDARY:
                    # Secondary configurations belong to Double, not Triple.
                    # A rejected secondary candidate must not be promoted to
                    # Tertiary merely because Triple is being generated.
                    allowed = config.key in double_keys
                else:
                    allowed = self.extra_admissible(n, left, right)
                if not allowed or config.key in seen:
                    continue
                seen.add(config.key)
                out.append(config)
            # Every inherited Basic/Primary element belongs to the inclusive
            # Extra family even if the Extra policy rejects all new candidates.
            for inherited in self._basic.get(n, ()):
                if inherited.key not in seen:
                    seen.add(inherited.key)
                    out.append(inherited)
            out.sort(key=_config_order_key, reverse=True)
            self._extra[n] = tuple(out)
        return dict(self._extra)


class RecursiveMassIndexedGenerator(MassIndexedGenerator):
    """Mass-indexed recursive closure matching the old level traversal universe."""

    def __init__(self, **kwargs: object) -> None:
        kwargs["recursive_extra"] = True
        super().__init__(**kwargs)


# Backward-compatible name retained for existing code that used the old
# experimental mass-indexed generator.
HyperatomicGenerator = MassIndexedGenerator


class LevelIndexedGenerator(BaseHyperatomicGenerator):
    """Reimplementation of the old ÆToE level-by-level object traversal.

    The public result is a set-like mapping indexed by mass, while the internal
    generation state preserves the historical level-major traversal order.
    ``extra_cap`` can reproduce the old book-generation limit ``c < 1000``;
    ``None`` means unlimited generation.
    """

    def __init__(
        self,
        *,
        basic_admissible: Admissibility = always_admissible,
        extra_admissible: Admissibility = always_admissible,
        extra_cap: int | None = None,
        max_extra_level: int | None = None,
        deduplicate: bool = True,
    ) -> None:
        if extra_cap is not None and extra_cap < 1:
            raise ValueError("extra_cap must be positive or None")
        self.basic_admissible = basic_admissible
        self.extra_admissible = extra_admissible
        self.extra_cap = extra_cap
        self.max_extra_level = max_extra_level
        self.deduplicate = deduplicate
        self._basic_done_to: int = 0
        self._extra_done_to: int = -1
        self._items: list[SequenceItem] = []
        self._seen: dict[tuple, SequenceItem] = {}
        self._level_items: dict[int, list[SequenceItem]] = defaultdict(list)
        self._basic_cache: dict[int, tuple[HyperatomConfig | HyperatomRef, ...]] | None = None
        self._extra_cache: dict[int, tuple[HyperatomConfig | HyperatomRef, ...]] | None = None
        self._generation_stats: list[LevelGenerationStat] = []
        self._primary_by_mass: dict[int, HyperatomConfig | HyperatomRef] = {1: HyperatomRef(1)}
        self._append_initial_magic()

    def _append_initial_magic(self) -> None:
        p1 = HyperatomRef(1)
        item = SequenceItem(1, p1, FAMILY_PRIMARY, KIND_MAGIC, "level")
        self._add_item(0, item, p1)

    @property
    def items(self) -> tuple[SequenceItem, ...]:
        return tuple(self._items)

    @property
    def generation_stats(self) -> tuple["LevelGenerationStat", ...]:
        return tuple(self._generation_stats)

    def _rebuild_items(self) -> None:
        self._items = [item for level in sorted(self._level_items) for item in self._level_items[level]]

    def _add_item(self, level: int, item: SequenceItem, config: Subatom) -> bool:
        if self.deduplicate and config.key in self._seen:
            return False
        stored = SequenceItem(primary_period(config.mass), config, item.category, item.kind, item.source)
        self._seen[config.key] = stored
        self._level_items[level].append(stored)
        if item.category == FAMILY_PRIMARY:
            self._primary_by_mass[config.mass] = config
        self._rebuild_items()
        return True

    def _old_create(self, level: int, kind: str, config: HyperatomConfig | HyperatomRef) -> bool:
        category = (
            SEQUENCE_PRIMARY if kind in (KIND_MAGIC, KIND_NUMBERED)
            else SEQUENCE_DOUBLE if kind == KIND_SECONDARY
            else SEQUENCE_TRIPLE
        )
        item = SequenceItem(primary_period(config.mass), config, category, kind, "level")
        return self._add_item(level, item, config)

    def _reset_generation_state(self) -> None:
        self._basic_done_to = 0
        self._extra_done_to = -1
        self._items = []
        self._seen = {}
        self._level_items = defaultdict(list)
        self._generation_stats = []
        self._primary_by_mass = {1: HyperatomRef(1)}
        self._basic_cache = None
        self._extra_cache = None
        self._append_initial_magic()

    def _generate_double_seed(self, max_mass: int) -> None:
        if max_mass < 1:
            return
        if self._basic_done_to >= max_mass:
            return
        if self._extra_done_to >= 0:
            self._reset_generation_state()
        # Historical traversal order: primary subatom number m is the outer
        # loop and the second number i runs from 1 through m.  The structural
        # level, however, is derived from the children themselves rather than
        # from mass sorting or a separate inferred mass level.
        for m in range(1, max_mass + 1):
            for i in range(1, m + 1):
                config = compose(HyperatomRef(m), HyperatomRef(i))
                if self.is_primary(config):
                    kind = primary_kind(config.mass)
                else:
                    if not self.basic_admissible(config.mass, config.children[0], config.children[1]):
                        continue
                    kind = KIND_SECONDARY
                self._old_create(config.hyper_level, kind, config)
        self._basic_done_to = max_mass
        self._basic_cache = None
        self._extra_cache = None
        self._rebuild_items()

    def primary(self, max_mass: int) -> Mapping[int, HyperatomConfig | HyperatomRef]:
        if max_mass < 1:
            return {}
        self._generate_double_seed(max_mass)
        return {n: self._primary_by_mass[n] for n in range(1, max_mass + 1)}

    def double(self, max_mass: int) -> Mapping[int, tuple[HyperatomConfig | HyperatomRef, ...]]:
        if max_mass < 1:
            return {}
        self._generate_double_seed(max_mass)
        out: dict[int, list[HyperatomConfig | HyperatomRef]] = defaultdict(list)
        for item in self._items:
            if item.mass > max_mass:
                continue
            if item.category in (SEQUENCE_PRIMARY, SEQUENCE_DOUBLE):
                out[item.mass].append(item.config)
        return {n: tuple(out[n]) for n in range(1, max_mass + 1)}

    def _extra_level_limit_for_mass(self, max_mass: int) -> int:
        if max_mass < 2:
            return 0
        return floor(log2(max_mass))

    def _generate_extra_to_level(self, max_level: int, *, mass_cutoff: int | None = None) -> None:
        if max_level <= self._extra_done_to:
            return
        c = 1
        for stat in self._generation_stats:
            c = stat.counter_after

        for level in range(max(1, self._extra_done_to + 1), max_level + 1):
            lower = [
                item
                for previous_level in range(level)
                for item in self._level_items.get(previous_level, ())
            ]
            current = list(self._level_items.get(level - 1, ()))
            candidate_count = 0
            extra_allowed = 0
            extra_blocked = 0
            created = 0
            counter_before = c
            for offset, item1 in enumerate(current):
                global_i = len(lower) + offset
                for j in range(global_i + 1):
                    item2 = lower[j] if j < len(lower) else current[j - len(lower)]
                    candidate_count += 1
                    left = item_subatom(item1)
                    right = item_subatom(item2)
                    config = compose(left, right)
                    if mass_cutoff is not None and config.mass > mass_cutoff:
                        continue
                    is_primary_candidate = self.is_primary(config)
                    children_are_primary = (
                        item1.composition_type == COMPOSITION_PRIMARY
                        and item2.composition_type == COMPOSITION_PRIMARY
                    )
                    kind: str | None
                    if is_primary_candidate:
                        kind = primary_kind(config.mass)
                    elif children_are_primary and self.basic_admissible(
                        config.mass, left, right
                    ):
                        kind = KIND_SECONDARY
                    elif self.extra_cap is None or c < self.extra_cap:
                        if self.extra_admissible(config.mass, left, right):
                            kind = KIND_TERTIARY
                            extra_allowed += 1
                        else:
                            kind = None
                    else:
                        kind = None
                        extra_blocked += 1
                    if kind is not None:
                        c += 1
                        if self._old_create(level, kind, config):
                            created += 1

            self._rebuild_items()
            self._generation_stats.append(
                LevelGenerationStat(
                    level=level,
                    counter_before=counter_before,
                    counter_after=c,
                    candidate_count=candidate_count,
                    extra_allowed=extra_allowed,
                    extra_blocked=extra_blocked,
                    created_count=created,
                )
            )
            self._extra_done_to = level
    def triple(self, max_mass: int) -> Mapping[int, tuple[HyperatomConfig | HyperatomRef, ...]]:
        if max_mass < 1:
            return {}
        self._generate_double_seed(max_mass)
        level_limit = self.max_extra_level
        if level_limit is None:
            level_limit = max_mass - 1
        self._generate_extra_to_level(level_limit, mass_cutoff=max_mass)
        # Return only requested masses; extra generation is level-based.
        out: dict[int, list[HyperatomConfig | HyperatomRef]] = defaultdict(list)
        for item in self._items:
            if item.mass <= max_mass:
                if item.category in (SEQUENCE_PRIMARY, SEQUENCE_DOUBLE, SEQUENCE_TRIPLE):
                    out[item.mass].append(item.config)
        self._extra_cache = {n: tuple(out[n]) for n in range(1, max_mass + 1)}
        return dict(self._extra_cache)

    @classmethod
    def legacy_book_sequence(
        cls,
        *,
        seed_max_mass: int = 128,
        max_extra_level: int = 8,
        extra_cap: int = 1000,
    ) -> tuple[SequenceItem, ...]:
        """Reproduce the historical finite Extra-book generation regime.

        The generation is intentionally not mass-pruned: the old code built a
        Primary/Basic seed from an empty collection and then traversed levels
        through ``max_extra_level`` with the historical global counter cap.
        """
        gen = cls(extra_cap=extra_cap, max_extra_level=max_extra_level)
        gen._generate_double_seed(seed_max_mass)
        gen._generate_extra_to_level(max_extra_level, mass_cutoff=None)
        return gen.items

    def generation_order(self, max_mass: int, family: str = "extra") -> tuple[SequenceItem, ...]:
        if family == FAMILY_PRIMARY:
            self.primary(max_mass)
        elif family == FAMILY_BASIC:
            self.double(max_mass)
        elif family == FAMILY_EXTRA:
            self.triple(max_mass)
        else:
            raise ValueError("family must be primary, basic, or extra")
        return tuple(item for item in self._items if item.mass <= max_mass)


@dataclass(frozen=True, slots=True)
class LevelGenerationStat:
    level: int
    counter_before: int
    counter_after: int
    candidate_count: int
    extra_allowed: int
    extra_blocked: int
    created_count: int


def _config_order_key(config: Subatom) -> tuple[int, str]:
    return (config.mass, config.canonical)


def _binary_candidates_by_mass(
    pool: Sequence[Subatom], target_mass: int
) -> Iterator[tuple[Subatom, Subatom]]:
    unique: dict[tuple, Subatom] = {item.key: item for item in pool if item.mass < target_mass}
    by_mass: dict[int, list[Subatom]] = defaultdict(list)
    for item in unique.values():
        by_mass[item.mass].append(item)
    for items in by_mass.values():
        items.sort(key=_config_order_key, reverse=True)

    for left_mass in sorted(by_mass):
        right_mass = target_mass - left_mass
        if left_mass > right_mass or right_mass not in by_mass:
            continue
        lefts = by_mass[left_mass]
        rights = by_mass[right_mass]
        if left_mass < right_mass:
            for left in lefts:
                for right in rights:
                    yield left, right
        else:
            for i, left in enumerate(lefts):
                for right in lefts[i:]:
                    yield left, right


def short_designation(config: HyperatomConfig | HyperatomRef) -> str:
    """Translate a structure to mass + canonical structure notation.

    Examples: ``2-(1'1)``, ``5-((3'1)'1)``.
    """
    return f"{config.mass}-({config.canonical})"


def legacy_sequence_line(config: HyperatomConfig | HyperatomRef) -> str:
    """Render one element in the historical sequence payload format."""
    return f"{config.mass}={config.canonical}."


def format_sequence(
    items: Iterable[SequenceItem],
    *,
    generation_order: bool = True,
    with_period_headers: bool = True,
    designation_format: str = "legacy",
) -> str:
    """Render a sequence as historical period text or standard designations."""
    data = list(items)
    if not generation_order:
        data.sort(key=lambda x: (x.atomic_level, x.mass, x.canonical))
    lines: list[str] = []
    current_period: int | None = None
    for item in data:
        if with_period_headers and item.atomic_level != current_period:
            current_period = item.atomic_level
            lines.append(f"{current_period}:")
        if designation_format == "legacy":
            lines.append(legacy_sequence_line(item.config))
        elif designation_format == "short":
            lines.append(item.designation + ".")
        elif designation_format == "structure":
            lines.append(item.canonical + ".")
        else:
            raise ValueError("designation_format must be legacy, short, or structure")
    return "\n".join(lines)


def format_designation_list(items: Iterable[SequenceItem], *, sort: bool = True) -> str:
    data = list(items)
    if sort:
        data.sort(key=lambda x: (x.mass, x.atomic_level, x.canonical))
    return "\n".join(item.designation + "." for item in data)


def _parse_text_entry(line: str) -> HyperatomConfig | HyperatomRef | None:
    line = line.strip()
    if not line or line.endswith(":"):
        return None
    if line.endswith("."):
        line = line[:-1].strip()
    if "=" in line:
        mass_text, structure = line.split("=", 1)
        mass = int(mass_text.strip())
        config = HyperatomConfig.from_structure(structure.strip())
        if config.mass != mass:
            raise ValueError(f"mass mismatch in line {line!r}: declared {mass}, actual {config.mass}")
        return config
    dash = line.find("-(")
    if dash <= 0:
        raise ValueError(f"unrecognized hyperatom line: {line!r}")
    mass = int(line[:dash])
    structure = line[dash + 2 :]
    if not structure.endswith(")"):
        raise ValueError(f"missing outer ')' in line: {line!r}")
    structure = structure[:-1]
    config = HyperatomConfig.from_structure(structure)
    if config.mass != mass:
        raise ValueError(f"mass mismatch in line {line!r}: declared {mass}, actual {config.mass}")
    return config


def parse_hyperatom_text(text: str) -> tuple[HyperatomConfig | HyperatomRef, ...]:
    values: list[HyperatomConfig | HyperatomRef] = []
    for line in text.splitlines():
        value = _parse_text_entry(line)
        if value is not None:
            values.append(value)
    return tuple(values)


def sort_hyperatom_text(text: str, *, output: str = "short", deduplicate: bool = False) -> str:
    """Normalize, sort, and optionally deduplicate a hyperatom text list."""
    values = list(parse_hyperatom_text(text))
    if deduplicate:
        unique: dict[tuple, Subatom] = {value.key: value for value in values}
        values = list(unique.values())
    values.sort(key=lambda x: (x.mass, x.atomic_level, x.canonical))
    if output == "short":
        return "\n".join(short_designation(value) + "." for value in values)
    if output == "legacy":
        return "\n".join(legacy_sequence_line(value) for value in values)
    if output == "structure":
        return "\n".join(value.canonical + "." for value in values)
    raise ValueError("output must be short, legacy, or structure")


@dataclass(frozen=True, slots=True)
class TextListComparison:
    equal: bool
    a_count: int
    b_count: int
    a_unique: int
    b_unique: int
    only_in_a: tuple[str, ...]
    only_in_b: tuple[str, ...]
    duplicates_in_a: tuple[str, ...]
    duplicates_in_b: tuple[str, ...]

    def summary(self) -> str:
        status = "equal" if self.equal else "different"
        return (
            f"{status}: A={self.a_count} ({self.a_unique} unique), "
            f"B={self.b_count} ({self.b_unique} unique), "
            f"only-A={len(self.only_in_a)}, only-B={len(self.only_in_b)}"
        )


def compare_text_lists(a_text: str, b_text: str) -> TextListComparison:
    a_values = parse_hyperatom_text(a_text)
    b_values = parse_hyperatom_text(b_text)
    a_counter = Counter(value.key for value in a_values)
    b_counter = Counter(value.key for value in b_values)
    key_to_value = {value.key: value for value in (*a_values, *b_values)}

    only_a: list[str] = []
    only_b: list[str] = []
    for key in sorted(a_counter.keys() | b_counter.keys(), key=lambda k: short_designation(key_to_value[k])):
        delta_a = a_counter[key] - b_counter[key]
        delta_b = b_counter[key] - a_counter[key]
        if delta_a > 0:
            only_a.extend([short_designation(key_to_value[key])] * delta_a)
        if delta_b > 0:
            only_b.extend([short_designation(key_to_value[key])] * delta_b)

    duplicates_a = tuple(
        short_designation(key_to_value[key])
        for key in sorted(a_counter, key=lambda k: short_designation(key_to_value[k]))
        if a_counter[key] > 1
    )
    duplicates_b = tuple(
        short_designation(key_to_value[key])
        for key in sorted(b_counter, key=lambda k: short_designation(key_to_value[k]))
        if b_counter[key] > 1
    )
    return TextListComparison(
        equal=a_counter == b_counter,
        a_count=len(a_values),
        b_count=len(b_values),
        a_unique=len(a_counter),
        b_unique=len(b_counter),
        only_in_a=tuple(only_a),
        only_in_b=tuple(only_b),
        duplicates_in_a=duplicates_a,
        duplicates_in_b=duplicates_b,
    )


def _normalize_sequence_family(name: str) -> str:
    aliases = {
        "primary": SEQUENCE_PRIMARY,
        "double": SEQUENCE_DOUBLE,
        "triple": SEQUENCE_TRIPLE,
        "basic": SEQUENCE_DOUBLE,
        "extra": SEQUENCE_TRIPLE,
    }
    try:
        return aliases[name]
    except KeyError as exc:
        raise ValueError(f"unknown sequence family: {name}") from exc


def _normalize_count_family(name: str) -> str:
    aliases = {
        "primary": SEQUENCE_PRIMARY,
        "double": SEQUENCE_DOUBLE,
        "triple": SEQUENCE_TRIPLE,
        "secondary": COMPOSITION_SECONDARY,
        "tertiary": COMPOSITION_TERTIARY,
        "basic": SEQUENCE_DOUBLE,
        "extra": SEQUENCE_TRIPLE,
        "basic_new": COMPOSITION_SECONDARY,
        "extra_new": COMPOSITION_TERTIARY,
        "secondary_new": COMPOSITION_SECONDARY,
        "tertiary_new": COMPOSITION_TERTIARY,
    }
    try:
        return aliases[name]
    except KeyError as exc:
        raise ValueError(f"unknown count family: {name}") from exc


@dataclass(frozen=True, slots=True)
class CombinatorialCountTable:
    """Exact unrestricted binary counts up to a finite target mass."""

    max_mass: int
    by_mass: Mapping[str, Mapping[int, int]]
    by_atomic_level: Mapping[str, Mapping[int, int]]
    by_mass_and_atomic_level: Mapping[str, Mapping[tuple[int, int], int]]

    def count(self, family: str, *, mass: int | None = None, atomic_level: int | None = None) -> int:
        family = _normalize_count_family(family)
        if family not in self.by_mass:
            raise ValueError(f"unknown family: {family}")
        if mass is not None and atomic_level is not None:
            return self.by_mass_and_atomic_level[family].get((mass, atomic_level), 0)
        if mass is not None:
            return self.by_mass[family].get(mass, 0)
        if atomic_level is not None:
            return self.by_atomic_level[family].get(atomic_level, 0)
        return sum(self.by_mass[family].values())


def _unordered_pair_group_count(counts: Mapping[int, int], left_mass: int, right_mass: int, parent_level: int, out: dict[tuple[int, int], int]) -> None:
    """Add unordered pairs of a single mass group, split by child levels."""
    if left_mass != right_mass:
        raise ValueError("same-mass helper requires equal masses")
    levels = sorted(counts)
    for idx, l1 in enumerate(levels):
        c1 = counts[l1]
        for l2 in levels[idx:]:
            c2 = counts[l2]
            multiplicity = c1 * c2 if l1 < l2 else c1 * (c1 + 1) // 2
            parent = 1 + max(l1, l2)
            out[(left_mass + right_mass, parent)] += multiplicity


def _pair_counts_for_target(
    item_counts: Mapping[tuple[int, int], int],
    target_mass: int,
) -> dict[tuple[int, int], int]:
    by_mass: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for (mass, level), count in item_counts.items():
        if 1 <= mass < target_mass:
            by_mass[mass][level] += count
    result: dict[tuple[int, int], int] = defaultdict(int)
    for left_mass in sorted(by_mass):
        right_mass = target_mass - left_mass
        if left_mass > right_mass or right_mass not in by_mass:
            continue
        if left_mass < right_mass:
            for l1, c1 in by_mass[left_mass].items():
                for l2, c2 in by_mass[right_mass].items():
                    result[(target_mass, 1 + max(l1, l2))] += c1 * c2
        else:
            _unordered_pair_group_count(by_mass[left_mass], left_mass, right_mass, 0, result)
    return result


def _pair_counts_by_mass_and_level(
    item_counts: Mapping[tuple[int, int], int],
    max_mass: int,
) -> dict[tuple[int, int], int]:
    by_mass: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for (mass, level), count in item_counts.items():
        if 1 <= mass <= max_mass:
            by_mass[mass][level] += count
    result: dict[tuple[int, int], int] = defaultdict(int)
    masses = sorted(by_mass)
    for left_mass in masses:
        right_mass = left_mass
        while right_mass <= max_mass - left_mass:
            if right_mass not in by_mass:
                right_mass += 1
                continue
            if left_mass > right_mass:
                right_mass += 1
                continue
            if left_mass < right_mass:
                for l1, c1 in by_mass[left_mass].items():
                    for l2, c2 in by_mass[right_mass].items():
                        result[(left_mass + right_mass, 1 + max(l1, l2))] += c1 * c2
            else:
                _unordered_pair_group_count(by_mass[left_mass], left_mass, right_mass, 0, result)
            right_mass += 1
    return result


def combinatorial_counts(max_mass: int, *, model: str = "double_only") -> CombinatorialCountTable:
    """Compute unrestricted binary family counts without materializing structures.

    ``model="double_only"`` matches the non-recursive Triple experiment: a
    tertiary parent may use Primary or Secondary children. ``basic_only`` is
    retained as a compatibility alias.

    ``model="recursive"`` matches the old level-by-level closure: a tertiary
    parent may use any already-generated Primary, Secondary, or Tertiary child.
    """
    if model == "basic_only":
        model = "double_only"
    if model not in {"double_only", "recursive"}:
        raise ValueError("model must be double_only or recursive")
    if max_mass < 1:
        empty = {name: {} for name in (SEQUENCE_PRIMARY, SEQUENCE_DOUBLE, SEQUENCE_TRIPLE, COMPOSITION_SECONDARY, COMPOSITION_TERTIARY)}
        return CombinatorialCountTable(0, empty, {name: {} for name in empty}, {name: {} for name in empty})

    primary_ml: dict[tuple[int, int], int] = {}
    for mass in range(1, max_mass + 1):
        primary_ml[(mass, primary_hyper_level(mass))] = 1

    double_candidates_ml = _pair_counts_by_mass_and_level(primary_ml, max_mass)
    secondary_new_ml: dict[tuple[int, int], int] = defaultdict(int)
    for key, count in double_candidates_ml.items():
        remaining = count - primary_ml.get(key, 0)
        if remaining < 0:
            raise AssertionError(f"primary exceeds Double candidates at {key}")
        if remaining:
            secondary_new_ml[key] = remaining
    double_ml: dict[tuple[int, int], int] = defaultdict(int, primary_ml)
    for key, count in secondary_new_ml.items():
        double_ml[key] += count

    if model == "double_only":
        triple_all_ml = _pair_counts_by_mass_and_level(double_ml, max_mass)
    else:
        recursive_all_ml: dict[tuple[int, int], int] = defaultdict(int, primary_ml)
        for mass in range(2, max_mass + 1):
            for key, count in _pair_counts_for_target(recursive_all_ml, mass).items():
                recursive_all_ml[key] = count
        triple_all_ml = dict(recursive_all_ml)

    tertiary_new_ml: dict[tuple[int, int], int] = defaultdict(int)
    for key, count in triple_all_ml.items():
        tertiary_new_ml[key] = count - double_ml.get(key, 0)
        if tertiary_new_ml[key] < 0:
            raise AssertionError(f"internal combinatorial inconsistency at {key}")

    primary_ml = dict(primary_ml)
    double_ml = dict(double_ml)
    triple_all_ml = dict(triple_all_ml)
    tertiary_new_ml = dict(tertiary_new_ml)

    def by_mass(ml: Mapping[tuple[int, int], int]) -> dict[int, int]:
        out: dict[int, int] = defaultdict(int)
        for (mass, _level), count in ml.items():
            out[mass] += count
        return dict(out)

    def by_level(ml: Mapping[tuple[int, int], int]) -> dict[int, int]:
        out: dict[int, int] = defaultdict(int)
        for (_mass, level), count in ml.items():
            out[level + 1] += count
        return dict(out)

    families_ml = {
        SEQUENCE_PRIMARY: primary_ml,
        SEQUENCE_DOUBLE: double_ml,
        SEQUENCE_TRIPLE: triple_all_ml,
        COMPOSITION_SECONDARY: secondary_new_ml,
        COMPOSITION_TERTIARY: tertiary_new_ml,
    }
    def public_mass_level(ml: Mapping[tuple[int, int], int]) -> dict[tuple[int, int], int]:
        return {(mass, level + 1): count for (mass, level), count in ml.items()}

    return CombinatorialCountTable(
        max_mass=max_mass,
        by_mass={name: by_mass(ml) for name, ml in families_ml.items()},
        by_atomic_level={name: by_level(ml) for name, ml in families_ml.items()},
        by_mass_and_atomic_level={name: public_mass_level(ml) for name, ml in families_ml.items()},
    )


def combinatorial_count(
    family: str,
    *,
    mass: int | None = None,
    atomic_level: int | None = None,
    max_mass: int = 128,
    model: str = "double_only",
) -> int:
    table = combinatorial_counts(max_mass, model=model)
    return table.count(family, mass=mass, atomic_level=atomic_level)


def validate_generated_counts(
    items: Iterable[SequenceItem],
    *,
    family: str,
    max_mass: int,
    model: str = "double_only",
) -> CountValidationResult:
    """Compare generated family counts with unrestricted combinatorial counts."""
    observed: Counter[tuple[int, int]] = Counter()
    family = _normalize_count_family(family)
    for item in items:
        if item.mass > max_mass:
            continue
        if family == SEQUENCE_PRIMARY:
            include = item.composition_type == COMPOSITION_PRIMARY
        elif family == COMPOSITION_SECONDARY:
            include = item.composition_type == COMPOSITION_SECONDARY
        elif family == SEQUENCE_DOUBLE:
            include = item.category in (SEQUENCE_PRIMARY, SEQUENCE_DOUBLE)
        elif family == COMPOSITION_TERTIARY:
            include = item.composition_type == COMPOSITION_TERTIARY
        else:
            include = item.category in (SEQUENCE_PRIMARY, SEQUENCE_DOUBLE, SEQUENCE_TRIPLE)
        if include:
            observed[(item.mass, item.atomic_level)] += 1
    expected = combinatorial_counts(max_mass, model=model).by_mass_and_atomic_level[family]
    keys = set(observed) | set(expected)
    mismatches = tuple(
        CountMismatch(mass, level, expected.get((mass, level), 0), observed.get((mass, level), 0))
        for mass, level in sorted(keys)
        if expected.get((mass, level), 0) != observed.get((mass, level), 0)
    )
    return CountValidationResult(equal=not mismatches, family=family, max_mass=max_mass, model=model, mismatches=mismatches)


@dataclass(frozen=True, slots=True)
class CountMismatch:
    mass: int
    atomic_level: int
    expected: int
    observed: int


@dataclass(frozen=True, slots=True)
class CountValidationResult:
    equal: bool
    family: str
    max_mass: int
    model: str
    mismatches: tuple[CountMismatch, ...]

    def summary(self) -> str:
        return (
            f"{self.family}/{self.model}: {'equal' if self.equal else 'different'} "
            f"through mass {self.max_mass}; mismatches={len(self.mismatches)}"
        )


def generate_special_configurations(
    base: Iterable[SequenceItem],
    specials: Iterable[tuple[Subatom, str, str]],
) -> tuple[SequenceItem, ...]:
    """Add explicitly declared non-binary configurations with deduplication.

    ``specials`` contains ``(config, family, kind)`` triples.  This hook is
    intended for configurations such as Ht-3-(1'1'1), which are outside the
    binary closure.
    """
    out = list(base)
    seen = {item.config.key for item in out}
    for config, family, kind in specials:
        if config.key in seen:
            continue
        out.append(SequenceItem(primary_period(config.mass), config, family, kind, "special"))
        seen.add(config.key)
    return tuple(out)


def _family_of_kind(kind: str) -> str:
    if kind in (KIND_MAGIC, KIND_NUMBERED):
        return SEQUENCE_PRIMARY
    if kind == KIND_SECONDARY:
        return SEQUENCE_DOUBLE
    return SEQUENCE_TRIPLE


__all__ = [
    "Admissibility",
    "BaseHyperatomicGenerator",
    "CombinatorialCountTable",
    "CountMismatch",
    "CountValidationResult",
    "COMPOSITION_PRIMARY",
    "COMPOSITION_SECONDARY",
    "COMPOSITION_TERTIARY",
    "FAMILY_BASIC",
    "FAMILY_EXTRA",
    "FAMILY_PRIMARY",
    "SEQUENCE_DOUBLE",
    "SEQUENCE_PRIMARY",
    "SEQUENCE_TRIPLE",
    "SEQUENCE_BASIC",
    "SEQUENCE_EXTRA",
    "HyperatomConfig",
    "HyperatomRef",
    "HyperatomicGenerator",
    "KIND_BASIC",
    "KIND_EXTRA",
    "KIND_SECONDARY",
    "KIND_TERTIARY",
    "KIND_MAGIC",
    "KIND_NUMBERED",
    "LevelGenerationStat",
    "LevelIndexedGenerator",
    "MassIndexedGenerator",
    "RecursiveMassIndexedGenerator",
    "SequenceItem",
    "Subatom",
    "TextListComparison",
    "always_admissible",
    "composition_type",
    "combinatorial_count",
    "combinatorial_counts",
    "compare_text_lists",
    "compose",
    "format_designation_list",
    "format_sequence",
    "generate_special_configurations",
    "is_power_of_two",
    "item_subatom",
    "legacy_sequence_line",
    "parse_hyperatom_text",
    "primary_atomic_level",
    "primary_hyper_level",
    "primary_kind",
    "primary_period",
    "primary_configuration",
    "recursive_primary_definition",
    "short_designation",
    "sort_hyperatom_text",
    "validate_generated_counts",
]
