from pathlib import Path

import pytest

from etoe import ElementCatalog, ElementCatalogError, HyperatomTranslator


PROJECT_DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "atom" / "element"


def _element_folder(root: Path, symbol: str, etoe: str | None = None) -> Path:
    if etoe is None:
        etoe = f"{symbol};"
    folder = root / symbol
    folder.mkdir(parents=True)
    (folder / f"{symbol}.etoe").write_text(etoe + "\n", encoding="utf-8")
    return folder


def test_project_catalog_loads_standard_custom_and_auxiliary_symbols():
    catalog = ElementCatalog(PROJECT_DATA_ROOT)

    hydrogen = catalog.require("H")
    sognesium = catalog.require("Nm")
    selector = catalog.require("X")

    assert len(catalog) == 123
    assert hydrogen.kind == "standard"
    assert hydrogen.atomic_number == 1
    assert hydrogen.name("en") == "hydrogen"
    assert sognesium.kind == "custom"
    assert sognesium.name("en") == "Sognesium"
    assert sognesium.name("ru") == "Согнезий"
    assert sognesium.role == "theoretical_element"
    assert selector.kind == "auxiliary"
    assert selector.name("ru") == "Икс"
    assert selector.role == "structure_selector"


def test_directory_without_toml_infers_standard_or_auxiliary(tmp_path):
    _element_folder(tmp_path, "Fe", "Fe-56-(28'28);")
    _element_folder(tmp_path, "X")

    catalog = ElementCatalog(tmp_path)
    assert catalog["Fe"].kind == "standard"
    assert catalog["Fe"].atomic_number == 26
    assert catalog["X"].kind == "auxiliary"
    assert catalog["X"].name("en") == "X"


def test_nonstandard_symbol_with_toml_defaults_to_custom_and_preserves_extension_metadata(tmp_path):
    folder = _element_folder(tmp_path, "Qq", "Qq-2-(1'1);")
    (folder / "Qq.toml").write_text(
        'symbol = "Qq"\n'
        'role = "theoretical_element"\n'
        '[names]\n'
        'en = "Quuxium"\n'
        'ru = "Квуксий"\n'
        '[properties]\n'
        'origin = "test fixture"\n',
        encoding="utf-8",
    )

    element = ElementCatalog(tmp_path).require("Qq")
    assert element.kind == "custom"
    assert element.name("ru-RU") == "Квуксий"
    assert element.metadata["properties"]["origin"] == "test fixture"


def test_explicit_toml_kind_overrides_inference(tmp_path):
    folder = _element_folder(tmp_path, "Fe", "Fe-56-(28'28);")
    (folder / "Fe.toml").write_text('kind = "auxiliary"\n', encoding="utf-8")
    assert ElementCatalog(tmp_path)["Fe"].kind == "auxiliary"
    assert ElementCatalog(tmp_path)["Fe"].atomic_number is None


def test_mismatched_symbol_in_toml_is_rejected(tmp_path):
    folder = _element_folder(tmp_path, "Nm")
    (folder / "Nm.toml").write_text('symbol = "X"\nkind = "custom"\n', encoding="utf-8")
    with pytest.raises(ElementCatalogError, match="must match its directory symbol"):
        ElementCatalog(tmp_path)


def test_invalid_kind_is_rejected(tmp_path):
    folder = _element_folder(tmp_path, "Qq")
    (folder / "Qq.toml").write_text('kind = "experimental"\n', encoding="utf-8")
    with pytest.raises(ElementCatalogError, match="Invalid kind"):
        ElementCatalog(tmp_path)



def test_metadata_only_directory_is_discovered(tmp_path):
    folder = tmp_path / "Qq"
    folder.mkdir()
    (folder / "Qq.toml").write_text(
        'symbol = "Qq"\nkind = "custom"\n[names]\nru = "Квуксий"\n',
        encoding="utf-8",
    )
    catalog = ElementCatalog(tmp_path)
    assert catalog.symbols == ("Qq",)
    assert catalog["Qq"].kind == "custom"
    assert catalog["Qq"].name("ru") == "Квуксий"


def test_malformed_toml_is_rejected(tmp_path):
    folder = _element_folder(tmp_path, "Qq")
    (folder / "Qq.toml").write_text('kind = "custom"\n[names\nen = "broken"\n', encoding="utf-8")
    with pytest.raises(ElementCatalogError, match="Cannot load element metadata"):
        ElementCatalog(tmp_path)

def test_catalog_refresh_picks_up_new_symbol_and_metadata(tmp_path):
    _element_folder(tmp_path, "H")
    catalog = ElementCatalog(tmp_path)
    assert len(catalog) == 1

    folder = _element_folder(tmp_path, "Nm", "Nm-2-(1'1);")
    (folder / "Nm.toml").write_text('kind = "custom"\n[names]\nru = "Согнезий"\n', encoding="utf-8")
    assert len(catalog) == 1
    catalog.refresh()
    assert len(catalog) == 2
    assert catalog["Nm"].name("ru") == "Согнезий"


def test_catalog_is_connected_to_translation_and_serialization():
    registry = HyperatomTranslator().translate_directory(PROJECT_DATA_ROOT)
    assert registry.element_catalog is not None
    assert registry.element_catalog["Nm"].kind == "custom"
    payload = registry.to_dict()
    assert payload["element_catalog"]["schema"] == "etoe.element-catalog.v1"
    records = {item["symbol"]: item for item in payload["element_catalog"]["elements"]}
    assert records["Nm"]["names"]["ru"] == "Согнезий"
    assert records["X"]["role"] == "structure_selector"
