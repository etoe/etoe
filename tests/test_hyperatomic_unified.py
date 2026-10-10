from etoe.hyperatomic import (
    COMPOSITION_PRIMARY,
    COMPOSITION_SECONDARY,
    COMPOSITION_TERTIARY,
    SEQUENCE_DOUBLE,
    SEQUENCE_TRIPLE,
    SEQUENCE_PRIMARY,
    SEQUENCE_DOUBLE,
    SEQUENCE_PRIMARY,
    SEQUENCE_TRIPLE,
    HyperatomConfig,
    LevelIndexedGenerator,
    MassIndexedGenerator,
    RecursiveMassIndexedGenerator,
    compare_text_lists,
    combinatorial_count,
    combinatorial_counts,
    format_designation_list,
    format_sequence,
    primary_configuration,
    short_designation,
    sort_hyperatom_text,
    validate_generated_counts,
)


def test_short_designation_and_parser_roundtrip():
    config = HyperatomConfig.from_structure("(3'1)'1")
    assert short_designation(config) == "5-((3'1)'1)"
    parsed = HyperatomConfig.from_structure(config.canonical)
    assert parsed.key == config.key


def test_primary_secondary_tertiary_composition_partition():
    primary = HyperatomConfig.from_structure("1'1")
    secondary = HyperatomConfig.from_structure("3'1")
    tertiary = HyperatomConfig.from_structure("(3'1)'1")
    special_secondary = HyperatomConfig.from_structure("1'1'1")
    mixed_tertiary = HyperatomConfig.from_structure("(3'1)'2")

    from etoe.hyperatomic import composition_type
    assert composition_type(primary) == COMPOSITION_PRIMARY
    assert composition_type(secondary) == COMPOSITION_SECONDARY
    assert composition_type(tertiary) == COMPOSITION_TERTIARY
    assert composition_type(special_secondary) == COMPOSITION_SECONDARY
    assert composition_type(mixed_tertiary) == COMPOSITION_TERTIARY


def test_text_sort_and_compare_ignore_generation_order():
    a = """\
4=3'1.\n
3=2'1.\n
4=2'2.\n
"""
    b = """\
3-(2'1).\n
4-(2'2).\n
4-(1'3).\n"""
    assert sort_hyperatom_text(a) == sort_hyperatom_text(b)
    comparison = compare_text_lists(a, b)
    assert comparison.equal
    assert comparison.a_count == comparison.b_count == 3


def test_primary_and_basic_match_between_generation_strategies():
    mass = MassIndexedGenerator()
    level = LevelIndexedGenerator()
    assert compare_text_lists(
        format_designation_list(mass.primary_sequence(16)),
        format_designation_list(level.primary_sequence(16)),
    ).equal
    assert compare_text_lists(
        format_designation_list(mass.secondary_new(16)),
        format_designation_list(level.secondary_new(16)),
    ).equal


def test_recursive_mass_and_level_generators_have_same_unrestricted_extra_set():
    mass = RecursiveMassIndexedGenerator()
    level = LevelIndexedGenerator()
    comparison = compare_text_lists(
        format_designation_list(mass.tertiary_new(12)),
        format_designation_list(level.tertiary_new(12)),
    )
    assert comparison.equal


def test_flat_extra_is_a_strict_subset_of_recursive_extra_from_mass_6_onward():
    flat = MassIndexedGenerator()
    recursive = RecursiveMassIndexedGenerator()
    flat_keys = {x.config.key for x in flat.tertiary_new(12)}
    recursive_keys = {x.config.key for x in recursive.tertiary_new(12)}
    assert flat_keys < recursive_keys


def test_combinatorial_counts_match_recursive_generation():
    gen = RecursiveMassIndexedGenerator()
    for family in (SEQUENCE_PRIMARY, SEQUENCE_DOUBLE, SEQUENCE_TRIPLE, "secondary", "tertiary"):
        if family == SEQUENCE_PRIMARY:
            items = gen.primary_sequence(10)
        elif family == SEQUENCE_DOUBLE:
            items = gen.basic_sequence(10)
        elif family == "secondary":
            items = gen.secondary_new(10)
        elif family == SEQUENCE_TRIPLE:
            items = gen.extra_sequence(10)
        else:
            items = gen.tertiary_new(10)
        result = validate_generated_counts(items, family=family, max_mass=10, model="recursive")
        assert result.equal, result.summary()


def test_flat_and_recursive_combinatorial_extra_counts_diverge_as_expected():
    flat = combinatorial_counts(12, model="basic_only")
    recursive = combinatorial_counts(12, model="recursive")
    assert flat.count("tertiary", mass=5) == recursive.count("tertiary", mass=5) == 1
    assert flat.count("tertiary", mass=6) == 2
    assert recursive.count("tertiary", mass=6) == 3
    assert recursive.count("tertiary", atomic_level=6) > flat.count("tertiary", atomic_level=6)


def test_primary_configuration_is_reference_based():
    p5 = primary_configuration(5)
    assert short_designation(p5) == "5-(4'1)"
    assert p5.mass == 5


def test_generated_text_can_use_historical_period_format():
    gen = MassIndexedGenerator()
    text = format_sequence(gen.primary_sequence(8), with_period_headers=True, designation_format="legacy")
    assert text.splitlines()[0] == "1:"
    assert "5=4'1." in text


def test_level_generator_resets_when_mass_domain_is_extended_after_extra_generation():
    gen = LevelIndexedGenerator()
    first = gen.tertiary_new(8)
    extended = gen.tertiary_new(10)
    fresh = LevelIndexedGenerator().tertiary_new(10)
    assert {x.config.key for x in extended} == {x.config.key for x in fresh}
    assert len(extended) > len(first)


def test_canonical_sequence_api_and_legacy_aliases_agree():
    gen = RecursiveMassIndexedGenerator()
    assert {x.config.key for x in gen.double_sequence(8)} == {x.config.key for x in gen.basic_sequence(8)}
    assert {x.config.key for x in gen.triple_sequence(8)} == {x.config.key for x in gen.extra_sequence(8)}
    assert {x.config.key for x in gen.secondary_new(8)} == {x.config.key for x in gen.basic_new(8)}
    assert {x.config.key for x in gen.tertiary_new(8)} == {x.config.key for x in gen.extra_new(8)}
    secondary_map = gen.secondary(8)
    tertiary_map = gen.tertiary(8)
    assert {x.config.key for x in gen.secondary_new(8)} == {c.key for configs in secondary_map.values() for c in configs}
    assert {x.config.key for x in gen.tertiary_new(8)} == {c.key for configs in tertiary_map.values() for c in configs}


def test_legacy_book_cap_is_explicit_and_bounded():
    items = LevelIndexedGenerator.legacy_book_sequence(seed_max_mass=8, max_extra_level=4, extra_cap=20)
    assert items
    assert any(item.category == SEQUENCE_TRIPLE for item in items)

