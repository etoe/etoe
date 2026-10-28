# Standard generated filenames

`etoe.filenames` is the shared naming layer for generated hyperatom
visualizations and selection graphs. It is deliberately separate from Graphviz:
resolving a name or looking for an existing file never launches a renderer.

## Filename convention

Visual files use the form:

```text
<stem>.<artifact>.<mode><source><target>.<format>
```

The artifact code identifies the visualization, and the three-character style
code makes the active style tuple part of the filename. The current codes are:

| Value | Code |
|---|---|
| Mode `Light` / `Dark` | `l` / `d` |
| Source or Target `GraphViz` | `g` |
| Source or Target `3D` | `3` |
| Source or Target `LaTeX` | `x` |
| Source or Target `Manim` | `m` |
| Source or Target `Books` | `b` |
| Source or Target `Articles` | `a` |
| Source or Target `Web` | `w` |

Artifact codes are `t` for a hyperatom occurrence tree, `g` for a hyperatom
graph, `m` for a hyperatom map, `p` for a periodic map, and `s` for a named
selection graph. For example, Dark/GraphViz/GraphViz produces `dgg`:

```text
data/atom/element/C/C-12-(8'4).t.dgg.png
```

When not supplied explicitly, style values come from `get_style_settings()`;
its defaults can in turn be configured with `ETOE_STYLE_MODE`,
`ETOE_STYLE_SOURCE`, and `ETOE_STYLE_TARGET`, or via `configure_styles()`.

## Default output locations

- A hyperatom occurrence tree is stored beside its element's source file:
  `<element-root>/<symbol>/<canonical>.t.<style>.<format>`.
- A map explicitly selected for one exact hyperatom uses the same directory and
  canonical stem, with artifact code `m`.
- An unfiltered registry graph, hyperatom map, or periodic map is stored under
  `<element-root>/` as `hyperatoms.g...`, `hyperatom-map.m...`, or
  `periodic-map.p...` respectively.
- A `GraphSelectionItem` writes into its own folder, using that folder's name as
  the stem, e.g. `data/atom/group/X-40/X-40.s.dgg.png`.
- Ad-hoc selector sets passed to a graph command use a stable token-derived
  directory under `data/atom/selection/`.

For visual writer functions, omitting `output` now selects the standard path and
PNG format. Set `format="dot"` to write DOT source without invoking Graphviz.
An explicitly provided `output` path always takes precedence and preserves the
previous explicit-output behavior. CLI visual commands also accept `--output`,
`--mode`, `--source`, and `--target`.

## Python API

```python
from etoe import (
    HyperatomTranslator,
    configure_styles,
    find_standard_hyperatom_file,
    write_hyperatom_tree,
)

registry = HyperatomTranslator().translate_directory("data/atom/element")
configure_styles(Mode="Dark", Source="GraphViz", Target="GraphViz")

# Uses data/atom/element/C/C-12-(8'4).t.dgg.dot and writes DOT source.
# Omit format="dot" to render the default PNG instead.
path = write_hyperatom_tree(
    registry, "C-12-(8'4)", element_root="data/atom/element", format="dot"
)
# Searches standard names in the requested format order.
existing = find_standard_hyperatom_file(
    "C-12-(8'4)", element_root="data/atom/element", formats=("png", "svg", "dot")
)
```

`standard_hyperatom_path()`, `standard_selection_path()`,
`standard_selection_tokens_path()`, and `standard_filename()` expose the path
convention directly. `find_standard_hyperatom_file()`,
`find_standard_selection_file()`, and `find_standard_selection_tokens_file()`
use those same path builders, avoiding separate write-vs-search rules. Notation
characters that are forbidden in filenames on common operating systems (such
as the colon in a subsort label) are replaced with underscores; the example
`C-12-(8'4)` remains unchanged.
