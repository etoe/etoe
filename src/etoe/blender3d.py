"""Blender batch-render helpers for hierarchical hyperatom structures.

This module intentionally contains no ``bpy`` imports so it is safe to use
from the normal etoe CLI and test suite. Blender-specific scene construction
lives in :mod:`etoe.blender_render`.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Iterable, Sequence

from .hyperatom_translation import HYPERATOM_KIND, HyperatomRegistry, SemanticComponent, SemanticHyperatom


BLENDER_STYLE_CODE = "b33"  # Blender backend, 3D source profile, 3D target profile.
BLENDER_ARTIFACT_CODE = "3"


class BlenderRenderError(ValueError):
    """Invalid selection, output path, or Blender invocation configuration."""


@dataclass(frozen=True, slots=True)
class Hyperatom3DNode:
    """Renderer-neutral recursive view of one hyperatom/subatom occurrence."""

    canonical: str
    designation: str
    symbol: str | None
    atomic_mass: int | None
    atomic_level: int | None
    chemical_category: str
    resolved: bool
    children: tuple["Hyperatom3DNode", ...] = ()

    @property
    def arity(self) -> int:
        return len(self.children)


def _safe_stem(canonical: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", canonical).rstrip(" .")
    if not value or value in {".", ".."}:
        raise BlenderRenderError(f"Cannot derive a filename from hyperatom {canonical!r}.")
    return value


def hyperatom_3d_paths(
    hyperatom: SemanticHyperatom,
    *,
    element_root: str | Path = "data/atom/element",
    output_root: str | Path | None = None,
    output: str | Path | None = None,
) -> dict[str, Path]:
    """Return canonical .blend, PNG, and TOML sidecar paths for a hyperatom.

    The default file convention is ``<notation>.3.b33.blend``; the PNG is
    appended to the blend filename, so all four expected paths stay together.
    """
    if not hyperatom.symbol:
        raise BlenderRenderError(
            f"Hyperatom {hyperatom.canonical!r} has no element symbol; cannot choose its output directory."
        )
    if output is not None:
        blend_path = Path(output).expanduser()
        if blend_path.suffix.casefold() != ".blend":
            raise BlenderRenderError("--output must name a .blend file.")
    else:
        base = Path(output_root).expanduser() if output_root is not None else Path(element_root).expanduser()
        directory = base / hyperatom.symbol
        blend_path = directory / f"{_safe_stem(hyperatom.canonical)}.{BLENDER_ARTIFACT_CODE}.{BLENDER_STYLE_CODE}.blend"

    png_path = Path(str(blend_path) + ".png")
    return {
        "blend": blend_path,
        "blend_toml": Path(str(blend_path) + ".toml"),
        "png": png_path,
        "png_toml": Path(str(png_path) + ".toml"),
    }


def _definition_sort_key(item: SemanticHyperatom) -> tuple[object, ...]:
    return (
        item.symbol or "",
        item.atomic_mass if item.atomic_mass is not None else -1,
        item.canonical,
        item.id,
    )


def select_hyperatoms(
    registry: HyperatomRegistry,
    *,
    hyperatoms: Iterable[str] = (),
    elements: Iterable[str] = (),
    categories: Iterable[str] = (),
    all_elements: bool = False,
) -> tuple[SemanticHyperatom, ...]:
    """Resolve direct hyperatom selectors and element/category batch filters.

    Selections are unioned, then deduplicated by canonical notation. Only
    source-defined concrete ``HYPERATOM_KIND`` records are returned; templates,
    molecules, and runtime placeholders are deliberately excluded.
    """
    requested_hyperatoms = tuple(dict.fromkeys(str(value).strip() for value in hyperatoms if str(value).strip()))
    requested_elements = tuple(dict.fromkeys(str(value).strip() for value in elements if str(value).strip()))
    requested_categories = tuple(dict.fromkeys(str(value).strip() for value in categories if str(value).strip()))
    if not (requested_hyperatoms or requested_elements or requested_categories or all_elements):
        raise BlenderRenderError(
            "Choose at least one --hyperatom, --element/--elements, --category, or --all-elements selector."
        )

    element_catalog = registry.element_catalog
    selected_symbols: set[str] = set()
    if requested_elements:
        if element_catalog is None:
            raise BlenderRenderError("The semantic registry has no element catalog.")
        for symbol in requested_elements:
            if element_catalog.get(symbol) is None:
                raise BlenderRenderError(f"Unknown chemical element symbol {symbol!r}.")
            selected_symbols.add(symbol)

    if all_elements or requested_categories:
        if element_catalog is None:
            raise BlenderRenderError("The semantic registry has no element catalog.")
        # Reuse the package's canonical category assignment, including explicit
        # per-element TOML overrides and the unknowns bucket for custom symbols.
        from .selections import ChemicalCategoryCatalog

        categories_catalog = ChemicalCategoryCatalog(
            element_catalog,
            registry,
            Path(registry.root).expanduser().resolve().parent / "category",
        )
        if all_elements:
            selected_symbols.update(element.symbol for element in element_catalog.elements)
        for slug in requested_categories:
            try:
                category = categories_catalog.require(slug)
            except KeyError as exc:
                choices = ", ".join(categories_catalog.slugs)
                raise BlenderRenderError(
                    f"Unknown chemical category {slug!r}; choose one of: {choices}."
                ) from exc
            selected_symbols.update(element.symbol for element in category.elements)

    selected: dict[str, SemanticHyperatom] = {}
    for selector in requested_hyperatoms:
        matches = [
            item for item in registry.definitions
            if item.kind == HYPERATOM_KIND
            and not item.source_path.startswith("<runtime:")
            and selector in {item.canonical, item.id, item.designation}
        ]
        if not matches:
            raise BlenderRenderError(f"No source-defined hyperatom matches {selector!r}.")
        for item in matches:
            selected[item.canonical] = item

    if selected_symbols:
        for item in registry.definitions:
            if (
                item.kind == HYPERATOM_KIND
                and not item.source_path.startswith("<runtime:")
                and item.symbol in selected_symbols
            ):
                selected[item.canonical] = item

    return tuple(sorted(selected.values(), key=_definition_sort_key))


def _placeholder_node(component: SemanticComponent, registry: HyperatomRegistry, visiting: frozenset[str]) -> Hyperatom3DNode:
    children = tuple(_component_node(child, registry, visiting) for child in component.children)
    symbol = component.symbol
    from .style import chemical_category_slug
    return Hyperatom3DNode(
        canonical=component.canonical,
        designation=component.canonical,
        symbol=symbol,
        atomic_mass=component.mass,
        atomic_level=None,
        chemical_category=chemical_category_slug(symbol, registry.element_catalog),
        resolved=False,
        children=children,
    )


def _component_node(
    component: SemanticComponent,
    registry: HyperatomRegistry,
    visiting: frozenset[str],
) -> Hyperatom3DNode:
    candidates = [
        registry.by_id[item_id]
        for item_id in component.candidate_ids
        if item_id in registry.by_id
        and registry.by_id[item_id].kind == HYPERATOM_KIND
        and not registry.by_id[item_id].source_path.startswith("<runtime:")
    ]
    # Only follow a link when the existing semantic map resolves it uniquely.
    # Rendering must not silently choose among physically ambiguous references.
    if len(candidates) == 1:
        return _definition_node(candidates[0], registry, visiting)
    return _placeholder_node(component, registry, visiting)


def _definition_node(
    definition: SemanticHyperatom,
    registry: HyperatomRegistry,
    visiting: frozenset[str],
) -> Hyperatom3DNode:
    if definition.id in visiting:
        return Hyperatom3DNode(
            canonical=definition.canonical,
            designation=definition.designation,
            symbol=definition.symbol,
            atomic_mass=definition.atomic_mass,
            atomic_level=definition.atomic_level,
            chemical_category=getattr(definition.chemical_category, "slug", "unknowns"),
            resolved=True,
            children=(),
        )
    next_visiting = visiting | {definition.id}
    children = tuple(_component_node(component, registry, next_visiting) for component in definition.components)
    category = getattr(definition.chemical_category, "slug", None)
    if not category:
        from .style import chemical_category_slug
        category = chemical_category_slug(definition.symbol, registry.element_catalog)
    return Hyperatom3DNode(
        canonical=definition.canonical,
        designation=definition.designation,
        symbol=definition.symbol,
        atomic_mass=definition.atomic_mass,
        atomic_level=definition.atomic_level,
        chemical_category=category,
        resolved=True,
        children=children,
    )


def build_hyperatom_3d_tree(
    registry: HyperatomRegistry,
    hyperatom: SemanticHyperatom | str,
    *,
    resolve_references: bool = True,
) -> Hyperatom3DNode:
    """Build a recursive scene description using the canonical hyperatom map.

    Batch renderers may resolve the registry once and pass
    ``resolve_references=False`` for each subsequent item.
    """
    if resolve_references:
        from .hyperatom_map import build_canonical_hyperatom_map
        build_canonical_hyperatom_map(registry, auto_patch_missing=False)
    if isinstance(hyperatom, str):
        matches = [item for item in registry.definitions if item.canonical == hyperatom or item.id == hyperatom]
        matches = [item for item in matches if item.kind == HYPERATOM_KIND]
        if not matches:
            raise BlenderRenderError(f"No concrete hyperatom found for {hyperatom!r}.")
        definition = sorted(matches, key=_definition_sort_key)[0]
    else:
        definition = hyperatom
    if definition.kind != HYPERATOM_KIND:
        raise BlenderRenderError(f"{definition.canonical!r} is not a concrete hyperatom definition.")
    return _definition_node(definition, registry, frozenset())


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return '""'
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def write_toml_sidecar(path: str | Path, metadata: dict[str, object]) -> Path:
    """Write a small deterministic TOML companion file (no third-party TOML writer)."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for section, values in metadata.items():
        if not isinstance(values, dict):
            lines.append(f"{section} = {_toml_value(values)}")
            continue
        lines.append("")
        lines.append(f"[{section}]")
        for key, value in values.items():
            if isinstance(value, (tuple, list)):
                encoded = "[" + ", ".join(_toml_value(item) for item in value) + "]"
            else:
                encoded = _toml_value(value)
            lines.append(f"{key} = {encoded}")
    output.write_text("\n".join(lines).lstrip() + "\n", encoding="utf-8")
    return output


