# ÆToE visualization style system

The `etoe.style` module provides a renderer-neutral cascade engine. Declarative
style assets live in the project-level `style/` directory, outside Python source
code. The style system is an implementation convention; it does not add physical
postulates to the ÆToE seed document.

## Global settings

```python
from etoe import configure_styles, get_style_settings

configure_styles(mode="Dark", source="GraphViz", target="Web")
print(get_style_settings())  # StyleSettings(mode='Dark', target='Web', source='GraphViz')
```

`Mode` / `Source` / `Target` aliases are also accepted to match ÆToE design terminology:

```python
configure_styles(Mode="Light", Source="GraphViz", Target="LaTeX")
```

Modes are `Light` and `Dark`. Source environments and targets are `GraphViz`,
`3D`, `LaTeX`, `Manim`, `Books`, `Articles`, and `Web`. `ETOE_STYLE_MODE`,
`ETOE_STYLE_SOURCE`, and `ETOE_STYLE_TARGET` establish defaults at process
startup. `ETOE_STYLE_DIR` can point at a custom style root. Graphviz functions
can also receive `mode=` and `target=` explicitly; explicit call arguments take
precedence over process-wide defaults.

## Stylesheet catalogue

Each source environment has a primary TOML style table with Light and Dark
modes. A source folder may contain extra TOML files named after target
environments; for example, `style/graphviz/latex.toml` adds Graphviz-to-LaTeX
target styling. Target overlays can use `[target_overrides.LaTeX.node]` defaults
and/or Light/Dark theme tables scoped to the target file. The shared
`style/shared/tokens.toml` file is the single source of truth for chemical
category and Protium palette tokens.

| Asset | Purpose |
| --- | --- |
| `style/shared/tokens.toml` | Shared Light/Dark semantic palette |
| `style/graphviz/stylesheet.toml` | Graph, node, edge, category and Protium rules |
| `style/graphviz/latex.toml` | Graphviz target overlay for LaTeX |
| `style/graphviz/manim.toml` | Graphviz target overlay for Manim |
| `style/graphviz/web.toml` | Graphviz target overlay for Web |
| `style/graphviz/books.toml` / `articles.toml` / `3d.toml` | Additional Graphviz target overlays |
| `style/3d/stylesheet.toml` | 3D scene and material tokens |
| `style/latex/stylesheet.toml` | Page, heading, math, code and figure tokens |
| `style/latex/book.tex` / `article.tex` | Standalone LaTeX document templates |
| `style/manim/stylesheet.toml` | Scene, mobject, label, edge and highlight tokens |
| `style/books/stylesheet.toml` | Book layout and typography tokens |
| `style/articles/stylesheet.toml` | Article typography and figure tokens |
| `style/web/stylesheet.toml` | Page, body, link, panel and graph tokens |

The profiles for 3D, LaTeX, Manim, books, articles and web are declarative
foundations for their future adapters. In this version, Graphviz is connected
end-to-end; the other profiles do not imply that those rendering pipelines are
already implemented.

## Cascade and specificity

Rules in a TOML stylesheet use `[[rules]]` entries with a selector and
`properties` table. Selectors support type selectors, classes (`.hyperatom`),
IDs (`#root`), simple attribute selectors (`[symbol=H]`) and descendant/direct
child relationships. Specificity follows the CSS tuple `(IDs, classes and
attributes, type selectors)`. For matching stylesheet rules, the cascade
resolves in this order:

1. Theme defaults for the selected mode.
2. Source theme defaults and target-specific theme/default overlays.
3. Inheritance of the explicitly inheritable properties.
4. Matching rules, ordered by `important`, specificity, then source order.
5. Per-element inline properties.

An explicit value at a stronger position in this sequence wins. The default
inherited-property set includes font family/name, font colour, font size,
colour, opacity and line/letter spacing; geometric and fill properties are not
inherited. A `$palette.<category>.<token>` reference in a rule resolves against
the currently selected Light/Dark palette.

