"""Discrete space/time primitives from the STÆ model."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class DiscreteDimensions:
    L_AE: int
    T_AE: int

    @property
    def D_AE(self) -> int:
        return self.L_AE - 1

    @property
    def V_AE(self) -> int:
        return self.L_AE ** 3

    def wrap_space(self, n: int) -> int:
        half = self.L_AE // 2
        return (n + half) % self.L_AE - half

    def wrap_time(self, n: int) -> int:
        half = self.T_AE // 2
        return (n + half) % self.T_AE - half

    def wrap_position(self, position: tuple[int, int, int]) -> tuple[int, int, int]:
        return tuple(self.wrap_space(v) for v in position)  # type: ignore[return-value]


def reference_delay(tau_move: int, D_AE: int) -> float:
    return tau_move * D_AE * sqrt(3.0)


def velocity_from_delay(D_AE: int, tau_AE: float, delay: int | float) -> float:
    return D_AE / (tau_AE + delay)


def compensation_ticks(tau_move: int, D_AE: int, direction: tuple[int, int, int]) -> float:
    manhattan = sum(abs(v) for v in direction)
    return tau_move * (D_AE * sqrt(3.0) - manhattan)


def manhattan_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return sum(abs(x-y) for x, y in zip(a, b))


def dominant_step(delta: tuple[int, int, int]) -> tuple[int, int, int]:
    """Choose one orthogonal neighbor by dominant-axis magnitude.

    Ties are resolved deterministically x > y > z, making simulations reproducible.
    """
    if delta == (0, 0, 0):
        return (0, 0, 0)
    values = [abs(v) for v in delta]
    axis = max(range(3), key=lambda i: (values[i], -i))
    step = [0, 0, 0]
    step[axis] = 1 if delta[axis] > 0 else -1
    return tuple(step)  # type: ignore[return-value]
