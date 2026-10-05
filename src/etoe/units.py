"""ÆSoU unit registry."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EtherUnit(str, Enum):
    N = "n"
    C = "c"
    L = "l"
    S = "s"
    T = "t"
    M = "m"
    V = "v"
    I = "i"


@dataclass(frozen=True)
class UnitSpec:
    suffix: str
    symbol: str
    name_ru: str
    name_en: str
    physical_kind: str
    base: bool = True


UNIT_SPECS = (
    UnitSpec("n", "æn", "эн", "æn", "quantity"),
    UnitSpec("c", "æc", "эя", "æc", "cell_count"),
    UnitSpec("l", "æl", "эл", "æl", "length"),
    UnitSpec("s", "æs", "эс", "æs", "volume"),
    UnitSpec("t", "æt", "эт", "æt", "time"),
    UnitSpec("m", "æm", "эм", "æm", "mass"),
    UnitSpec("v", "æv", "эв", "æv", "velocity"),
    UnitSpec("i", "æi", "эй", "æi", "inertness"),
)

UNIT_BY_SUFFIX = {u.suffix: u for u in UNIT_SPECS}
