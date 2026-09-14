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
