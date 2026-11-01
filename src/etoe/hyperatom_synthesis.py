"""Deterministic, renderer-neutral synthesis model for hierarchical hyperatoms.

The ÆToE seed does not yet define calibrated equations for etheron counts,
forces, radii, or shell constitutive laws.  This module therefore implements
an explicit *phenomenological simulation profile*: stable separated Protium
sites are gradually coupled by an increasing spiral parameter and relaxed
into the semantic, bottom-up atomahedron prescribed by the source composition.
All numerical coefficients are versioned visualization/model conventions, not
experimentally established physical constants.

The module deliberately has no Blender dependency so that simulation planning,
profiles, and cache decisions can be tested with ordinary CPython.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class SynthesisProfile:
    name: str
    steps: int
    attempts: int
    relaxation: float
    tolerance: float
    mesh_subdivisions: int
    render_samples: int
    atmosphere_layers: int
    clump_layers: int = 2


PROFILES: dict[str, SynthesisProfile] = {
    "rough": SynthesisProfile(
        name="rough", steps=24, attempts=3, relaxation=0.19,
        tolerance=0.025, mesh_subdivisions=2, render_samples=16,
        atmosphere_layers=3, clump_layers=2,
    ),
    "strict": SynthesisProfile(
        name="strict", steps=96, attempts=12, relaxation=0.105,
        tolerance=0.002, mesh_subdivisions=4, render_samples=64,
        atmosphere_layers=5, clump_layers=3,
    ),
}


@dataclass(frozen=True, slots=True)
class SynthesisFrame:
    frame: int
    spiral_addition: float
    compression: float
    positions: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True, slots=True)
class HyperatomSynthesis:
    quality: str
    success: bool
    expected_structure: str
    expected_atomahedron: str
    attempt_count: int
    steps: int
    residual: float
    initial_positions: tuple[tuple[float, float, float], ...]
    final_positions: tuple[tuple[float, float, float], ...]
    frames: tuple[SynthesisFrame, ...]
    model: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "quality": self.quality,
            "success": self.success,
            "expected_structure": self.expected_structure,
            "expected_atomahedron": self.expected_atomahedron,
            "attempt_count": self.attempt_count,
            "steps": self.steps,
            "residual": round(self.residual, 10),
            "initial_positions": [list(value) for value in self.initial_positions],
            "final_positions": [list(value) for value in self.final_positions],
            "frames": [
                {
                    "frame": item.frame,
                    "spiral_addition": round(item.spiral_addition, 8),
                    "compression": round(item.compression, 8),
                    "positions": [list(value) for value in item.positions],
                }
                for item in self.frames
            ],
            "model": self.model,
        }


def _rotate(point: Sequence[float], angle: float, axis: tuple[float, float, float]) -> tuple[float, float, float]:
    """Rotate a point with Rodrigues' formula; all calculations are deterministic."""
    x, y, z = map(float, point)
    ax, ay, az = axis
    dot = x * ax + y * ay + z * az
    cross = (ay * z - az * y, az * x - ax * z, ax * y - ay * x)
    c, s = math.cos(angle), math.sin(angle)
    return (
        x * c + cross[0] * s + ax * dot * (1.0 - c),
        y * c + cross[1] * s + ay * dot * (1.0 - c),
        z * c + cross[2] * s + az * dot * (1.0 - c),
    )


