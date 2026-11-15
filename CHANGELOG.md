# Changelog

## Unreleased

### Fixed

- Hub print-id glyphs are un-mirrored, and the cap is larger (QA-73, code landed in `2bfde35`). The printed coupon has not passed.

### Changed

- The noise row is never marked better or worse. Expert still shows a hint that scales with tip speed and airflow only (`8d06672`). That hint is not a noise comparison.
- Stock's Expert text states that the parametric recipe reads about 5% less airflow than the real A12x25 shape in the same test (55.7 vs 58.3 CFM). Designs are compared with this Stock.
- Validate, Assess, and Export use the same hub height, with growth below the blades.
- A built blade that hangs more than 2 mm is refused.

Assess on the screening mesh is for ranking. This list does not treat that mesh as a grid-converged airflow number. No printed measurement has been accepted.
