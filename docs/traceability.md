# ÆToE 0.1.48 → `etoe` traceability

| Seed concept | Source | Python layer | Status |
|---|---:|---|---|
| Version/date metadata | EToE.md L5–L8 | `pyproject.toml`, `__version__`, `spec/` snapshot | implemented |
| `.etoe` as source text and AST separation | EToE.md L152–L153 | `parser.py`, `ast.py`, `EToEFile` | implemented |
| LaTeX de-LaTeXization before canonical parsing | EToE.md L598–L600 | extension point; no LaTeX parser bundled yet | scaffolded |
| Lossless programming-language identifier serialization | EToE.md L602 | `serialization.py` | implemented |
| Eight matter stairs | EToE.md L130–L150 | `matter.py`, `standard_model.json` | implemented as registry |
| Discrete toroidal space / cyclic history | EToE.md L55–L127 | `coordinates.py` | implemented |
| SoA simulation preference | EToE.md L664 | `simulation/soa.py` | implemented |
| Four etheron states | EToE.md L668–L678 | `simulation/world.py` | executable micro-kernel |
| Minimum state/cycle durations | EToE.md L680–L744 | `simulation/world.py` | partially implemented; duration model is extensible |
| Etheron parameters and discrete free movement | EToE.md L780–L930 | `simulation/world.py`, `coordinates.py` | foundation only |
| Inertness equations and conservation | EToE.md L930–L982 | `simulation/invariants.py` | invariant helper implemented |
| Higher-level organization: spiral/major/hyperatom/molecule/body/astr | EToE.md L1396–L1578 | `matter.py`, `models.py`, `evolution.py` | model scaffolding |

## Important implementation boundaries

The package does not silently convert qualitative statements from the seed into invented numerical laws. Higher matter stairs therefore have registry/model types and transition hooks until the standard supplies sufficiently complete executable rules.

The grammar file is intentionally close to the seed EBNF, but Lark's LALR parser exposes genuine ambiguities in optional dotted quantity segments and the `X-123` chemical suffix. The implementation therefore uses Earley with `ambiguity="resolve"`; the chosen resolution is documented in `docs/architecture.md`.
