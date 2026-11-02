"""Geometric hyperatom synthesis and dependency scheduling tests."""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from etoe.blender3d import (
    BlenderRenderError, Hyperatom3DNode, build_hyperatom_3d_tree,
    hyperatom_3d_paths, hyperatom_dependency_order,
)
from etoe.blender_render import _assert_fully_resolved, build_hyperatom_layout
from etoe.hyperatom_map import build_canonical_hyperatom_map
from etoe.hyperatom_synthesis import (
    PROFILES,
    _levitation_vertices,
    simulate_hyperatom_synthesis,
    simulation_fingerprint,
)
from etoe.hyperatom_translation import HyperatomTranslator


DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "atom" / "element"


@pytest.fixture(scope="module")
def registry():
    value = HyperatomTranslator().translate_directory(DATA_ROOT)
    build_canonical_hyperatom_map(value, auto_patch_missing=False)
    return value


def _definition(registry, canonical: str):
    return next(item for item in registry.definitions if item.canonical == canonical)


def test_initial_levitation_configuration_uses_unit_gabarit_nearest_neighbour_spacing():
    for count in (2, 3, 4, 5, 8, 12):
        points = _levitation_vertices(count, minimum_pair_distance=1.0)
        nearest = min(
            math.dist(points[left], points[right])
            for left in range(count) for right in range(left + 1, count)
        )
        assert nearest == pytest.approx(1.0, abs=1e-9)


def test_dependency_order_is_bottom_up_and_deduplicates_artifacts(registry):
    carbon = _definition(registry, "C-12-(8'4)")
    order = hyperatom_dependency_order(registry, [carbon])
    assert [item.canonical for item in order] == [
        "H-1-1", "D-2-(1'1)", "He-4-(2'2)", "Be-8-(4'4)", "C-12-(8'4)"
    ]


def test_rough_and_strict_synthesis_are_deterministic_and_converge(registry):
    for canonical in ("D-2-(1'1)", "He-4-(2'2)", "C-12-(8'4)"):
        definition = _definition(registry, canonical)
        node = build_hyperatom_3d_tree(registry, definition, resolve_references=False)
        layout = build_hyperatom_layout(node)
        for quality in ("rough", "strict"):
            first = simulate_hyperatom_synthesis(node, layout, quality=quality)
            second = simulate_hyperatom_synthesis(node, layout, quality=quality)
            assert first.success
            assert first.residual <= PROFILES[quality].tolerance
            for actual, site in zip(first.final_positions, layout.protium_sites):
                assert actual == pytest.approx(site.center, abs=1e-8)
            assert simulation_fingerprint(first.to_dict()) == simulation_fingerprint(second.to_dict())
            assert first.model["simulation"]["force_law_status"].startswith("phenomenological surrogate")

def test_expected_atomahedron_hierarchy_and_layer_parameters_are_exported(registry):
    from etoe.blender3d import build_hyperatom_3d_tree

    expected = {
        "D-2-(1'1)": ("diatomahedron", [1, 1]),
        "T-3-(2'1)": ("triatomahedron", [2, 2, 1]),
        "Ht-3-(1'1'1)": ("triatomahedron", [1, 1, 1]),
        "He-4-(2'2)": ("tetraatomahedron", [2, 2, 2, 2]),
    }
    for canonical, (atomahedron, depths) in expected.items():
        node = build_hyperatom_3d_tree(registry, _definition(registry, canonical), resolve_references=False)
        layout = build_hyperatom_layout(node)
        assert layout.atomahedron == atomahedron
        assert [site.depth for site in layout.protium_sites] == depths
        result = simulate_hyperatom_synthesis(node, layout, quality="rough")
        root = result.model["root"]
        assert len(root["atmospheric_layers"]) == PROFILES["rough"].atmosphere_layers
        assert root["spin"] is None
        assert "spin" in root["unresolved_parameters"]
        if canonical == "D-2-(1'1)":
            protium = root["children"][0]
            assert len(protium["clumping_layers"]) == PROFILES["rough"].clump_layers
            assert protium["protium_reference"]["minimum_gabarit"] == 1.0

