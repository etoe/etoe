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

`EToE.md` (language: ru; version: 0.1.60; date: 2026-10-19) is the seed document used as the design basis for this package snapshot.

## Scope of this first package skeleton

The parser implements the core EBNF vocabulary in the seed: `.etoe` files, comments, e-notation objects/ether/etherons, chemical notation, quantity expressions, constants and measurements.

The STÆ simulator currently implements the discrete space/time primitives, SoA etheron storage, four microstates, wrapped coordinates and a conservative movement state machine. Higher matter stairs are represented as typed, extensible model metadata rather than being given invented numerical laws where the seed does not specify a complete executable algorithm.

This repository therefore provides a **real locally installable reference implementation foundation** and an explicit place for subsequent theory-driven modules, while keeping the distinction between normative ÆToE and Python-specific implementation choices.

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
python -m etoe hyperatoms graph --data-root data/atom/element \
  --output build/hyperatoms.svg
python -m etoe hyperatoms graph --data-root data/atom/element \
  --include-templates --output build/hyperatoms-with-templates.svg
```

Generating `.dot` source is pure Python. Rendering SVG/PNG/PDF requires the
Graphviz system executable (`dot`, `neato`, `fdp`, `sfdp`, `circo` or `twopi`).
See [the translator design and legacy-code audit](docs/hyperatom-translation.md)
for semantics, diagnostics and limitations.
