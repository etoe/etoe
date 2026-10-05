"""Typed placeholders for higher matter stairs.

The 0.1.48 seed defines qualitative organizations for all eight stairs, but
not a complete executable numerical law set for every stair. These classes keep
the model layer explicit without inventing equations absent from the source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .matter import MatterLevel


class ObjectOrganization(str, Enum):
    COLLISION = "collision"
    BATCH = "batch"
    SPIRAL = "spiral"
    MAJOR = "major"
    HYPERATOM = "hyperatom"
    MOLECULE = "molecule"
    BODY = "body"
    ASTR = "astr"


@dataclass(frozen=True)
class MatterObject:
    level: MatterLevel
    class_name: str
    object_id: str | None = None
    subobject_ids: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MatterLadderModel:
    objects: tuple[MatterObject, ...] = ()

    def add(self, obj: MatterObject) -> "MatterLadderModel":
        return MatterLadderModel(self.objects + (obj,))
