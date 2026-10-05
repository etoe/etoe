"""Collision invariants explicitly stated by the 0.1.48 seed."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InertnessInvariants:
    """The vector and scalar inertness sums used by the collision layer."""

    vector: tuple[float, float, float]
    scalar: float


def inertness_invariants(items) -> InertnessInvariants:
    vx = vy = vz = scalar = 0.0
    for direction, delay, D_AE in items:
        dx, dy, dz = direction
        if delay < 0 or D_AE <= 0:
            raise ValueError("delay must be non-negative and D_AE positive")
        norm = (dx * dx + dy * dy + dz * dz) ** 0.5
        if norm == 0:
            continue
        weight = delay / D_AE
        vx += -dx / norm * weight
        vy += -dy / norm * weight
        vz += -dz / norm * weight
        scalar += weight
    return InertnessInvariants((vx, vy, vz), scalar)


def approximately_conserved(before: InertnessInvariants, after: InertnessInvariants, *, atol: float = 1e-12) -> bool:
    return (
        all(abs(a - b) <= atol for a, b in zip(before.vector, after.vector))
        and abs(before.scalar - after.scalar) <= atol
    )
