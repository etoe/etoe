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

    # Both top-level missing masses are patched to fully structured primary
    # hyperatoms, not mass-only placeholders. Their missing children are
    # recursively synthesized down to the mass-one base object.
    expected_runtime = {
        "X1-1",
        "X2-2-(1'1)",
        "X3-3-(2'1)",
        "X3-4-(2'2)",
        "X4-8-(4'4)",
        "X5-9-(8'1)",
        "X5-11-(8'3)",
    }
    runtime = {item.canonical: item for item in registry.definitions if item.source_path.startswith("<runtime:")}
    assert set(runtime) == expected_runtime
    assert len(registry.definitions) == original_count + len(expected_runtime)
    assert all(component.resolution == "patched" for component in parent.components)
    patched = [registry.by_id[component.candidate_ids[0]] for component in parent.components]
    assert {item.canonical for item in patched} == {"X5-9-(8'1)", "X5-11-(8'3)"}
    assert all(item.atomic_level == 5 for item in patched)
    assert registry.element_catalog is not None
    assert registry.element_catalog["X5"].metadata["runtime"] is True
    assert all(edge.auto_patched for edge in canonical_map.edges if edge.source_id == parent.id)
    assert canonical_map.statistics()["patched_hyperatoms"] == 7

    # The recursively synthesized primary links themselves are fully resolved.
    mass11 = runtime["X5-11-(8'3)"]
    assert [registry.by_id[component.candidate_ids[0]].canonical for component in mass11.components] == [
        "X4-8-(4'4)", "X3-3-(2'1)"
    ]
    mass8 = runtime["X4-8-(4'4)"]
    assert all(registry.by_id[component.candidate_ids[0]].canonical == "X3-4-(2'2)" for component in mass8.components)
    mass4 = runtime["X3-4-(2'2)"]
    assert all(registry.by_id[component.candidate_ids[0]].canonical == "X2-2-(1'1)" for component in mass4.components)
    assert all(registry.by_id[component.candidate_ids[0]].canonical == "X1-1" for component in runtime["X2-2-(1'1)"].components)
    assert {item.canonical for item in canonical_map.find_by_mass(11)} == {"X5-11-(8'3)"}

    # Rebuilding a map from the same in-memory registry preserves recursive
    # runtime-patch links and does not create duplicates.
    second_map = build_canonical_hyperatom_map(registry, auto_patch_missing=True)
    assert second_map.statistics()["patched_hyperatoms"] == 7
    assert len(registry.definitions) == original_count + 7
    assert all(edge.auto_patched for edge in second_map.edges if edge.source_id == parent.id)
    assert not (tmp_path / "X5").exists()


def test_auto_patch_does_not_replace_ambiguous_nonprimary_structural_candidates(tmp_path):
    _write_element(tmp_path, "Qq", "Qq-20-(8-(5'3)'12);")
    _write_element(tmp_path, "Rr", "Rr-8-(5'3);")
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
    # The non-primary (5'3) structure remains ambiguous and untouched. A
    # primary mass-8 node may still be synthesized as a prerequisite of the
    # unrelated mass-only primary reference 12.
    assert not any(
        item.source_path.startswith("<runtime:")
        and item.atomic_mass == 8
        and item.canonical_structure == "(5'3)"
        for item in registry.definitions
    )
    assert any(
        item.source_path.startswith("<runtime:")
        and item.atomic_mass == 8
        and item.canonical_structure == "(4'4)"
        for item in registry.definitions
    )


def test_seed_atomic_level_rule_and_nested_patch_level_are_applied():
    registry = HyperatomTranslator().translate_directory(DATA_ROOT)
    by_canonical = {item.canonical: item for item in registry.definitions}
    assert by_canonical["H-1-1"].atomic_level == 1
    assert by_canonical["D-2-(1'1)"].atomic_level == 2
    assert by_canonical["T-3-(2'1)"].atomic_level == 3
    assert by_canonical["He-4-(2'2)"].atomic_level == 3
    assert by_canonical["He-5-(4'1)"].atomic_level == 4
    assert by_canonical["O-16-(8'8)"].atomic_level == 5
    assert by_canonical["S-32-(16'16)"].atomic_level == 6
    assert by_canonical["Zn-64-(32'32)"].atomic_level == 7 
    assert by_canonical["Te-128-(64'64)"].atomic_level == 8

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



