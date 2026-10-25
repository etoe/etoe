from pathlib import Path

import pytest

from etoe import (
    HyperatomTranslator,
    build_element_subelement_numbering,
    hyperatom_map_to_dot,
    hyperatom_tree_to_dot,
    periodic_map_to_dot,
    write_hyperatom_map,
    write_hyperatom_tree,
    write_periodic_map,
)
from etoe.hyperatom_translation import ELEMENT_SYMBOL_KIND, ELEMENT_TEMPLATE_KIND, HYPERATOM_KIND


DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "atom" / "element"


@pytest.fixture(scope="module")
def registry():
    return HyperatomTranslator().translate_directory(DATA_ROOT)


def _find(registry, canonical):
    return next(obj for obj in registry.definitions if obj.canonical == canonical)


def test_subelement_numbering_is_bottom_up_and_isotope_variants_inherit_template_number(registry):
    numbers = build_element_subelement_numbering(registry)
    expected = {
        "He-(D'D)": 1,
        "He-(He'H)": 2,
        "He-4-(2'2)": 1,
        "He-5-(4'1)": 2,
        "D-(H'H)": 0,
        "T-(D'H)": 0,
        "Ht-(H'H'H)": 0,
        "D-2-(1'1)": 0,
        "C-(Be'He)": 1,
        "C-(C'H)": 2,
        "C-12-(8'4)": 1,
        "C-13-(12'1)": 2,
        "H-1-1": 0,
    }
    for canonical, number in expected.items():
        assert numbers[_find(registry, canonical).id] == number


def test_periodic_map_uses_full_canonical_labels_and_direct_recursive_subelement_edge(registry):
    dot = periodic_map_to_dot(registry, symbols=["He"])
    assert 'graph [rankdir="TB"' in dot
    assert 'label="He:1-(D\'D)"' in dot
    assert 'label="He:2-(He:1\'H)"' in dot
    assert 'label="He:1-4-(2\'2)"' not in dot
    assert 'label="He:2-5-(4\'1)"' not in dot
    assert 'label="H-1-1"' not in dot
    assert 'label="D"' in dot
    assert 'label="D:1-(H\'H)"' not in dot
    assert ":0" not in dot

    element_ids = {
        obj.id for obj in registry.definitions
        if obj.kind in {ELEMENT_TEMPLATE_KIND, ELEMENT_SYMBOL_KIND}
    }
    node_ids = {
        line.split('"', 2)[1]
        for line in dot.splitlines()
        if '" [label=' in line
    }
    assert node_ids <= element_ids
    lower = _find(registry, "He-(D'D)")
    higher = _find(registry, "He-(He'H)")
    assert f'"{higher.id}" -> "{lower.id}"' in dot
    # The recursive reference should not be left as an ambiguity proxy.
    assert f'"{higher.id}" -> "ref_' not in dot


def test_h_dt_and_ht_keep_zero_index_but_preserve_structural_edges(registry):
    numbers = build_element_subelement_numbering(registry)
    cases = (
        ("H", "H", ()),
        ("D", "D-(H'H)", (("H", "H"),)),
        ("T", "T-(D'H)", (("D", "D-(H'H)"), ("H", "H"))),
        ("Ht", "Ht-(H'H'H)", (("H", "H"),)),
    )
    for symbol, canonical, children in cases:
        element = _find(registry, canonical)
        assert numbers[element.id] == 0
        dot = periodic_map_to_dot(registry, symbols=[symbol])
        assert f'label="{symbol}"' in dot
        assert f'label="{symbol}:1' not in dot
        for child_symbol, child_canonical in children:
            child = _find(registry, child_canonical)
            assert child.symbol == child_symbol
            assert f'"{element.id}" -> "{child.id}"' in dot
        if not children:
            assert f'"{element.id}" ->' not in dot


def test_periodic_helium_map_preserves_deuterium_to_hydrogen_edge(registry):
    dot = periodic_map_to_dot(registry, symbols=["He"])
    deuterium = _find(registry, "D-(H'H)")
    hydrogen = _find(registry, "H")
    assert f'label="D"' in dot
    assert f'label="H"' in dot
    assert f'"{deuterium.id}" -> "{hydrogen.id}"' in dot


def test_periodic_map_for_deuterium_includes_hydrogen_child(registry):
    dot = periodic_map_to_dot(registry, symbols=["D"])
    deuterium = _find(registry, "D-(H'H)")
    hydrogen = _find(registry, "H")
    assert f'"{deuterium.id}" -> "{hydrogen.id}"' in dot