def test_rough_strict_paths_are_separate_and_include_style_code(registry):
    carbon = _definition(registry, "C-12-(8'4)")
    rough = hyperatom_3d_paths(carbon, element_root=DATA_ROOT, quality="rough", mode="Light")
    strict = hyperatom_3d_paths(carbon, element_root=DATA_ROOT, quality="strict", mode="Light")
    point_cloud = hyperatom_3d_paths(
        carbon, element_root=DATA_ROOT, quality="rough", mode="Light", representation="point-cloud"
    )
    assert rough["simulation"].name == "C-12-(8'4).rough.toml"
    assert rough["blend"].name == "C-12-(8'4).rough.3.l33.blend"
    assert strict["simulation"].name == "C-12-(8'4).strict.toml"
    assert strict["blend"].name == "C-12-(8'4).strict.3.l33.blend"
    assert rough["blend"] != strict["blend"]
    assert point_cloud["blend"].name == "C-12-(8'4).rough.3.l33.point-cloud.blend"
    assert point_cloud["simulation"].name == "C-12-(8'4).rough.l33.point-cloud.toml"
    assert point_cloud["blend"] != rough["blend"]

def test_cli_exposes_hyperatom_batch_selection_quality_and_rebuild():
    from etoe.cli import build_parser

    args = build_parser().parse_args([
        "hyperatoms", "render-3d", "--element", "C", "--elements", "Be,He",
        "--category", "noble-gases", "--quality", "strict", "--rebuild",
        "--attempts", "7", "--representation", "wireframe",
    ])
    assert args.element == ["C"]
    assert args.elements == "Be,He"
    assert args.category == ["noble-gases"]
    assert args.quality == "strict"
    assert args.rebuild is True
    assert args.attempts == 7
    assert args.representation == "wireframe"


def test_unresolved_subatom_reference_blocks_parent_synthesis():
    child = Hyperatom3DNode(
        canonical="X-1-1", designation="X-1-1", symbol="X", atomic_mass=1,
        atomic_level=None, chemical_category="unknowns", resolved=False,
    )
    root = Hyperatom3DNode(
        canonical="Y-2-(1'1)", designation="Y-2-(1'1)", symbol="Y", atomic_mass=2,
        atomic_level=None, chemical_category="unknowns", resolved=True, children=(child,),
    )
    with pytest.raises(BlenderRenderError, match="unresolved subatom reference"):
        _assert_fully_resolved(root, root=root.canonical)


def test_classic_interaction_converges_without_interpenetration_and_records_force_terms(registry):
    for canonical in ("D-2-(1'1)", "He-4-(2'2)", "C-12-(8'4)"):
        definition = _definition(registry, canonical)
        node = build_hyperatom_3d_tree(registry, definition, resolve_references=False)
        layout = build_hyperatom_layout(node)
        for quality in ("rough", "strict"):
            result = simulate_hyperatom_synthesis(
                node, layout, quality=quality, physics="classic",
                gravity_weight=0.85, magnetic_weight=0.15,
            )
            assert result.success
            assert result.residual <= PROFILES[quality].tolerance
            force_model = result.model["simulation"]
            assert force_model["physics"] == "classic"
            assert force_model["gravity_antigravity"]["weight"] == pytest.approx(0.85)
            assert force_model["magnetic_dipole"]["weight"] == pytest.approx(0.15)
            assert force_model["minimum_final_pair_distance"] >= 1.0 - 1e-5
            assert force_model["accepted_atomahedron"] == layout.atomahedron
            assert force_model["source_atomahedron_geometry_match"] is True
            assert result.frames[-1].spin_axes
            def terminal_protia(current):
                children = current.get("children", [])
                if children:
                    for child in children:
                        yield from terminal_protia(child)
                elif current.get("symbol") == "H":
                    yield current
            leaves = list(terminal_protia(result.model["root"]))
            assert len(leaves) == len(layout.protium_sites)
            assert all(
                leaf["protium_parameters"]["spin"]["status"].startswith("final axis")
                for leaf in leaves
            )


