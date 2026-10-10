from etoe.hyperatomic import (
    HyperatomConfig,
    HyperatomRef,
    HyperatomicGenerator,
    primary_period,
    recursive_primary_definition,
)


def test_primary_recursive_sequence_first_sixteen():
    gen = HyperatomicGenerator()
    seq = gen.primary_sequence(16)
    assert [item.canonical for item in seq] == [
        "1", "1'1", "2'1", "2'2", "4'1", "4'2", "4'3", "4'4",
        "8'1", "8'2", "8'3", "8'4", "8'5", "8'6", "8'7", "8'8",
    ]
    assert [item.mass for item in seq] == list(range(1, 17))


def test_primary_pair_formula_and_periods():
    assert recursive_primary_definition(3) == (2, 1)
    assert recursive_primary_definition(12) == (8, 4)
    assert recursive_primary_definition(16) == (8, 8)
    assert primary_period(1) == 1
    assert primary_period(2) == 2
    assert primary_period(3) == 3
    assert primary_period(4) == 3
    assert primary_period(5) == 4
    assert primary_period(16) == 5


def test_bare_numbers_are_primary_references_not_recursive_expansions():
    node = HyperatomConfig.from_structure("2'1")
    assert node == HyperatomConfig.compose(HyperatomRef(2), HyperatomRef(1))
    assert node.canonical == "2'1"
    assert node.mass == 3


def test_structural_commutativity_and_multiplicity():
    a = HyperatomConfig.from_structure("2'1")
    b = HyperatomConfig.from_structure("1'2")
    assert a == b
    assert a.canonical == "2'1"

    triple = HyperatomConfig.from_structure("1'1'1")
    pair = HyperatomConfig.from_structure("1'1")
    assert triple.mass == 3
    assert pair.mass == 2
    assert triple != pair


def test_nested_non_primary_subatom():
    node = HyperatomConfig.from_structure("(3'1)'1")
    assert node.mass == 5
    assert node.arity == 2
    assert node.canonical == "(3'1)'1"
    assert isinstance(node.children[0], HyperatomConfig)
    assert isinstance(node.children[1], HyperatomRef)


def test_basic_and_extra_are_nested_families_and_deduped():
    gen = HyperatomicGenerator()
    primary = gen.primary(16)
    basic = gen.basic(16)
    extra = gen.extra(16)

    for n, p in primary.items():
        assert any(config.key == p.key for config in basic[n])
        assert any(config.key == p.key for config in extra[n])

    for family in (basic, extra):
        for configs in family.values():
            assert len({config.key for config in configs}) == len(configs)

    c1 = HyperatomConfig.from_structure("8'2")
    c2 = HyperatomConfig.from_structure("5'5")
    assert c1.mass == c2.mass == 10
    assert c1 != c2


def test_unrestricted_basic_contains_all_binary_primary_candidates():
    gen = HyperatomicGenerator()
    basic = gen.basic(13)
    values = {c.canonical for c in basic[13]}
    assert "12'1" in values
    assert "8'5" in values


def test_extra_can_nest_a_non_primary_basic_configuration():
    # Start with Double containing only Primary configurations plus Secondary 5'5.
    def basic_policy(n, left, right):
        candidate = HyperatomConfig.compose(left, right).canonical
        return candidate == "5'5"

    # In the experimental Triple layer, accept every binary combination of the
    # Double family. This should allow (5'5)'16 -> 16'(5'5).
    gen = HyperatomicGenerator(basic_admissible=basic_policy)
    extra = gen.extra(26)
    values = {c.canonical for c in extra[26]}
    assert "16'(5'5)" in values


def test_admissibility_hook_can_reproduce_a_legacy_basic_subset():
    allowed_basic = {"5'5"}

    def basic_policy(n, left, right):
        return HyperatomConfig.compose(left, right).canonical in allowed_basic

    gen = HyperatomicGenerator(basic_admissible=basic_policy)
    basic = gen.basic(13)
    assert [c.canonical for c in basic[10]] == ["8'2", "5'5"]
    assert "12'1" not in {c.canonical for c in basic[13]}


def test_legacy_examples_are_reclassified_by_the_new_composition_taxonomy():
    def basic_policy(n, left, right):
        return HyperatomConfig.compose(left, right).canonical in {"5'5", "12'1"}

    def extra_policy(n, left, right):
        return HyperatomConfig.compose(left, right).canonical == "16'(5'5)"

    gen = HyperatomicGenerator(
        basic_admissible=basic_policy,
        extra_admissible=extra_policy,
    )
    assert [x.canonical for x in gen.secondary_new(16) if x.mass == 10] == ["5'5"]
    assert "12'1" in {x.canonical for x in gen.secondary_new(16)}
    assert "12'1" not in {x.canonical for x in gen.tertiary_new(26)}
    assert "16'(5'5)" in {x.canonical for x in gen.tertiary_new(26)}
