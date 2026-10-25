# Ether Theory of Everything (EToE)

## Quick Start for AI

**Start here:** [Core Concepts Seed Document](docs/seed/en/EToE.md)

This document contains the foundational understanding of EToE and serves as 
the initial prompt for AI collaborators. Russian version available [here](docs/seed/ru/EToE.md).

## For Humans

## etoe — reference Python implementation of ÆToE

`etoe` is the Python implementation layer for the **Ether Theory of Everything (ÆToE)**. The Markdown seed document defines the theory and notation; this repository implements a Python package that can parse, represent, validate, serialize and simulate parts of that specification.

The package is intentionally **an implementation of the standard, not the standard itself**.

## Installation

```bash
pip install etoe
```

For local development:

```bash
python -m pip install -e .[test]
pytest
```

## Python API

```python
import etoe

stmt = etoe.parse_statement("Æ2.b.s.br-{id=1}-(æ:s|æ:f)")
print(stmt.to_canonical())

result = etoe.validate(stmt)
print(result.ok)
```

## Package layers

- `etoe.notation` — Lark grammar and parser for canonical ÆToE text.
- `etoe.ast` — typed AST for `.etoe` source and individual notations.
- `etoe.transformer` — Lark `Transformer` converting the parse tree into the AST.
- `etoe.validation` — semantic checks that cannot be expressed by the grammar alone.
- `etoe.serialization` — lossless identifier serialization helpers.
- `etoe.simulation` — executable STÆ micro-dynamics and data-oriented simulation scaffolding.
- `etoe.data` — versioned machine-readable reference data for the eight-level matter ladder and ÆSoU unit system.

## Canonical source

`EToE.md` (language: ru; version: 0.1.65; date: 2026-10-23) is the seed document used as the design basis for this package snapshot.

## Scope of this first package skeleton

The parser implements the core EBNF vocabulary in the seed: `.etoe` files, comments, e-notation objects/ether/etherons, chemical notation, quantity expressions, constants and measurements.

The STÆ simulator currently implements the discrete space/time primitives, SoA etheron storage, four microstates, wrapped coordinates and a conservative movement state machine. Higher matter stairs are represented as typed, extensible model metadata rather than being given invented numerical laws where the seed does not specify a complete executable algorithm.

This repository therefore provides a **real locally installable reference implementation foundation** and an explicit place for subsequent theory-driven modules, while keeping the distinction between normative ÆToE and Python-specific implementation choices.

## Element metadata catalog

`etoe.ElementCatalog` discovers element symbols from `data/atom/element/<SYMBOL>/` and reads optional per-element metadata from `<SYMBOL>.toml`. The TOML file can define localized names and the symbol role (`standard`, `custom` or `auxiliary`) without changing the parser grammar. See [the ElementCatalog guide](docs/element-catalog.md) for the schema and examples for `Nm` and `X`.

## Experimental hyperatomic sequence generator

The module `etoe.hyperatomic` contains the unified experimental implementation
of two binary hyperatomic sequence generators:

```python
from etoe.hyperatomic import MassIndexedGenerator, RecursiveMassIndexedGenerator, LevelIndexedGenerator

mass = RecursiveMassIndexedGenerator()
level = LevelIndexedGenerator()

print(mass.primary_sequence(16)[-1].designation)
print(level.extra_new(12)[-1].designation)
```

`MassIndexedGenerator` preserves the earlier mass-indexed experiment. Its
`recursive_extra=True` mode is exposed as `RecursiveMassIndexedGenerator` and
generates Extra from all already-generated configurations. `LevelIndexedGenerator`
is the level-major implementation of the old object-oriented traversal.

All generators share one structural data model, canonical unordered sibling
representation, mass/level properties, family and kind labels, and text tools.
Use `short_designation()` for mass-qualified notation such as
`5-((3'1)'1)`. `sort_hyperatom_text()` and `compare_text_lists()` normalize and
compare textual lists independently of generation order.

`combinatorial_counts()` and `validate_generated_counts()` provide the
non-materializing combinatorial reference calculations. The canonical terminology
is Primary/Secondary/Tertiary for composition classes and Primary/Double/Triple for
sequence families. The `recursive` model corresponds to the old level traversal; the
`double_only` model corresponds to the earlier non-recursive Triple experiment.
Historical `basic`/`extra` method names remain available as compatibility aliases.

`examples/hyperatomic_verification.py` runs the main equivalence and
count checks.


## Semantic hyperatom translation and Graphviz

The `etoe.hyperatom_translation` module translates all chemical statements under
`data/atom/element/**/**/*.etoe` into a `HyperatomRegistry` containing typed
semantic definitions, source provenance, component references, reference
ambiguity and mass-balance diagnostics. It uses the package's canonical parser;
it does not introduce a second `.etoe` grammar. Structural components are
matched as partial patterns, and ambiguous references are retained instead of
being resolved by dictionary overwrite order.

```python
from etoe import HyperatomTranslator, hyperatom_graph_to_dot

registry = HyperatomTranslator().translate_directory("data/atom/element")
print(registry.statistics())

# DOT text does not require the Graphviz Python package.
dot_text = hyperatom_graph_to_dot(registry, include_templates=False)
```

CLI examples (run from the project root after installing the project):