def test_classic_initial_state_uses_unit_gabarit_and_geometry_target_is_separate(registry):
    definition = _definition(registry, "D-2-(1'1)")
    node = build_hyperatom_3d_tree(registry, definition, resolve_references=False)
    layout = build_hyperatom_layout(node)
    result = simulate_hyperatom_synthesis(node, layout, physics="classic")
    initial_distance = math.dist(*result.initial_positions)
    final_distance = math.dist(*result.final_positions)
    assert initial_distance == pytest.approx(1.0, abs=1e-8)
    assert final_distance >= 1.0
    assert final_distance == pytest.approx(1.15, abs=0.02)


def test_protium_parameter_retrieval_is_separate_from_hyperatom_synthesis(registry):
    from etoe.hyperatom_synthesis import build_protium_parameter_result, default_protium_parameters

    definition = _definition(registry, "H-1-1")
    node = build_hyperatom_3d_tree(registry, definition, resolve_references=False)
    parameters = default_protium_parameters("strict")
    layout = build_hyperatom_layout(node, parameter_models={"H-1-1": parameters})
    result = build_protium_parameter_result(node, layout, quality="strict")
    assert result.success
    assert result.steps == 0
    assert result.attempt_count == 0
    assert result.expected_atomahedron == "protium-body"
    assert result.model["protium_parameters"]["maximum_gabarit_size_model_units"] == 1.0
    assert result.model["root"]["outer_radius_model_units"] == pytest.approx(0.5, abs=1e-6)
    assert len(result.model["protium_parameters"]["clumping_layers"]) == PROFILES["strict"].clump_layers
    assert len(result.model["protium_parameters"]["atmospheric_layers"]) == PROFILES["strict"].atmosphere_layers
    assert result.model["simulation"]["physics"] == "not-applicable"
    assert result.model["root"]["protium_parameters"]["spin"]["axis"] == [0.0, 0.0, 1.0]


def test_reserved_physics_models_fail_explicitly_until_force_laws_exist(registry):
    definition = _definition(registry, "D-2-(1'1)")
    node = build_hyperatom_3d_tree(registry, definition, resolve_references=False)
    layout = build_hyperatom_layout(node)
    for physics in ("vanguard", "natural"):
        with pytest.raises(NotImplementedError, match="reserved"):
            simulate_hyperatom_synthesis(node, layout, physics=physics)


def test_cli_exposes_physics_weights_and_protium_guides():
    from etoe.cli import build_parser

    args = build_parser().parse_args([
        "hyperatoms", "render-3d", "--hyperatom", "D-2-(1'1)",
        "--physics", "classic", "--gravity-weight", "0.9", "--magnetic-weight", "0.1",
        "--show-protium-axis", "--show-protium-spin",
    ])
    assert args.physics == "classic"
    assert args.gravity_weight == pytest.approx(0.9)
    assert args.magnetic_weight == pytest.approx(0.1)
    assert args.show_protium_axis is True
    assert args.show_protium_spin is True


def test_protium_spin_guide_style_is_resolved_from_shared_tokens():
    from etoe.style import resolve_style

    style = resolve_style("3D", "protium-spin", mode="Dark", source="3D", target="3D")
    assert style["axis_color"] == "#FBBF24"
    assert style["equator_color"] == "#67E8F9"
    assert style["axis_width"] > 0
    assert style["equator_width"] > 0


def test_standalone_protium_has_unit_maximum_gabarit(registry):
    definition = _definition(registry, "H-1-1")
    node = build_hyperatom_3d_tree(registry, definition, resolve_references=False)
    layout = build_hyperatom_layout(node)
    assert 2.0 * layout.outer_radius == pytest.approx(1.0, abs=1e-5)
