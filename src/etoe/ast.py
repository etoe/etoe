"""Typed AST for the canonical ÆToE notation.

The AST intentionally mirrors the EBNF vocabulary rather than attempting to
encode a complete physical ontology. Semantic meaning beyond syntax belongs
in validation and simulation/model layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence, Union


class Notation:
    """Base class for any canonical ÆToE notation node."""

    def to_canonical(self) -> str:
        raise NotImplementedError


Statement = Notation


@dataclass(frozen=True)
class SourceComment:
    text: str
    kind: str
    start: int
    end: int


@dataclass(frozen=True)
class ObjectContext:
    part: str
    subpart: str | None = None
    subsubpart: str | None = None

    def to_canonical(self) -> str:
        out = self.part
        if self.subpart is not None:
            out += f".{self.subpart}"
        if self.subsubpart is not None:
            out += f".{self.subsubpart}"
        return out


@dataclass(frozen=True)
class Instance:
    pairs: tuple[tuple[str, Any], ...] = ()

    def to_canonical(self) -> str:
        return "-{%s}" % ",".join(f"{k}={_value_to_text(v)}" for k, v in self.pairs)


@dataclass(frozen=True)
class Structure:
    objects: tuple[Notation, ...] = ()
    separators: tuple[str, ...] = ()

    def to_canonical(self) -> str:
        if not self.objects:
            return "-()"
        chunks = [self.objects[0].to_canonical()]
        for sep, obj in zip(self.separators, self.objects[1:]):
            chunks.append(sep)
            chunks.append(obj.to_canonical())
        return "-(" + "".join(chunks) + ")"


@dataclass(frozen=True)
class EFullObject(Notation):
    level: int
    class_name: str
    context: ObjectContext | None = None
    instance: Instance | None = None
    structure: Structure | None = None

    def to_canonical(self) -> str:
        out = f"Æ{self.level}.{self.class_name}"
        if self.context:
            out += f".{self.context.to_canonical()}"
        if self.instance:
            out += self.instance.to_canonical()
        if self.structure:
            out += self.structure.to_canonical()
        return out


@dataclass(frozen=True)
class ECompactObject(Notation):
    class_name: str
    context: ObjectContext | None = None
    instance: Instance | None = None
    structure: Structure | None = None

    def to_canonical(self) -> str:
        out = f"Æ{self.class_name}"
        if self.context:
            out += f".{self.context.to_canonical()}"
        if self.instance:
            out += self.instance.to_canonical()
        if self.structure:
            out += self.structure.to_canonical()
        return out


@dataclass(frozen=True)
class EEther(Notation):
    role: str | None = None
    subrole: str | None = None
    instance: Instance | None = None
    structure: Structure | None = None

    def to_canonical(self) -> str:
        out = "Æ"
        if self.role:
            out += f":{self.role}"
            if self.subrole:
                out += f".{self.subrole}"
        if self.instance:
            out += self.instance.to_canonical()
        if self.structure:
            out += self.structure.to_canonical()
        return out


@dataclass(frozen=True)
class EEtheron(Notation):
    role: str | None = None
    subrole: str | None = None
    instance: Instance | None = None
    structure: Structure | None = None

    def to_canonical(self) -> str:
        out = "æ"
        if self.role:
            out += f":{self.role}"
            if self.subrole:
                out += f".{self.subrole}"
        if self.instance:
            out += self.instance.to_canonical()
        if self.structure:
            out += self.structure.to_canonical()
        return out


@dataclass(frozen=True)
class ELevel(Notation):
    level: int

    def to_canonical(self) -> str:
        return f"Æ{self.level}"


@dataclass(frozen=True)
class EUnit(Notation):
    suffix: str

    def to_canonical(self) -> str:
        return f"æ{self.suffix}"


@dataclass(frozen=True)
class ChemicalNotation(Notation):
    kind: str  # element | molecule | mass | protium_core | proton | neutron
    symbol: str | None = None
    subsort: str | None = None
    atomic_mass: int | None = None
    structure: Structure | None = None

    def to_canonical(self) -> str:
        if self.kind == "mass":
            assert self.atomic_mass is not None
            return str(self.atomic_mass)
        if self.kind == "protium_core":
            return "0"
        if self.kind == "proton":
            return "p"
        if self.kind == "neutron":
            return "n"
        assert self.symbol is not None
        out = self.symbol
        if self.subsort is not None:
            out += f":{self.subsort}"
        if self.atomic_mass is not None:
            out += f"-{self.atomic_mass}"
        if self.structure is not None:
            out += self.structure.to_canonical()
        return out


@dataclass(frozen=True)
class ScienceContext:
    domain: str
    subdomains: tuple[str, ...] = ()

    def to_canonical(self) -> str:
        return ".".join((self.domain, *self.subdomains))


@dataclass(frozen=True)
class Aspect:
    kind: str
    value: str

    def to_canonical(self) -> str:
        return self.value


@dataclass(frozen=True)
class QuantityExpression(Notation):
    quantity: str
    science_context: ScienceContext | None = None
    aspects: tuple[Aspect, ...] = ()
    character: str | None = None
    object: Notation | None = None

    def to_canonical(self) -> str:
        parts = [self.quantity]
        if self.science_context:
            parts.append(self.science_context.to_canonical())
        parts.extend(a.to_canonical() for a in self.aspects)
        if self.character:
            parts.append(self.character)
        if self.object is None:
            raise ValueError("QuantityExpression requires an object")
        parts.append(self.object.to_canonical())
        return ".".join(parts)


@dataclass(frozen=True)
class ConstantExpression(Notation):
    form: str
    name: str
    quantity: str | None = None
    character: str | None = None
    object: Notation | None = None

    def to_canonical(self) -> str:
        if self.form == "full":
            assert self.quantity is not None and self.character is not None and self.object is not None
            return f"const.{self.quantity}.{self.character}.{self.object.to_canonical()}"
        if self.form == "compact_letter":
            return f"Ꞓ{self.name}"
        if self.form == "compact_at":
            return f"@{self.name}"
        raise ValueError(f"Unknown constant form: {self.form}")


@dataclass(frozen=True)
class MeasurementExpression(Notation):
    value: int | float
    unit: EUnit

    def to_canonical(self) -> str:
        return f"{_number_to_text(self.value)}{self.unit.to_canonical()}"


@dataclass(frozen=True)
class EToEFile:
    statements: tuple[Statement, ...] = ()
    comments: tuple[SourceComment, ...] = ()

    def to_canonical(self) -> str:
        return "\n".join(f"{s.to_canonical()};" for s in self.statements)


def _number_to_text(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    return format(value, ".15g")


def _value_to_text(value: Any) -> str:
    if isinstance(value, str):
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(value, (int, float)):
        return _number_to_text(value)
    if isinstance(value, MeasurementExpression):
        return value.to_canonical()
    return str(value)
