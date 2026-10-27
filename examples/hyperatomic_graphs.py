from etoe import (
    configure_styles, 
    HyperatomTranslator,
    write_periodic_map,
    write_hyperatom_map,
    write_hyperatom_tree,
)

configure_styles(
    Mode="Dark",
    Source="GraphViz",
    Target="GraphViz",
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