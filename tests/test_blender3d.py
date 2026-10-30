"""Blender bridge and structural scene-data tests; no Blender binary required."""
from pathlib import Path
import tomllib

import pytest

from etoe.blender3d import (
    BlenderRenderError,
    BLENDER_STYLE_CODE,
    build_blender_command,
    build_hyperatom_3d_tree,
    hyperatom_3d_paths,
    select_hyperatoms,
    write_toml_sidecar,
)
from etoe.hyperatom_translation import HyperatomTranslator


def _write_element(root: Path, symbol: str, *statements: str) -> None:
    folder = root / symbol
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{symbol}.etoe").write_text("\n".join(f"{item};" for item in statements) + "\n", encoding="utf-8")


@pytest.fixture()
def registry(tmp_path):
    root = tmp_path / "data" / "atom" / "element"
    _write_element(root, "H", "H-1")
    _write_element(root, "D", "D-2-(1'1)")
    _write_element(root, "T", "T-3-(2'1)")
    _write_element(root, "Ht", "Ht-3-(1'1'1)")
    _write_element(root, "He", "He-4-(2'2)")
    _write_element(root, "Be", "Be-8-(4'4)")
    _write_element(root, "C", "C-12-(8'4)")
    _write_element(root, "Li", "Li-6-(4'2)")
    return HyperatomTranslator().translate_directory(root)


def test_hyperatom_3d_paths_follow_requested_blend_and_png_convention(registry, tmp_path):
    atom = next(item for item in registry.definitions if item.canonical == "C-12-(8'4)")
    paths = hyperatom_3d_paths(atom, element_root=registry.root)
    expected = Path(registry.root) / "C" / f"C-12-(8'4).3.{BLENDER_STYLE_CODE}.blend"
    assert paths["blend"] == expected
    assert str(paths["png"]) == str(expected) + ".png"
    assert str(paths["blend_toml"]) == str(expected) + ".toml"
    assert str(paths["png_toml"]) == str(expected) + ".png.toml"


def test_output_path_must_be_blend(registry, tmp_path):
    atom = next(item for item in registry.definitions if item.canonical == "C-12-(8'4)")
    with pytest.raises(BlenderRenderError, match=".blend"):
        hyperatom_3d_paths(atom, output=tmp_path / "wrong.png")


def test_select_hyperatoms_by_exact_symbol_category_and_all(registry):
    by_symbol = select_hyperatoms(registry, elements=("C", "He"))
    assert {item.canonical for item in by_symbol} == {"C-12-(8'4)", "He-4-(2'2)"}

    by_category = select_hyperatoms(registry, categories=("alkali-metals",))
    assert {item.canonical for item in by_category} == {"Li-6-(4'2)"}

    all_items = select_hyperatoms(registry, all_elements=True)
    assert len(all_items) == 8


def test_select_hyperatoms_rejects_missing_or_unknown_selectors(registry):
    with pytest.raises(BlenderRenderError, match="Choose at least one"):
        select_hyperatoms(registry)
    with pytest.raises(BlenderRenderError, match="Unknown chemical element"):
        select_hyperatoms(registry, elements=("Qq",))
    with pytest.raises(BlenderRenderError, match="Unknown chemical category"):
        select_hyperatoms(registry, categories=("not-a-category",))


def test_structural_tree_uses_canonical_mass_linking_recursively(registry):
    tree = build_hyperatom_3d_tree(registry, "C-12-(8'4)")
    assert tree.canonical == "C-12-(8'4)"
    assert tree.atomic_level == 5
    assert [item.canonical for item in tree.children] == ["Be-8-(4'4)", "He-4-(2'2)"]
    assert tree.children[0].atomic_level == 4
    assert [item.canonical for item in tree.children[0].children] == ["He-4-(2'2)", "He-4-(2'2)"]
    assert [item.canonical for item in tree.children[1].children] == ["D-2-(1'1)", "D-2-(1'1)"]
    assert tree.children[1].children[0].children[0].canonical == "H-1"


