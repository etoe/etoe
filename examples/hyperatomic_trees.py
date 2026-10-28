import os
import cairosvg
from etoe import ( 
    configure_styles, 
    HyperatomTranslator, build_canonical_hyperatom_map, 
    hyperatom_tree_to_dot, write_hyperatom_tree, write_hyperatom_map 
)

os.environ["ETOE_GRAPHVIZ_CAIROSVG"] = "1"

configure_styles(
    #Mode="Light",
    Mode="Dark",
    Source="GraphViz",
    Target="GraphViz",
)

registry = HyperatomTranslator().translate_directory("data/atom/element")
canonical_map = build_canonical_hyperatom_map(registry, auto_patch_missing=True)

# Компактное дерево — режим по умолчанию
write_hyperatom_tree(
    registry,
    "Li-7-(4'3)",
    "build/Li-7_compact.png"
)

write_hyperatom_map(
    registry,
    "build/Li-7_map.png",
    symbols=["Li-7-(4'3)"],    
)

write_hyperatom_tree(
    registry,
    "Na-23-(16'7)",
    "build/Na-23_compact.png"
)

write_hyperatom_tree(
    registry,
    "C-12-(8'4)",
    "build/C-12_compact.png"
)

write_hyperatom_tree(
    registry,
    "C-12-(8'4)",
    "build/C-12_compact.svg"
)

cairosvg.svg2png(url="build/C-12_compact.svg", write_to="build/C-12_compact.svg.png")

dot = hyperatom_tree_to_dot(registry, "C-12-(8'4)")

write_hyperatom_tree(
    registry,
    "C-12-(8'4)",
    "build/C-12_compact.dot"
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

cairosvg.svg2png(url="build/U-235_compact.svg", write_to="build/U-235_compact.svg.png")


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