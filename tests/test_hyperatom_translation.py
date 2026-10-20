from pathlib import Path

import pytest

from etoe.hyperatom_translation import HyperatomTranslator, _components_from_structure, _pattern_matches_structure
from etoe.parser import EToEParser
from etoe.hyperatom_graphviz import hyperatom_graph_to_dot, write_hyperatom_graph


DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "atom" / "element"


@pytest.fixture(scope="module")
def registry():
    return HyperatomTranslator().translate_directory(DATA_ROOT)


def _find(registry, canonical):
    return next(obj for obj in registry.definitions if obj.canonical == canonical)


def test_translate_all_element_files_and_balance_declared_masses(registry):
    assert registry.source_file_count == 123
    assert registry.statement_count == 457
    assert len(registry.definitions) == 457
    mass_bearing = [obj for obj in registry.definitions if obj.atomic_mass is not None and obj.components]
    assert mass_bearing
    assert all(obj.mass_balance == "consistent" for obj in mass_bearing)
    assert all(obj.matter_level == 5 for obj in mass_bearing)
    assert max(obj.syntax_depth for obj in mass_bearing) > 0


def test_numeric_components_resolve_to_semantic_hyperatoms(registry):
    carbon = _find(registry, "C-12-(8'4)")
    assert [component.mass for component in carbon.components] == [8, 4]
    assert all(component.resolution == "unique" for component in carbon.components)
    resolved = [registry.get(component.candidate_ids[0]) for component in carbon.components]
    assert [obj.atomic_mass for obj in resolved] == [8, 4]



def test_apostrophe_joined_subatoms_match_as_an_unordered_multiset():
    parser = EToEParser()
    reversed_pattern = parser.parse_statement("C-12-(4'8)")
    canonical_definition = parser.parse_statement("C-12-(8'4)")
    assert reversed_pattern.structure is not None
    assert canonical_definition.structure is not None
    assert _pattern_matches_structure(
        _components_from_structure(reversed_pattern.structure),
        canonical_definition.structure,
    )


def test_parenthesized_mass_group_infers_mass_without_losing_group_structure(registry):
    magnesium = _find(registry, "Mg-26-(16'(5'5))")
    group = magnesium.components[1]
    assert group.reference_kind == "group"
    assert group.mass == 10
    assert group.mass_origin == "inferred_sum"
    assert group.resolution == "unique"
    assert registry.get(group.candidate_ids[0]).canonical == "Be-10-(5'5)"


def test_symbolic_template_ambiguity_is_preserved_not_first_match_wins(registry):
    silver_template = _find(registry, "Ag-(Co'V)")
    co_reference = silver_template.components[0]
    assert co_reference.resolution == "ambiguous"
    assert len(co_reference.candidate_ids) > 1
    assert all(registry.get(candidate_id).symbol == "Co" for candidate_id in co_reference.candidate_ids)


def test_custom_element_symbols_from_element_folders_are_not_misclassified_as_molecules(registry):
    nm = _find(registry, "Nm-46-(24'22)")
    x = _find(registry, "X-107-(64'43)")
    assert nm.kind == "hyperatom"
    assert x.kind == "hyperatom"


def test_graphviz_export_keeps_ambiguity_visible_and_is_deterministic(registry, tmp_path):
    first = hyperatom_graph_to_dot(registry)
    second = hyperatom_graph_to_dot(registry)
    assert first == second
    assert "digraph hyperatoms" in first
    assert "candidate" in first
    assert "ambiguous" in first
    assert "C-12" in first
    out = write_hyperatom_graph(registry, tmp_path / "hyperatoms.dot")
    assert out.exists()
    assert out.read_text(encoding="utf-8") == first


def test_source_comments_are_preserved_and_associated_with_their_statements(registry):
    hydrogen = _find(registry, "H-1-1")
    carbon = _find(registry, "C-12-(8'4)")
    assert hydrogen.source_comments == ("// 99.989",)
    assert carbon.source_comments == ("// 98.930",)
    assert registry.statistics()["source_comments"] == len(registry.source_annotations)
    assert any(annotation.text == "// 98.930" and annotation.line_number > 0
               for annotation in registry.source_annotations)
