"""Renderer-neutral snapshots for future STÆ visualization backends."""

from __future__ import annotations

from dataclasses import asdict

from .simulation import STAEWorld


def world_snapshot(world: STAEWorld) -> dict:
    """Return a JSON-ready state snapshot without imposing a graphics stack."""
    e = world.etherons
    return {
        "time": world.t,
        "space": {"L_AE": world.config.L_AE, "T_AE": world.config.T_AE},
        "etherons": [
            {
                "id": i,
                "position": e.position(i),
                "state": e.state[i],
                "direction": e.direction(i),
                "delay": e.delay[i],
            }
            for i in range(len(e))
        ],
    }
