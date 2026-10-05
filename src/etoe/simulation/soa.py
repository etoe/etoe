"""Structure-of-arrays (SoA) storage for etherons."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EtheronSoA:
    x: list[int]
    y: list[int]
    z: list[int]
    state: list[int]
    collision_x: list[int]
    collision_y: list[int]
    collision_z: list[int]
    collision_t: list[int]
    direction_x: list[int]
    direction_y: list[int]
    direction_z: list[int]
    delay: list[int]
    state_ticks: list[int]
    processed: list[int]

    @classmethod
    def empty(cls) -> "EtheronSoA":
        return cls(*([[] for _ in range(14)]))

    def __len__(self) -> int:
        return len(self.state)

    def append(
        self,
        position: tuple[int, int, int],
        *,
        state: int = 1,
        direction: tuple[int, int, int] = (1, 0, 0),
        delay: int = 0,
        collision_time: int = 0,
    ) -> int:
        x, y, z = position
        dx, dy, dz = direction
        i = len(self.state)
        self.x.append(x); self.y.append(y); self.z.append(z)
        self.state.append(state)
        self.collision_x.append(x); self.collision_y.append(y); self.collision_z.append(z)
        self.collision_t.append(collision_time)
        self.direction_x.append(dx); self.direction_y.append(dy); self.direction_z.append(dz)
        self.delay.append(delay)
        self.state_ticks.append(0)
        self.processed.append(0)
        return i

    def position(self, i: int) -> tuple[int, int, int]:
        return self.x[i], self.y[i], self.z[i]

    def direction(self, i: int) -> tuple[int, int, int]:
        return self.direction_x[i], self.direction_y[i], self.direction_z[i]

    def set_position(self, i: int, position: tuple[int, int, int]) -> None:
        self.x[i], self.y[i], self.z[i] = position
