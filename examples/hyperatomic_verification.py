"""Run the unified hyperatomic generation and verification experiment."""

from etoe.hyperatomic import (
    LevelIndexedGenerator,
    MassIndexedGenerator,
    RecursiveMassIndexedGenerator,
    compare_text_lists,
    combinatorial_counts,
    format_designation_list,
    validate_generated_counts,
)


def main() -> None:
    max_mass = 12

    mass_flat = MassIndexedGenerator()
    mass_recursive = RecursiveMassIndexedGenerator()
    level = LevelIndexedGenerator()

    print("=== Primary: recursive-mass vs level ===")
    comparison = compare_text_lists(
        format_designation_list(mass_recursive.primary_sequence(max_mass)),
        format_designation_list(level.primary_sequence(max_mass)),
    )
    print(comparison.summary())

    print("=== Secondary: recursive-mass vs level ===")
    comparison = compare_text_lists(
        format_designation_list(mass_recursive.secondary_new(max_mass)),
        format_designation_list(level.secondary_new(max_mass)),
    )
    print(comparison.summary())

    print("=== Tertiary: recursive-mass vs level ===")
    comparison = compare_text_lists(
        format_designation_list(mass_recursive.tertiary_new(max_mass)),
        format_designation_list(level.tertiary_new(max_mass)),
    )
    print(comparison.summary())

    print("=== Flat Triple vs recursive Triple ===")
    flat = mass_flat.tertiary_new(max_mass)
    recursive = mass_recursive.tertiary_new(max_mass)
    print(f"flat Primary+Secondary -> Tertiary: {len(flat)}")
    print(f"recursive Triple:                 {len(recursive)}")

    print("=== Generated counts vs combinatorial reference ===")
    table = combinatorial_counts(max_mass, model="recursive")
    for family, items in (
        ("primary", mass_recursive.primary_sequence(max_mass)),
        ("double", mass_recursive.basic_sequence(max_mass)),
        ("secondary", mass_recursive.secondary_new(max_mass)),
        ("triple", mass_recursive.extra_sequence(max_mass)),
        ("tertiary", mass_recursive.tertiary_new(max_mass)),
    ):
        result = validate_generated_counts(
            items,
            family=family,
            max_mass=max_mass,
            model="recursive",
        )
        print(result.summary())

    print("=== Selected recursive combinatorial counts ===")
    for mass in range(5, max_mass + 1):
        print(
            f"M={mass}: secondary={table.count('secondary', mass=mass)}, "
            f"tertiary={table.count('tertiary', mass=mass)}"
        )


if __name__ == "__main__":
    main()
