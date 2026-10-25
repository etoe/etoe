from etoe import (
    HyperatomTranslator,
    write_periodic_map,
    write_hyperatom_map,
    write_hyperatom_tree,
)

registry = HyperatomTranslator().translate_directory(
    "data/atom/element"
)

write_periodic_map(
    registry,
    "build/periodic-He.svg",
    symbols=["He"],
    show_subelement_numbers=True,
)

write_hyperatom_map(
    registry,
    "build/hyperatom-He.svg",
    symbols=["He"],
    show_subelement_numbers=False,
)

write_hyperatom_tree(
    registry,
    "He-5-(4'1)",
    "build/He-5-tree.svg",
    show_subelement_numbers=False,
)