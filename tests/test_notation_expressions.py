from etoe import parse_statement
from etoe.ast import ConstantExpression, MeasurementExpression, QuantityExpression


def test_measurement():
    node = parse_statement("12.5æv")
    assert isinstance(node, MeasurementExpression)
    assert node.value == 12.5
    assert node.to_canonical() == "12.5æv"


def test_quantity_expression():
    node = parse_statement("τ.physics.kinematic.avg.Æ2.b")
    assert isinstance(node, QuantityExpression)
    assert node.quantity == "τ"
    assert node.science_context.domain == "physics"
    assert [a.value for a in node.aspects] == ["kinematic"]
    assert node.character == "avg"
    assert node.object.to_canonical() == "Æ2.b"


def test_constant_forms():
    full = parse_statement("const.τ.avg.Æ2.b")
    assert isinstance(full, ConstantExpression)
    assert full.form == "full"
    assert full.to_canonical() == "const.τ.avg.Æ2.b"
    assert parse_statement("ꞒC").to_canonical() == "ꞒC"
    assert parse_statement("@C").to_canonical() == "@C"


def test_chemical_notation_roundtrip():
    assert parse_statement("H-1").to_canonical() == "H-1"
    assert parse_statement("Cu-62-(P-31'P-31)").to_canonical() == "Cu-62-(P-31'P-31)"
