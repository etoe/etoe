from pathlib import Path

import pytest

from etoe import AtomSelectionCatalog, hyperatom_graph_to_dot


PROJECT_ELEMENT_ROOT = Path(__file__).resolve().parents[1] / "data" / "atom" / "element"


@pytest.fixture(scope="module")
def selection_catalog():
    return AtomSelectionCatalog(PROJECT_ELEMENT_ROOT)


def test_chemical_categories_are_exclusive_and_link_elements_and_hyperatoms(selection_catalog):
    catalog = selection_catalog
    assert len(catalog.categories) == 11
    assert sum(len(category.elements) for category in catalog.categories) == len(catalog.element_catalog)

    assert catalog.element_catalog["K"].chemical_category is catalog.categories["alkali-metals"]
    assert catalog.element_catalog["Ca"].category is catalog.categories["alkaline-earth-metals"]
    assert catalog.element_catalog["Fe"].chemical_category.slug == "transition-metals"
    assert catalog.element_catalog["B"].chemical_category.slug == "metalloids"
    assert catalog.element_catalog["F"].chemical_category.slug == "halogens"
    assert catalog.element_catalog["Ne"].chemical_category.slug == "noble-gases"
    assert catalog.element_catalog["Nm"].chemical_category.slug == "unknowns"

    potassium = catalog.categories["alkali-metals"]
    assert "K" in potassium.symbols
    assert any(atom.canonical == "K-40-(33'7)" for atom in potassium.hyperatoms)
    selected_atom = next(atom for atom in potassium.hyperatoms if atom.canonical == "K-40-(33'7)")
    assert selected_atom.chemical_category is potassium
    assert selected_atom.category is potassium


def test_atomic_level_catalog_reuses_inferred_levels_and_provides_graph_tokens(selection_catalog):
    catalog = selection_catalog.levels
    assert catalog.levels
    assert catalog.get(1) is not None
    assert catalog[1].directory.name == "1"
    for level in catalog:
        assert all(atom.atomic_level == level.level for atom in level.hyperatoms)
        assert set(level.symbols) == {atom.canonical for atom in level.hyperatoms}
        assert level.output_dir == level.directory


def test_toml_group_catalogs_read_the_project_custom_groups(selection_catalog):
    elements = selection_catalog.element_groups
    assert len(elements) == 18
    assert elements["Be_B"].symbols == ("Be", "B")
    assert elements["Na_Mg_K_Nm_Ca"].symbols == ("Na", "Mg", "K", "Nm", "Ca")
    assert {item.symbol for item in elements["K_Ca"].elements} == {"K", "Ca"}
    assert elements["K_Ca"].directory.name == "K_Ca"
    assert (elements["K_Ca"].directory / "groupel.toml").is_file()

    hyperatoms = selection_catalog.hyperatom_groups
    assert len(hyperatoms) == 1
    group = hyperatoms["X-40"]
    assert group.symbols == ("K-40-(33'7)", "Ca-40-(32'8)", "Ar-40-(20'20)")
    assert [atom.canonical for atom in group.hyperatoms] == list(group.symbols)
    assert (group.directory / "group.toml").is_file()


def test_graph_builder_accepts_exact_hyperatom_selectors_from_groups(selection_catalog):
    group = selection_catalog.hyperatom_groups["X-40"]
    dot = hyperatom_graph_to_dot(selection_catalog.registry, symbols=group.symbols)
    for atom in group.hyperatoms:
        assert f'"{atom.id}"' in dot
    assert group.output_dir == group.directory
    assert group.symbols_for_graph() == group.symbols


def test_catalogs_are_serializable_without_recursive_object_links(selection_catalog):
    payload = selection_catalog.to_dict()
    assert payload["schema"] == "etoe.atom-selection-catalogs.v1"
    assert payload["chemical_categories"]["schema"] == "etoe.chemical-categories.v1"
    assert payload["atomic_levels"]["schema"] == "etoe.atomic-levels.v1"
    assert payload["element_groups"]["groups"]
    assert payload["hyperatom_groups"]["groups"][0]["hyperatoms"] == [
        "K-40-(33'7)", "Ca-40-(32'8)", "Ar-40-(20'20)"
    ]

    # The new category links are represented as category slugs in existing JSON APIs.
    potassium = selection_catalog.element_catalog["K"].to_dict()
    assert potassium["chemical_category"] == "alkali-metals"
