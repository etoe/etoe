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
around the contained body or child-cluster support envelope. In the default `surface` representation no wireframe is overlaid; a central
core is never generated. Select `wireframe` or `point-cloud` explicitly with
`--representation` when an alternate display is required.

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

For `C-12-(8'4)` in the default Light style, the standard rough result set is:

```text
data/atom/element/C/C-12-(8'4).rough.toml
data/atom/element/C/C-12-(8'4).rough.3.l33.blend
data/atom/element/C/C-12-(8'4).rough.3.l33.blend.toml
data/atom/element/C/C-12-(8'4).rough.3.l33.blend.png
data/atom/element/C/C-12-(8'4).rough.3.l33.blend.png.toml
```

Use `--quality strict` for the `strict` simulation and geometry profile. The
quality name is part of every output filename, so rough and strict products do
not overwrite one another. `--representation point-cloud` and
`--representation wireframe` select alternative renderable geometry styles;
the default `surface` keeps the exact compact filename above, while alternate
representations get their own filename suffix. Point-cloud mode emits a
deterministically sampled bead cloud from mesh vertices; wireframe mode uses a
Blender Wireframe modifier. `--output-root DIR` changes the output root while
preserving per-element folders. `--output FILE.blend` is allowed only for one
explicitly selected hyperatom.

The synthesis manifest and both artifact sidecars record source/style
fingerprints, Blender version, simulation settings and the SHA-256 hashes of
the generated files. Inputs include each transitive `.etoe` definition, available element metadata
TOML files, the seed specification `docs/seed/ru/EToE.md`,
`style/shared/tokens.toml`, `style/3d/stylesheet.toml`, and the synthesis,
renderer, adapter, translation, selection, element-map, and style-resolution
modules. When those dependencies and all result hashes are unchanged,
the complete result bundle is reused; `--rebuild` forces a new simulation and
render. A parent job is not permitted to substitute a placeholder for a child:
it requires the child simulation manifest, `.blend`, and successful metadata
sidecar, then instances that saved child collection into its own nested
collection. Child jobs are run first in dependency order.

The TOML sidecars record the hyperatom, renderer settings, construction order,
collection hierarchy, atomahedron kind, Protium hierarchy depths, compression
factors, deformation factors, layer parameters, simulation attempts/residual,
and the explicit fact that no core is generated.

Rendering options:

```text
--mode Light|Dark              3D style theme
--quality rough|strict         simulation profile (rough is the default)
--representation surface|point-cloud|wireframe
                                Blender geometry representation
--engine eevee|cycles           render engine
--resolution N                  square PNG dimension
--samples N                     render samples (profile default: rough 16, strict 64)
--shell-layers N                atmospheric layers (profile default: rough 3, strict 5)
--attempts N                    initial arrangement retries (profile default: rough 3, strict 12)
--max-depth N                   recursion depth; 0 means unlimited
--labels                       annotate hierarchy levels
--transparent-background       save RGBA PNG with transparent background
--rebuild                      force simulation and rendering (alias: --overwrite)
--blender PATH                 Blender executable
```

## CLI selection examples

The normal `etoe` process only resolves the command-line options and starts
Blender in background mode. The package script `etoe/blender_render.py`
performs registry selection, dependency planning, synthesis, scene construction,
saving and rendering inside Blender. All script-specific arguments are passed
after Blender's `--` separator.

```bash
# One hyperatom and its complete subatom dependency closure
etoe hyperatoms render-3d --hyperatom "C-12-(8'4)"

# Every source-defined hyperatom of one element
etoe hyperatoms render-3d --element C --quality strict

# A comma-separated element list (repeat --element is also supported)
etoe hyperatoms render-3d --elements "C,Be,He" --representation point-cloud

# All hyperatoms of a chemical category
etoe hyperatoms render-3d --category noble-gases --representation wireframe

# Every source-defined hyperatom from every element directory
etoe hyperatoms render-3d --all-elements --rebuild
```

Multiple selectors are unioned and duplicate definitions are removed.

## Incremental synthesis and quality profiles

`rough` performs a shorter, lower-resolution geometric-relaxation sequence;
`strict` uses more steps, more initial orientation attempts, more surface
subdivisions, more atmospheric layers and more render samples. Both profiles
start from a stable levitation arrangement whose nearest-neighbour Protium
spacing is normalized to exactly two model units (one minimum Protium gabarit
is one model unit). The simulated sequence progressively increases the
spiral-coupling parameter and contracts the sites toward the source-defined
composition.

The dependency plan is postorder. For example, selecting `C-12-(8'4)` creates
or reuses `H-1-1`, then `D-2-(1'1)`, then `He-4-(2'2)` and
`Be-8-(4'4)`, and only then builds carbon. The helium scene instantiates two
Deuterium scene collections; the deuterium scene instantiates two Protium
collections. Carbon instantiates the pre-synthesized Beryllium and Helium
collections. Repeated child occurrences remain repeated in the Outliner even
though each distinct dependency file is generated only once per quality/style.

The current seed defines composition and hierarchy but not calibrated
interaction forces or etheron constitutive equations. The relaxation and
spiral-coupling sequence is therefore an explicit deterministic geometric
surrogate. Etheron counts, etheron mass and spin are left unresolved in model
metadata rather than invented.

The recursive tree is built from the semantic registry and canonical
hyperatom map. A reference is followed only when it resolves uniquely; missing
or ambiguous references remain represented as unresolved nodes.

**Scientific scope:** this is a structural visualization of ÆToE composition.
The seed does not prescribe calibrated spatial coordinates, compression laws,
surface deformations, or atmospheric optical constants. The renderer's
parameters are explicitly visual conventions and are not presented as a
validated physical simulation.
