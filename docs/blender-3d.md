# Blender 3D hyperatom rendering

`etoe hyperatoms render-3d` delegates scene construction and rendering to a
separate Python script executed by Blender in background mode. The regular
`etoe` process does not import `bpy`, construct a Blender scene, or render an
image. It starts Blender with `--background --python ... -- <script options>`.

## Requirements

- Blender must be available as `blender` on `PATH`, or be selected with
  `--blender /path/to/blender` or the `BLENDER` environment variable.
- The installed `etoe` package and its `lark` dependency must be importable by
  Blender's embedded Python. The launcher supplies their paths through
  `PYTHONPATH` and uses `--python-use-system-env`.
- Use a Blender build whose embedded Python is compatible with the Python
  version used to install the package.

Check the executable before a large batch with `blender --version`. For a
single diagnostic run, the Blender-side script can be invoked directly:

```bash
blender --background --python path/to/site-packages/etoe/blender_render.py -- \
  --data-root data/atom/element --hyperatom "C-12-(8'4)"
```

## Selection

The renderer supports individual hyperatoms,
elements, lists of elements, chemical categories, or every source-defined
hyperatom:

```bash
etoe hyperatoms render-3d --hyperatom "C-12-(8'4)"
etoe hyperatoms render-3d --element C
etoe hyperatoms render-3d --elements C,He,Be
etoe hyperatoms render-3d --category noble-gases
etoe hyperatoms render-3d --all-elements
```

## Scene hierarchy and construction order

The Blender Outliner is a real tree of nested `Collection` datablocks, not a
flat list of meshes. The scene has a structural root collection; each
hyperatom has its own child collection; each sub-hyperatom collection is
nested inside its immediate parent's collection. Child mesh objects are also
parented to the outer atmospheric object of their parent hyperatom, preserving
the transform hierarchy as well as the collection hierarchy.

The geometry is constructed bottom-up:

1. Terminal Protium bodies are generated first as deformable organic meshes.
   Each Protium has its own atmospheric layers; none is a strict sphere.
2. A parent sub-hyperatom is measured from its already-built children. Its
   atmospheric layers are irregular envelope meshes that enclose the complete
   child envelopes.
3. The resulting child collection and objects are nested under the parent.
   The parent envelope becomes the object parent for the direct child objects.
4. This reduction continues until the requested root hyperatom has been
   enveloped. No central core object is created at any level.

Meshes use an icosphere topology only as a tessellation starting point; their
vertices are deterministically displaced with smooth angular deformation and
anisotropic compression. Atmospheric layers are separate deformed surfaces
around the contained body or child-cluster support envelope. A wireframe outline
and a central core are not generated.

## Atomahedron geometry follows Protium leaves

The atomhedral form is selected by the number of terminal Protium constituents,
not by the number of immediate semantic children. This is necessary because
Tritium and helium-4 each have two immediate children but different total
Protium counts.

| Hyperatom | Semantic composition | Protium hierarchy depths | Outer form |
|---|---|---|---|
| `D-2-(1'1)` | H + H | 1, 1 | Diatomahedron |
| `T-3-(2'1)` | D + H | 2, 2, 1 | Triatomahedron |
| `Ht-3-(1'1'1)` | H + H + H | 1, 1, 1 | Triatomahedron |
| `He-4-(2'2)` | D + D | 2, 2, 2, 2 | Tetraatomahedron |

The recursive grouping remains intact: Tritium's first two Protium sites are
inside its Deuterium child collection, and helium-4 contains two Deuterium
child collections, each wrapping its own Protium pair. Consequently Tritium's
three Protia occupy different hierarchy levels, whereas Helitrium's three
Protia share one level. The two Deuterium clusters in helium-4 occupy paired
vertex groups of a tetrahedral four-site arrangement.

For higher Protium counts, the existing deterministic Fibonacci-sphere
fallback supplies a repeatable vertex distribution. This is a rendering
fallback, not a new physical postulate.

## Compression and deformation

The deeper a terminal Protium lies in the composition tree, the smaller its
content radius and the larger its deterministic deformation factor. The
current renderer uses the monotonic convention `radius ∝ 0.92 ** depth`; the
deformation factor grows with depth and is capped to avoid destroying mesh
readability. For example, Tritium's two Protia inside Deuterium are more
compressed and deformed than its direct Protium subatom. Helitrium's three
Protia receive the same depth-dependent treatment because they are all at the
same level.

These numerical factors, spatial offsets, atmospheric thicknesses, material
opacity, and deformation amplitudes are visualization parameters, not
calibrated physical constants derived from ÆToE.

## Output and options

For `C-12-(8'4)`, the four default files are:

```text
data/atom/element/C/C-12-(8'4).3.b33.blend
data/atom/element/C/C-12-(8'4).3.b33.blend.toml
data/atom/element/C/C-12-(8'4).3.b33.blend.png
data/atom/element/C/C-12-(8'4).3.b33.blend.png.toml
```

`--output-root DIR` changes the output root while preserving per-element
folders. `--output FILE.blend` is allowed only for one explicitly selected
hyperatom. A complete existing v2 set is reused unless `--overwrite` is
supplied. Files created by the earlier flat-sphere renderer have v1 sidecars
and are regenerated automatically, even when `--overwrite` is omitted.
The TOML sidecars record the hyperatom, renderer settings, construction order,
collection hierarchy, atomahedron kind, Protium hierarchy depths, compression
factors, deformation factors, and the explicit fact that no core is generated.

Rendering options:

```text
--mode Light|Dark              3D style theme
--engine eevee|cycles           render engine
--resolution N                  square PNG dimension
--samples N                     render samples
--shell-layers N                atmospheric layers (1–8; default: 3)
--max-depth N                   recursion depth; 0 means unlimited
--labels                       annotate hierarchy levels
--transparent-background       save RGBA PNG with transparent background
--overwrite                    regenerate existing output files
--blender PATH                 Blender executable
```

The recursive tree is built from the semantic registry and canonical
hyperatom map. A reference is followed only when it resolves uniquely; missing
or ambiguous references remain represented as unresolved nodes.

**Scientific scope:** this is a structural visualization of ÆToE composition.
The seed does not prescribe calibrated spatial coordinates, compression laws,
surface deformations, or atmospheric optical constants. The renderer's
parameters are explicitly visual conventions and are not presented as a
validated physical simulation.