def test_periodic_map_preserves_element_component_multiplicity(registry):
    """Each subatom occurrence produces its own edge, even to the same node."""
    cases = (
        ("D-(H'H)", "H", 2),
        ("Ht-(H'H'H)", "H", 3),
        ("T-(D'H)", "H", 1),
        ("T-(D'H)", "D-(H'H)", 1),
    )
    for parent_canonical, child_canonical, expected_count in cases:
        parent = _find(registry, parent_canonical)
        child = _find(registry, child_canonical)
        dot = periodic_map_to_dot(registry, symbols=[parent.symbol])
        edge_prefix = f'  "{parent.id}" -> "{child.id}" '
        assert sum(line.startswith(edge_prefix) for line in dot.splitlines()) == expected_count


def test_periodic_map_svg_renders_parallel_edges(tmp_path, registry):
    """Graphviz output retains two D->H edges and three Ht->H edges."""
    import shutil
    import subprocess

    dot_executable = shutil.which("dot")
    if dot_executable is None:
        pytest.skip("Graphviz `dot` is not installed")
    svg_path = tmp_path / "periodic-He.svg"
    write_periodic_map(registry, svg_path, symbols=["He"])
    svg = svg_path.read_text(encoding="utf-8")
    deuterium = _find(registry, "D-(H'H)")
    hydrogen = _find(registry, "H")
    edge_title = f'{deuterium.id}&#45;&gt;{hydrogen.id}'
    # Graphviz renders every parallel edge as its own <g class="edge"> group.
    # Match the edge tooltip instead of depending on generated SVG IDs.
    import re
    groups = re.findall(r'<g id="edge[^>]*" class="edge">.*?</g>', svg, flags=re.S)
    d_to_h_groups = [group for group in groups if edge_title in group or f'{deuterium.id}-&gt;{hydrogen.id}' in group]
    assert len(d_to_h_groups) == 2


def test_tree_unfolds_each_subatom_occurrence_as_a_distinct_node(registry):
    dot = hyperatom_tree_to_dot(registry, "He-5-(4'1)")
    assert 'graph [rankdir="TB"' in dot
    assert "digraph hyperatom_tree" in dot
    # He-5 -> He-4 + H; each of the two D subatoms in He-4 is unfolded
    # separately, including its own two H occurrences: 9 occurrences total.
    node_lines = [line for line in dot.splitlines() if " [label=" in line and " -> " not in line]
    assert len(node_lines) == 9
    assert sum('label="D-2-(1\'1)"' in line for line in node_lines) == 2
    assert sum('label="H-1-1"' in line for line in node_lines) == 5
    assert len({line.split('"', 2)[1] for line in node_lines}) == len(node_lines)
    assert not any('shape="diamond"' in line for line in node_lines)


def test_subelement_number_visibility_can_be_disabled_for_all_graph_types(registry):
    periodic = periodic_map_to_dot(registry, symbols=["He"], show_subelement_numbers=False)
    assert 'label="He-(D\'D)"' in periodic
    assert 'label="He-(He\'H)"' in periodic
    assert ":1" not in periodic

    hyper_map = hyperatom_map_to_dot(registry, symbols=["He"], show_subelement_numbers=False)
    assert 'label="He-4-(2\'2)"' in hyper_map
    assert 'label="He-5-(4\'1)"' in hyper_map
    assert ":1-4" not in hyper_map and ":2-5" not in hyper_map

    tree = hyperatom_tree_to_dot(registry, "He-5-(4'1)", show_subelement_numbers=False)
    assert 'label="He-5-(4\'1)"' in tree
    assert ":1-4" not in tree and ":2-5" not in tree


def test_hyperatom_map_contains_only_concrete_hyperatom_nodes(registry, tmp_path):
    dot = hyperatom_map_to_dot(registry, symbols=["He"])
    assert "digraph hyperatom_map" in dot
    assert 'label="He:1-4-(2\'2)"' in dot
    assert 'label="He:2-5-(4\'1)"' in dot
    assert 'label="He:1-(D\'D)"' not in dot
    assert "ambiguous ×" not in dot
    hyperatom_ids = {obj.id for obj in registry.definitions if obj.kind == HYPERATOM_KIND}
    node_ids = {
        line.split('"', 2)[1]
        for line in dot.splitlines()
        if '" [label=' in line
    }
    assert node_ids <= hyperatom_ids
    output = write_hyperatom_map(registry, tmp_path / "hyperatom-map.dot", symbols=["He"])
    assert output.is_file()
    assert "digraph hyperatom_map" in output.read_text(encoding="utf-8")


