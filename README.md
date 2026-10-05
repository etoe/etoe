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

`EToE.md` (language: ru; version: 0.1.48; date: 2026-10-04) is the seed document used as the design basis for this package snapshot. The seed itself states version `0.1.48`, date `2026-10-04`, status `active`, and Apache-2.0 licensing.

## Scope of this first package skeleton

The parser implements the core EBNF vocabulary in the 0.1.48 seed: `.etoe` files, comments, e-notation objects/ether/etherons, chemical notation, quantity expressions, constants and measurements.

The STÆ simulator currently implements the discrete space/time primitives, SoA etheron storage, four microstates, wrapped coordinates and a conservative movement state machine. Higher matter stairs are represented as typed, extensible model metadata rather than being given invented numerical laws where the seed does not specify a complete executable algorithm.

This repository therefore provides a **real locally installable reference implementation foundation** and an explicit place for subsequent theory-driven modules, while keeping the distinction between normative ÆToE and Python-specific implementation choices.
