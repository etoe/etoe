from pathlib import Path

from etoe import ElementCatalog, HyperatomTranslator, build_canonical_hyperatom_map
from etoe.hyperatom_translation import _components_from_structure
from etoe.parser import EToEParser


DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "atom" / "element"


def _write_element(root: Path, symbol: str, text: str) -> None:
    folder = root / symbol
    folder.mkdir(parents=True)
    (folder / f"{symbol}.etoe").write_text(text + "\n", encoding="utf-8")


def test_apostrophe_joined_components_are_mass_sorted_recursively():
    parser = EToEParser()
    statement = parser.parse_statement("Qq-30-(3-(4'8)'9'12)")
    assert statement.structure is not None

    components = _components_from_structure(statement.structure)
    assert [component.mass for component in components] == [12, 9, 3]
    assert components[2].canonical_structure == "3-(8'4)"


def test_structure_keys_ignore_sibling_order_but_keep_source_canonical_lossless(tmp_path):
    _write_element(tmp_path, "Qq", "Qq-20-(9'11);")
    _write_element(tmp_path, "Rr", "Rr-20-(11'9);")
    registry = HyperatomTranslator().translate_directory(tmp_path)

    q = next(item for item in registry.definitions if item.symbol == "Qq")
    r = next(item for item in registry.definitions if item.symbol == "Rr")
    assert q.canonical == "Qq-20-(9'11)"
    assert r.canonical == "Rr-20-(11'9)"
    assert [component.mass for component in q.components] == [11, 9]
    assert q.canonical_structure == r.canonical_structure == "(11'9)"

    canonical_map = build_canonical_hyperatom_map(registry)
    matches = canonical_map.find_by_structure("(11'9)")
    assert {item.symbol for item in matches} == {"Qq", "Rr"}


def test_runtime_auxiliary_registration_is_in_memory_and_survives_refresh(tmp_path):
    _write_element(tmp_path, "Qq", "Qq-20-(11'9);")
    catalog = ElementCatalog(tmp_path)
    record = catalog.register_runtime_auxiliary("X4", atomic_level=4)

    assert record.kind == "auxiliary"
    assert record.role == "runtime_auxiliary_hyperatom"
    assert record.metadata["runtime"] is True
    assert record.metadata["atomic_level"] == 4
    assert catalog["X4"].name("ru").startswith("Вспомогательный гиператом")
    assert not (tmp_path / "X4").exists()
    catalog.refresh()
    assert catalog["X4"].metadata["runtime"] is True


def test_auto_patch_adds_missing_mass_hyperatoms_and_links_components(tmp_path):
    _write_element(tmp_path, "Qq", "Qq-20-(11'9);")
    registry = HyperatomTranslator().translate_directory(tmp_path)
    parent = next(item for item in registry.definitions if item.symbol == "Qq")
    assert all(component.resolution == "unresolved" for component in parent.components)
    original_count = len(registry.definitions)

    canonical_map = build_canonical_hyperatom_map(registry, auto_patch_missing=True)

    assert len(registry.definitions) == original_count + 2
    assert all(component.resolution == "patched" for component in parent.components)
    patched = [registry.by_id[component.candidate_ids[0]] for component in parent.components]
    assert {item.symbol for item in patched} == {"X4"}
    assert {item.atomic_mass for item in patched} == {9, 11}
    assert all(item.source_path.startswith("<runtime:X4>") for item in patched)
    assert all(item.atomic_level == 4 for item in patched)
    assert registry.element_catalog is not None
    assert registry.element_catalog["X4"].metadata["runtime"] is True
    assert all(edge.auto_patched for edge in canonical_map.edges if edge.source_id == parent.id)
    assert canonical_map.statistics()["patched_hyperatoms"] == 2
    assert not (tmp_path / "X4").exists()


def test_auto_patch_does_not_replace_ambiguous_candidates(tmp_path):
    _write_element(tmp_path, "Qq", "Qq-20-(8'12);")
    _write_element(tmp_path, "Rr", "Rr-8-(4'4);")
    _write_element(tmp_path, "Ss", "Ss-8-(5'3);")
    registry = HyperatomTranslator().translate_directory(tmp_path)
    parent = next(item for item in registry.definitions if item.symbol == "Qq")
    mass8 = next(component for component in parent.components if component.mass == 8)
    assert mass8.resolution == "ambiguous"
    before = len(registry.definitions)

    build_canonical_hyperatom_map(registry, auto_patch_missing=True)

    assert mass8.resolution == "ambiguous"
    assert len(mass8.candidate_ids) == 2
    assert len(registry.definitions) >= before
    assert not any(item.symbol == "X4" and item.atomic_mass == 8 for item in registry.definitions)


def test_seed_atomic_level_rule_and_nested_patch_level_are_applied():
    registry = HyperatomTranslator().translate_directory(DATA_ROOT)
    by_canonical = {item.canonical: item for item in registry.definitions}
    assert by_canonical["H-1-1"].atomic_level == 1
    assert by_canonical["D-2-(1'1)"].atomic_level == 2
    assert by_canonical["T-3-(2'1)"].atomic_level == 3
    assert by_canonical["He-4-(2'2)"].atomic_level == 3
    assert by_canonical["He-5-(4'1)"].atomic_level == 4

    canonical_map = build_canonical_hyperatom_map(registry, auto_patch_missing=True)
    runtime = {item.canonical: item for item in registry.definitions if item.source_path.startswith("<runtime:")}
    # The missing 97–99 subatoms have explicit nested structures. Their level
    # is inferred structurally (9), not guessed from floor(log2(mass)) (7).
    assert set(runtime) == {
        "X9-97-(96-(48'48)'1)",
        "X9-98-(96-(48'48)'2)",
        "X9-99-(96-(48'48)'3)",
    }
    assert all(item.atomic_level == 9 and item.atomic_level_source == "nested_structure" for item in runtime.values())
    assert canonical_map.statistics()["patched_hyperatoms"] == 3
