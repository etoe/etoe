"""Demonstrate the legacy examples under the canonical terminology.

The historical C-13-(12'1) entry was printed in the old Extra sequence, but
under the new structural taxonomy it is a Secondary composition and therefore
belongs to the Double sequence.
"""

from etoe.hyperatomic import HyperatomConfig, HyperatomicGenerator


def secondary_policy(n, left, right):
    return HyperatomConfig.compose(left, right).canonical in {
        "5'5", "12'1",
    }


def tertiary_policy(n, left, right):
    return HyperatomConfig.compose(left, right).canonical == "16'(5'5)"


def main() -> None:
    gen = HyperatomicGenerator(
        basic_admissible=secondary_policy,
        extra_admissible=tertiary_policy,
    )

    print("Primary 1..16")
    for item in gen.primary_sequence(16):
        print(f"{item.period}: {item.mass}={item.canonical}.")

    print("\nSecondary additions 1..26")
    for item in gen.secondary_new(26):
        print(f"{item.period}: {item.mass}={item.canonical}.")

    print("\nTertiary additions 1..26")
    for item in gen.tertiary_new(26):
        print(f"{item.period}: {item.mass}={item.canonical}.")


if __name__ == "__main__":
    main()