def test_hyperatom_map_preserves_component_multiplicity(registry):
    """Each concrete subatom occurrence contributes its own outgoing edge."""
    cases = (
        ("He-4-(2'2)", "D-2-(1'1)", 2),
        ("D-2-(1'1)", "H-1-1", 2),
        ("He-5-(4'1)", "He-4-(2'2)", 1),
        ("He-5-(4'1)", "H-1-1", 1),
    )
    dot = hyperatom_map_to_dot(registry, symbols=["He"])
    for parent_canonical, child_canonical, expected_count in cases:
        parent = _find(registry, parent_canonical)
        child = _find(registry, child_canonical)
        edge_prefix = f'  "{parent.id}" -> "{child.id}" '
        assert sum(line.startswith(edge_prefix) for line in dot.splitlines()) == expected_count


def test_hyperatom_map_svg_renders_parallel_edges(tmp_path, registry):
    """Graphviz renders both He-4 -> D edges as distinct SVG edge groups."""
    import re
    import shutil

    if shutil.which("dot") is None:
        pytest.skip("Graphviz `dot` is not installed")
    svg_path = tmp_path / "hyperatom-He.svg"
    write_hyperatom_map(registry, svg_path, symbols=["He"])
    svg = svg_path.read_text(encoding="utf-8")
    parent = _find(registry, "He-4-(2'2)")
    child = _find(registry, "D-2-(1'1)")
    edge_title = f'{parent.id}&#45;&gt;{child.id}'
    groups = re.findall(r'<g id="edge[^>]*" class="edge">.*?</g>', svg, flags=re.S)
    parent_child_edges = [
        group for group in groups
        if edge_title in group or f'{parent.id}-&gt;{child.id}' in group
    ]
    assert len(parent_child_edges) == 2


def test_tree_can_be_written_to_a_file_and_rejects_non_hyperatom_roots(registry, tmp_path):
    output = write_hyperatom_tree(registry, "He-4-(2'2)", tmp_path / "trees" / "He-4.dot")
    assert output.is_file()
    assert "digraph hyperatom_tree" in output.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="not a concrete hyperatom"):
        hyperatom_tree_to_dot(registry, "He-(D'D)")


def test_periodic_map_writer_and_numbering_are_deterministic(registry, tmp_path):
    first = build_element_subelement_numbering(registry)
    second = build_element_subelement_numbering(registry)
    assert first == second

    output = write_periodic_map(registry, tmp_path / "periodic.dot", symbols=["He"])
    assert output.is_file()
    text = output.read_text(encoding="utf-8")
    assert 'label="He:2-(He:1\'H)"' in text


def test_cli_exposes_periodic_map_and_tree_subcommands(tmp_path):
    from etoe.cli import main

    periodic_output = tmp_path / "periodic-He.dot"
    tree_output = tmp_path / "He-5-tree.dot"
    assert main([
        "hyperatoms", "periodic-map",
        "--data-root", str(DATA_ROOT),
        "--symbols", "He",
        "--output", str(periodic_output),
    ]) == 0
    assert 'label="He:2-(He:1\'H)"' in periodic_output.read_text(encoding="utf-8")

    assert main([
        "hyperatoms", "tree", "He-5-(4'1)",
        "--data-root", str(DATA_ROOT),
        "--output", str(tree_output),
        "--hide-subelement-numbers",
    ]) == 0
    tree_text = tree_output.read_text(encoding="utf-8")
    assert "digraph hyperatom_tree" in tree_text
    assert 'label="He-5-(4\'1)"' in tree_text
    assert ":2-5" not in tree_text

    hyperatom_map_output = tmp_path / "hyperatom-map-He.dot"
    assert main([
        "hyperatoms", "hyperatom-map",
        "--data-root", str(DATA_ROOT),
        "--symbols", "He",
        "--output", str(hyperatom_map_output),
        "--hide-subelement-numbers",
    ]) == 0
    hyperatom_map_text = hyperatom_map_output.read_text(encoding="utf-8")
    assert "digraph hyperatom_map" in hyperatom_map_text
    assert 'label="He-5-(4\'1)"' in hyperatom_map_text
    assert 'label="He-(He\'H)"' not in hyperatom_map_text
