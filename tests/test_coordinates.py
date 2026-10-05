from etoe.coordinates import DiscreteDimensions, compensation_ticks, reference_delay, velocity_from_delay


def test_wrapping_matches_toroidal_definition():
    d = DiscreteDimensions(8, 8)
    assert d.wrap_space(4) == -4
    assert d.wrap_space(-5) == 3
    assert d.wrap_time(4) == -4


def test_reference_speed_helpers():
    D = 7
    tau = reference_delay(3, D)
    assert tau > 0
    assert velocity_from_delay(D, tau, 0) > velocity_from_delay(D, tau, 4)
    assert compensation_ticks(3, D, (7, 0, 0)) > compensation_ticks(3, D, (7, 7, 7))
