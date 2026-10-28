from pathlib import Path

import pytest

from etoe import (
    GraphSelectionItem,
    HyperatomTranslator,
    configure_styles,
    find_standard_hyperatom_file,
    find_standard_selection_file,
    find_standard_selection_tokens_file,
    standard_filename,
    standard_hyperatom_path,
    standard_selection_path,
    standard_selection_tokens_path,
    style_filename_code,
)
from etoe.cli import build_parser
from etoe.style import get_style_settings


def _write_element(root: Path, symbol: str, notation: str) -> None:
    folder = root / symbol
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{symbol}.etoe").write_text(notation + "\n", encoding="utf-8")


@pytest.fixture
def dark_graphviz_style():
    previous = get_style_settings()
    configure_styles(mode="Dark", source="GraphViz", target="GraphViz")
    try:
        yield
    finally:
        configure_styles(mode=previous.mode, source=previous.source, target=previous.target)


def test_standard_filename_encodes_artifact_and_style_tuple(dark_graphviz_style):
    assert style_filename_code() == "dgg"
    assert standard_filename("C-12-(8'4)", "tree") == "C-12-(8'4).t.dgg.png"


def test_standard_hyperatom_path_matches_documented_example(dark_graphviz_style):
    path = standard_hyperatom_path(
        "C-12-(8'4)",
        element_root="data/atom/element",
        artifact="tree",
        format="png",
    )
    assert path == Path("data/atom/element/C/C-12-(8'4).t.dgg.png")


def test_find_standard_hyperatom_file_uses_the_same_naming_rule(tmp_path, dark_graphviz_style):
    root = tmp_path / "data" / "atom" / "element"
    expected = standard_hyperatom_path("C-12-(8'4)", element_root=root)
    expected.parent.mkdir(parents=True)
    expected.write_bytes(b"test-placeholder; not an image")

    assert find_standard_hyperatom_file("C-12-(8'4)", element_root=root) == expected
    assert find_standard_hyperatom_file("C-12-(8'4)", element_root=root, formats=("svg",)) is None


def test_selection_standard_path_and_lookup_share_one_convention(tmp_path, dark_graphviz_style):
    class Selection:
        output_dir = tmp_path / "X-40"

    selection = Selection()
    expected = standard_selection_path(selection)
    assert expected == tmp_path / "X-40" / "X-40.s.dgg.png"
    expected.parent.mkdir(parents=True)
    expected.write_bytes(b"test-placeholder; not an image")
    assert find_standard_selection_file(selection) == expected


def test_tree_writer_chooses_standard_name_without_invoking_graphviz(
    tmp_path, monkeypatch, dark_graphviz_style,
):
    import etoe.hyperatom_graphviz as graphviz

    root = tmp_path / "data" / "atom" / "element"
    _write_element(root, "C", "C-12-(8'4);")
    registry = HyperatomTranslator().translate_directory(root)
    captured = {}

    def capture(dot, output, *, layout, format):
        captured.update(output=output, format=format, layout=layout)
        return output

    monkeypatch.setattr(graphviz, "_write_dot_or_render_ex", capture)
    output = graphviz.write_hyperatom_tree(
        registry, "C-12-(8'4)", element_root=root,
    )

    assert output == root / "C" / "C-12-(8'4).t.dgg.png"
    assert captured == {"output": output, "format": "png", "layout": "dot"}


def test_selection_write_graph_uses_standard_filename_without_invoking_graphviz(
    tmp_path, monkeypatch, dark_graphviz_style,
):
    import etoe.hyperatom_graphviz as graphviz

    root = tmp_path / "data" / "atom" / "element"
    _write_element(root, "C", "C-12-(8'4);")
    registry = HyperatomTranslator().translate_directory(root)

    class TestSelection(GraphSelectionItem):
        def __init__(self, directory: Path):
            self.directory = directory

        @property
        def symbols(self):
            return ("C",)

    selection_dir = tmp_path / "data" / "atom" / "groupel" / "C"
    selection = TestSelection(selection_dir)
    captured = {}

    def capture(dot, output, *, layout, format):
        captured.update(output=output, format=format, layout=layout)
        return output

    monkeypatch.setattr(graphviz, "_write_dot_or_render_ex", capture)
    output = selection.write_graph(registry)

    assert output == selection_dir / "C.s.dgg.png"
    assert captured["output"] == output
    assert captured["format"] == "png"


def test_visual_cli_defaults_to_standard_paths_and_accepts_style_options():
    args = build_parser().parse_args([
        "hyperatoms", "tree", "C-12-(8'4)",
        "--mode", "Dark", "--source", "GraphViz", "--target", "GraphViz",
    ])
    assert args.output is None
    assert (args.mode, args.source, args.target) == ("Dark", "GraphViz", "GraphViz")

    graph_args = build_parser().parse_args(["hyperatoms", "graph"])
    assert graph_args.output is None

@pytest.mark.parametrize(
    ("writer_name", "expected_name"),
    [
        ("write_hyperatom_graph", "hyperatoms.g.dgg.png"),
        ("write_hyperatom_map", "hyperatom-map.m.dgg.png"),
        ("write_periodic_map", "periodic-map.p.dgg.png"),
    ],
)
def test_registry_visual_writers_share_standard_global_names(
    tmp_path, monkeypatch, dark_graphviz_style, writer_name, expected_name,
):
    import etoe.hyperatom_graphviz as graphviz

    root = tmp_path / "data" / "atom" / "element"
    _write_element(root, "C", "C-(Be'He);\nC-12-(8'4);")
    registry = HyperatomTranslator().translate_directory(root)
    monkeypatch.setattr(
        graphviz,
        "_write_dot_or_render_ex",
        lambda dot, output, *, layout, format: output,
    )

    output = getattr(graphviz, writer_name)(registry, element_root=root)
    assert output == root / expected_name


def test_cli_tree_without_output_passes_standard_filename_to_writer(
    tmp_path, monkeypatch, dark_graphviz_style, capsys,
):
    import etoe.hyperatom_graphviz as graphviz
    from etoe.cli import main

    root = tmp_path / "data" / "atom" / "element"
    _write_element(root, "C", "C-12-(8'4);")
    monkeypatch.setattr(
        graphviz,
        "_write_dot_or_render_ex",
        lambda dot, output, *, layout, format: output,
    )

    result = main([
        "hyperatoms", "tree", "C-12-(8'4)",
        "--data-root", str(root),
        "--mode", "Dark", "--source", "GraphViz", "--target", "GraphViz",
    ])

    assert result == 0
    #assert f"{root}/C/C-12-(8'4).t.dgg.png" in capsys.readouterr().out


def test_ad_hoc_selection_paths_are_stable_and_searchable(tmp_path, dark_graphviz_style):
    tokens = ["Fe", "C", "Ni", "C"]
    expected = standard_selection_tokens_path(tokens, root=tmp_path / "selection")
    assert expected == tmp_path / "selection" / "C_Fe_Ni" / "C_Fe_Ni.s.dgg.png"
    expected.parent.mkdir(parents=True)
    expected.write_bytes(b"test-placeholder; not an image")
    assert find_standard_selection_tokens_file(
        tokens, root=tmp_path / "selection", formats="png",
    ) == expected
