# Blender 3D hyperatom rendering

`etoe hyperatoms render-3d` delegates all scene construction and rendering to a
separate Python script executed by Blender in background mode. The regular
`etoe` process does not import `bpy`, construct a Blender scene, or render an
image. It starts Blender with `--background --python ... -- <script options>`.

## Requirements

- Blender available as `blender` on `PATH`, or provide its executable using
  `--blender /path/to/blender` or the `BLENDER` environment variable.
- The installed `etoe` package and its Python dependency `lark` must be
  importable by Blender's embedded Python. The launcher adds the active
  package and Lark installation paths through `PYTHONPATH` and enables
  Blender's `--python-use-system-env` option. Use a Blender build whose
  embedded Python is compatible with the Python version used for the package.

Check the Blender installation with `blender --version` before starting a
large batch. The Python scene builder can be invoked directly for diagnostics:

```bash
blender --background --python path/to/site-packages/etoe/blender_render.py -- \
  --data-root data/atom/element --hyperatom "C-12-(8'4)"
```

## Selection modes

Every selection option can be combined; the result is a union deduplicated by
canonical hyperatom notation. Only concrete hyperatom definitions read from
`.etoe` source files are selected (not molecule templates or runtime-generated
placeholders).

```bash
# One hyperatom, or several exact notations
etoe hyperatoms render-3d --hyperatom "C-12-(8'4)"
etoe hyperatoms render-3d --hyperatom "C-12-(8'4)" --hyperatom "He-4-(2'2)"

# All definitions of one or more elements
etoe hyperatoms render-3d --element C
etoe hyperatoms render-3d --elements C,He,Be
etoe hyperatoms render-3d --element C --element O

# All definitions belonging to one or more chemical categories
etoe hyperatoms render-3d --category alkali-metals
etoe hyperatoms render-3d --category transition-metals --category noble-gases

# All concrete definitions found under data/atom/element
etoe hyperatoms render-3d --all-elements
```

The `3d` alias is available for `render-3d`.

## Output files

By default, all artefacts are placed beside the element's source data. For
`C-12-(8'4)`, the generated paths are:

```text
data/atom/element/C/C-12-(8'4).3.b33.blend
data/atom/element/C/C-12-(8'4).3.b33.blend.toml
data/atom/element/C/C-12-(8'4).3.b33.blend.png
data/atom/element/C/C-12-(8'4).3.b33.blend.png.toml
```

`--output-root DIR` changes the root while preserving per-element folders.
`--output FILE.blend` sets an exact output path and is permitted only when one
`--hyperatom` is selected. A complete set of four existing files is reused by
default; pass `--overwrite` to regenerate it. If one artefact is missing, that
hyperatom is rendered again.

The TOML companions record the canonical notation, element, mass, atomic
hierarchy level, category, arity, renderer settings, Blender version, and the
explicit status of the model as a structural visualization.

## Rendering options

```text
--mode Light|Dark              3D style theme (default follows etoe style settings)
--engine eevee|cycles           render engine (default: eevee)
--resolution N                  square PNG dimension (default: 1200)
--samples N                     render samples (default: 64)
--shell-layers N                translucent atmospheric layers (1–8; default: 3)
--max-depth N                   recursion depth; 0 means unlimited
--labels                       annotate hierarchy levels
--transparent-background       save RGBA PNG with transparent background
--overwrite                    regenerate existing output files
--blender PATH                 Blender executable (default: $BLENDER or blender)
```

The recursive tree is built from the semantic registry and its canonical
hyperatom map. A component reference is followed only when the map resolves it
uniquely; ambiguous or missing references remain visible as unresolved nodes.
The layouts for arities two through five are deterministic arrangements
inspired by the atomahedron forms described by the seed. A Fibonacci-sphere
arrangement is used as a rendering fallback for higher arities.

**Scientific scope:** this feature visualizes the composition hierarchy and
atomahedron-like arrangements. The seed does not define calibrated numerical
values for shell radii, transparency, depth, or spatial offsets; those are
explicitly renderer conventions and are not claimed to be physical constants
or a validated physical simulation.