The general API can resolve a style without invoking a renderer:

```python
from etoe import resolve_style

props = resolve_style(
    "graphviz",
    "node",
    classes=["hyperatom", "category-noble-gases"],
    mode="Dark",
    target="Web",
)
print(props["fillcolor"])
```

## Graphviz integration

The following functions consume the global style settings and optionally
accept per-call overrides: `hyperatom_graph_to_dot()`, `periodic_map_to_dot()`,
`hyperatom_map_to_dot()`, `hyperatom_tree_to_dot()` and their corresponding
`write_*` helpers. Graph, node, edge, proxy and element-category styles all
come from the Graphviz stylesheet, not from separate hard-coded Light/Dark
branches.

### Compact structural diagrams

`periodic_map_to_dot()`, `hyperatom_map_to_dot()` and `hyperatom_tree_to_dot()`
default to `compact=True`. In this mode, graph titles are omitted unless a
`title=` is explicitly supplied; graph padding and node margins are zero;
edges have no arrowheads; layout gaps contract as atomic level increases; and
node labels omit recursively expanded structure. Periodic element templates
retain only the element symbol and, where useful, the subelement index.
Hyperatom maps use short designations (such as `He-5`), while occurrence trees
use these designations without structural suffixes. Protium is labelled `H`
for root atomic levels 1–4 and becomes an empty, role-coloured circle in trees
rooted at level 5 or above. In those trees, node typography and Protium circles
also shrink with root level and occurrence depth.

Full structural labels and the previous roomy layout remain available with
`compact=False`; this is useful for diagnostics and notation-focused figures.
Passing `title="..."` adds a heading even when compact mode is enabled. The
canonical notation remains available in node tooltips regardless of the label
mode. The compact sizes and spacing are rendering heuristics, not additional
physical postulates of ÆToE.

Chemical categories reuse the category assignments already present in
`etoe.selections`; unknown/custom symbols use the `unknowns` palette until a
richer category is defined. These colours are stable visual encodings for
reading graphs, not theoretical claims.

Protium (`H`) is emitted as a Graphviz circle. The stylesheet supplies its
base size; compact graph builders override its diameter using root atomic level
and occurrence depth:

- In periodic maps and hyperatom maps, its colour is the purple “only/base
  Protium” role.
- In a hyperatom occurrence tree, `H` in the first subatom position is blue,
  `H` in the second position is red, and a sole subatom is purple.
- Other chemical hyperatoms inherit the fill, text and outline colours of their
  chemical category in the selected mode.

Target-specific Graphviz overlays adjust typography and spacing for figures
intended for LaTeX, Manim or Web output while retaining the graph semantics.
The mode and target affect visual parameters only; they do not alter graph
membership, component resolution, or edge multiplicity.

## Extending the system

1. Add or update semantic classes and attributes when constructing a
   `StyleElement`.
2. Add selector/property entries to the source `stylesheet.toml`, or add a target-specific overlay beside it.
3. Keep Light and Dark values together in the same TOML file, with shared semantic colours in `style/shared/tokens.toml`.
4. Add a regression test for specificity, inheritance, target overlays, and
   the renderer adapter.


## Style asset layout

- `style/shared/tokens.toml`: shared colour and semantic tokens.
- `style/graphviz/stylesheet.toml`: Graphviz base rules.
- `style/graphviz/latex.toml`: Graphviz-to-LaTeX target overlay.
- `style/latex/book.tex` and `style/latex/article.tex`: standalone TeX document templates.
- `src/etoe/style.py`: renderer-neutral cascade engine.
- `src/etoe/styles/graphviz.py`: Graphviz-specific adapter.

The environment variables are `ETOE_STYLE_MODE`, `ETOE_STYLE_SOURCE`, and `ETOE_STYLE_TARGET`. `ETOE_STYLE_DIR` can point to a custom global style directory.
