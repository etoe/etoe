from etoe import configure_styles, HyperatomTranslator, hyperatom_tree_to_dot, write_hyperatom_tree

registry = HyperatomTranslator().translate_directory("data/atom/element")

configure_styles(
    Mode="Dark",
    Source="GraphViz",
    Target="GraphViz",
)

# Компактное дерево — режим по умолчанию
write_hyperatom_tree(
    registry,
    "C-12-(8'4)",
    "build/C-12_compact.png"
)

write_hyperatom_tree(
    registry,
    "U-235-(120-(60'60)'115-(60'55))",
    "build/U-235_compact.png"
)

write_hyperatom_tree(
    registry,
    "U-235-(120-(60'60)'115-(60'55))",
    "build/U-235_compact.svg"
)

dot = hyperatom_tree_to_dot(registry, "C-12-(8'4)")

write_hyperatom_tree(
    registry,
    "C-12-(8'4)",
    "build/C-12_compact.dot"
)

# Подробная структурная нотация
write_hyperatom_tree(
    registry,
    "C-12-(8'4)",
    "build/C-12_detailed.png",
    show_subelement_numbers=True,
    compact=False,
)

detailed_dot = hyperatom_tree_to_dot(
    registry,
    "C-12-(8'4)",
    compact=False,
    title="Structure of C-12",
)

write_hyperatom_tree(
    registry,
    "C-12-(8'4)",
    "build/C-12_detailed.dot",
    show_subelement_numbers=True,
    compact=False,
)