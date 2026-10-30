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
from pathlib import Path
import sys
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Sequence


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
    write_toml_sidecar,
)
from etoe.hyperatom_translation import HyperatomTranslator  # noqa: E402
from etoe.style import configure_styles, chemical_category_slug, resolve_style  # noqa: E402


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
    parser.add_argument("--output", type=Path, default=None, help="Explicit .blend path (only for one hyperatom)")
    parser.add_argument("--output-root", type=Path, default=None, help="Override the standard element-directory output root")
    parser.add_argument("--style-dir", type=Path, default=None)
    parser.add_argument("--mode", choices=("Light", "Dark"), default="Dark")
    parser.add_argument("--engine", choices=("eevee", "cycles"), default="eevee")
    parser.add_argument("--resolution", type=int, default=1200)
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--shell-layers", type=int, default=3)
    parser.add_argument("--max-depth", type=int, default=0, help="Maximum recursive atom depth (0 = unlimited)")
    parser.add_argument("--labels", action="store_true", help="Add small labels to all hierarchy levels")
    parser.add_argument("--transparent-background", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
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
    span = {1: 0.0, 2: 0.62, 3: 0.74, 4: 0.78, 5: 0.82}.get(total_sites, 0.88)
    target_centers = tuple(_vec_scale(point, span) for point in positions)
    cursor = 0
    base_protium_radius = 0.42 / math.sqrt(max(1.0, total_sites / 2.0))

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
            deformation = min(0.48, 0.105 + 0.075 * depth)
            atmosphere = max(0.035, radius * 0.36)
            return HyperatomLayout(
                node=current,
                depth=depth,
                center=center,
                content_radius=radius,
                atmosphere_thickness=atmosphere,
                outer_radius=(radius * (1.0 + deformation * 1.10 + 0.02) + atmosphere) * 1.045,
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


def _material_for_content(node: Hyperatom3DNode, mode: str) -> Any:
    style = resolve_style(
        "3D", "entity", classes=(f"category-{node.chemical_category or 'unknowns'}",),
        mode=mode, source="3D", target="3D",
    )
    color = str(style.get("outline", style.get("color", "#60A5FA")))
    return _new_material(
        f"ÆToE_{_safe_id(node.canonical)}_deformable_content",
        color,
        0.64,
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
) -> Any:
    """Build descendants first, then wrap their finished envelopes in this node."""
    node = layout.node
    node_collection = _make_node_collection(node, parent_collection, layout)

    # Child collections are nested directly below this hyperatom's collection.
    # Their meshes are generated before the current node's atmospheric meshes.
    child_collections = []
    for child_layout in layout.children:
        child_collections.append(_render_node_bottom_up(
            child_layout,
            node_collection,
            mode=mode,
            shell_layers=shell_layers,
            labels=labels,
        ))

    phase = sum((index + 1) * ord(char) for index, char in enumerate(node.canonical)) * 0.017

    if layout.terminal:
        # Every terminal component is a deformable body with its own atmosphere.
        content_material = _material_for_content(node, mode)
        content_obj = _make_deformed_surface(
            f"{_safe_id(node.canonical)}_L{layout.depth}_content",
            layout.center,
            lambda _direction: layout.content_radius,
            content_material,
            node_collection,
            deformation=layout.deformation,
            phase=phase,
            subdivisions=3,
        )
        content_obj["etoe.role"] = (
            "deformable-protium-content" if layout.is_protium
            else "deformable-truncated-subhyperatom-content"
        )
        content_obj["etoe.hierarchy_depth"] = layout.depth
        content_obj["etoe.compression_factor"] = round(0.92 ** layout.depth, 6)

    # For a composite node, the support function follows the already-built
    # child envelopes. For a Protium node it follows that Protium's deformable
    # body. Every atmospheric layer is an irregular mesh around that content.
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
            # Parent atmospheres must remain outside the finished child shells;
            # they deform, but less aggressively than the contents they wrap.
            deformation=min(0.035, layout.deformation * 0.12),
            phase=phase + (layer_index + 1) * 0.41,
            subdivisions=3,
        )
        shell["etoe.role"] = "atmospheric-layer"
        shell["etoe.layer_index"] = layer_index + 1
        shell["etoe.hierarchy_depth"] = layout.depth
        shell["etoe.atomahedron"] = layout.atomahedron
        outermost_shell = shell

    # Object parenting mirrors the collection hierarchy: direct subatom objects
    # inherit the enclosing hyperatom's outer atmospheric object transform.
    # Their world matrices are restored so the measured arrangement is unchanged.
    if outermost_shell is not None:
        for child_collection in child_collections:
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
    mode: str,
    engine: str,
    resolution: int,
    samples: int,
    shell_layers: int,
    max_depth: int,
    artifact: str,
) -> dict[str, object]:
    return {
        "schema": "etoe.hyperatom-3d-artifact.v2",
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
            "engine": engine,
            "resolution_x": resolution,
            "resolution_y": resolution,
            "samples": samples,
            "shell_layers": shell_layers,
            "max_depth": max_depth,
            "blend_file": str(blend_path),
        },
        "geometry": {
            "construction_order": "bottom-up",
            "scene_collection_structure": "nested hyperatom collections; each child collection is inside its parent collection",
            "protium_hierarchy_depths": [site.depth for site in layout.protium_sites],
            "protium_compression_factors": [round(0.92 ** site.depth, 6) for site in layout.protium_sites],
            "protium_deformation_factors": [round(site.deformation, 6) for site in layout.protium_sites],
            "has_core": False,
            "body_geometry": "deterministically deformed icosphere meshes; no strict UV spheres",
            "atmosphere": "nested deformed envelope meshes wrapping child contents",
        },
        "model": {
            "kind": "bottom-up nested hyperatom and atomahedron visualization",
            "physical_status": "structural visualization; geometry, compression, deformation, shell thickness and opacity are renderer conventions, not derived physical constants",
        },
    }

