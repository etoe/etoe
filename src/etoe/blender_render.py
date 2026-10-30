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
from typing import Any, Iterable, Sequence


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


def _make_uv_sphere(name: str, location: Sequence[float], radius: float, material: Any, collection: Any, *, segments: int = 40, rings: int = 24) -> Any:
    import bpy

    mesh = bpy.data.meshes.new(name + "_mesh")
    # bmesh creates proper pole topology and avoids context-sensitive operators.
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm,
        u_segments=max(12, int(segments)),
        v_segments=max(8, int(rings)),
        radius=float(radius),
    )
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    from mathutils import Vector
    obj = bpy.data.objects.new(name, mesh)
    _link_object(obj, collection)
    obj.location = Vector(location)
    if material is not None:
        obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def _make_wire_outline(name: str, location: Sequence[float], radius: float, color: str, collection: Any) -> None:
    """Add a subtle wireframe outline to improve silhouette readability."""
    import bpy

    material = _new_material(name + "_outline_material", color, 0.55, roughness=0.38, metalness=0.12)
    obj = _make_uv_sphere(name, location, radius, material, collection, segments=24, rings=16)
    modifier = obj.modifiers.new(name="Fine wire outline", type="WIREFRAME")
    modifier.thickness = max(0.002, radius * 0.0025)
    modifier.use_replace = True


