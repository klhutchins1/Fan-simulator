# A12x25 reference geometry assets

## Trusted impeller STL (future)

When a licensed or otherwise distributable watertight impeller mesh is available, place it here as:

`validation/reference/a12x25_impeller.stl`

Stock loading and geometry acceptance can then move from the yaml **reference-parametric** recipe
(`config/problems/a12x25_reference.yaml`) to an STL-backed import without changing the structure of
`docs/validation/a12x25_geometry_acceptance.md`.

## CFD absolute claims

Interim CFD pass/fail against published free-air and shut-off numbers should wait until:

1. A trusted STL (or equivalent CAD-backed mesh) is in this directory, **and**
2. Phase 3 mesh-study work (Task 3.1) has tightened the CFD budget.

Geometry envelope checks and CFD performance checks remain separate gates.