def _artifacts_use_current_geometry(paths: dict[str, Path]) -> bool:
    """Avoid treating pre-bottom-up v1 renders as up-to-date cache entries."""
    expected = 'schema = "etoe.hyperatom-3d-artifact.v2"'
    try:
        return all(expected in paths[key].read_text(encoding="utf-8") for key in ("blend_toml", "png_toml"))
    except OSError:
        return False


def render_one(
    bpy: Any,
    registry: Any,
    definition: Any,
    args: argparse.Namespace,
) -> tuple[Path, Path]:
    node = build_hyperatom_3d_tree(registry, definition, resolve_references=False)
    paths = hyperatom_3d_paths(
        definition,
        element_root=args.data_root,
        output_root=args.output_root,
        output=args.output,
    )
    blend_path, png_path = paths["blend"], paths["png"]
    if (
        not args.overwrite
        and all(path.is_file() for path in paths.values())
        and _artifacts_use_current_geometry(paths)
    ):
        print(f"SKIP {definition.canonical}: current bottom-up scene, snapshot, and TOML sidecars already exist")
        return blend_path, png_path

    blend_path.parent.mkdir(parents=True, exist_ok=True)
    layout = build_hyperatom_layout(node, max_depth=args.max_depth)
    scene_root = _clear_scene(bpy)
    _configure_scene(
        bpy, node,
        mode=args.mode,
        engine=args.engine,
        resolution=args.resolution,
        samples=args.samples,
        transparent=args.transparent_background,
        frame_radius=layout.outer_radius,
        frame_center=layout.center,
    )
    _render_node_bottom_up(
        layout,
        scene_root,
        mode=args.mode,
        shell_layers=args.shell_layers,
        labels=args.labels,
    )

    scene = bpy.context.scene
    scene.render.filepath = str(png_path)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if args.transparent_background else "RGB"
    # Save before rendering so the .blend is still available if the renderer
    # exits unexpectedly while writing the PNG.
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    bpy.ops.render.render(write_still=True)

    common = _artifact_metadata(
        node, layout, blend_path,
        mode=args.mode,
        engine=args.engine,
        resolution=args.resolution,
        samples=args.samples,
        shell_layers=args.shell_layers,
        max_depth=args.max_depth,
        artifact="blender-scene",
    )
    common["renderer"]["blender_version"] = getattr(bpy.app, "version_string", "unknown")
    write_toml_sidecar(paths["blend_toml"], common)
    image_metadata = dict(common)
    image_metadata["artifact"] = "png-snapshot"
    image_metadata["snapshot"] = {"path": str(png_path), "format": "PNG"}
    write_toml_sidecar(paths["png_toml"], image_metadata)
    print(f"WROTE {definition.canonical}: {blend_path} + {png_path}")
    return blend_path, png_path


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(blender_script_args() if argv is None else argv)
    if args.resolution < 64:
        raise BlenderRenderError("--resolution must be at least 64 pixels.")
    if args.samples < 1 or args.shell_layers < 1 or args.shell_layers > 8:
        raise BlenderRenderError("--samples must be positive and --shell-layers must be between 1 and 8.")
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

    registry = HyperatomTranslator().translate_directory(args.data_root)
    # This applies the seed's primary-by-mass and non-primary-by-structure
    # reference rules before the 3D tree is unfolded.
    build_canonical_hyperatom_map(registry, auto_patch_missing=False)
    elements = [*args.element, *_parse_list(args.elements)]
    definitions = select_hyperatoms(
        registry,
        hyperatoms=args.hyperatom,
        elements=elements,
        categories=args.category,
        all_elements=args.all_elements,
    )
    if not definitions:
        print("No source-defined hyperatoms matched the requested selection.")
        return 0
    if args.output is not None and len(definitions) != 1:
        raise BlenderRenderError("An explicit --output path requires exactly one matched hyperatom.")

    import bpy

    failures: list[tuple[str, str]] = []
    total = len(definitions)
    for index, definition in enumerate(definitions, start=1):
        print(f"[{index}/{total}] {definition.canonical}")
        # Avoid Blender process termination on one bad output; keep batch jobs
        # independent and report a non-zero exit status after all were attempted.
        try:
            render_one(bpy, registry, definition, args)
        except Exception as exc:  # noqa: BLE001 - batch must isolate per-item failures
            failures.append((definition.canonical, str(exc)))
            traceback.print_exc()
    print(f"3D batch finished: {total - len(failures)} succeeded/reused, {len(failures)} failed.")
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
