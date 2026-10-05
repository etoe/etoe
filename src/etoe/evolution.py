"""Evolutionary ladder hooks for Æ1..Æ8.

The seed defines the qualitative organization of the eight matter stairs, but
not a complete numerical executable law for every transition. This module
therefore provides typed transition hooks rather than fabricating dynamics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any

from .matter import MatterLevel


@dataclass(frozen=True)
class MatterTransition:
    source: MatterLevel
    target: MatterLevel
    name: str
    rule: Callable[[Any], Any] | None = None
    implemented: bool = False


class MatterEvolutionPipeline:
    def __init__(self, transitions: tuple[MatterTransition, ...] | None = None):
        self.transitions = transitions or default_transitions()

    def next_transition(self, level: MatterLevel) -> MatterTransition | None:
        for transition in self.transitions:
            if transition.source == level:
                return transition
        return None


def default_transitions() -> tuple[MatterTransition, ...]:
    names = (
        (MatterLevel.E1, MatterLevel.E2, "collision-to-batch emergence"),
        (MatterLevel.E2, MatterLevel.E3, "batch-to-spiral organization"),
        (MatterLevel.E3, MatterLevel.E4, "spiral-to-major closure"),
        (MatterLevel.E4, MatterLevel.E5, "major-to-hyperatom organization"),
        (MatterLevel.E5, MatterLevel.E6, "hyperatom-to-molecule organization"),
        (MatterLevel.E6, MatterLevel.E7, "molecule-to-body organization"),
        (MatterLevel.E7, MatterLevel.E8, "body-to-astr organization"),
    )
    return tuple(MatterTransition(*item) for item in names)
