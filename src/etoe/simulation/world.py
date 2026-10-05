"""Executable STÆ micro-dynamics scaffold.

This module deliberately implements only rules that are sufficiently explicit
in the 0.1.48 seed to be expressed as a deterministic reference kernel:
wrapped discrete space/time, four etheron states, same-cell collision detection,
and one-neighbor orthogonal movement toward the current target direction.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ..coordinates import DiscreteDimensions, dominant_step
from .soa import EtheronSoA


@dataclass(frozen=True)
class SimulationConfig:
    L_AE: int = 16
    T_AE: int = 16
    tau_move: int = 3
    default_delay: int = 0

    def __post_init__(self) -> None:
        if self.L_AE <= 0 or self.L_AE % 2:
            raise ValueError("L_AE must be a positive even integer")
        if self.T_AE <= 0 or self.T_AE % 2:
            raise ValueError("T_AE must be a positive even integer")
        if self.tau_move < 3:
            raise ValueError("tau_move must be >= 3 in the simplest model")


class STAEWorld:
    def __init__(self, config: SimulationConfig | None = None):
        self.config = config or SimulationConfig()
        self.dim = DiscreteDimensions(self.config.L_AE, self.config.T_AE)
        self.t = 0
        self.etherons = EtheronSoA.empty()

    def add_etheron(
        self,
        position: tuple[int, int, int],
        *,
        state: int = 1,
        direction: tuple[int, int, int] = (1, 0, 0),
        delay: int | None = None,
    ) -> int:
        wrapped = self.dim.wrap_position(position)
        d = self.config.default_delay if delay is None else delay
        return self.etherons.append(wrapped, state=state, direction=direction, delay=d, collision_time=self.t)

    def populate_one_per_cell(self) -> None:
        half = self.config.L_AE // 2
        for x in range(-half, half):
            for y in range(-half, half):
                for z in range(-half, half):
                    self.add_etheron((x, y, z))

    def occupancy(self, *, states: tuple[int, ...] | None = None) -> dict[tuple[int, int, int], int]:
        counts: dict[tuple[int, int, int], int] = defaultdict(int)
        allowed = set(states) if states is not None else None
        for i in range(len(self.etherons)):
            if allowed is None or self.etherons.state[i] in allowed:
                counts[self.etherons.position(i)] += 1
        return dict(counts)

    def step(self, steps: int = 1) -> None:
        for _ in range(steps):
            self._step_once()

    def _step_once(self) -> None:
        e = self.etherons
        occupied_s1 = self.occupancy(states=(1,))
        for i in range(len(e)):
            e.processed[i] = 0

        # Each etheron is processed at most once during a tick.
        for i in range(len(e)):
            state = e.state[i]
            pos = e.position(i)
            if state == 1:
                # s1 -> s2 when another etheron is simultaneously resting in the cell.
                if occupied_s1.get(pos, 0) > 1:
                    e.state[i] = 2
                    e.state_ticks[i] = 1
                    e.collision_x[i], e.collision_y[i], e.collision_z[i] = pos
                    e.collision_t[i] = self.t
                    e.processed[i] = 1
                    continue
                # Otherwise move toward the target direction after the current rest tick.
                if e.state_ticks[i] >= e.delay[i]:
                    e.state[i] = 3
                    e.state_ticks[i] = 1
                    e.processed[i] = 1
                else:
                    e.state_ticks[i] += 1
                    e.processed[i] = 1
            elif state == 2:
                # Collision state lasts at least one tick; then continue to departure.
                e.state[i] = 3
                e.state_ticks[i] = 1
                e.processed[i] = 1
            elif state == 3:
                # Determine a single orthogonal neighbor toward the long-term direction target.
                step = dominant_step(e.direction(i))
                e.direction_x[i], e.direction_y[i], e.direction_z[i] = e.direction(i)
                e.state[i] = 4
                e.state_ticks[i] = 1
                # Store the next cell temporarily in collision coordinates. This keeps the
                # SoA kernel allocation-free while the full future-position model is evolving.
                target = self.dim.wrap_position((pos[0] + step[0], pos[1] + step[1], pos[2] + step[2]))
                e.collision_x[i], e.collision_y[i], e.collision_z[i] = target
                e.processed[i] = 1
            elif state == 4:
                target = (e.collision_x[i], e.collision_y[i], e.collision_z[i])
                e.set_position(i, self.dim.wrap_position(target))
                e.state[i] = 1
                e.state_ticks[i] = 0
                e.processed[i] = 1
            else:
                raise ValueError(f"Invalid etheron state {state}; expected one of 1,2,3,4")

        self.t = self.dim.wrap_time(self.t + 1)
