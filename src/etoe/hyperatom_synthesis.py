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
    spin_axes: tuple[tuple[float, float, float], ...] = ()


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
                    "spin_axes": [list(value) for value in item.spin_axes],
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


def _levitation_vertices(count: int, minimum_pair_distance: float = 1.0) -> tuple[tuple[float, float, float], ...]:
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
            "initial_levitation_pair_distance": 1.0,
        },
        "clumping_layers": clumps,
        "atmospheric_layers": atmospheres,
        "children": [_node_model(child, profile) for child in layout.children],
    }


PHYSICS_MODELS = ("surrogate", "classic", "vanguard", "natural")


def default_protium_parameters(quality: str = "rough") -> dict[str, Any]:
    """Return explicit fallback parameters for a standalone Protium atom.

    The seed gives Protium a layered clump/atmosphere and spin, but it does not
    yet give calibrated radii, etheron counts, or constitutive coefficients.
    Values below are dimensionless modelling defaults; unknown physical values
    remain ``None`` rather than being fabricated.
    """
    try:
        profile = PROFILES[quality.casefold()]
    except (AttributeError, KeyError) as exc:
        raise ValueError("quality must be 'rough' or 'strict'") from exc

    clumps = [
        {
            "index": index + 1,
            "radius_factor": round(0.72 - 0.13 * index, 6),
            "deformation": round(0.15 + 0.045 * index, 6),
            "relative_mass_band": round(0.90 - 0.20 * index, 6),
            "kind": "deformable-ether-spiral-clump-layer",
        }
        for index in range(profile.clump_layers)
    ]
    atmospheres = [
        {
            "index": index + 1,
            "radius_factor": round(0.78 + 0.22 * (index + 1) / profile.atmosphere_layers, 6),
            "deformation": round(0.018 / (index + 1), 6),
            "relative_mass_band": round(0.30 / (index + 1), 6),
            "kind": "ether-spiral-atmospheric-layer",
        }
        for index in range(profile.atmosphere_layers)
    ]
    return {
        "schema": "etoe.protium-parameters.v1",
        "canonical": "H-1-1",
        "quality": profile.name,
        "atomic_mass_amu": 1,
        "maximum_gabarit_size_model_units": 1.0,
        "content_radius_model_units": 0.28,
        "outer_radius_model_units": 0.5,
        "atmosphere_thickness_model_units": 0.1682,
        "deformation_factor": 0.15,
        "compressibility_factor": 0.12,
        "spin": {
            "axis": [0.0, 0.0, 1.0],
            "direction": "right-handed about +Z in the local model frame",
            "magnitude": None,
            "status": "axis is a visualization convention; physical spin magnitude is unspecified",
        },
        "mass_etheron_units": None,
        "etheron_count": None,
        "ether_spiral_count": None,
        "unresolved_parameters": ["spin_magnitude", "mass_etheron_units", "etheron_count", "ether_spiral_count"],
        "clumping_layers": clumps,
        "atmospheric_layers": atmospheres,
        "parameter_origin": "default fallback; replace with saved standalone H-1-1 model when available",
    }



def build_protium_parameter_result(node: Any, layout: Any, *, quality: str = "rough") -> HyperatomSynthesis:
    """Create a parameter-only result for elementary Protium H-1-1.

    This is intentionally not a hyperatom synthesis: it describes the atomic
    body that parent hyperatoms consume as a reusable physical parameter model.
    """
    try:
        profile = PROFILES[quality.casefold()]
    except (AttributeError, KeyError) as exc:
        raise ValueError("quality must be 'rough' or 'strict'") from exc
    parameters = default_protium_parameters(quality)
    center = tuple(map(float, layout.center))
    root = _node_model(layout, profile)
    root.update({
        "maximum_gabarit_size_model_units": parameters["maximum_gabarit_size_model_units"],
        "content_radius_model_units": parameters["content_radius_model_units"],
        "outer_radius_model_units": parameters["outer_radius_model_units"],
        "atmosphere_thickness_model_units": parameters["atmosphere_thickness_model_units"],
        "deformation_factor": parameters["deformation_factor"],
        "spin": parameters["spin"],
        "mass_etheron_units": parameters["mass_etheron_units"],
        "etheron_count": parameters["etheron_count"],
        "ether_spiral_count": parameters["ether_spiral_count"],
        "unresolved_parameters": parameters["unresolved_parameters"],
        "protium_parameters": parameters,
        "clumping_layers": parameters["clumping_layers"],
        "atmospheric_layers": parameters["atmospheric_layers"],
    })
    model = {
        "profile": asdict(profile),
        "root": root,
        "protium_parameters": parameters,
        "simulation": {
            "algorithm": "elementary Protium parameter retrieval; no hyperatom synthesis performed",
            "physics": "not-applicable",
            "initial_condition": "standalone elementary Protium atom",
            "force_law_status": "not applicable to elementary-atom parameter retrieval",
        },
    }
    frame = SynthesisFrame(
        frame=1, spiral_addition=0.0, compression=1.0,
        positions=(tuple(round(value, 9) for value in center),),
        spin_axes=(tuple(parameters["spin"]["axis"]),),
    )
    return HyperatomSynthesis(
        quality=profile.name,
        success=True,
        expected_structure=node.canonical,
        expected_atomahedron="protium-body",
        attempt_count=0,
        steps=0,
        residual=0.0,
        initial_positions=(center,),
        final_positions=(center,),
        frames=(frame,),
        model=model,
    )