def _levitation_vertices(count: int, minimum_pair_distance: float = 2.0) -> tuple[tuple[float, float, float], ...]:
    """Return a repeatable initially separated arrangement of Protium sites."""
    if count <= 0:
        return ()
    if count == 1:
        return ((0.0, 0.0, 0.0),)
    if count == 2:
        points = [(-1.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
    elif count == 3:
        points = [(-0.5, -math.sqrt(3.0) / 6.0, 0.0),
                  (0.5, -math.sqrt(3.0) / 6.0, 0.0),
                  (0.0, math.sqrt(3.0) / 3.0, 0.0)]
    elif count == 4:
        q = 1.0 / math.sqrt(3.0)
        points = [(q, q, q), (q, -q, -q), (-q, q, -q), (-q, -q, q)]
    else:
        golden = math.pi * (3.0 - math.sqrt(5.0))
        points = []
        for index in range(count):
            z = 1.0 - 2.0 * (index + 0.5) / count
            radius = math.sqrt(max(0.0, 1.0 - z * z))
            angle = golden * index
            points.append((radius * math.cos(angle), radius * math.sin(angle), z))
    # Normalize every arrangement by its actual nearest-neighbour distance.
    # Earlier versions accidentally gave the explicit triangle/tetrahedron a
    # one-unit separation while the two-Protium case had a two-unit separation.
    nearest = min(
        math.dist(points[i], points[j])
        for i in range(count) for j in range(i + 1, count)
    )
    scale = minimum_pair_distance / max(nearest, 1e-9)
    return tuple(tuple(component * scale for component in point) for point in points)


def _bounding_dimensions(points: Sequence[Sequence[float]], margin: float) -> tuple[float, float, float]:
    if not points:
        return (2.0 * margin, 2.0 * margin, 2.0 * margin)
    return tuple(
        max(point[axis] for point in points) - min(point[axis] for point in points) + 2.0 * margin
        for axis in range(3)
    )


def _node_model(layout: Any, profile: SynthesisProfile) -> dict[str, Any]:
    """Export common and per-layer model parameters for each tree node."""
    node = layout.node
    is_terminal_protium = bool(layout.terminal and layout.is_protium)
    compression = round(0.92 ** int(layout.depth), 8)
    clumps = []
    if is_terminal_protium:
        for index in range(profile.clump_layers):
            # Layer radii are normalized to the local body radius. The values
            # are geometric modelling parameters, not measured density shells.
            clumps.append({
                "index": index + 1,
                "radius_factor": round(1.0 - 0.19 * index, 6),
                "deformation": round(min(0.48, layout.deformation + 0.035 * index), 6),
                "kind": "deformable-clump-layer",
            })
    atmospheres = [
        {
            "index": index + 1,
            "radius_factor": round(1.0 + (0.45 + 0.55 * (index + 1) / profile.atmosphere_layers)
                                    * layout.atmosphere_thickness / max(layout.content_radius, 1e-9), 6),
            "deformation": round(min(0.035, layout.deformation * 0.12), 6),
            "kind": "atmospheric-layer",
        }
        for index in range(profile.atmosphere_layers)
    ]
    return {
        "canonical": node.canonical,
        "designation": node.designation,
        "symbol": node.symbol or "",
        "atomic_mass_amu": node.atomic_mass,
        "atomic_level": node.atomic_level,
        "atomahedron": layout.atomahedron,
        "hierarchy_depth": layout.depth,
        "protium_constituents": len(layout.protium_sites),
        "bounding_dimensions_model_units": [
            round(2.0 * layout.outer_radius, 8),
            round(2.0 * layout.outer_radius, 8),
            round(2.0 * layout.outer_radius, 8),
        ],
        "content_radius_model_units": round(layout.content_radius, 8),
        "outer_radius_model_units": round(layout.outer_radius, 8),
        "compression_factor": compression,
        "deformation_factor": round(layout.deformation, 8),
        "spin": None,
        "mass_etheron_units": None,
        "etheron_count": None,
        "ether_spiral_count": None,
        "unresolved_parameters": ["spin", "mass_etheron_units", "etheron_count", "ether_spiral_count"],
        "protium_reference": {
            "minimum_gabarit": 1.0,
            "unit": "model-unit",
            "initial_levitation_pair_distance": 2.0,
        },
        "clumping_layers": clumps,
        "atmospheric_layers": atmospheres,
        "children": [_node_model(child, profile) for child in layout.children],
    }


def simulate_hyperatom_synthesis(
    node: Any,
    layout: Any,
    *,
    quality: str = "rough",
    attempts: int | None = None,
) -> HyperatomSynthesis:
    """Simulate a deterministic spiral-addition/relaxation trajectory.

    The expected hierarchy comes from the semantic source tree; retries vary
    only the initial levitation orientation. Since the current seed specifies
    structural composition but not force laws, the relaxation is a documented
    geometric surrogate and does not claim to predict nuclear physics.
    """
    try:
        profile = PROFILES[quality.casefold()]
    except (AttributeError, KeyError) as exc:
        raise ValueError("quality must be 'rough' or 'strict'") from exc
    attempt_limit = profile.attempts if attempts is None else int(attempts)
    if attempt_limit < 1:
        raise ValueError("attempts must be positive")

    target = tuple(tuple(map(float, site.center)) for site in layout.protium_sites)
    count = len(target)
    if count == 0:
        raise ValueError("cannot synthesize a hyperatom without Protium constituents")
    center = tuple(map(float, layout.center))
    initial_radius = 0.0
    base_initial = _levitation_vertices(count, 2.0)
    # Keep the prescribed minimum Protium gabarit as the absolute model unit:
    # initial nearest-neighbour spacing remains exactly 2.0 regardless of the
    # final atomhedral envelope. Composite atoms contract from this levitating
    # state rather than silently rescaling the reference unit per element.
    radius = 1.0 if count > 1 else 0.0
    base_initial = tuple(
        tuple(center[axis] + point[axis] * radius for axis in range(3))
        for point in base_initial
    )
    initial_radius = max((math.dist(point, center) for point in base_initial), default=0.0)

    best: tuple[float, tuple[SynthesisFrame, ...], tuple[tuple[float, float, float], ...], int] | None = None
    axis_options = ((0.0, 0.0, 1.0), (0.577350269, 0.577350269, 0.577350269),
                    (0.0, 1.0, 0.0), (1.0, 0.0, 0.0))
    for attempt in range(attempt_limit):
        axis = axis_options[attempt % len(axis_options)]
        angle = attempt * math.pi * (3.0 - math.sqrt(5.0))
        initial = tuple(_rotate(tuple(point[axis_i] - center[axis_i] for axis_i in range(3)), angle, axis)
                        for point in base_initial)
        initial = tuple(tuple(point[axis_i] + center[axis_i] for axis_i in range(3)) for point in initial)
        positions = [tuple(point) for point in initial]
        frames: list[SynthesisFrame] = []

        for step in range(profile.steps + 1):
            progress = step / profile.steps
            spiral = progress
            # Smoothly increase the effective spiral coupling. Each step adds
            # a small, transient helical displacement while the sites converge.
            if step >= profile.steps - max(8, profile.steps // 5):
                stiffness = 0.58  # final stabilization interval
            else:
                stiffness = profile.relaxation * (0.30 + 0.70 * progress)
            wobble_amplitude = (1.0 - progress) * min(0.08, radius * 0.035)
            next_positions: list[tuple[float, float, float]] = []
            for index, (current, destination) in enumerate(zip(positions, target)):
                phase = 2.0 * math.pi * (progress * (1.0 + 0.11 * index)) + angle
                wobble = (
                    wobble_amplitude * math.cos(phase),
                    wobble_amplitude * math.sin(phase),
                    wobble_amplitude * math.sin(phase * 0.5),
                )
                next_positions.append(tuple(
                    current[axis_i] + stiffness * (destination[axis_i] - current[axis_i]) + wobble[axis_i]
                    for axis_i in range(3)
                ))
            positions = next_positions
            if step in {0, profile.steps} or step % max(1, profile.steps // 24) == 0:
                frames.append(SynthesisFrame(
                    frame=step + 1,
                    spiral_addition=spiral,
                    compression=1.08 - 0.08 * progress,
                    positions=tuple(tuple(round(v, 9) for v in point) for point in positions),
                ))

        residual = math.sqrt(sum(math.dist(a, b) ** 2 for a, b in zip(positions, target)) / count)
        candidate = (residual, tuple(frames), initial, attempt + 1)
        if best is None or residual < best[0]:
            best = candidate
        if residual <= profile.tolerance:
            break

    assert best is not None
    residual, frames, initial, used_attempts = best
    success = residual <= profile.tolerance
    # Store the idealized accepted target as the final state only on success.
    final_positions = target if success else tuple(tuple(value) for value in frames[-1].positions)
    if success and frames[-1].positions != target:
        frames = (*frames[:-1], SynthesisFrame(
            frame=profile.steps + 1, spiral_addition=1.0, compression=1.0,
            positions=target,
        ))
    model = {
        "profile": asdict(profile),
        "root": _node_model(layout, profile),
        "simulation": {
            "algorithm": "deterministic spiral-coupled damped geometric relaxation",
            "initial_condition": "stable separated Protium levitation configuration",
            "minimum_protium_gabarit_model_units": 1.0,
            "initial_pair_distance_model_units": 2.0,
            "spiral_addition": "monotonic 0..1 over simulation steps",
            "compression": "heuristic 1.08..1.0 (gradual envelope compression)",
            "expected_structure_is_source_defined": True,
            "force_law_status": "phenomenological surrogate; no calibrated ÆToE force law is supplied in seed v0.1.74",
            "success_criterion": f"RMS positional residual <= {profile.tolerance}",
        },
    }
    return HyperatomSynthesis(
        quality=profile.name,
        success=success,
        expected_structure=node.canonical,
        expected_atomahedron=layout.atomahedron,
        attempt_count=used_attempts,
        steps=profile.steps,
        residual=residual,
        initial_positions=tuple(tuple(round(v, 9) for v in point) for point in initial),
        final_positions=tuple(tuple(round(v, 9) for v in point) for point in final_positions),
        frames=frames,
        model=model,
    )


def simulation_fingerprint(payload: dict[str, Any]) -> str:
    """Stable hash of a simulation result, excluding non-deterministic timestamps."""
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "PROFILES", "SynthesisProfile", "SynthesisFrame", "HyperatomSynthesis",
    "simulate_hyperatom_synthesis", "simulation_fingerprint",
]
