# Low-Re airfoil polars (BEM / BEMT)

Condensed representative polars for **NACA 0012 / 2412 / 4412** (12% thick) plus
**Eppler e387** (~9%), **Selig–Donovan sd7032** (~10%), and **Selig s1223** (high-lift,
~12%) at Re = 4×10⁴, 8×10⁴, and 1.6×10⁵. Values follow published **UIUC Low-Speed
Airfoil Tests (LSATs)** trends (Clmax drop, Cd0 rise, earlier stall as Re falls) for
offline fan/prop BEM — not a line-by-line dump of every tunnel run in Selig’s volumes.

Family match uses **camber + thickness**: `abs(c−c*) + 0.5·abs(t−t*)`.

## Attribution

Produced under / aligned with the UIUC Low-Speed Airfoil Test program:

- Selig, M.S. et al., *Summary of Low-Speed Airfoil Data*, Vols. 1–3, SoarTech.
- Data site: https://m-selig.web.engr.illinois.edu/pd.html  
  (UIUC performance data is freely usable under their stated GPL-style terms with attribution.)

## Format

`{family}_re{tag}.csv` with header `alpha_deg,cl,cd`.

## Adding a family

1. Add three CSVs at the Re tags `4e4`, `8e4`, `1.6e5`.
2. Register `(name, design_camber, design_thickness)` in `fansim.propeller.polars._FAMILIES`.
