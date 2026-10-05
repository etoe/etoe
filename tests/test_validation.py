from etoe import parse_statement, validate


def test_valid_nesting_same_or_lower_level():
    node = parse_statement("Æ2.b-(Æ2.b|æ:s)")
    result = validate(node)
    assert result.ok, result.issues


def test_invalid_upward_nesting():
    node = parse_statement("Æ1.c-(Æ2.b)")
    result = validate(node)
    assert not result.ok
    assert any(i.code == "upward-nesting" for i in result.issues)


def test_class_level_mismatch():
    node = parse_statement("Æ3.b")
    result = validate(node)
    assert any(i.code == "class-level-mismatch" for i in result.issues)
