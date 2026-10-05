# Architecture

## Boundary: standard vs implementation

The ÆToE seed is the normative conceptual/notation source. `etoe` is a reference Python implementation. The package may add implementation metadata and APIs, but those additions are not automatically part of the standard.

## Data flow

```text
.etoe text
   |
   v
Lark grammar (canonical syntax)
   |
   v
CST / Transformer
   |
   v
Typed AST
   |
   +--> semantic validation
   |
   +--> lossless identifier serialization
   |
   +--> model/evolution layer
   |
   +--> STÆ simulation kernel --> renderer-neutral snapshot --> visual backends
```

## Parser policy

The 0.1.48 seed grammar contains optional dotted segments in quantity expressions and an overlap between the mass suffix and the short chemical-structure form. For a practical reference parser the package uses Lark Earley with `ambiguity="resolve"` and represents the common `X-123` form as an atomic mass, while retaining parenthesized chemical structures as structure nodes. This is an implementation resolution of a source-level grammar ambiguity; it should be revisited against a future normative grammar revision.

Comments are lexically ignored and therefore do not enter individual statement ASTs. `preserve_comments=True` stores their source spans in `EToEFile.comments` as file metadata.

## Simulation policy

The seed explicitly recommends a structure-of-arrays representation for optimized simulations. `EtheronSoA` follows that direction without adding a mandatory NumPy dependency. The current executable kernel covers wrapped discrete space/time, four etheron states, same-cell interaction detection and orthogonal neighbor movement. Higher matter stairs are represented by `MatterLevel`, `MatterLevelSpec`, `MatterObject` and `MatterEvolutionPipeline`; future modules can attach theory-specific numerical transition kernels without coupling them to the parser.
