# Round 14, Task B: independent maths check (master 9562574)

Prereg `prereg/round14` 586bbe9 (`qa_r14/PREREG_R14.md`, sha256 0ce049ca…16adc). I wrote the expected values from
first principles in each script before calling the code, and I did not read the tests. Agree = within 1 % or
0.001 abs. Scripts and data: `handoff/2026-10-16_from-qa-14/scripts/b_maths.py`, `b5_hang.py` →
`data/b_maths.json`, `data/b5_hang.jsonl`.

## B1 `cfd.cfm_from_outlet_flow` / `parse_fan_metrics`: 4/5 agree, (d) FAIL → QA-39 (LOW)
- (a) 0.025 m³/s → 52.972 CFM (CFM constant rel. error 9.4e-7). (b) −0.010 → −21.189 CFM (signed, not abs).
  (c) the tail is `rows[int(0.75 n):]`, matching the mean of the last 25 %. (e) p_out − p_in = 5 m²/s² × 1.2 = 6.0 Pa. All agree.
- **(d) restart dirs `0/`, `500/`, `1000/`:** the code returns the `500/` flow (42.38 CFM) instead of the latest
  `1000/` (63.57). `_pp_file` sorts time directories as **strings** ("1000" < "500"). The same string sort is in
  `sanity.py`, the `timing.py` mirror and the free-history copy in `objectives`. Latent today: shipped flows wipe
  `postProcessing` on every `build_case` and always `startFrom startTime`, so only one time dir exists. Note that
  `flow_report_case.latest_time` already sorts numerically.

## B2 motor derate: all agree
Budget 12 V · 0.14 A · 0.50 = 0.84 W in both the spec and `A12X25_MOTOR`. λ = 1 / 1 / 0.7937 / 0.6542 for
P = 0.5 / 0.84 / 1.68 / 3.0 W. `rescore_from_raw`: flow ∝ λ, Δp_op ∝ λ², η unchanged (18.507 %).
`rederate_scale` 1.26 and 0.7937 agree. Code read: `objectives.py:520-583` uses the same algebra.

## B3 `fan.bem_prescreen`: PASS
5 guided wrapped designs (5 tries, seed 14002) × 2 pressure models: 0 bound violations (max Q·Δp/P = 0.583,
Δp ≤ ρU_tip²). Every free delivery is "crossed" with |Δp| inside the tolerance.

## B4 wrapped section `_section_loop(wrap=True)`: a, b PASS. c FAIL as registered (my estimator, not the code)
- (a) every point lies on r = 40 mm (max error 7e-15 mm). (b) unrolled, the loop matches my own NACA 4412-type
  section rotated 30° and skewed 5 mm: max 0.0055 mm (tolerance 0.036 mm).
- (c) my estimator reads chord 30.0 but camber 0.0379 / stagger 30.20° on the code's loop, and 0.0382 / 30.18° on
  **my own reference section**. So the miss is estimator bias. Code vs my reference: chord 0.006 mm, stagger 0.027°,
  camber 0.0003.
- Convention (doc note): the LE leads in +θ and sits upstream at +Z, consistent with rotation +θ pumping −Z.

## B5 hub-hang measure: explanation test PASS (10/10)
10 designs (r7 stress pool, seed 14005, designed hang > 0):

| design | designed (mm) | realised mesh (mm) | section formula on loft stations (mm) | ratio | mid chord design → loft (mm) |
|---|---|---|---|---|---|
| S4_0065 | 0.20 | 0.53 | 0.53 | 2.69 | 34.6 → 35.6 |
| S4_0186 | 0.81 | 1.74 | 1.74 | 2.15 | 35.5 → 38.7 |
| S4_0117 | 4.04 | 7.72 | 7.72 | 1.91 | 39.3 → 49.0 |
| S6_0094 | 3.74 | 7.06 | 6.80 | 1.89 | 34.8 → 44.9 |
| S4_0264 | 4.43 | 8.31 | 8.31 | 1.88 | 33.9 → 43.7 |
| S1_0330 | 2.35 | 4.28 | 4.28 | 1.82 | 33.9 → 39.7 |
| S4_0207 | 1.10 | 1.95 | 1.95 | 1.77 | 35.9 → 38.6 |
| S1_0163 | 2.56 | 4.41 | 4.41 | 1.72 | 38.5 → 44.4 |
| S1_0374 | 2.00 | 3.26 | 3.26 | 1.63 | 30.6 → 34.5 |
| S6_0000 | 0.91 | 1.41 | 1.36 | 1.55 | 25.9 → 27.6 |

Median ratio **1.85** (1.55–2.69). The same section-point formula evaluated on `prepare_loft_chords(p)`
reproduces the mesh hang within max(0.1 mm, 5 %) on 10/10. So the ~1.6–2× ratio is the chord realisation. The
loft stretches the mid-station chord by up to +10 mm (+29 %) and turns its stagger by up to +4.4°. The deepest
point stays at the root (r/R 0.47–0.53).
**Doc note / decision for Kimball (not a new QA item):** the 2 mm hang limit is checked on the *designed* chords,
so a design at the limit really hangs ~3.7 mm (up to ~5.4 mm at the worst ratio). If the 2 mm rule is meant for
the built blade, the check should use the realised loft stations. The formula is right; the basis is a choice.