def test_toml_sidecar_is_valid_and_round_trips(tmp_path):
    path = write_toml_sidecar(tmp_path / "scene.blend.toml", {
        "schema": "etoe.hyperatom-3d-artifact.v1",
        "hyperatom": {"canonical": "C-12-(8'4)", "atomic_mass": 12, "resolved": True},
        "renderer": {"name": "Blender", "resolution": 1200},
    })
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "etoe.hyperatom-3d-artifact.v1"
    assert payload["hyperatom"]["canonical"] == "C-12-(8'4)"
    assert payload["hyperatom"]["resolved"] is True


def test_blender_command_uses_background_python_and_double_dash(tmp_path):
    script = tmp_path / "render_hyperatoms.py"
    command = build_blender_command("/opt/blender", script, ["--element", "C"])
    assert command[:2] == ["/opt/blender", "--background"]
    assert "--python" in command
    assert command[command.index("--python") + 1] == str(script.resolve())
    assert command[command.index("--") + 1:] == ["--element", "C"]


def test_cli_render_3d_only_delegates_to_blender(monkeypatch, capsys):
    import etoe.blender3d as blender3d
    from etoe.cli import main

    captured = {}

    def fake_run(executable, script, args):
        captured.update(executable=executable, script=script, args=list(args))
        return 0

    monkeypatch.setattr(blender3d, "run_blender", fake_run)
    code = main([
        "hyperatoms", "render-3d", "--hyperatom", "C-12-(8'4)",
        "--blender", "/opt/blender", "--mode", "Dark",
    ])
    assert code == 0
    assert captured["executable"] == "/opt/blender"
    assert captured["script"].name == "blender_render.py"
    assert captured["args"][captured["args"].index("--hyperatom") + 1] == "C-12-(8'4)"
    assert captured["args"][captured["args"].index("--mode") + 1] == "Dark"
    assert "Launching Blender" not in capsys.readouterr().out


def test_blender_script_receives_only_arguments_after_double_dash():
    from etoe.blender_render import blender_script_args

    assert blender_script_args([
        "blender", "--background", "--python", "render.py", "--",
        "--hyperatom", "C-12-(8'4)", "--mode", "Dark",
    ]) == ["--hyperatom", "C-12-(8'4)", "--mode", "Dark"]
    assert blender_script_args(["blender", "--background", "--python", "render.py"]) == []


def test_atomahedron_position_layouts_are_deterministic_and_unit_normalized():
    from etoe.blender_render import _child_positions

    for arity in (2, 3, 4, 5, 7):
        first = _child_positions(arity)
        assert len(first) == arity
        assert first == _child_positions(arity)
        for point in first:
            assert sum(value * value for value in point) == pytest.approx(1.0)


def test_bottom_up_atomahedron_layout_uses_protium_leaves_and_preserves_hierarchy(registry):
    from etoe.blender_render import build_hyperatom_layout, _protium_depths

    def layout(canonical):
        definition = next(item for item in registry.definitions if item.canonical == canonical)
        tree = build_hyperatom_3d_tree(registry, definition, resolve_references=False)
        return build_hyperatom_layout(tree)

    deuterium = layout("D-2-(1'1)")
    tritium = layout("T-3-(2'1)")
    helitrium = layout("Ht-3-(1'1'1)")
    helium4 = layout("He-4-(2'2)")

    assert (deuterium.atomahedron, len(deuterium.protium_sites)) == ("diatomahedron", 2)
    assert (tritium.atomahedron, len(tritium.protium_sites)) == ("triatomahedron", 3)
    assert (helitrium.atomahedron, len(helitrium.protium_sites)) == ("triatomahedron", 3)
    assert (helium4.atomahedron, len(helium4.protium_sites)) == ("tetraatomahedron", 4)

    # Tritium is a D sub-hyperatom plus one Protium: its three Protia occupy
    # different hierarchy depths. Helitrium's three Protia are co-level.
    assert _protium_depths(tritium.node) == (2, 2, 1)
    assert _protium_depths(helitrium.node) == (1, 1, 1)
    assert _protium_depths(helium4.node) == (2, 2, 2, 2)

    # Semantic containment is preserved: D stays nested inside T; He-4 has
    # two D sub-hyperatoms, each containing a pair of Protium sites.
    assert len(tritium.children) == 2
    assert tritium.children[0].atomahedron == "diatomahedron"
    assert len(tritium.children[0].protium_sites) == 2
    assert len(tritium.children[1].protium_sites) == 1
    assert len(helium4.children) == 2
    assert all(child.atomahedron == "diatomahedron" for child in helium4.children)
    assert all(len(child.protium_sites) == 2 for child in helium4.children)