def test_primary_links_use_mass_and_nonprimary_links_use_canonical_structure(tmp_path):
    _write_element(tmp_path, "H", "H-1-1;")
    _write_element(tmp_path, "D", "D-2-(1'1);")
    _write_element(tmp_path, "He", "He-4-(2'2);")
    _write_element(tmp_path, "Be", "Be-8-(4'4);")
    _write_element(tmp_path, "C", "C-12-(8'4);")
    _write_element(tmp_path, "Xx", "Xx-12-(6'6);")
    _write_element(tmp_path, "Qq", "Qq-24-(12'12-(6'6));")
    _write_element(tmp_path, "Pp", "Pp-24-(12-(8'4)'12-(6'6));")

    registry = HyperatomTranslator().translate_directory(tmp_path)
    canonical_map = build_canonical_hyperatom_map(registry)
    q = next(item for item in registry.definitions if item.canonical.startswith("Qq-24-"))
    bare_mass = next(component for component in q.components if component.canonical == "12")
    structured_mass = next(component for component in q.components if "12-(6'6)" in component.canonical)

    # Mass-only links denote the primary hyperatom for mass 12.
    assert bare_mass.resolution == "unique"
    assert [registry.by_id[item].canonical for item in bare_mass.candidate_ids] == ["C-12-(8'4)"]
    # An explicit non-primary structure denotes the non-primary definition
    # with that canonical_structure, even when its mass also has a primary.
    assert structured_mass.resolution == "unique"
    assert [registry.by_id[item].canonical for item in structured_mass.candidate_ids] == ["Xx-12-(6'6)"]

    # Explicitly structured references to the primary configuration still link
    # to the primary by mass, while the non-primary structure uses its own key.
    pp = next(item for item in registry.definitions if item.canonical.startswith("Pp-24-"))
    pp_primary = next(component for component in pp.components if "12-(8'4)" in component.canonical)
    pp_non_primary = next(component for component in pp.components if "12-(6'6)" in component.canonical)
    assert [registry.by_id[item].canonical for item in pp_primary.candidate_ids] == ["C-12-(8'4)"]
    assert [registry.by_id[item].canonical for item in pp_non_primary.candidate_ids] == ["Xx-12-(6'6)"]

    carbon = next(item for item in registry.definitions if item.canonical == "C-12-(8'4)")
    assert [registry.by_id[item].canonical for item in carbon.components[0].candidate_ids] == ["Be-8-(4'4)"]
    assert [registry.by_id[item].canonical for item in carbon.components[1].candidate_ids] == ["He-4-(2'2)"]
    assert [item.canonical for item in canonical_map.find_by_mass("12")] == ["C-12-(8'4)"]
    assert {item.canonical for item in canonical_map.find_by_mass(12, primary_only=False)} == {
        "C-12-(8'4)", "Xx-12-(6'6)"
    }
    assert "candidate_scope" not in canonical_map.statistics()
    assert "candidate_scope" not in canonical_map.to_dict()["canonicalization"]


def test_primary_index_identifies_primary_by_canonical_configuration():
    registry = HyperatomTranslator().translate_directory(DATA_ROOT)
    canonical_map = build_canonical_hyperatom_map(registry)

    carbon = next(item for item in registry.definitions if item.canonical == "C-12-(8'4)")
    beryllium = next(item for item in registry.definitions if item.canonical == "Be-8-(4'4)")
    helium = next(item for item in registry.definitions if item.canonical == "He-4-(2'2)")
    assert carbon.id in canonical_map.by_primary_mass[12]
    assert beryllium.id in canonical_map.by_primary_mass[8]
    assert helium.id in canonical_map.by_primary_mass[4]
    assert [item.canonical for item in canonical_map.find_by_mass("12")] == ["C-12-(8'4)"]


def test_primary_classification_requires_primary_canonical_configuration(tmp_path):
    _write_element(tmp_path, "H", "H-1-1;")
    _write_element(tmp_path, "D", "D-2-(1'1);")
    _write_element(tmp_path, "He", "He-4-(2'2);")
    _write_element(tmp_path, "Be", "Be-8-(4'4);")
    _write_element(tmp_path, "C", "C-12-(8'4);")
    # The direct masses are 8 and 4, but the expanded child structure means
    # this is not the canonical primary configuration for mass 12.
    _write_element(tmp_path, "Yy", "Yy-12-(8-(4'4)'4);")

    registry = HyperatomTranslator().translate_directory(tmp_path)
    canonical_map = build_canonical_hyperatom_map(registry)

    assert [item.canonical for item in canonical_map.find_by_mass(12)] == ["C-12-(8'4)"]
    assert {item.canonical for item in canonical_map.find_by_mass(12, primary_only=False)} == {
        "C-12-(8'4)", "Yy-12-(8-(4'4)'4)"
    }
    yy = next(item for item in registry.definitions if item.canonical == "Yy-12-(8-(4'4)'4)")
    assert [registry.by_id[item].canonical for item in yy.components[0].candidate_ids] == ["Be-8-(4'4)"]