```bash
python -m pip install -e .
python -m etoe hyperatoms translate --data-root data/atom/element \
  --output build/hyperatoms.semantic.json
python -m etoe hyperatoms map --data-root data/atom/element \
  --output build/hyperatoms.map.json
python -m etoe hyperatoms map --data-root data/atom/element \
  --auto-patch-missing --output build/hyperatoms.patched-map.json
python -m etoe hyperatoms graph --data-root data/atom/element \
  --output build/hyperatoms.svg
python -m etoe hyperatoms graph --data-root data/atom/element \
  --auto-patch-missing --output build/hyperatoms.patched.svg
python -m etoe hyperatoms graph --data-root data/atom/element \
  --include-templates --output build/hyperatoms-with-templates.svg
```

Generating `.dot` source is pure Python. Rendering SVG/PNG/PDF requires the
Graphviz system executable (`dot`, `neato`, `fdp`, `sfdp`, `circo` or `twopi`).
See [the translator design and legacy-code audit](docs/hyperatom-translation.md)
for semantics, diagnostics and limitations.

### Periodic maps and hyperatom occurrence trees

Graph maps are oriented top-to-bottom and have distinct contracts:

- `periodic_map_to_dot()` contains chemical-element definitions only, never
  isotope-specific/concrete hyperatoms. It connects their element subelements.
- `hyperatom_map_to_dot()` contains only concrete hyperatoms and connects each
  parent hyperatom directly to the concrete hyperatom candidates for its
  subatoms. Ambiguous references do not introduce proxy nodes.
- `hyperatom_tree_to_dot()` unfolds one concrete hyperatom into an occurrence
  tree: every concrete subatom occurrence gets its own node, even when the same
  definition is used more than once. Non-concrete element templates are not
  drawn as atom nodes.

The three builders accept `show_subelement_numbers=True`; passing `False`
suppresses nonzero `:n` subelement suffixes. Elements without a subelement have
internal number `0`, shown without `:0`. ÆToE treats `H`, `D`, `T` and `Ht` as
independently named chemical elements for numbering, so these labels never get
an inferred `:n` suffix. This does **not** suppress structural edges when an
element template contains components: every subatom occurrence yields an edge.
Thus `D-(H'H)` contributes two parallel `D -> H` edges, and `Ht-(H'H'H)`
contributes three `Ht -> H` edges. Their concrete hyperatom definitions can
also be expanded as hyperatoms. For the other symbols, identical
component-symbol signatures within one element share a number, and recursively
defined subelements are placed after their lower same-symbol definitions. This
is a deterministic indexing convention inferred from the current `.etoe` files,
not an additional physical postulate of the seed.

```python
from etoe import (
    HyperatomTranslator,
    build_element_subelement_numbering,
    hyperatom_map_to_dot,
    hyperatom_tree_to_dot,
    periodic_map_to_dot,
    write_hyperatom_tree,
    write_periodic_map,
)

registry = HyperatomTranslator().translate_directory("data/atom/element")
numbers = build_element_subelement_numbering(registry)  # object ID -> integer

periodic_dot = periodic_map_to_dot(registry, symbols=["He"])
    hyperatom_map_dot = hyperatom_map_to_dot(registry, symbols=["He"])
tree_dot = hyperatom_tree_to_dot(registry, "He-5-(4'1)")
write_periodic_map(registry, "build/periodic-He.dot", symbols=["He"])
write_hyperatom_tree(registry, "He-5-(4'1)", "build/He-5-tree.dot")
```

The equivalent command-line operations are available as
`etoe hyperatoms periodic-map --symbols He --output build/periodic-He.svg`,
`etoe hyperatoms hyperatom-map --symbols He --output build/hyperatom-He.svg`
and `etoe hyperatoms tree "He-5-(4'1)" --output build/He-5-tree.svg`. Add
`--hide-subelement-numbers` to any of these commands to hide nonzero suffixes.

## Hyperatom selection catalogs

`etoe.AtomSelectionCatalog` builds four related catalogs from `data/atom/element`
and the sibling selection directories. Chemical categories are derived
automatically for the standard periodic table; project-specific and auxiliary
symbols are assigned to `unknowns`. To ensure each standard element has exactly
one category, halogens and noble gases are separate from the `nonmetals` bucket.
Element and semantic hyperatom records receive a runtime `chemical_category`
object reference. The atomic-level catalog reuses `atomic_level` inferred by the
semantic translator.

```python
from etoe import AtomSelectionCatalog

selections = AtomSelectionCatalog("data/atom/element")
alkali_metals = selections.categories["alkali-metals"]
level_five = selections.levels[5]
curated_atoms = selections.hyperatom_groups["X-40"]

print(alkali_metals.symbols)
print(level_five.symbols_for_graph())
curated_atoms.write_graph(selections.registry, "X-40.dot")
```

Every selection item exposes `symbols` / `symbols_for_graph()` and `directory` /
`output_dir`; `write_graph()` writes a DOT graph into that item's directory. In
addition to element symbols, graph filters accept exact canonical hyperatom
notations, designations, or semantic IDs. Custom element groups are read from
`data/atom/groupel/<name>/groupel.toml` (`elements = ["Be", "B"]`); concrete
hyperatom groups are read from `data/atom/group/<name>/group.toml`
(`hyperatoms = ["K-40-(33'7)"]`). These folders are data-driven and can be
extended without changing Python code. The project includes the example groups
from the 0.1.65 seed request.
