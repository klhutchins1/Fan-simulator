# A12x25 reference geometry assets

## Trusted impeller STL

`validation/reference/a12x25_impeller.stl` — watertight impeller mesh used for silhouette
checks and optional CFD (`scripts/run_a12x25_validation.py --stl …`).

| Field | Value |
|-------|--------|
| Provenance | User-provided close reference to NF-A12x25 (not OEM CAD / not a licensed Noctua mesh) |
| Source file | `A12x25_Fan.STL` (Downloads); prepared into this path |
| Prep | Thin axis reoriented to **+Z** (OpenFOAM MRF), bounds-centered |
| Silhouette (approx.) | **9** blades, tip ~**55.3 mm**, hub vertex p5 ~**19.2 mm**, axial ~**16.7 mm** |

Do **not** claim this file is official Noctua CAD. Geometry pass (silhouette) and CFD pass
(published CFM/Pa) remain independent gates — see
`docs/validation/a12x25_geometry_acceptance.md`.

## CFD absolute claims

Interim CFD vs published free-air / shut-off should prefer this mesh (or equivalent) over the
parametric Stock yaml alone, with tip gap **0.5 mm** and a documented mesh budget.

Geometry envelope checks and CFD performance checks remain separate gates.

## Drone radial / impeller STL batch

`validation/reference/drone_radial/` — prepared millimeter STLs from the
`radial+impeller_stls` Downloads dump (≈60 mm “impeller” and ≈90 mm open rotors,
CW/CCW pairs). Prep via `scripts/import_prop_stls.py`: XY-centered on +Z, inverted
normals fixed, `manifest.json` + per-file `.meta.json`.

Open-air prop CFD (no BEMT):

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --spec cine_3inch --rpm 25000 --dry-run
```

Spin defaults from the filename (`CCW` → `-1`, `CW` → `+1`); override with `--spin`.

## UIUC PropDB fixture

`validation/reference/uiuc_propdb/apcsf_9x4.7_static.json` — vendored static CT/CP row for
APC Slow Flyer 9×4.7 @ 6026 RPM (Track A A3 Q7). Source catalog:
[UIUC PropDB](https://m-selig.ae.illinois.edu/props/propDB.html) (`volume-1/data/apcsf_9x4.7_static_kt1032.txt`).

## Blade geometry golden (§15.2)

`a12x25_blade_golden.json` — parametric Stock volume / bounds / tip-section sample from
`fansim.validation.blade_golden`. Guards `blade.py` regressions. Soft tip/axial envelope vs
the close-ref STL is checked in `tests/test_blade_golden.py` (absolute volume is *not* matched —
Stock is an approximate recipe).