def _attach_protium_leaf_parameters(
    root_model: dict[str, Any],
    axes: Sequence[Sequence[float]],
    *,
    quality: str,
    spin_simulated: bool,
) -> None:
    """Attach the full standalone-Protium parameter schema to every H-1-1 leaf."""
    axis_index = 0
    fallback_axis = default_protium_parameters(quality)["spin"]["axis"]

    def visit(current: dict[str, Any]) -> None:
        nonlocal axis_index
        children = current.get("children", [])
        if children:
            for child in children:
                visit(child)
            return
        if not (current.get("canonical") in {"H-1-1", "H-1"}
                or (current.get("symbol") == "H" and current.get("atomic_mass_amu") == 1)):
            return
        parameters = default_protium_parameters(quality)
        axis = list(axes[axis_index]) if axis_index < len(axes) else list(fallback_axis)
        axis_index += 1
        parameters["spin"]["axis"] = [round(float(value), 9) for value in axis]
        parameters["spin"]["direction"] = "right-handed around the stored local spin axis"
        parameters["spin"]["status"] = (
            "final axis from the classic magnetic-torque integration; spin magnitude remains unspecified"
            if spin_simulated else
            "default local +Z visualization axis; spin dynamics are not modelled in surrogate mode"
        )
        current["spin"] = parameters["spin"]
        current["protium_parameters"] = parameters
        unresolved = [value for value in current.get("unresolved_parameters", []) if value != "spin"]
        if "spin_magnitude" not in unresolved:
            unresolved.append("spin_magnitude")
        current["unresolved_parameters"] = unresolved
        current["maximum_gabarit_size_model_units"] = 1.0
        current["local_maximum_gabarit_size_model_units"] = round(
            2.0 * float(current.get("outer_radius_model_units", 0.5)), 8
        )

    visit(root_model)


def _unit_vector(vector: Sequence[float]) -> tuple[float, float, float]:
    length = math.sqrt(sum(float(value) ** 2 for value in vector))
    if length <= 1e-12:
        return (0.0, 0.0, 1.0)
    return tuple(float(value) / length for value in vector)  # type: ignore[return-value]


def _cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (
        float(a[1]) * float(b[2]) - float(a[2]) * float(b[1]),
        float(a[2]) * float(b[0]) - float(a[0]) * float(b[2]),
        float(a[0]) * float(b[1]) - float(a[1]) * float(b[0]),
    )


def _dipole_force(
    moment_a: Sequence[float], moment_b: Sequence[float], displacement: Sequence[float],
) -> tuple[float, float, float]:
    """Dimensionless point-dipole force (without the adjustable coupling)."""
    distance = math.sqrt(sum(float(value) ** 2 for value in displacement))
    if distance <= 1e-9:
        return (0.0, 0.0, 0.0)
    direction = tuple(float(value) / distance for value in displacement)
    ma_r = sum(float(moment_a[i]) * direction[i] for i in range(3))
    mb_r = sum(float(moment_b[i]) * direction[i] for i in range(3))
    ma_mb = sum(float(moment_a[i]) * float(moment_b[i]) for i in range(3))
    scale = 0.012 / (distance ** 4)
    return tuple(
        scale * 3.0 * (
            ma_r * float(moment_b[i])
            + mb_r * float(moment_a[i])
            + ma_mb * direction[i]
            - 5.0 * ma_r * mb_r * direction[i]
        )
        for i in range(3)
    )


def _pair_distance_residual(
    positions: Sequence[Sequence[float]],
    reference: Sequence[Sequence[float]],
) -> float:
    errors: list[float] = []
    for left in range(len(positions)):
        for right in range(left + 1, len(positions)):
            actual = math.dist(positions[left], positions[right])
            expected = math.dist(reference[left], reference[right])
            errors.append((actual - expected) ** 2)
    return math.sqrt(sum(errors) / max(1, len(errors)))


