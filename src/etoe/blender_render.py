"""Blender background entry point for ÆToE hyperatom 3D generation.

Run by the etoe CLI as::

    blender --background --python blender_render.py -- --data-root ... --element C

This file is intentionally executable by Blender's embedded Python. It adds
its source/install root to ``sys.path`` before importing the normal etoe
translation, selection, style, and filename code.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import traceback
import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


# When Blender runs a package file directly, sys.path[0] is src/etoe rather
# than src. Add src so the exact package version containing this script loads.
_PACKAGE_PARENT = Path(__file__).resolve().parent.parent
if str(_PACKAGE_PARENT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_PARENT))

from etoe.blender3d import (  # noqa: E402
    BlenderRenderError,
    Hyperatom3DNode,
    build_hyperatom_3d_tree,
    hyperatom_3d_paths,
    select_hyperatoms,
    hyperatom_dependency_order,
    write_toml_sidecar,
)
from etoe.hyperatom_translation import HyperatomTranslator  # noqa: E402
from etoe.style import configure_styles, chemical_category_slug, resolve_style  # noqa: E402
from etoe.hyperatom_synthesis import (  # noqa: E402
    PHYSICS_MODELS,
    PROFILES,
    HyperatomSynthesis,
    default_protium_parameters,
    build_protium_parameter_result,
    simulate_hyperatom_synthesis,
    simulation_fingerprint,
)
from etoe.incremental import snapshot_dependencies  # noqa: E402


def _parse_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render ÆToE hyperatoms to Blender .blend files and PNG snapshots")
    parser.add_argument("--data-root", type=Path, default=Path("data/atom/element"))
    parser.add_argument("--hyperatom", action="append", default=[], help="Canonical hyperatom notation or semantic id (repeatable)")
    parser.add_argument("--element", action="append", default=[], help="Element symbol (repeatable)")
    parser.add_argument("--elements", default="", help="Comma-separated element symbols")
    parser.add_argument("--category", action="append", default=[], help="Chemical category slug (repeatable)")
    parser.add_argument("--all-elements", action="store_true", help="Render all source-defined hyperatoms for every element")
    parser.add_argument("--quality", choices=("rough", "strict"), default="rough")
    parser.add_argument("--physics", choices=PHYSICS_MODELS, default="surrogate")
    parser.add_argument("--gravity-weight", type=float, default=0.85)
    parser.add_argument("--magnetic-weight", type=float, default=0.15)
    parser.add_argument("--show-protium-axis", action="store_true")
    parser.add_argument("--show-protium-spin", action="store_true")
    parser.add_argument("--representation", choices=("surface", "point-cloud", "wireframe"), default="surface")
    parser.add_argument("--output", type=Path, default=None, help="Explicit .blend path (only for one hyperatom)")
    parser.add_argument("--output-root", type=Path, default=None, help="Override the standard element-directory output root")
    parser.add_argument("--style-dir", type=Path, default=None)
    parser.add_argument("--mode", choices=("Light", "Dark"), default="Dark")
    parser.add_argument("--engine", choices=("eevee", "cycles"), default="eevee")
    parser.add_argument("--resolution", type=int, default=1200)
    parser.add_argument("--samples", type=int, default=None)
    parser.add_argument("--shell-layers", type=int, default=None)
    parser.add_argument("--attempts", type=int, default=None)
    parser.add_argument("--max-depth", type=int, default=0, help="Maximum recursive atom depth (0 = unlimited)")
    parser.add_argument("--labels", action="store_true", help="Add small labels to all hierarchy levels")
    parser.add_argument("--transparent-background", action="store_true")
    parser.add_argument("--rebuild", "--overwrite", dest="rebuild", action="store_true")
    return parser


def blender_script_args(argv: Sequence[str] | None = None) -> list[str]:
    """Extract only the Python script's arguments from Blender's argv."""
    values = list(sys.argv if argv is None else argv)
    if "--" not in values:
        return []
    return values[values.index("--") + 1 :]


def _hex_rgb(value: str) -> tuple[float, float, float]:
    text = value.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(char * 2 for char in text)
    if len(text) != 6:
        return (0.1, 0.1, 0.1)
    try:
        return tuple(int(text[index:index + 2], 16) / 255.0 for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return (0.1, 0.1, 0.1)


def _set_transparency(material: Any, opacity: float) -> None:
    material.diffuse_color = (*material.diffuse_color[:3], opacity)
    if not material.use_nodes:
        material.use_nodes = True
    principled = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if principled is not None:
        base = principled.inputs.get("Base Color")
        alpha = principled.inputs.get("Alpha")
        if base is not None:
            base.default_value = (*material.diffuse_color[:3], opacity)
        if alpha is not None:
            alpha.default_value = opacity
    # Blender 4.x uses surface_render_method; older releases use blend_method.
    if hasattr(material, "surface_render_method"):
        try:
            material.surface_render_method = "DITHERED"
        except (TypeError, ValueError):
            pass
    elif hasattr(material, "blend_method"):
        try:
            material.blend_method = "BLEND"
        except (TypeError, ValueError):
            pass
    if hasattr(material, "show_transparent_back"):
        material.show_transparent_back = True


def _new_material(name: str, color: str, opacity: float, roughness: float = 0.45, metalness: float = 0.05) -> Any:
    import bpy

    rgb = _hex_rgb(color)
    material = bpy.data.materials.new(name=name)
    material.diffuse_color = (*rgb, opacity)
    material.use_nodes = True
    principled = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if principled is not None:
        principled.inputs["Base Color"].default_value = (*rgb, opacity)
        principled.inputs["Alpha"].default_value = opacity
        principled.inputs["Roughness"].default_value = roughness
        principled.inputs["Metallic"].default_value = metalness
        transmission = principled.inputs.get("Transmission Weight") or principled.inputs.get("Transmission")
        if transmission is not None:
            transmission.default_value = 0.08
    _set_transparency(material, opacity)
    return material


def _material_for_node(node: Hyperatom3DNode, mode: str, layer_index: int, shell_layers: int) -> Any:
    category = node.chemical_category or chemical_category_slug(node.symbol)
    style = resolve_style(
        "3D", "entity", classes=(f"category-{category}",),
        mode=mode, source="3D", target="3D",
    )
    opacity = float(style.get("opacity", 0.16))
    # Each successive atmospheric layer becomes lighter and less opaque. These
    # are illustrative rendering layers, not measured ÆToE shell radii/masses.
    layer_opacity = max(0.025, min(0.24, opacity * (0.24 / (1 + 0.42 * layer_index))))
    if not node.resolved:
        color = "#B0B7C3"
    else:
        color = str(style.get("color", "#60A5FA"))
    return _new_material(
        f"ÆToE_{_safe_id(node.canonical)}_atmosphere_{layer_index + 1}",
        color,
        layer_opacity,
        float(style.get("roughness", 0.52)),
        float(style.get("metalness", 0.08)),
    )


def _safe_id(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value)[:64] or "hyperatom"


def _link_object(obj: Any, collection: Any) -> None:
    collection.objects.link(obj)


@dataclass(frozen=True, slots=True)
class ProtiumSite:
    """A terminal Protium content site in root-hyperatom coordinates."""

    center: tuple[float, float, float]
    radius: float
    depth: int
    deformation: float


@dataclass(frozen=True, slots=True)
class HyperatomLayout:
    """Bottom-up spatial envelope for one node in the semantic composition tree."""

    node: Hyperatom3DNode
    depth: int
    center: tuple[float, float, float]
    content_radius: float
    atmosphere_thickness: float
    outer_radius: float
    deformation: float
    atomahedron: str
    children: tuple["HyperatomLayout", ...] = ()
    protium_sites: tuple[ProtiumSite, ...] = ()
    terminal: bool = False
    is_protium: bool = False


def _vec_sub(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (float(a[0]) - float(b[0]), float(a[1]) - float(b[1]), float(a[2]) - float(b[2]))


def _vec_dot(a: Sequence[float], b: Sequence[float]) -> float:
    return float(a[0]) * float(b[0]) + float(a[1]) * float(b[1]) + float(a[2]) * float(b[2])


def _vec_length(value: Sequence[float]) -> float:
    return math.sqrt(_vec_dot(value, value))


def _vec_scale(value: Sequence[float], factor: float) -> tuple[float, float, float]:
    return (float(value[0]) * factor, float(value[1]) * factor, float(value[2]) * factor)


def _atomahedron_kind(protium_count: int) -> str:
    """Name the atomhedral form by terminal Protium count, not direct child arity.

    This distinction is essential for T-3-(2'1): it has two immediate children
    (D and H), but three Protium constituents and therefore a triatomahedron.
    He-4-(2'2) similarly has two direct D children but four Protium vertices.
    """
    return {
        1: "protium-body",
        2: "diatomahedron",
        3: "triatomahedron",
        4: "tetraatomahedron",
        5: "pentaatomahedron",
    }.get(protium_count, "hypercentric-atomahedron")


def _child_positions(arity: int) -> tuple[tuple[float, float, float], ...]:
    """Return normalized vertices for an atomahedron with *terminal* atom sites.

    For a composite such as tritium or helium-4, callers pass the total number
    of Protium leaves, not ``len(node.children)``. Child sub-hyperatoms retain
    their own nested grouping when those sites are assigned to the tree.
    """
    if arity <= 0:
        return ()
    if arity == 1:
        return ((0.0, 0.0, 0.0),)
    if arity == 2:
        return ((-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    if arity == 3:
        return ((-0.8660254, -0.5, 0.0), (0.8660254, -0.5, 0.0), (0.0, 1.0, 0.0))
    if arity == 4:
        scale = 1.0 / math.sqrt(3.0)
        return tuple((x * scale, y * scale, z * scale) for x, y, z in (
            (1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1),
        ))
    if arity == 5:
        radial = math.sqrt(8.0 / 9.0)
        return (
            (0.0, 0.0, 1.0), (0.0, 0.0, -1.0),
            (radial, 0.0, -1.0 / 3.0),
            (-radial / 2.0, radial * math.sqrt(3.0) / 2.0, -1.0 / 3.0),
            (-radial / 2.0, -radial * math.sqrt(3.0) / 2.0, -1.0 / 3.0),
        )
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    points = []
    for index in range(arity):
        z = 1.0 - 2.0 * (index + 0.5) / arity
        radial = math.sqrt(max(0.0, 1.0 - z * z))
        angle = golden_angle * index
        points.append((radial * math.cos(angle), radial * math.sin(angle), z))
    return tuple(points)


def _terminal_count(node: Hyperatom3DNode, depth: int = 0, max_depth: int = 0) -> int:
    if not node.children or (max_depth > 0 and depth >= max_depth):
        return 1
    return sum(_terminal_count(child, depth + 1, max_depth) for child in node.children)


def _protium_depths(node: Hyperatom3DNode, depth: int = 0) -> tuple[int, ...]:
    """Return the hierarchy depths of all terminal Protium nodes, in tree order."""
    if not node.children:
        return (depth,)
    return tuple(value for child in node.children for value in _protium_depths(child, depth + 1))


def build_hyperatom_layout(
    node: Hyperatom3DNode,
    *,
    max_depth: int = 0,
    parameter_models: Mapping[str, Mapping[str, Any]] | None = None,
) -> HyperatomLayout:
    """Build a bottom-up geometric plan while preserving the semantic tree.

    Terminal Protium sites are first assigned vertices of the appropriate
    atomahedron. The recursive reduction then encloses already measured child
    layouts in each parent's atmospheric envelope. Thus D, T, Ht and He-4 are
    laid out as 2-, 3-, 3- and 4-Protium structures respectively, even though
    T and He-4 each have only two immediate semantic children.
    """
    total_sites = _terminal_count(node, max_depth=max_depth)
    positions = _child_positions(total_sites)
    # Scale the normalized atomhedral vertices to a compact but visible unit.
    if total_sites <= 1:
        span = 0.0
    else:
        nearest = min(
            math.dist(positions[left], positions[right])
            for left in range(total_sites) for right in range(left + 1, total_sites)
        )
        # The Protium maximum gabarit is the unit length. Keep at least 1.15
        # units between centres in the final, relaxed configuration so that
        # separately modelled clump bodies cannot geometrically interpenetrate.
        span = 1.15 / max(nearest, 1e-9)
    target_centers = tuple(_vec_scale(point, span) for point in positions)
    cursor = 0
    parameter_models = parameter_models or {}
    protium_parameters = dict(default_protium_parameters("rough"))
    protium_parameters.update(parameter_models.get("H-1-1", {}))
    # A standalone Protium's maximum gabarit is exactly one model unit; inner
    # hierarchy levels compress it by depth rather than by the parent's atom count.
    base_protium_radius = float(protium_parameters.get("content_radius_model_units", 0.28))
    base_protium_atmosphere = float(protium_parameters.get("atmosphere_thickness_model_units", 0.1682))
    base_protium_deformation = float(protium_parameters.get("deformation_factor", 0.15))

    def measure(current: Hyperatom3DNode, depth: int) -> HyperatomLayout:
        nonlocal cursor
        terminal = not current.children or (max_depth > 0 and depth >= max_depth)
        if terminal:
            center = target_centers[cursor]
            cursor += 1
            # Protium is progressively compressed with hierarchy depth. The
            # deformation grows at the same time, so inner Protia are neither
            # rigid nor geometrically interchangeable with outer ones.
            radius = base_protium_radius * (0.92 ** depth)
            deformation = min(0.48, base_protium_deformation + 0.075 * depth)
            atmosphere = max(0.035, base_protium_atmosphere * (0.92 ** depth))
            return HyperatomLayout(
                node=current,
                depth=depth,
                center=center,
                content_radius=radius,
                atmosphere_thickness=atmosphere,
                outer_radius=radius * (1.0 + deformation * 1.10 + 0.02) + atmosphere,
                deformation=deformation,
                atomahedron="protium-body",
                children=(),
                protium_sites=(ProtiumSite(center, radius, depth, deformation),),
                terminal=True,
                is_protium=not current.children,
            )

        # Bottom-up: fully measure every sub-hyperatom before sizing the parent.
        children = tuple(measure(child, depth + 1) for child in current.children)
        weight_total = sum(len(child.protium_sites) for child in children) or len(children)
        center = tuple(
            sum(child.center[axis] * (len(child.protium_sites) or 1) for child in children) / weight_total
            for axis in range(3)
        )
        content_radius = max(
            (_vec_length(_vec_sub(child.center, center)) + child.outer_radius for child in children),
            default=base_protium_radius,
        )
        atmosphere = max(0.055, content_radius * (0.105 + 0.012 * min(depth, 6)))
        sites = tuple(site for child in children for site in child.protium_sites)
        deformation = min(0.34, 0.065 + 0.028 * depth + 0.012 * len(children))
        saved_model = parameter_models.get(current.canonical)
        if saved_model:
            # Consume the child's physical parameter result, but rebuild its
            # Blender geometry from this hierarchy rather than importing .blend.
            content_radius = float(saved_model.get("content_radius_model_units", content_radius))
            atmosphere = float(saved_model.get("atmosphere_thickness_model_units", atmosphere))
            deformation = float(saved_model.get("deformation_factor", deformation))
        return HyperatomLayout(
            node=current,
            depth=depth,
            center=center,
            content_radius=content_radius,
            atmosphere_thickness=atmosphere,
            outer_radius=(content_radius + atmosphere) * 1.045,
            deformation=deformation,
            atomahedron=_atomahedron_kind(len(sites)),
            children=children,
            protium_sites=sites,
            terminal=False,
            is_protium=False,
        )

    return measure(node, 0)


def _surface_warp(direction: Sequence[float], phase: float, amount: float) -> float:
    """Smooth deterministic angular deformation for organic, non-spherical surfaces."""
    x, y, z = (float(direction[0]), float(direction[1]), float(direction[2]))
    wave_a = math.sin(3.1 * x + 2.3 * y - 1.7 * z + phase)
    wave_b = math.cos(2.4 * x - 3.6 * y + 2.8 * z - phase * 0.73)
    wave_c = math.sin(5.0 * z + 1.8 * x * y + phase * 1.31)
    return amount * (0.42 * wave_a + 0.33 * wave_b + 0.25 * wave_c)


def _make_deformed_surface(
    name: str,
    center: Sequence[float],
    radius_at: Callable[[Sequence[float]], float],
    material: Any,
    collection: Any,
    *,
    deformation: float,
    phase: float,
    subdivisions: int = 3,
    toroidality: float = 0.0,
) -> Any:
    """Create a smooth but deliberately non-spherical organic icosphere mesh."""
    import bpy
    import bmesh
    from mathutils import Vector

    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=max(2, int(subdivisions)), radius=1.0)
    for vertex in bm.verts:
        direction = vertex.co.normalized()
        unit = (float(direction.x), float(direction.y), float(direction.z))
        base_radius = max(0.001, float(radius_at(unit)))
        warp = _surface_warp(unit, phase, deformation)
        # A low-amplitude equatorial waist/bulge makes the body "doughnut-like"
        # without opening a mathematically toroidal hole or losing a closed shell.
        warp += max(0.0, min(0.22, toroidality)) * (0.55 - 0.95 * unit[2] * unit[2])
        # A small directional squeeze makes every body anisotropic in addition
        # to the smooth harmonic deformation; no generated body is a strict sphere.
        squeeze = 1.0 + 0.035 * deformation * (unit[0] * unit[1] - 0.5 * unit[2])
        vertex.co = direction * (base_radius * (1.0 + warp) * squeeze)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    _link_object(obj, collection)
    obj.location = Vector(center)
    if material is not None:
        obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def _support_radius(layout: HyperatomLayout, direction: Sequence[float]) -> float:
    """Directional support of the already-built child envelopes."""
    if not layout.children:
        # Bound the deformed terminal body, not its undeformed base radius.
        return layout.content_radius * (1.0 + layout.deformation * 1.10 + 0.02)
    return max(
        _vec_dot(direction, _vec_sub(child.center, layout.center)) + child.outer_radius
        for child in layout.children
    )


def _material_for_content(node: Hyperatom3DNode, mode: str, layer_index: int = 0) -> Any:
    style = resolve_style(
        "3D", "entity", classes=(f"category-{node.chemical_category or 'unknowns'}",),
        mode=mode, source="3D", target="3D",
    )
    color = str(style.get("outline", style.get("color", "#60A5FA")))
    return _new_material(
        f"ÆToE_{_safe_id(node.canonical)}_deformable_content",
        color,
        max(0.12, 0.58 / (1.0 + 0.45 * layer_index)),
        float(style.get("roughness", 0.52)),
        float(style.get("metalness", 0.08)),
    )


def _make_node_collection(node: Hyperatom3DNode, parent: Any, layout: HyperatomLayout) -> Any:
    import bpy

    label = f"{node.canonical} [{layout.atomahedron}]"
    collection = bpy.data.collections.new(label)
    parent.children.link(collection)
    collection["etoe.canonical"] = node.canonical
    collection["etoe.designation"] = node.designation
    collection["etoe.depth"] = int(layout.depth)
    collection["etoe.atomahedron"] = layout.atomahedron
    collection["etoe.protium_count"] = len(layout.protium_sites)
    collection["etoe.construction"] = "bottom-up"
    return collection


def _render_node_bottom_up(
    layout: HyperatomLayout,
    parent_collection: Any,
    *,
    mode: str,
    shell_layers: int,
    labels: bool,
    mesh_subdivisions: int = 3,
    clump_layers: int = 2,
    animation_tracks: list[tuple[Any, int, int, float]] | None = None,
    atmosphere_tracks: list[Any] | None = None,
    site_offset: int = 0,
    max_depth: int = 0,
) -> Any:
    """Rebuild descendants bottom-up from physical parameters; never import child .blend files."""
    import bpy
    node = layout.node
    node_collection = _make_node_collection(node, parent_collection, layout)
    animation_tracks = animation_tracks if animation_tracks is not None else []
    atmosphere_tracks = atmosphere_tracks if atmosphere_tracks is not None else []

    visual_leaf = bool(max_depth > 0 and layout.depth >= max_depth and layout.children)
    child_collections = []
    child_offset = site_offset
    if not visual_leaf:
        for child_layout in layout.children:
            child_count = len(child_layout.protium_sites)
            # Child synthesis manifests supply model parameters, not Blender scene
            # objects. Every child graph is rebuilt in this parent scene so that
            # geometry stays editable and the hierarchy remains a true object tree.
            child_collections.append(_render_node_bottom_up(
                child_layout,
                node_collection,
                mode=mode,
                shell_layers=shell_layers,
                labels=labels,
                mesh_subdivisions=mesh_subdivisions,
                clump_layers=clump_layers,
                animation_tracks=animation_tracks,
                atmosphere_tracks=atmosphere_tracks,
                site_offset=child_offset,
                max_depth=max_depth,
            ))
            child_offset += child_count

    phase = sum((index + 1) * ord(char) for index, char in enumerate(node.canonical)) * 0.017

    if layout.terminal or visual_leaf:
        # Terminal Protium bodies and max-depth collapsed sub-hyperatoms both
        # receive layered clumps. A collapsed composite is one visual object,
        # but its full descendant Protium sites remain in the physical solver.
        for clump_index in range(clump_layers):
            factor = 1.0 - 0.19 * clump_index
            content_material = _material_for_content(node, mode, clump_index)
            content_obj = _make_deformed_surface(
                f"{_safe_id(node.canonical)}_L{layout.depth}_clump_{clump_index + 1}",
                layout.center,
                lambda _direction, radius=layout.content_radius * factor: radius,
                content_material,
                node_collection,
                deformation=min(0.55, layout.deformation + 0.035 * clump_index),
                phase=phase + clump_index * 0.29,
                subdivisions=mesh_subdivisions,
                toroidality=0.055 + 0.025 * clump_index,
            )
            content_obj["etoe.role"] = "deformable-protium-clumping-layer" if layout.is_protium else "deformable-truncated-subhyperatom-layer"
            content_obj["etoe.layer_index"] = clump_index + 1
            content_obj["etoe.hierarchy_depth"] = layout.depth
            content_obj["etoe.compression_factor"] = round(0.92 ** layout.depth, 6)
            if clump_index == 0:
                track_count = len(layout.protium_sites) if visual_leaf else 1
                animation_tracks.append((content_obj, site_offset, track_count, 1.0))

    # Each composite atmosphere encloses the already-created child results.
    outermost_shell = None
    for layer_index in range(shell_layers):
        fraction = (layer_index + 1) / shell_layers
        layer_margin = layout.atmosphere_thickness * (0.45 + 0.55 * fraction)
        material = _material_for_node(node, mode, layer_index, shell_layers)
        shell = _make_deformed_surface(
            f"{_safe_id(node.canonical)}_L{layout.depth}_atmosphere_{layer_index + 1}",
            layout.center,
            lambda direction, margin=layer_margin: _support_radius(layout, direction) + margin,
            material,
            node_collection,
            deformation=min(0.035, layout.deformation * 0.12),
            phase=phase + (layer_index + 1) * 0.41,
            subdivisions=mesh_subdivisions,
            toroidality=0.018,
        )
        shell["etoe.role"] = "atmospheric-layer"
        shell["etoe.layer_index"] = layer_index + 1
        shell["etoe.hierarchy_depth"] = layout.depth
        shell["etoe.atomahedron"] = layout.atomahedron
        if layer_index < shell_layers - 1:
            atmosphere_tracks.append(shell)
        outermost_shell = shell

    # Preserve local transform inheritance for generated child objects in the nested hierarchy.
    if outermost_shell is not None:
        for child_collection in child_collections:
            if child_collection is None:
                continue
            for child_object in list(child_collection.objects):
                world_matrix = child_object.matrix_world.copy()
                child_object.parent = outermost_shell
                child_object.matrix_world = world_matrix

    if labels:
        _make_label(
            node.designation,
            layout.center,
            layout.outer_radius,
            layout.depth,
            mode,
            node_collection,
        )
    return node_collection


def _apply_geometry_representation(bpy: Any, root_collection: Any, representation: str) -> None:
    """Apply a renderable surface, sampled point-cloud, or wireframe style.

    Point-cloud mode represents a bounded, deterministic subset of the surface
    vertices as joined low-poly beads. Wireframe mode adds Blender's native
    Wireframe modifier, so the saved file remains editable.
    """
    normalized = str(representation).casefold()
    if normalized == "surface":
        return
    import bmesh
    from mathutils import Matrix

    collections = [root_collection]
    while collections:
        collection = collections.pop()
        collections.extend(list(collection.children))
        for obj in list(collection.objects):
            if obj.type != "MESH":
                continue
            if normalized == "wireframe":
                modifier = obj.modifiers.new(name="ÆToE_Wireframe", type="WIREFRAME")
                extent = max(float(value) for value in obj.dimensions) if obj.dimensions else 1.0
                modifier.thickness = max(0.0015, extent * 0.006)
                modifier.use_even_offset = True
                modifier.use_replace = True
                continue
            if normalized != "point-cloud":
                raise BlenderRenderError(f"Unsupported geometry representation {representation!r}.")
            vertices = list(obj.data.vertices)
            if not vertices:
                continue
            stride = max(1, math.ceil(len(vertices) / 320))
            extent = max((float(value) for value in obj.dimensions), default=1.0)
            point_radius = max(0.002, extent * 0.012)
            bm = bmesh.new()
            try:
                for vertex in vertices[::stride]:
                    bmesh.ops.create_icosphere(
                        bm, subdivisions=1, radius=point_radius,
                        matrix=Matrix.Translation(vertex.co),
                    )
                cloud_mesh = bpy.data.meshes.new(obj.data.name + "_point_cloud")
                bm.to_mesh(cloud_mesh)
                cloud_mesh.update()
            finally:
                bm.free()
            old_mesh = obj.data
            for material in old_mesh.materials:
                cloud_mesh.materials.append(material)
            obj.data = cloud_mesh
            obj.name = obj.name + "_point_cloud"
            if old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh)


def _animate_synthesis(
    bpy: Any,
    synthesis: HyperatomSynthesis,
    animation_tracks: Sequence[tuple[Any, int, int, float]],
    atmosphere_tracks: Sequence[Any] = (),
) -> None:
    """Animate subatom bodies and the emergence of intermediate atmosphere layers."""
    from mathutils import Vector

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = max((frame.frame for frame in synthesis.frames), default=synthesis.steps + 1)
    for obj, offset, count, base_scale in animation_tracks:
        for frame in synthesis.frames:
            group = frame.positions[offset:offset + count]
            if not group:
                continue
            world_center = tuple(
                sum(point[axis] for point in group) / len(group)
                for axis in range(3)
            )
            world_vector = Vector(world_center)
            if obj.parent is not None:
                local_vector = obj.parent.matrix_world.inverted() @ world_vector
                obj.location = local_vector
            else:
                obj.location = world_vector
            contraction = float(frame.compression)
            obj.scale = (base_scale * contraction,) * 3
            obj.keyframe_insert(data_path="location", frame=frame.frame)
            obj.keyframe_insert(data_path="scale", frame=frame.frame)
    # Intermediate atmospheric sheets are independent meshes (not parents of
    # child bodies), so their gradual expansion cannot move or scale the atom
    # hierarchy. The outermost envelope remains the stable parent transform.
    for obj in atmosphere_tracks:
        for frame in synthesis.frames:
            emergence = 0.82 + 0.18 * float(frame.spiral_addition)
            scale = emergence * float(frame.compression)
            obj.scale = (scale, scale, scale)
            obj.keyframe_insert(data_path="scale", frame=frame.frame)
    scene.frame_set(scene.frame_end)



def _render_protium_spin_guides(
    bpy: Any,
    layout: HyperatomLayout,
    *,
    mode: str,
    show_axis: bool,
    show_spin: bool,
    collection: Any | None = None,
) -> None:
    """Draw the optional spin axis and equatorial direction marker for H-1-1."""
    from mathutils import Vector

    style = resolve_style("3D", "protium-spin", mode=mode, source="3D", target="3D")
    center = Vector(layout.center)
    radius = float(layout.outer_radius)

    def curve_line(name: str, points: Sequence[Sequence[float]], color: str, width: float) -> Any:
        curve = bpy.data.curves.new(name=name, type="CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 1
        spline = curve.splines.new("POLY")
        spline.points.add(len(points) - 1)
        for point, value in zip(spline.points, points):
            point.co = (float(value[0]), float(value[1]), float(value[2]), 1.0)
        curve.bevel_depth = width
        curve.bevel_resolution = 3
        obj = bpy.data.objects.new(name, curve)
        (collection.objects if collection is not None else bpy.context.scene.collection.objects).link(obj)
        material = _new_material(name + "_material", color, 1.0, roughness=0.35, metalness=0.25)
        curve.materials.append(material)
        obj["etoe.role"] = "protium-spin-guide"
        return obj

    if show_axis:
        axis_color = str(style.get("axis_color", "#F59E0B"))
        axis_width = float(style.get("axis_width", 0.012)) * radius
        curve_line(
            "H-1-1_spin_axis",
            (center + Vector((0, 0, -0.78 * radius)), center + Vector((0, 0, 0.78 * radius))),
            axis_color, axis_width,
        )

    if show_spin:
        equator_color = str(style.get("equator_color", "#06B6D4"))
        equator_width = float(style.get("equator_width", 0.018)) * radius
        points = [
            center + Vector((0.69 * radius * math.cos(2.0 * math.pi * index / 96),
                            0.69 * radius * math.sin(2.0 * math.pi * index / 96), 0.0))
            for index in range(97)
        ]
        curve_line("H-1-1_equatorial_spin_direction", points, equator_color, equator_width)

        # A small cone tangent to the equator makes the rotation direction clear.
        arrow_angle = math.pi / 3.0
        arrow_location = center + Vector((0.69 * radius * math.cos(arrow_angle),
                                          0.69 * radius * math.sin(arrow_angle), 0.0))
        tangent = Vector((-math.sin(arrow_angle), math.cos(arrow_angle), 0.0))
        arrow_size = float(style.get("arrow_size", 0.075)) * radius
        bpy.ops.mesh.primitive_cone_add(
            vertices=24, radius1=arrow_size, radius2=0.0,
            depth=arrow_size * 2.0,
            location=arrow_location,
        )
        arrow = bpy.context.object
        arrow.name = "H-1-1_equatorial_spin_arrow"
        arrow.rotation_mode = "QUATERNION"
        arrow.rotation_quaternion = tangent.to_track_quat("Z", "Y")
        if collection is not None:
            for linked_collection in list(arrow.users_collection):
                linked_collection.objects.unlink(arrow)
            collection.objects.link(arrow)
        arrow.data.materials.append(_new_material(
            "H-1-1_equatorial_spin_arrow_material", equator_color,
            1.0, roughness=0.35, metalness=0.25,
        ))
        arrow["etoe.role"] = "protium-spin-direction-arrow"

def _make_label(text: str, center: tuple[float, float, float], radius: float, depth: int, mode: str, collection: Any) -> None:
    import bpy
    from mathutils import Vector

    style = resolve_style("3D", "label", mode=mode, source="3D", target="3D")
    curve = bpy.data.curves.new(name=f"label_{_safe_id(text)}_{depth}", type="FONT")
    curve.body = text
    curve.size = max(0.035, radius * 0.10)
    curve.extrude = radius * 0.001
    obj = bpy.data.objects.new(curve.name, curve)
    _link_object(obj, collection)
    obj.location = Vector((center[0] - radius * 0.42, center[1] - radius * 0.72, center[2] + radius * 0.84))
    material = _new_material(curve.name + "_material", str(style.get("color", "#F9FAFB")), 0.92, roughness=0.7)
    curve.materials.append(material)


def _clear_scene(bpy: Any) -> Any:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablock in (bpy.data.materials, bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        for item in list(datablock):
            if item.users == 0:
                datablock.remove(item)
    scene = bpy.context.scene
    for old_collection in reversed(list(bpy.data.collections)):
        if old_collection != scene.collection:
            bpy.data.collections.remove(old_collection, do_unlink=True)
    collection = bpy.data.collections.new("ÆToE_Hyperatom_Structure")
    collection["etoe.geometry_revision"] = "bottom-up-v2"
    collection["etoe.has_core"] = False
    collection["etoe.hyperatom_root"] = True
    scene.collection.children.link(collection)
    return collection


def _configure_scene(
    bpy: Any,
    node: Hyperatom3DNode,
    *,
    mode: str,
    engine: str,
    resolution: int,
    samples: int,
    transparent: bool,
    frame_radius: float,
    frame_center: Sequence[float],
) -> float:
    from mathutils import Vector

    scene = bpy.context.scene
    if engine == "cycles":
        scene.render.engine = "CYCLES"
    else:
        # EEVEE was renamed in Blender 4.2; assignment provides a simple
        # version-independent capability check without depending on RNA enums.
        try:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        except (TypeError, ValueError):
            scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    scene.render.film_transparent = bool(transparent)
    if engine == "cycles":
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
    elif hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = samples

    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except (TypeError, ValueError):
        scene.view_settings.view_transform = "Standard"
        try:
            scene.view_settings.look = "Medium High Contrast"
        except (TypeError, ValueError):
            pass
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0

    scene_style = resolve_style("3D", "scene", mode=mode, source="3D", target="3D")
    bg = _hex_rgb(str(scene_style.get("background", "#111827")))
    world = bpy.data.worlds.new("ÆToE_World") if bpy.data.worlds.get("ÆToE_World") is None else bpy.data.worlds["ÆToE_World"]
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (*bg, 1.0)
        background.inputs["Strength"].default_value = 0.45

    root_radius = max(0.8, float(frame_radius))
    # Frame the measured bottom-up envelope rather than assuming a unit sphere.
    camera_data = bpy.data.cameras.new("ÆToE_Camera")
    camera = bpy.data.objects.new("ÆToE_Camera", camera_data)
    scene.collection.objects.link(camera)
    target = Vector(frame_center)
    camera.location = target + Vector((root_radius * 2.8, -root_radius * 3.4, root_radius * 2.45))
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = root_radius * 2.85
    scene.camera = camera

    for name, location, energy, size in (
        ("ÆToE_Key", (root_radius * 1.85, -root_radius * 1.35, root_radius * 2.35), 1450, root_radius * 1.65),
        ("ÆToE_Fill", (-root_radius * 1.7, -root_radius * 0.5, root_radius * 0.85), 780, root_radius * 1.45),
        ("ÆToE_Rim", (0.0, root_radius * 2.0, root_radius * 1.35), 1050, root_radius * 1.15),
    ):
        light_data = bpy.data.lights.new(name=name, type="AREA")
        light_data.energy = energy * float(scene_style.get("key_light", 0.8))
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        scene.collection.objects.link(light)
        light.location = target + Vector(location)
        light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()

    # Turn on ambient occlusion where the Blender version exposes it.
    eevee = getattr(scene, "eevee", None)
    if eevee is not None and hasattr(eevee, "use_gtao"):
        eevee.use_gtao = True
    return root_radius


def _artifact_metadata(
    node: Hyperatom3DNode,
    layout: HyperatomLayout,
    blend_path: Path,
    *,
    synthesis: HyperatomSynthesis | None = None,
    mode: str,
    quality: str = "rough",
    representation: str = "surface",
    engine: str,
    resolution: int,
    samples: int,
    shell_layers: int,
    max_depth: int,
    artifact: str,
    dependency_artifacts: Sequence[str] = (),
) -> dict[str, object]:
    return {
        "schema": "etoe.hyperatom-3d-artifact.v3",
        "artifact": artifact,
        "hyperatom": {
            "canonical": node.canonical,
            "designation": node.designation,
            "symbol": node.symbol or "",
            "atomic_mass": node.atomic_mass,
            "atomic_level": node.atomic_level,
            "chemical_category": node.chemical_category,
            "direct_subatom_arity": node.arity,
            "protium_count": len(layout.protium_sites),
            "atomahedron": layout.atomahedron,
            "resolved": node.resolved,
        },
        "renderer": {
            "name": "Blender",
            "mode": mode,
            "quality": quality,
            "representation": representation,
            "engine": engine,
            "resolution_x": resolution,
            "resolution_y": resolution,
            "samples": samples,
            "shell_layers": shell_layers,
            "max_depth": max_depth,
            "blend_file": str(blend_path),
            "simulation_steps": synthesis.steps if synthesis is not None else 0,
            "simulation_attempts": synthesis.attempt_count if synthesis is not None else 0,
            "simulation_success": synthesis.success if synthesis is not None else False,
        },
        "geometry": {
            "construction_order": "bottom-up",
            "scene_collection_structure": "nested hyperatom collections; child meshes rebuilt from synthesized parameter models",
            "protium_hierarchy_depths": [site.depth for site in layout.protium_sites],
            "protium_compression_factors": [round(0.92 ** site.depth, 6) for site in layout.protium_sites],
            "protium_deformation_factors": [round(site.deformation, 6) for site in layout.protium_sites],
            "has_core": False,
            "body_geometry": "deformed torus-like closed meshes with multiple clumping layers; no strict UV spheres",
            "atmosphere": "nested deformed envelope meshes wrapping child synthesis results",
            "dependency_artifacts": list(dependency_artifacts),
            "animation": "keyframed synthesis sequence from initial levitation through spiral addition and compression",
        },
        "simulation": {
            "quality": quality,
            "success": synthesis.success if synthesis is not None else False,
            "expected_structure": synthesis.expected_structure if synthesis is not None else node.canonical,
            "expected_atomahedron": synthesis.expected_atomahedron if synthesis is not None else layout.atomahedron,
            "attempt_count": synthesis.attempt_count if synthesis is not None else 0,
            "steps": synthesis.steps if synthesis is not None else 0,
            "residual": round(synthesis.residual, 10) if synthesis is not None else 0.0,
            "fingerprint": simulation_fingerprint(synthesis.to_dict()) if synthesis is not None else "",
            "physical_scope": (synthesis.model.get("simulation", {}).get("force_law_status", "not specified")
                               if synthesis is not None else "not specified"),
            "physics": synthesis.model.get("simulation", {}).get("physics", "not-applicable")
                       if synthesis is not None else "not-applicable",
            "gravity_weight": synthesis.model.get("simulation", {}).get("gravity_antigravity", {}).get("weight")
                             if synthesis is not None else None,
            "magnetic_weight": synthesis.model.get("simulation", {}).get("magnetic_dipole", {}).get("weight")
                               if synthesis is not None else None,
        },
        "model": {
            "kind": "bottom-up hierarchical hyperatom synthesis model",
            "physical_status": "unvalidated model parameters are explicitly marked; known atomic mass comes from source notation; spin and etheron-based quantities remain null until specified",
        },
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_dependencies(
    registry: Any,
    definition: Any,
    dependency_definitions: Sequence[Any],
    style_dir: Path,
) -> list[tuple[Path, str]]:
    root = Path(registry.root).expanduser().resolve()
    dependencies: list[tuple[Path, str]] = []
    symbols: set[str] = set()
    for item in (definition, *dependency_definitions):
        dependencies.append((root / item.source_path, "hyperatom-source"))
        if item.symbol:
            symbols.add(item.symbol)
    for symbol in sorted(symbols):
        element_metadata = root / symbol / f"{symbol}.toml"
        if element_metadata.is_file():
            dependencies.append((element_metadata, "element-metadata"))
    repository_root = root.parents[2] if len(root.parents) >= 3 else root
    seed_specification = repository_root / "docs" / "seed" / "ru" / "EToE.md"
    if seed_specification.is_file():
        dependencies.append((seed_specification, "etoe-seed-specification"))
    dependencies.extend([
        (style_dir / "shared" / "tokens.toml", "shared-style-tokens"),
        (style_dir / "3d" / "stylesheet.toml", "3d-stylesheet"),
        (Path(__file__).resolve(), "blender-render-script"),
        (Path(__file__).with_name("hyperatom_synthesis.py").resolve(), "synthesis-model"),
        (Path(__file__).with_name("blender3d.py").resolve(), "blender-adapter"),
        (Path(__file__).with_name("hyperatom_translation.py").resolve(), "semantic-translator"),
        (Path(__file__).with_name("hyperatom_map.py").resolve(), "canonical-reference-map"),
        (Path(__file__).with_name("elements.py").resolve(), "element-catalog"),
        (Path(__file__).with_name("selections.py").resolve(), "chemical-category-catalog"),
        (Path(__file__).with_name("style.py").resolve(), "style-resolver"),
    ])
    return dependencies


def _cache_context_options(args: argparse.Namespace, blender_version: str) -> dict[str, Any]:
    return {
        "schema": "etoe.hyperatom-synthesis-cache.v1",
        "quality": args.quality,
        "physics": args.physics,
        "gravity_weight": args.gravity_weight,
        "magnetic_weight": args.magnetic_weight,
        "show_protium_axis": bool(args.show_protium_axis),
        "show_protium_spin": bool(args.show_protium_spin),
        "representation": args.representation,
        "mode": args.mode,
        "engine": args.engine,
        "resolution": args.resolution,
        "samples": args.samples,
        "shell_layers": args.shell_layers,
        "max_depth": args.max_depth,
        "attempts": args.attempts,
        "labels": bool(args.labels),
        "transparent_background": bool(args.transparent_background),
        "blender_version": blender_version,
    }


def _cache_context(
    args: argparse.Namespace,
    synthesis: HyperatomSynthesis,
    blender_version: str,
) -> dict[str, Any]:
    return {
        **_cache_context_options(args, blender_version),
        "simulation_fingerprint": simulation_fingerprint(synthesis.to_dict()),
    }


def _json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _artifacts_use_current_geometry(paths: Mapping[str, Path]) -> bool:
    """Compatibility probe for callers that only inspect renderer sidecars.

    The hierarchical renderer introduced schema v2; schema v3 adds explicit
    synthesis/cache metadata. Both describe the current non-flat geometry.
    """
    accepted = {"etoe.hyperatom-3d-artifact.v2", "etoe.hyperatom-3d-artifact.v3"}
    try:
        for key in ("blend_toml", "png_toml"):
            if key not in paths or not paths[key].is_file():
                return False
            metadata = tomllib.loads(paths[key].read_text(encoding="utf-8"))
            if metadata.get("schema") not in accepted:
                return False
        return True
    except (OSError, ValueError, tomllib.TOMLDecodeError):
        return False


def _bundle_cache_current_for_inputs(
    paths: Mapping[str, Path],
    *,
    args: argparse.Namespace,
    blender_version: str,
    dependencies: Sequence[tuple[Path, str]],
) -> bool:
    """Skip even numerical synthesis when all current inputs match a saved bundle."""
    try:
        manifest = tomllib.loads(paths["simulation"].read_text(encoding="utf-8"))
        cache = manifest.get("cache", {})
        stored_context = json.loads(cache.get("context_json", "{}"))
        if not isinstance(stored_context, dict):
            return False
        options = _cache_context_options(args, blender_version)
        if any(stored_context.get(key) != value for key, value in options.items()):
            return False
        return _bundle_cache_current(paths, context=stored_context, dependencies=dependencies)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, tomllib.TOMLDecodeError):
        return False


def _bundle_cache_current(
    paths: Mapping[str, Path],
    *,
    context: Mapping[str, Any],
    dependencies: Sequence[tuple[Path, str]],
) -> bool:
    """Validate every result file against the exact model/style/source inputs."""
    required = ("simulation", "blend", "blend_toml", "png", "png_toml")
    if any(not paths[key].is_file() for key in required):
        return False
    try:
        manifest = tomllib.loads(paths["simulation"].read_text(encoding="utf-8"))
        cache = manifest.get("cache", {})
        if cache.get("schema") != "etoe.hyperatom-synthesis-cache.v1":
            return False
        if cache.get("context_json") != _json_compact(context):
            return False
        payload_json = manifest.get("synthesis", {}).get("payload_json")
        if not payload_json:
            return False
        payload = json.loads(payload_json)
        if simulation_fingerprint(payload) != context.get("simulation_fingerprint"):
            return False
        if manifest.get("synthesis", {}).get("success") is not True:
            return False
        expected_dependencies = snapshot_dependencies(dependencies)
        if cache.get("dependencies_json") != _json_compact(expected_dependencies):
            return False
        if manifest.get("dependencies") != expected_dependencies:
            return False
        artifact_hashes = json.loads(cache.get("artifact_hashes_json", "{}"))
        for key in ("blend", "png", "blend_toml", "png_toml"):
            if artifact_hashes.get(key) != _file_sha256(paths[key]):
                return False
            sidecar = tomllib.loads(paths[key].read_text(encoding="utf-8")) if key.endswith("toml") else None
            if sidecar is not None:
                sidecar_cache = sidecar.get("cache", {})
                output_key = "blend" if key == "blend_toml" else "png"
                if (
                    sidecar_cache.get("schema") != cache.get("schema")
                    or sidecar_cache.get("context_json") != cache.get("context_json")
                    or sidecar_cache.get("dependencies_json") != cache.get("dependencies_json")
                    or sidecar.get("dependencies") != expected_dependencies
                    or sidecar_cache.get("output_sha256") != _file_sha256(paths[output_key])
                ):
                    return False
        return True
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, tomllib.TOMLDecodeError):
        return False


def _is_protium_node(node: Hyperatom3DNode) -> bool:
    """Whether a semantic leaf denotes the elementary Protium atom H-1-1."""
    return (
        not node.children
        and (node.canonical in {"H-1-1", "H-1"} or (node.symbol == "H" and node.atomic_mass == 1))
    )


def _dependency_model(path: Path) -> dict[str, Any] | None:
    """Read a generated physical model from a simulation TOML companion."""
    if not path.is_file():
        return None
    try:
        manifest = tomllib.loads(path.read_text(encoding="utf-8"))
        model_json = manifest.get("model", {}).get("model_json")
        if model_json:
            value = json.loads(model_json)
            if isinstance(value, dict):
                return value
        # Compatibility with early 0.1.75 manifests.
        payload_json = manifest.get("synthesis", {}).get("payload_json")
        if payload_json:
            payload = json.loads(payload_json)
            if isinstance(payload, dict) and isinstance(payload.get("model"), dict):
                return payload["model"]
    except (OSError, ValueError, TypeError, json.JSONDecodeError, tomllib.TOMLDecodeError):
        return None
    return None


def _validate_dependency_artifacts(
    dependency_definitions: Sequence[Any],
    dependency_paths: Mapping[str, Path],
    *,
    args: argparse.Namespace,
) -> None:
    """Require successful child simulation manifests, never child .blend files.

    Protium is an elementary atom, not a hyperatom synthesis dependency. Its
    parameter result is optional: parents fall back to the explicit default
    Protium model when H-1-1 has not been rendered yet.
    """
    for dependency in dependency_definitions:
        if dependency.canonical in {"H-1-1", "H-1"} and dependency.symbol == "H":
            continue
        paths = hyperatom_3d_paths(
            dependency, element_root=args.data_root, output_root=args.output_root,
            quality=args.quality, mode=args.mode, representation=args.representation,
        )
        simulation_path = Path(dependency_paths.get(dependency.canonical, paths["simulation"]))
        if not simulation_path.is_file():
            raise BlenderRenderError(
                f"Missing synthesized physical parameters for sub-hyperatom {dependency.canonical}; "
                f"expected {simulation_path}. The dependency must complete before its parent is synthesized."
            )
        try:
            simulation = tomllib.loads(simulation_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise BlenderRenderError(
                f"Invalid TOML simulation result for {dependency.canonical}: {exc}"
            ) from exc
        if (
            simulation.get("schema") != "etoe.hyperatom-synthesis.v1"
            or simulation.get("hyperatom", {}).get("canonical") != dependency.canonical
            or simulation.get("synthesis", {}).get("quality") != args.quality
            or simulation.get("synthesis", {}).get("physics", "surrogate") != args.physics
            or simulation.get("synthesis", {}).get("success") is not True
            or _dependency_model(simulation_path) is None
        ):
            raise BlenderRenderError(
                f"The physical parameter result for {dependency.canonical} is stale, incompatible, or unsuccessful; "
                "rerun the dependency synthesis before building its parent."
            )

def _assert_fully_resolved(node: Hyperatom3DNode, *, root: str) -> None:
    """Reject an incomplete semantic tree instead of synthesizing placeholders."""
    unresolved: list[str] = []
    stack = [node]
    while stack:
        current = stack.pop()
        if not current.resolved:
            unresolved.append(current.canonical)
        stack.extend(current.children)
    if unresolved:
        names = ", ".join(dict.fromkeys(unresolved))
        raise BlenderRenderError(
            f"Cannot synthesize {root}: unresolved subatom reference(s): {names}. "
            "Add or correct the source-defined hyperatom before running the parent synthesis."
        )


def render_one(
    bpy: Any,
    registry: Any,
    definition: Any,
    args: argparse.Namespace,
    *,
    dependency_definitions: Sequence[Any] = (),
    dependency_paths: Mapping[str, Path] | None = None,
) -> tuple[Path, Path]:
    node = build_hyperatom_3d_tree(registry, definition, resolve_references=False)
    _assert_fully_resolved(node, root=definition.canonical)
    paths = hyperatom_3d_paths(
        definition,
        element_root=args.data_root,
        output_root=args.output_root,
        output=args.output,
        quality=args.quality,
        mode=args.mode,
        representation=args.representation,
    )
    blend_path, png_path = paths["blend"], paths["png"]
    dependency_paths = dict(dependency_paths or {})
    _validate_dependency_artifacts(dependency_definitions, dependency_paths, args=args)
    style_dir = args.style_dir.resolve() if args.style_dir is not None else Path(os.environ.get("ETOE_STYLE_DIR", "style")).resolve()
    dependencies = _source_dependencies(registry, definition, dependency_definitions, style_dir)
    # Physical parameter manifests are inputs; child .blend files deliberately
    # are not. Child scene geometry is reconstructed bottom-up in this scene.
    for dependency in dependency_definitions:
        child_paths = hyperatom_3d_paths(
            dependency, element_root=args.data_root, output_root=args.output_root,
            quality=args.quality, mode=args.mode, representation=args.representation,
        )
        if child_paths["simulation"].is_file():
            dependencies.append((child_paths["simulation"], "synthesized-subatom-physical-parameters"))
    blender_version = getattr(bpy.app, "version_string", "unknown")
    if not args.rebuild and _bundle_cache_current_for_inputs(
        paths, args=args, blender_version=blender_version, dependencies=dependencies,
    ):
        print(f"SKIP {definition.canonical}: unchanged inputs; numerical synthesis and rendering are current")
        return blend_path, png_path

    parameter_models: dict[str, Mapping[str, Any]] = {}
    for dependency in dependency_definitions:
        model = _dependency_model(Path(dependency_paths.get(
            dependency.canonical,
            hyperatom_3d_paths(
                dependency, element_root=args.data_root, output_root=args.output_root,
                quality=args.quality, mode=args.mode, representation=args.representation,
            )["simulation"],
        )))
        if model:
            if dependency.canonical in {"H-1-1", "H-1"}:
                protium_model = model.get("protium_parameters", model.get("root", {}))
                parameter_models["H-1-1"] = protium_model
            else:
                parameter_models[dependency.canonical] = model.get("root", {})
    if "H-1-1" not in parameter_models:
        parameter_models["H-1-1"] = default_protium_parameters(args.quality)

    layout = build_hyperatom_layout(
        node, max_depth=0, parameter_models=parameter_models,
    )
    is_protium = _is_protium_node(node)
    if is_protium:
        synthesis = build_protium_parameter_result(node, layout, quality=args.quality)
    else:
        synthesis = simulate_hyperatom_synthesis(
            node, layout, quality=args.quality, attempts=args.attempts,
            physics=args.physics, gravity_weight=args.gravity_weight, magnetic_weight=args.magnetic_weight,
        )
    if not synthesis.success:
        raise BlenderRenderError(
            f"Synthesis failed for {definition.canonical}: no accepted configuration after "
            f"{synthesis.attempt_count} orientation attempt(s); residual={synthesis.residual:.6g}."
        )

    context = _cache_context(args, synthesis, blender_version)

    blend_path.parent.mkdir(parents=True, exist_ok=True)
    scene_root = _clear_scene(bpy)
    scene_root["etoe.canonical"] = node.canonical
    scene_root["etoe.outer_radius"] = float(layout.outer_radius)
    scene_root["etoe.protium_count"] = len(layout.protium_sites)
    _configure_scene(
        bpy, node,
        mode=args.mode,
        engine=args.engine,
        resolution=args.resolution,
        samples=args.samples,
        transparent=args.transparent_background,
        frame_radius=max(
            layout.outer_radius,
            max((math.dist(point, layout.center) for point in synthesis.initial_positions), default=0.0),
        ),
        frame_center=layout.center,
    )
    animation_tracks: list[tuple[Any, int, int, float]] = []
    atmosphere_tracks: list[Any] = []
    _render_node_bottom_up(
        layout,
        scene_root,
        mode=args.mode,
        shell_layers=args.shell_layers,
        labels=args.labels,
        mesh_subdivisions=PROFILES[args.quality].mesh_subdivisions,
        clump_layers=PROFILES[args.quality].clump_layers,
        animation_tracks=animation_tracks,
        atmosphere_tracks=atmosphere_tracks,
        max_depth=args.max_depth,
    )
    if is_protium and (args.show_protium_axis or args.show_protium_spin):
        _render_protium_spin_guides(
            bpy, layout, mode=args.mode,
            show_axis=args.show_protium_axis, show_spin=args.show_protium_spin,
            collection=scene_root,
        )
    _apply_geometry_representation(bpy, scene_root, args.representation)
    _animate_synthesis(bpy, synthesis, animation_tracks, atmosphere_tracks)

    scene = bpy.context.scene
    scene.render.filepath = str(png_path)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if args.transparent_background else "RGB"
    # Save the complete animated .blend before rendering the final frame.
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    bpy.ops.render.render(write_still=True)

    dependency_artifacts = [str(path) for path in dependency_paths.values()]
    common = _artifact_metadata(
        node, layout, blend_path, synthesis=synthesis,
        mode=args.mode, quality=args.quality, representation=args.representation, engine=args.engine,
        resolution=args.resolution, samples=args.samples,
        shell_layers=args.shell_layers, max_depth=args.max_depth,
        artifact="blender-scene", dependency_artifacts=dependency_artifacts,
    )
    common["renderer"]["blender_version"] = blender_version
    dependency_snapshot = snapshot_dependencies(dependencies)
    common["dependencies"] = dependency_snapshot
    context_json = _json_compact(context)
    dependencies_json = _json_compact(dependency_snapshot)

    def attach_cache(metadata: dict[str, object], output_path: Path) -> None:
        metadata["cache"] = {
            "schema": "etoe.hyperatom-synthesis-cache.v1",
            "context_json": context_json,
            "dependencies_json": dependencies_json,
            "output_sha256": _file_sha256(output_path),
        }

    blend_metadata = dict(common)
    attach_cache(blend_metadata, blend_path)
    write_toml_sidecar(paths["blend_toml"], blend_metadata)
    image_metadata = dict(common)
    image_metadata["artifact"] = "png-snapshot"
    image_metadata["snapshot"] = {"path": str(png_path), "format": "PNG"}
    attach_cache(image_metadata, png_path)
    write_toml_sidecar(paths["png_toml"], image_metadata)

    artifact_hashes = {
        key: _file_sha256(paths[key]) for key in ("blend", "png", "blend_toml", "png_toml")
    }
    simulation_payload = synthesis.to_dict()
    simulation_metadata = {
        "schema": "etoe.hyperatom-synthesis.v1",
        "hyperatom": {
            "canonical": definition.canonical,
            "designation": definition.designation,
            "symbol": definition.symbol or "",
            "atomic_mass": definition.atomic_mass,
            "source_path": definition.source_path,
        },
        "synthesis": {
            "quality": args.quality,
            "physics": "not-applicable" if is_protium else args.physics,
            "gravity_weight": args.gravity_weight,
            "magnetic_weight": args.magnetic_weight,
            "success": synthesis.success,
            "expected_structure": synthesis.expected_structure,
            "expected_atomahedron": synthesis.expected_atomahedron,
            "attempt_count": synthesis.attempt_count,
            "steps": synthesis.steps,
            "residual": round(synthesis.residual, 10),
            "fingerprint": simulation_fingerprint(simulation_payload),
            "payload_json": _json_compact(simulation_payload),
        },
        "dependencies": dependency_snapshot,
        "model": {"model_json": _json_compact(synthesis.model)},
        "cache": {
            "schema": "etoe.hyperatom-synthesis-cache.v1",
            "context_json": context_json,
            "dependencies_json": dependencies_json,
            "artifact_hashes_json": _json_compact(artifact_hashes),
        },
    }
    write_toml_sidecar(paths["simulation"], simulation_metadata)
    print(f"WROTE {definition.canonical} [{args.quality}]: {paths['simulation']} + {blend_path} + {png_path}")
    return blend_path, png_path


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(blender_script_args() if argv is None else argv)
    if args.quality not in PROFILES:
        raise BlenderRenderError("--quality must be rough or strict.")
    if args.physics in {"vanguard", "natural"}:
        raise BlenderRenderError(
            f"--physics {args.physics} is reserved; executable interaction models are surrogate and classic."
        )
    if args.gravity_weight < 0 or args.magnetic_weight < 0 or args.gravity_weight + args.magnetic_weight <= 0:
        raise BlenderRenderError("--gravity-weight and --magnetic-weight must be non-negative and not both zero.")
    profile = PROFILES[args.quality]
    args.samples = profile.render_samples if args.samples is None else args.samples
    args.shell_layers = profile.atmosphere_layers if args.shell_layers is None else args.shell_layers
    args.attempts = profile.attempts if args.attempts is None else args.attempts
    if args.resolution < 64:
        raise BlenderRenderError("--resolution must be at least 64 pixels.")
    if args.samples < 1 or args.shell_layers < 1 or args.shell_layers > 8:
        raise BlenderRenderError("--samples must be positive and --shell-layers must be between 1 and 8.")
    if args.attempts < 1:
        raise BlenderRenderError("--attempts must be positive.")
    if args.max_depth < 0:
        raise BlenderRenderError("--max-depth must be zero or greater.")
    if args.output is not None and (
        args.all_elements or args.elements or args.element or args.category or len(args.hyperatom) != 1
    ):
        raise BlenderRenderError("--output can be used only with exactly one --hyperatom and no batch selectors.")
    if args.style_dir is not None:
        os.environ["ETOE_STYLE_DIR"] = str(args.style_dir.resolve())
    configure_styles(mode=args.mode, source="3D", target="3D")

    from etoe.hyperatom_map import build_canonical_hyperatom_map
    from etoe.style import get_style_directory

    registry = HyperatomTranslator().translate_directory(args.data_root)
    # Apply the seed's primary-by-mass and non-primary-by-structure links once.
    build_canonical_hyperatom_map(registry, auto_patch_missing=False)
    elements = [*args.element, *_parse_list(args.elements)]
    selected = select_hyperatoms(
        registry,
        hyperatoms=args.hyperatom,
        elements=elements,
        categories=args.category,
        all_elements=args.all_elements,
    )
    if not selected:
        print("No source-defined hyperatoms matched the requested selection.")
        return 0
    if args.output is not None and len(selected) != 1:
        raise BlenderRenderError("An explicit --output path requires exactly one matched hyperatom.")

    # Build each selected atom's complete dependency closure. The union is a
    # stable postorder: primitive Protium first, then D/He/Be, then the root.
    build_order = hyperatom_dependency_order(registry, selected)
    if not build_order:
        raise BlenderRenderError("The selected hyperatom set produced an empty dependency plan.")
    print(f"Synthesis plan ({args.quality}): {len(selected)} selected root(s), {len(build_order)} unique atom job(s).")

    style_dir = get_style_directory()
    # Use a single Blender process, and ensure each parent consumes the saved
    # .blend result of its uniquely resolved child hyperatoms.
    import bpy

    failures: list[tuple[str, str]] = []
    failed_ids: set[str] = set()
    selected_ids = {item.id for item in selected}
    for index, definition in enumerate(build_order, start=1):
        dependency_order = hyperatom_dependency_order(registry, [definition])
        dependency_definitions = dependency_order[:-1]
        blocked = [item.canonical for item in dependency_definitions if item.id in failed_ids]
        if blocked:
            message = "dependency synthesis failed: " + ", ".join(blocked)
            failures.append((definition.canonical, message))
            failed_ids.add(definition.id)
            print(f"SKIP {definition.canonical}: {message}", file=sys.stderr)
            continue
        dependency_paths: dict[str, Path] = {}
        for dependency in dependency_definitions:
            dependency_paths[dependency.canonical] = hyperatom_3d_paths(
                dependency, element_root=args.data_root, output_root=args.output_root,
                quality=args.quality, mode=args.mode, representation=args.representation,
            )["simulation"]
        item_args = argparse.Namespace(**vars(args))
        # An explicit output path belongs only to the selected root, never to
        # its automatically synthesized child dependencies.
        if definition.id not in selected_ids:
            item_args.output = None
        item_args.style_dir = style_dir
        print(f"[{index}/{len(build_order)}] synthesize {definition.canonical}")
        try:
            render_one(
                bpy, registry, definition, item_args,
                dependency_definitions=dependency_definitions,
                dependency_paths=dependency_paths,
            )
        except Exception as exc:  # noqa: BLE001 - isolate each dependency/root job
            failures.append((definition.canonical, str(exc)))
            failed_ids.add(definition.id)
            traceback.print_exc()

    print(
        f"3D synthesis batch finished: {len(build_order) - len(failures)} succeeded/reused, "
        f"{len(failures)} failed."
    )
    for canonical, message in failures:
        print(f"FAILED {canonical}: {message}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - pass a reliable failure code to the CLI
        print(f"ERROR: {exc}", file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1)
