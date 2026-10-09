# Prop CT0 rpm-creep diagnosis: decision rules (pre-registered 2026-10-09, before any experiment)

## Measure
- Creep = BEMT static CT0(30,000 rpm) / CT0(4,000 rpm) − 1 for the cockpit preset `fpv_5inch`
  (default flat).
- Matched-geometry check: the slope of BEMT/measured CT0 against rpm on the GWS 5×4.3 UIUC
  static file, 1530–7897 rpm. Report the max−min spread of the ratio.
- Reference: UIUC measured CT0 is flat to within about ±4 % from 2.5k to 7.9k rpm. APC PER3
  3-blade 5" curves change by ≤ +4 % from 4k to 30k.

## Attribution
Switch off one mechanism at a time (monkeypatch only, no code edits), then switch them off in
combination:
- M = Prandtl-Glauert / wave drag (`_compressibility_cl_cd`);
- F = the analytic fallback for Re below the lowest table (`polars.py:151`), replaced by clamping
  to the lowest table;
- T = the Re trend inside the tables (e387 4e4 → 8e4 → 1.6e5), replaced by a fixed Re.

A mechanism is "responsible" if switching it off removes ≥ 1/3 of the creep.

## Patch rule
Propose a patch only if a single, physically defensible change meets all of these:
- (i) cuts the preset creep to ≤ 20 %;
- (ii) keeps the GWS static CT0 at 7407 rpm within ±15 % of 0.149 (Audit #3 tolerance);
- (iii) reduces the GWS CT0 ratio spread from 2.5k to 7.9k rpm;
- (iv) keeps the GWS J-sweep CT rms at 6047 rpm ≤ 0.015.

Otherwise: diagnosis only, no patch.