def _simulate_classic(
    node: Any,
    layout: Any,
    profile: SynthesisProfile,
    *,
    attempts: int,
    gravity_weight: float,
    magnetic_weight: float,
) -> HyperatomSynthesis:
    """Damped pair-interaction model with gravity/antigravity and dipoles.

    The source hierarchy supplies pair equilibrium distances, not absolute
    target coordinates. Bodies start at unit-gabarit levitation spacing and
    evolve under pair forces. A short-range antigravity/contact term prevents
    interpenetration; magnetic dipoles add orientation-dependent forces and
    torques. Coefficients are dimensionless and deliberately exposed as model
    parameters because ÆToE seed v0.1.75 does not calibrate them.
    """
    reference = tuple(tuple(map(float, site.center)) for site in layout.protium_sites)
    count = len(reference)
    if count < 2:
        raise ValueError("classic hyperatom synthesis requires at least two Protium constituents")
    center = tuple(map(float, layout.center))
    initial_shape = _levitation_vertices(count, 1.0)
    base = tuple(tuple(center[axis] + point[axis] for axis in range(3)) for point in initial_shape)
    min_distance = 1.0  # one Protium maximum gabarit; each side contributes half
    reference_distances = [
        [math.dist(reference[i], reference[j]) for j in range(count)]
        for i in range(count)
    ]
    reference_distances = [
        [max(min_distance, value) if i != j else 0.0 for j, value in enumerate(row)]
        for i, row in enumerate(reference_distances)
    ]

    axis_options = (
        (0.0, 0.0, 1.0),
        (0.577350269, 0.577350269, 0.577350269),
        (0.0, 1.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.707106781, 0.0, 0.707106781),
        (0.0, 0.707106781, 0.707106781),
    )
    best: tuple[float, tuple[SynthesisFrame, ...], tuple[tuple[float, float, float], ...], int, float] | None = None
    steps = max(profile.steps * 8, 192)
    dt = 0.012 if profile.name == "rough" else 0.008
    spring = 160.0 * max(gravity_weight, 0.05)
    damping = 0.90 if profile.name == "rough" else 0.93

    for attempt in range(attempts):
        axis = axis_options[attempt % len(axis_options)]
        angle = attempt * math.pi * (3.0 - math.sqrt(5.0))
        initial = tuple(
            tuple(_rotate(tuple(point[i] - center[i] for i in range(3)), angle, axis)[i] + center[i]
                  for i in range(3))
            for point in base
        )
        positions = [list(point) for point in initial]
        velocities = [[0.0, 0.0, 0.0] for _ in range(count)]
        spin_axes = [
            _unit_vector((
                math.cos((index + 1) * 2.399963229728653 + angle),
                math.sin((index + 1) * 2.399963229728653 + angle),
                0.35 + 0.13 * ((index + attempt) % 4),
            ))
            for index in range(count)
        ]
        frames: list[SynthesisFrame] = []

        for step in range(steps + 1):
            progress = step / steps
            coupling = 0.20 + 0.80 * progress  # gradual addition of binding mass / ether spirals
            forces = [[0.0, 0.0, 0.0] for _ in range(count)]
            torques = [[0.0, 0.0, 0.0] for _ in range(count)]
            for left in range(count):
                for right in range(left + 1, count):
                    displacement = [positions[right][axis_i] - positions[left][axis_i] for axis_i in range(3)]
                    distance = math.sqrt(sum(value * value for value in displacement))
                    if distance <= 1e-8:
                        continue
                    direction = [value / distance for value in displacement]
                    rest = reference_distances[left][right]
                    # Gravitation attracts above unit spacing; antigravitation
                    # repels below it. Both vanish at the Protium gabarit.
                    ga_scalar = gravity_weight * coupling * (1.0 / distance**2 - 1.0 / distance**4)
                    # A hierarchy-derived bond potential preserves only pair
                    # separations; absolute target positions are never imposed.
                    bond_scalar = spring * coupling * (distance - rest)
                    contact_scalar = -120.0 * max(0.0, min_distance - distance)
                    ga_total = ga_scalar + bond_scalar + contact_scalar
                    force = [ga_total * value for value in direction]
                    dipole = _dipole_force(spin_axes[left], spin_axes[right], displacement)
                    for axis_i in range(3):
                        force[axis_i] += magnetic_weight * coupling * dipole[axis_i]
                        forces[left][axis_i] += force[axis_i]
                        forces[right][axis_i] -= force[axis_i]

                    # Dipole-field torque rotates the spin axes toward compatible
                    # directions. It is not a calibrated gyromagnetic equation.
                    ma_r = sum(spin_axes[left][i] * direction[i] for i in range(3))
                    field_right = [
                        (3.0 * sum(spin_axes[right][k] * direction[k] for k in range(3)) * direction[i]
                         - spin_axes[right][i]) / distance**3
                        for i in range(3)
                    ]
                    field_left = [
                        (3.0 * ma_r * direction[i] - spin_axes[left][i]) / distance**3
                        for i in range(3)
                    ]
                    torque_left = _cross(spin_axes[left], field_right)
                    torque_right = _cross(spin_axes[right], field_left)
                    for axis_i in range(3):
                        torques[left][axis_i] += magnetic_weight * torque_left[axis_i]
                        torques[right][axis_i] += magnetic_weight * torque_right[axis_i]

            for index in range(count):
                for axis_i in range(3):
                    velocities[index][axis_i] = (
                        velocities[index][axis_i] + forces[index][axis_i] * dt
                    ) * damping
                    positions[index][axis_i] += velocities[index][axis_i] * dt
                spin_axes[index] = _unit_vector(tuple(
                    spin_axes[index][j] + torques[index][j] * dt * 0.25 for j in range(3)
                ))

            # Remove numerical centre-of-mass drift without imposing a shape.
            current_center = [sum(point[i] for point in positions) / count for i in range(3)]
            for point in positions:
                for axis_i in range(3):
                    point[axis_i] += center[axis_i] - current_center[axis_i]

            if step in {0, steps} or step % max(1, steps // 24) == 0:
                frames.append(SynthesisFrame(
                    frame=step + 1,
                    spiral_addition=progress,
                    compression=1.0 - 0.08 * progress,
                    positions=tuple(tuple(round(value, 9) for value in point) for point in positions),
                    spin_axes=tuple(tuple(round(value, 9) for value in axis_value) for axis_value in spin_axes),
                ))

        final_positions = tuple(tuple(point) for point in positions)
        residual = _pair_distance_residual(final_positions, reference)
        actual_minimum = min(
            math.dist(final_positions[i], final_positions[j])
            for i in range(count) for j in range(i + 1, count)
        )
        collision_penalty = max(0.0, min_distance - actual_minimum)
        score = residual + collision_penalty * 8.0
        candidate = (score, tuple(frames), initial, attempt + 1, actual_minimum)
        if best is None or candidate[0] < best[0]:
            best = candidate
        if residual <= profile.tolerance and collision_penalty <= 1e-6:
            break

    assert best is not None
    score, frames, initial, used_attempts, actual_minimum = best
    final_positions = frames[-1].positions
    residual = _pair_distance_residual(final_positions, reference)
    success = residual <= profile.tolerance and actual_minimum >= min_distance - 1e-5
    root_model = _node_model(layout, profile)
    _attach_protium_leaf_parameters(
        root_model, frames[-1].spin_axes, quality=profile.name, spin_simulated=True,
    )
    model = {
        "profile": asdict(profile),
        "root": root_model,
        "simulation": {
            "algorithm": "damped pair-force integration with hierarchy-derived equilibrium distances",
            "candidate_structure_policy": "accept only the source-defined pair-distance topology; alternate nuclear compositions are not inferred",
            "physics": "classic",
            "initial_condition": "stable Protium levitation; nearest centre distance equals sum of half-gabarits",
            "minimum_protium_gabarit_model_units": 1.0,
            "initial_pair_distance_model_units": 1.0,
            "spiral_addition": "binding coupling increases monotonically from 0.20 to 1.0",
            "gravity_antigravity": {
                "weight": gravity_weight,
                "law": "dimensionless attractive r^-2 and repulsive r^-4 terms with equilibrium at unit gabarit",
            },
            "magnetic_dipole": {
                "weight": magnetic_weight,
                "law": "dimensionless point-dipole force and spin-axis torque",
            },
            "nonpenetration": "short-range antigravity/contact penalty enforces centre distance >= 1 model unit",
            "hierarchy_binding": "pair-distance potentials derived from the source-defined hierarchy; no absolute target coordinates",
            "source_atomahedron_geometry_match": bool(success),
            "accepted_atomahedron": layout.atomahedron if success else "unclassified",
            "pair_distance_residual": round(residual, 10),
            "minimum_final_pair_distance": round(actual_minimum, 10),
            "force_law_status": "phenomenological classic interaction; dimensionless coefficients are not experimentally calibrated",
            "success_criterion": f"pair-distance RMS <= {profile.tolerance} and no interpenetration",
        },
    }
    return HyperatomSynthesis(
        quality=profile.name,
        success=success,
        expected_structure=node.canonical,
        expected_atomahedron=layout.atomahedron,
        attempt_count=used_attempts,
        steps=steps,
        residual=residual,
        initial_positions=tuple(tuple(round(value, 9) for value in point) for point in initial),
        final_positions=tuple(tuple(round(value, 9) for value in point) for point in final_positions),
        frames=frames,
        model=model,
    )


def simulate_hyperatom_synthesis(
    node: Any,
    layout: Any,
    *,
    quality: str = "rough",
    attempts: int | None = None,
    physics: str = "surrogate",
    gravity_weight: float = 0.85,
    magnetic_weight: float = 0.15,
) -> HyperatomSynthesis:
    """Simulate hierarchical hyperatom synthesis with selectable interactions.

    ``surrogate`` retains the deterministic source-geometry relaxation.
    ``classic`` integrates the dimensionless gravity/antigravity and magnetic
    dipole interactions. ``vanguard`` and ``natural`` are reserved model
    families and fail explicitly until their force laws are specified.
    """
    try:
        profile = PROFILES[quality.casefold()]
    except (AttributeError, KeyError) as exc:
        raise ValueError("quality must be 'rough' or 'strict'") from exc
    normalized_physics = str(physics).casefold()
    if normalized_physics not in PHYSICS_MODELS:
        raise ValueError(f"physics must be one of: {', '.join(PHYSICS_MODELS)}")
    if normalized_physics in {"vanguard", "natural"}:
        raise NotImplementedError(
            f"physics={normalized_physics!r} is reserved; only 'surrogate' and 'classic' have executable models"
        )
    if not math.isfinite(gravity_weight) or gravity_weight < 0:
        raise ValueError("gravity_weight must be a finite non-negative number")
    if not math.isfinite(magnetic_weight) or magnetic_weight < 0:
        raise ValueError("magnetic_weight must be a finite non-negative number")
    if gravity_weight + magnetic_weight <= 0:
        raise ValueError("at least one of gravity_weight or magnetic_weight must be positive")
    attempt_limit = profile.attempts if attempts is None else int(attempts)
    if attempt_limit < 1:
        raise ValueError("attempts must be positive")

    target = tuple(tuple(map(float, site.center)) for site in layout.protium_sites)
    count = len(target)
    if count == 0:
        raise ValueError("cannot synthesize a hyperatom without Protium constituents")
    if count == 1:
        raise ValueError("a single Protium is an elementary atom, not a hyperatom synthesis")
    if normalized_physics == "classic":
        result = _simulate_classic(
            node, layout, profile, attempts=attempt_limit,
            gravity_weight=gravity_weight, magnetic_weight=magnetic_weight,
        )
        return result

    center = tuple(map(float, layout.center))
    base_initial = _levitation_vertices(count, 1.0)
    base_initial = tuple(
        tuple(center[axis] + point[axis] for axis in range(3))
        for point in base_initial
    )

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
            if step == profile.steps:
                stiffness = 1.0
            elif step >= profile.steps - max(8, profile.steps // 5):
                stiffness = 0.58
            else:
                stiffness = profile.relaxation * (0.30 + 0.70 * progress)
            wobble_amplitude = (1.0 - progress) * min(0.08, 0.035)
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
                    spiral_addition=progress,
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
    final_positions = tuple(tuple(value) for value in frames[-1].positions)
    root_model = _node_model(layout, profile)
    _attach_protium_leaf_parameters(
        root_model, (), quality=profile.name, spin_simulated=False,
    )
    model = {
        "profile": asdict(profile),
        "root": root_model,
        "simulation": {
            "algorithm": "deterministic spiral-coupled damped geometric relaxation",
            "physics": "surrogate",
            "initial_condition": "stable separated Protium levitation configuration",
            "minimum_protium_gabarit_model_units": 1.0,
            "initial_pair_distance_model_units": 1.0,
            "spiral_addition": "monotonic 0..1 over simulation steps",
            "compression": "heuristic 1.08..1.0 (gradual envelope compression)",
            "expected_structure_is_source_defined": True,
            "force_law_status": "phenomenological surrogate geometry; no calibrated ÆToE force law is applied",
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
    "PHYSICS_MODELS", "default_protium_parameters", "build_protium_parameter_result",
    "simulate_hyperatom_synthesis", "simulation_fingerprint",
]