def build_blender_command(
    blender_executable: str,
    script_path: str | Path,
    script_args: Sequence[str],
) -> list[str]:
    """Build a deterministic background command with script args after ``--``."""
    return [
        str(blender_executable),
        "--background",
        "--factory-startup",
        "--python-use-system-env",
        "--python-exit-code", "1",
        "--python", str(Path(script_path).resolve()),
        "--",
        *[str(value) for value in script_args],
    ]


def blender_python_environment(base_environment: dict[str, str] | None = None) -> dict[str, str]:
    """Expose the active etoe/Lark installation to Blender's embedded Python.

    Blender can use these paths with ``--python-use-system-env``. Lark and etoe
    are pure Python; users should use a Blender Python version compatible with
    the Python version used to install the package.
    """
    env = dict(os.environ if base_environment is None else base_environment)
    package_root = str(Path(__file__).resolve().parents[1])
    paths = [package_root]
    try:
        import lark
        lark_root = str(Path(lark.__file__).resolve().parent.parent)
        paths.append(lark_root)
    except ImportError:
        # The command will still start; the Blender script will report the
        # missing dependency as a normal Python import error.
        pass
    existing = [item for item in env.get("PYTHONPATH", "").split(os.pathsep) if item]
    combined = list(dict.fromkeys([*paths, *existing]))
    if combined:
        env["PYTHONPATH"] = os.pathsep.join(combined)
    return env


def run_blender(
    blender_executable: str,
    script_path: str | Path,
    script_args: Sequence[str],
) -> int:
    """Start Blender in background mode and return its process exit code."""
    command = build_blender_command(blender_executable, script_path, script_args)
    print("Launching Blender: " + shlex.join(command))
    try:
        completed = subprocess.run(command, env=blender_python_environment(), check=False)
    except FileNotFoundError as exc:
        raise BlenderRenderError(
            f"Blender executable {blender_executable!r} was not found. Install Blender or pass --blender /path/to/blender."
        ) from exc
    except OSError as exc:
        raise BlenderRenderError(f"Could not start Blender: {exc}") from exc
    return int(completed.returncode)


__all__ = [
    "BLENDER_ARTIFACT_CODE",
    "BLENDER_STYLE_CODE",
    "BlenderRenderError",
    "Hyperatom3DNode",
    "build_blender_command",
    "build_hyperatom_3d_tree",
    "blender_python_environment",
    "hyperatom_3d_paths",
    "run_blender",
    "select_hyperatoms",
    "write_toml_sidecar",
]