def _child_positions(arity: int) -> tuple[tuple[float, float, float], ...]:
    """Deterministic normalized placement inspired by the seed's atomahedra.

    2 = diatomahedron, 3 = triatomahedron, 4 = tetraatomahedron, 5 =
    trigonal bipyramid. Higher arities use a deterministic Fibonacci sphere
    distribution as a visualization fallback, not as a physical postulate.
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
        radius = math.sqrt(max(0.0, 1.0 - z * z))
        angle = golden_angle * index
        points.append((radius * math.cos(angle), radius * math.sin(angle), z))
    return tuple(points)


def _child_radius(parent_radius: float, arity: int) -> float:
    scale = {1: 0.54, 2: 0.48, 3: 0.43, 4: 0.38, 5: 0.34}.get(arity, max(0.22, 0.31 / math.sqrt(max(1, arity - 4))))
    return parent_radius * scale


def _render_node(
    node: Hyperatom3DNode,
    center: tuple[float, float, float],
    radius: float,
    collection: Any,
    *,
    mode: str,
    shell_layers: int,
    depth: int,
    max_depth: int,
    labels: bool,
) -> None:
    import bpy

    # Atmosphere: translucent nested envelopes and a fine outer contour.
    for layer_index in range(shell_layers):
        layer_radius = radius * (1.0 - layer_index * 0.075)
        material = _material_for_node(node, mode, layer_index, shell_layers)
        _make_uv_sphere(
            f"{_safe_id(node.canonical)}_L{depth}_shell{layer_index + 1}",
            center,
            layer_radius,
            material,
            collection,
        )
    style = resolve_style(
        "3D", "entity", classes=(f"category-{node.chemical_category or 'unknowns'}",),
        mode=mode, source="3D", target="3D",
    )
    _make_wire_outline(
        f"{_safe_id(node.canonical)}_L{depth}_outline",
        center,
        radius,
        str(style.get("outline", "#60A5FA")),
        collection,
    )

    # A small denser center emphasizes the hierarchical core without asserting
    # an electron-shell or conventional nuclear model.
    core_material = _new_material(
        f"{_safe_id(node.canonical)}_L{depth}_core_material",
        str(style.get("outline", "#60A5FA")),
        0.62 if node.arity else 0.78,
        roughness=0.32,
        metalness=0.12,
    )
    _make_uv_sphere(
        f"{_safe_id(node.canonical)}_L{depth}_core",
        center,
        radius * (0.105 if node.arity else 0.19),
        core_material,
        collection,
        segments=32,
        rings=20,
    )

    if labels:
        _make_label(node.designation, center, radius, depth, mode, collection)

    if not node.children or (max_depth > 0 and depth >= max_depth):
        return

    positions = _child_positions(len(node.children))
    child_radius = _child_radius(radius, len(node.children))
    # Placement factors are compact enough to keep all children within the
    # parent atmosphere while retaining a visible tetrahedral/axial pattern.
    offset = radius * (0.33 if len(node.children) == 2 else 0.31 if len(node.children) <= 4 else 0.34)
    for index, (child, position) in enumerate(zip(node.children, positions)):
        child_center = tuple(center[axis] + position[axis] * offset for axis in range(3))
        _render_node(
            child,
            child_center,
            child_radius,
            collection,
            mode=mode,
            shell_layers=shell_layers,
            depth=depth + 1,
            max_depth=max_depth,
            labels=labels,
        )


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
    for collection in list(bpy.data.collections):
        if collection != scene.collection:
            bpy.data.collections.remove(collection)
    collection = bpy.data.collections.new("ÆToE_Hyperatom_Structure")
    scene.collection.children.link(collection)
    return collection


def _configure_scene(bpy: Any, node: Hyperatom3DNode, *, mode: str, engine: str, resolution: int, samples: int, transparent: bool) -> float:
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

    root_radius = 3.0
    # Orthographic camera framing is independent of hierarchy arity; the outer
    # envelope is the root unit sphere at this scale.
    camera_data = bpy.data.cameras.new("ÆToE_Camera")
    camera = bpy.data.objects.new("ÆToE_Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = Vector((root_radius * 2.8, -root_radius * 3.4, root_radius * 2.45))
    direction = Vector((0.0, 0.0, 0.0)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = root_radius * 3.05
    scene.camera = camera

    for name, location, energy, size in (
        ("ÆToE_Key", (5.5, -4.0, 7.0), 1450, 5.0),
        ("ÆToE_Fill", (-5.0, -1.5, 2.5), 780, 4.5),
        ("ÆToE_Rim", (0.0, 6.0, 4.0), 1050, 3.5),
    ):
        light_data = bpy.data.lights.new(name=name, type="AREA")
        light_data.energy = energy * float(scene_style.get("key_light", 0.8))
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        scene.collection.objects.link(light)
        light.location = Vector(location)
        light.rotation_euler = (Vector((0, 0, 0)) - light.location).to_track_quat("-Z", "Y").to_euler()

    # Turn on ambient occlusion where the Blender version exposes it.
    eevee = getattr(scene, "eevee", None)
    if eevee is not None and hasattr(eevee, "use_gtao"):
        eevee.use_gtao = True
    return root_radius


def _artifact_metadata(node: Hyperatom3DNode, blend_path: Path, *, mode: str, engine: str, resolution: int, samples: int, shell_layers: int, max_depth: int, artifact: str) -> dict[str, object]:
    return {
        "schema": "etoe.hyperatom-3d-artifact.v1",
        "artifact": artifact,
        "hyperatom": {
            "canonical": node.canonical,
            "designation": node.designation,
            "symbol": node.symbol or "",
            "atomic_mass": node.atomic_mass,
            "atomic_level": node.atomic_level,
            "chemical_category": node.chemical_category,
            "arity": node.arity,
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
        "model": {
            "kind": "recursive hyperatom composition visualization",
            "physical_status": "structural visualization; shell radii, opacity and placement are renderer conventions, not derived physical constants",
        },
    }


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
    ):
        print(f"SKIP {definition.canonical}: scene, snapshot, and both TOML sidecars already exist")
        return blend_path, png_path

    blend_path.parent.mkdir(parents=True, exist_ok=True)
    collection = _clear_scene(bpy)
    _configure_scene(
        bpy, node,
        mode=args.mode,
        engine=args.engine,
        resolution=args.resolution,
        samples=args.samples,
        transparent=args.transparent_background,
    )
    _render_node(
        node,
        (0.0, 0.0, 0.0),
        3.0,
        collection,
        mode=args.mode,
        shell_layers=args.shell_layers,
        depth=0,
        max_depth=args.max_depth,
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
        node, blend_path,
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
