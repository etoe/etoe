from etoe import (
    ECompactObject,
    EFullObject,
    ELevel,
    EEtheron,
    EUnit,
    parse_file,
    parse_statement,
)


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
