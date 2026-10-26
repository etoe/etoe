# Changelog

## 0.1.68 cascading visualization styles

- Added a renderer-neutral style cascade with global Light/Dark, Source and Target
  settings, CSS-like selectors, property inheritance, specificity, source-order
  resolution, and inline overrides.
- Moved declarative TOML and TeX assets to the project-level `style/` tree, with
  `style/shared/tokens.toml`, one primary stylesheet per source environment, and
  source/target overlays such as `style/graphviz/latex.toml`.
- Moved the cascade engine to `src/etoe/style.py` and added the renderer-specific
  Graphviz adapter at `src/etoe/styles/graphviz.py`; the style tree is included in
  source and wheel distributions.
- Routed all Graphviz hyperatom, periodic-map, hyperatom-map, and occurrence-tree
  styles through the adapter, including target-specific typography overlays.
- Added chemical-category colouring and fixed-size circular Protium nodes: blue for
  the first tree subatom, red for the second, purple for the sole/root subatom and
  for Protium in maps.
- Added the style guide and tests covering the cascade, category palette, modes,
  targets, Graphviz integration, and Protium position rules.
- Connected Graphviz end-to-end; 3D/LaTeX/Manim/book/article/web profiles are
  declarative foundations for adapters that are not yet implemented.

## 0.1.65 hyperatom selection catalogs

- Added data-driven chemical categories, atomic-level indexes, custom element groups, and concrete hyperatom groups.
- Linked element and semantic hyperatom records to their runtime chemical category; serialize those links by category slug.
- Added stable output directories and a shared graph-selection API for all selection items.
- Extended Graphviz selection filters to accept element symbols, hyperatom canonical notation, compact designations, or semantic IDs.
- Added the example `groupel` TOML folders and the `X-40` hyperatom group; documented the new API and covered it with tests.
- Added top-to-bottom periodic maps with inferred subelement numbers and explicit
  links from recursive subelements to the immediately lower same-symbol item.
- Added occurrence-based hyperatom trees: repeated subatoms get distinct nodes,
  while ambiguous and unresolved references remain visible without arbitrary resolution.
- Added public map/tree writer functions and `etoe hyperatoms periodic-map` / `tree`
  command-line subcommands; documented APIs and added structural regression tests.
- Fixed periodic-map traversal so the special zero-index elements H, D, T, and Ht
  retain their structural component edges; in particular, the He map now includes
  `D -> H`, and a map rooted at D includes H. Added regression tests for these edges.
- Preserved structural edge multiplicity in periodic maps: each subatom occurrence
  creates its own edge, so `D-(H'H)` draws two `D -> H` edges and
  `Ht-(H'H'H)` draws three `Ht -> H` edges. Added DOT and Graphviz SVG regressions.
- Preserved structural edge multiplicity in hyperatom maps as well: each concrete
  subatom occurrence creates its own outgoing edge (for example, `He-4-(2'2)` has
  two edges to `D-2-(1'1)`, and each `D-2-(1'1)` has two edges to `H-1-1`).
  Added DOT-level and Graphviz SVG regression tests.

## 0.1.63 canonical hyperatom map and runtime patching

- Resolve primary references by atomic mass and explicitly non-primary structural references by `canonical_structure`; remove the redundant `candidate_scope` map and CLI option.
- Classify primary definitions according to the seed's exact canonical-configuration rule; add `by_mass`, `by_primary_mass`, and `find_by_mass(int | str, primary_only=...)`.
- Preserve explicit runtime-placeholder links and report placeholders consistently when rebuilding a map from the same registry.
- Canonically sort apostrophe-joined sibling subatoms by descending mass, recursively; preserve source `.etoe` notation unchanged.
- Add canonical structure text keys and a structure index for comparing structurally equivalent hyperatoms across element symbols.
- Infer atomic levels from resolved structures using the seed's hierarchical level rule, separate from matter level `E5`.
- Add `etoe.hyperatom_map` / `build_canonical_hyperatom_map()` and JSON CLI export via `etoe hyperatoms map`.
- Add recursive auto-patching for unresolved primary mass references: synthesize the exact primary configuration and its missing child masses recursively down to mass one (for example, `11` becomes `X5-11-(8'3)`); preserve explicitly non-primary structures and leave ambiguous references untouched.
- Reuse already-defined primary candidates during recursive auto-patching, link generated primary nodes to their children immediately, and keep all runtime auxiliary records in memory only.
- Add tests for recursive mass sorting, hybrid primary/non-primary linking, structural indexing, runtime catalog records, automatic patching, and ambiguity preservation.

## 0.1.60 semantic hyperatom translation and graphing

- Added a semantic translator over the canonical parser for `data/atom/element/**/*.etoe`.
- Added provenance-aware hyperatom records, component resolution states, partial structure-pattern matching and mass-balance diagnostics.
- Added deterministic DOT generation and Graphviz SVG/PNG/PDF rendering without a mandatory Python Graphviz dependency.
- Documented findings from the legacy hyperatom binder/graphing scripts and made project seed references consistent with the supplied 0.1.60 seed metadata.
- Preserved unresolved and ambiguous references rather than selecting an arbitrary candidate.


## 0.1.55 unified hyperatomic terminology

- Canonicalized composition classes as Primary, Secondary, and Tertiary.
- Canonicalized inclusive sequence families as Primary, Double, and Triple.
- Added `composition_type()`, `double_sequence()`, `triple_sequence()`,
  `secondary_new()`, and `tertiary_new()`.
- Retained Basic/Extra API names as compatibility aliases.
- Updated hierarchical-generation, pseudocode, combinatorial, and verification docs.
- Clarified that Tertiary is the exhaustive residual composition class, including mixed
  primary/non-primary child cases.

### Unified hyperatomic sequence verification

- Unified the mass-indexed and old level-indexed binary generators under one structural API.
- Added recursive mass-indexed generation corresponding to the old level-by-level Extra closure.
- Added standard mass-qualified short designations and historical periodic-list formatting.
- Added text normalization, sorting, structural comparison, and duplicate diagnostics.
- Added non-materializing combinatorial counts by mass, atomic level, and both.
- Added generated-vs-combinatorial count validation and cross-generator equivalence tests.
- Kept the historical `c < 1000` Extra cap as an explicit book-output option rather than a mathematical rule.

### Experimental hyperatomic generator

- Added `etoe.hyperatomic` with immutable primary-reference/configuration objects.
- Added deterministic binary Primary → Basic → Extra generation.
- Added canonical commutative structural equality with multiplicity preservation.
- Added structural de-duplication independent of atomic mass.
- Added injectable Basic/Extra admissibility predicates.
- Added reproducibility example for the supplied `5'5`, `12'1` and `16'(5'5)` additions.

## 0.1.48

Initial Python reference implementation skeleton aligned to the uploaded ÆToE seed document dated 2026-10-04.

- PEP 621 packaging under PyPI project name `etoe`.
- Lark grammar and parser for canonical `.etoe` notation.
- Typed AST and transformer.
- Semantic validation layer.
- Lossless Python-identifier serialization helpers.
- ÆSoU unit registry and matter-ladder registry.
- Executable STÆ microstate/world scaffolding using a structure-of-arrays representation.
- Test suite covering parser, AST, validation, serialization and simulation primitives.
