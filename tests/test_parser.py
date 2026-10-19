from pathlib import Path

import pytest

from etoe import (
    ECompactObject,
    EFullObject,
    EToEFile,
    ELevel,
    EEtheron,
    EToEParser,
    EUnit,
    parse_file,
    parse_statement,
)


_ELEMENT_DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "atom" / "element"
_ELEMENT_DATA_FILES = tuple(sorted(_ELEMENT_DATA_ROOT.rglob("*.etoe")))


@pytest.fixture(scope="module")
def element_data_parser() -> EToEParser:
    """Reuse one parser instance across the chemical-element data set."""
    return EToEParser()


def test_parse_full_object_and_roundtrip():
    node = parse_statement("Æ2.b.s.br-{id=1}-(æ:s|æ:f)")
    assert isinstance(node, EFullObject)
    assert node.level == 2
    assert node.class_name == "b"
    assert node.context.part == "s"
    assert node.context.subpart == "br"
    assert node.to_canonical() == "Æ2.b.s.br-{id=1}-(æ:s|æ:f)"


def test_parse_level_and_unit():
    # `Æ2` is a level notation; `æv` is a unit notation.
    level = parse_statement("Æ2")
    assert isinstance(level, ELevel)
    assert level.to_canonical() == "Æ2"
    unit = parse_statement("æv")
    assert isinstance(unit, EUnit)
    assert unit.to_canonical() == "æv"


def test_parse_compact_object():
    node = parse_statement("Æhb")
    assert isinstance(node, ECompactObject)
    assert node.class_name == "hb"


def test_comments_are_not_statement_ast_nodes():
    doc = parse_file("# hello\nÆ2.b; // world\n/* block */ Æ3.sp;", preserve_comments=True)
    assert len(doc.statements) == 2
    assert len(doc.comments) == 3


def test_chemical_element_data_files_exist():
    assert _ELEMENT_DATA_ROOT.is_dir(), f"Element data directory not found: {_ELEMENT_DATA_ROOT}"
    assert _ELEMENT_DATA_FILES, f"No .etoe files found below {_ELEMENT_DATA_ROOT}"


@pytest.mark.parametrize(
    "element_file",
    _ELEMENT_DATA_FILES,
    ids=lambda path: f"{path.parent.name}/{path.name}",
)
def test_parse_chemical_element_data_file(element_data_parser, element_file):
    """Every element .etoe file must be accepted by the canonical parser."""
    parsed = element_data_parser.parse_path(element_file)
    # Empty element files are valid placeholders; successful parsing is the contract.
    assert isinstance(parsed, EToEFile)


@pytest.mark.parametrize(
    "source",
    [
        "H-1-1",
        "Ag-107-(58-(32'26)'49-(26'23))",
        "Mg-26-(16'(5'5))",
        "Ac-227-(114-(64'50-(48'2))'113-(64'49-(27'22)))",
    ],
)
def test_nested_chemical_notation_roundtrips(source):
    assert parse_statement(source).to_canonical() == source
