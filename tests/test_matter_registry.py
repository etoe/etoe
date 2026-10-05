from etoe.matter import CLASS_LEVELS, MATTER_LEVELS, MatterLevel


def test_eight_matter_levels_exist():
    assert len(MATTER_LEVELS) == 8
    assert MATTER_LEVELS[0].level == MatterLevel.E1
    assert MATTER_LEVELS[-1].level == MatterLevel.E8
    assert CLASS_LEVELS["b"] == 2
    assert CLASS_LEVELS["sp"] == 3
    assert CLASS_LEVELS["mj"] == 4
    assert CLASS_LEVELS["ha"] == 5
    assert CLASS_LEVELS["ml"] == 6
    assert CLASS_LEVELS["bd"] == 7
    assert CLASS_LEVELS["as"] == 8
