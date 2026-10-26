from etoe import configure_styles, hyperatom_tree_to_dot

configure_styles(
    Mode="Dark",
    Source="GraphViz",
    Target="LaTeX",
)

dot = hyperatom_tree_to_dot(registry, "He-5-(4'1)")