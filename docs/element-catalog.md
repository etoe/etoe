# ÆToE `ElementCatalog`

`etoe.ElementCatalog` discovers symbol directories under `data/atom/element` and loads optional per-element TOML metadata. This keeps project-specific element identity and display names out of the parser grammar and Python conditionals.

## Basic use

```python
from etoe import ElementCatalog

catalog = ElementCatalog("data/atom/element")

iron = catalog["Fe"]
sognesium = catalog["Nm"]
selector = catalog["X"]

print(iron.kind)            # standard
print(iron.name("en"))     # iron
print(sognesium.kind)      # custom
print(sognesium.name("ru"))  # Согнезий
print(selector.kind)       # auxiliary
print(selector.role)       # structure_selector
```

A fresh catalog is normally created after adding folders or editing TOML. An existing catalog can be rescanned with `catalog.refresh()`.

## Discovery and classification

A direct child directory is discovered when it contains at least one `*.etoe` file or a matching `<SYMBOL>.toml` file. Symbol folders and metadata files use the same symbol: `Nm/Nm.etoe` and `Nm/Nm.toml`. Other TOML filenames are ignored.

Classification rules are deterministic:

1. With no TOML file, one of the 118 standard IUPAC symbols is classified as `standard`; other symbols are classified as `auxiliary`.
2. An explicit `kind` in TOML wins and must be `standard`, `custom` or `auxiliary`.
3. With TOML but no `kind`, a standard IUPAC symbol remains `standard`; an unrecognized symbol defaults to `custom`.

This means custom elements should have a TOML file, while helper symbols may either have no metadata file (the symbol name is then used) or a TOML file if localized names and a semantic role are useful.

## TOML fields

The metadata file is optional. Supported fields are:

- `symbol`: optional; when present it must match the containing directory.
- `kind`: `standard`, `custom` or `auxiliary`.
- `role`: machine-readable semantic role; defaults to `chemical_element`, `theoretical_element` or `auxiliary` by kind.
- `description`: optional explanatory text.
- `names`: a table of locale-to-name strings such as `[names]`, `en = "Sognesium"`, `ru = "Согнезий".
- `name`: optional shorthand for a single English name.
- `aliases`: optional array of strings.
- `chemical_category`: optional category slug. When supplied, it overrides the built-in category for this element. The slug must match a category in `ChemicalCategoryCatalog` (for example `noble-gases`, `metalloids`, or `transition-metals`). If omitted, standard symbols use the built-in periodic-table mapping and custom/auxiliary symbols default to `unknowns`. For example: `chemical_category = "noble-gases"`.
- `metadata`: an optional table of project-specific fields. Additional unrecognized top-level keys are also preserved under `metadata`.

Malformed TOML, an unsupported `kind`, a non-string or empty `chemical_category` value, or a `symbol` that does not match the directory name raises `ElementCatalogError` rather than silently ignoring the metadata. A category slug not present in `ChemicalCategoryCatalog` raises `SelectionCatalogError` when that catalog is refreshed.

## Example: Sognesium

`data/atom/element/Nm/Nm.toml`:

```toml
symbol = "Nm"
kind = "custom"
role = "theoretical_element"
description = "Теоретический химический элемент ÆToE."

[names]
en = "Sognesium"
ru = "Согнезий"
```

## Example: auxiliary symbol `X`

`data/atom/element/X/X.toml`:

```toml
symbol = "X"
kind = "auxiliary"
role = "structure_selector"

[names]
en = "X"
ru = "Икс"
```

An auxiliary symbol is not assigned an atomic number merely because it uses element-like ÆToE notation.

## Translator and Graphviz integration

`HyperatomTranslator.translate_directory(root)` creates and attaches a catalog for that root. The resulting `HyperatomRegistry.element_catalog` exposes the same public API, and serialized registries include an `element_catalog` object.

To append localized names to Graphviz node labels:

```bash
python -m etoe hyperatoms graph \
  --data-root data/atom/element \
  --element-names --language ru \
  --output build/hyperatoms-names.svg
```

The standard element symbol/name table is built into `etoe` for basic classification and naming; `periodictable` is not a required dependency. Scientific properties and the names used by that library are not silently substituted for ÆToE-defined masses or structural values.