def test_deeper_protium_is_more_compressed_and_more_deformed(registry):
    from etoe.blender_render import build_hyperatom_layout

    definition = next(item for item in registry.definitions if item.canonical == "T-3-(2'1)")
    tree = build_hyperatom_3d_tree(registry, definition, resolve_references=False)
    layout = build_hyperatom_layout(tree)
    deeper_pair = layout.protium_sites[:2]
    upper_protium = layout.protium_sites[2]

    assert all(site.depth == 2 for site in deeper_pair)
    assert upper_protium.depth == 1
    assert all(site.radius < upper_protium.radius for site in deeper_pair)
    assert all(site.deformation > upper_protium.deformation for site in deeper_pair)


def test_bottom_up_layout_centers_proton_groups_on_atomahedron_vertices(registry):
    from etoe.blender_render import build_hyperatom_layout

    definition = next(item for item in registry.definitions if item.canonical == "Ht-3-(1'1'1)")
    tree = build_hyperatom_3d_tree(registry, definition, resolve_references=False)
    layout = build_hyperatom_layout(tree)
    sites = [site.center for site in layout.protium_sites]

    # Three same-level Protia are at the vertices of an equilateral triangle.
    distances = []
    for index in range(3):
        left, right = sites[index], sites[(index + 1) % 3]
        distances.append(sum((left[axis] - right[axis]) ** 2 for axis in range(3)) ** 0.5)
    assert distances[0] == pytest.approx(distances[1])
    assert distances[1] == pytest.approx(distances[2])


def test_renderer_metadata_describes_bottom_up_geometry_without_a_core(registry, tmp_path):
    from etoe.blender_render import _artifact_metadata, build_hyperatom_layout

    definition = next(item for item in registry.definitions if item.canonical == "T-3-(2'1)")
    tree = build_hyperatom_3d_tree(registry, definition, resolve_references=False)
    layout = build_hyperatom_layout(tree)
    metadata = _artifact_metadata(
        tree,
        layout,
        tmp_path / "T-3-(2'1).blend",
        mode="Dark",
        engine="eevee",
        resolution=1200,
        samples=64,
        shell_layers=3,
        max_depth=0,
        artifact="blender-scene",
    )
    assert metadata["schema"] == "etoe.hyperatom-3d-artifact.v2"
    assert metadata["hyperatom"]["atomahedron"] == "triatomahedron"
    assert metadata["geometry"]["construction_order"] == "bottom-up"
    assert metadata["geometry"]["protium_hierarchy_depths"] == [2, 2, 1]
    assert metadata["geometry"]["has_core"] is False


def test_old_flat_renderer_sidecars_are_not_treated_as_current(tmp_path):
    from etoe.blender_render import _artifacts_use_current_geometry

    paths = {
        "blend_toml": tmp_path / "scene.blend.toml",
        "png_toml": tmp_path / "scene.blend.png.toml",
    }
    for path in paths.values():
        path.write_text('schema = "etoe.hyperatom-3d-artifact.v1"\n', encoding="utf-8")
    assert not _artifacts_use_current_geometry(paths)
    for path in paths.values():
        path.write_text('schema = "etoe.hyperatom-3d-artifact.v2"\n', encoding="utf-8")
    assert _artifacts_use_current_geometry(paths)
