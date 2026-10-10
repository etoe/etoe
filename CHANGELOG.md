# Changelog

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
