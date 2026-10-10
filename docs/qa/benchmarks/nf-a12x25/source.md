# nf-a12x25: Noctua NF-A12x25 PWM, 120 mm frame, 9 blades, 2000 rpm

- **Curve (2 points):** Noctua spec page https://www.noctua.at/en/products/nf-a12x25-pwm/specifications
  - Max airflow 60.09 CFM, max static pressure 2.34 mmH2O, at 2000 rpm max speed.
  - Rig and uncertainty are not stated. Manufacturer numbers are cited only.
- **Not stored, citation only (`terms_unclear`):** Cybenetics test report (issued 2023-04-27), https://www.cybenetics.com/evaluations/fans/4/de/pdf/
  - It is a full 8-point P–Q table at 100 % PWM (1978–2132 rpm) with current and power, measured on a Long Win LW-9266 rig to ISO 5801 / AMCA 210.
  - Stated expanded uncertainty: about ±1.2 % of flow + 1.8 CFM, and ±0.67 Pa static.
  - I found no reuse terms in the report, so the table is not copied here. The README quotes only my derived BEM error against it.
- **Geometry: derived, not OEM.** The repo Stock recipe `config/problems/a12x25_reference.yaml` (master 31228d0) is fitted to `validation/reference/a12x25_impeller.stl`. That STL is user-provided and its origin is undocumented.
  - The licence of that STL is unknown. Ask Kimball before any MIT release of the geometry.
- **Geometry quality: full (derived).**
