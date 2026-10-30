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
    assert len(all_items) == 6


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
