"""Machine-readable matter ladder and object-class registry."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class MatterLevel(IntEnum):
    E1 = 1
    E2 = 2
    E3 = 3
    E4 = 4
    E5 = 5
    E6 = 6
    E7 = 7
    E8 = 8


@dataclass(frozen=True)
class MatterLevelSpec:
    level: MatterLevel
    name_ru: str
    name_en: str
    classes: tuple[str, ...]
    implementation_state: str


MATTER_LEVELS: tuple[MatterLevelSpec, ...] = (
    MatterLevelSpec(MatterLevel.E1, "эфирон", "etheron", ("c",), "microdynamics"),
    MatterLevelSpec(MatterLevel.E2, "эфирный батч / гипербатч", "ether batch / hyperbatch", ("b", "hb"), "model-scaffold"),
    MatterLevelSpec(MatterLevel.E3, "эфирная спираль / гиперспираль", "ether spiral / hyperspiral", ("sp", "hsp"), "model-scaffold"),
    MatterLevelSpec(MatterLevel.E4, "эфирный мажор / гипермажор", "ether major / hypermajor", ("mj", "hmj"), "model-scaffold"),
    MatterLevelSpec(MatterLevel.E5, "гиператом", "hyperatom", ("el", "ps", "p", "n", "a", "pna", "ha"), "model-scaffold"),
    MatterLevelSpec(MatterLevel.E6, "молекула / гипермолекула", "molecule / hypermolecule", ("ml", "hml"), "model-scaffold"),
    MatterLevelSpec(MatterLevel.E7, "тело / гипертело", "body / hyperbody", ("bd", "hbd"), "model-scaffold"),
    MatterLevelSpec(MatterLevel.E8, "астр / гиперастр", "astr / hyperastr", ("as", "has"), "model-scaffold"),
)

CLASS_LEVELS = {cls: int(level.level) for level in MATTER_LEVELS for cls in level.classes}
LEVEL_BY_CLASS = {cls: level for level in MATTER_LEVELS for cls in level.classes}
