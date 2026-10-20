# Round 17, Task C (R1.3 after R1.7 / R1.8): hang refusals with 1.75× and with the export hub

Prereg a212b29 (`prereg/round17`). Master 46a3408 (geometry identical to 9562574: `git diff` touches only
`registry.yaml`), run clone `qa/run_r17`, box only, no fansim edits. Scripts and data are in
`handoff/2026-10-19_from-qa-17/`: `c_common.py`, `c300_analytic.py`, `c300_built.py`, `c_r14.py`, `c_analyse.py`
→ `c300_analytic.jsonl`, `c300_built.jsonl`, `c_r14.json`, `c_summary.json`.

## Plain-language answer
- **Yes: with both fixes, the r14 proposed bounds keep refusals well under 5 %.** On the r14 P0 sample (seed 14004,
  n = 300) the share is **2.0 % (6/300, Wilson 0.9–4.3 %)**; even the Wilson upper bound is under 5 %. The current
  guided bounds give 1.3 %. **C-bounds: PASS.** No bounds change is needed.
- The order the fixes land in matters:
  - **R1.8 alone** (1.75× on today's auto hub) pushes P0 refusals to **7.7 %**;
  - **R1.7 alone** (export hub, growth below) drops them to **0.3 %**;
  - together, 2.0 %.
- If R1.8 lands first and you want < 5 % in the meantime (report-only, not pre-registered), raising sweep_tip's
  lower bound from 0 to 1.2 mm gives 5.0 % on the ladder draw and 4.3 % on a fresh hold-out.
- On the 300 r16 designs (a deliberately hang-heavy set, not the optimizer space), the refused share is:

| rule | refused | share (Wilson 95 %) |
|---|---|---|
| today (designed hang > 2 mm, auto hub) | 73 | 24.3 % (19.8–29.5) |
| (i) 1.75 × designed > 2, auto hub | 127 | 42.3 % (36.9–48.0) |
| (ii) designed > 2 at the export hub | 32 | 10.7 % (7.7–14.7) |
| (i + ii) 1.75 × designed at export hub > 2 | 58 | 19.3 % (15.3–24.2) |

- The validator verdict matches "today" on all 300, and there are no non-hang refusals.
- The export hub grows 174/300 hubs (Δh up to 6.66 mm). After growth, 115 designs still hang at all.
- The export hub is built as `hub_height_mm = need` (15 mm for a12x25) with `blade_hub_z_mm += Δh/2`. That keeps
  the top face fixed to 1e-6 mm and puts all growth below the blades, as R1.7 specifies.

## Built check at the export hub (the r16 P2 method, all 115 still-hanging designs, 0 errors)
- With the export hub, 58/300 designs are built deeper than 2 mm (123 with the auto hub). The built/designed ratio
  at the export hub is median **1.77** (p5 1.38, p95 2.00, n = 89 with h ≥ 0.5 mm), so the 1.75× rule carries over.
- **(i + ii) against built hang at the export hub:**
  - **C-sens FAIL: 57/58 refused, 1 missed.** S5_0207 has LE/TE features (tubercles, serrations, dimples), the known
    r16 tail: designed 0.86 mm, built 2.62 mm (3.0×).
  - **C-spec PASS:** 1/242 false refusals (0.4 %).
- **(i) against the r16 built hang (auto hub)**, which is a preview of R1.8's own acceptance test:
  - **1 missed (S2_0269, feature-free):** designed 1.141 mm, so 1.75× = 1.997 ≤ 2 mm, but built 2.252 mm;
  - 5/177 false refusals (2.8 %).
  - So **R1.8's pre-registered acceptance "every design whose built hang > 2 mm is refused" will FAIL by one design**
    on these data. Report-only factor scan: 1.78× catches it but refuses 4.5 % (> 3 %), and 1.80× refuses 5.1 %.
    No constant factor meets both R1.8 rules (→ QA-46).
  - With the export hub, S2_0269 doesn't hang at all (h = 0).
- (ii) alone misses 26 of the 58 (it doesn't model the 1.75× refill), so it is not enough without R1.8.

## For the board
- R1.3 can move once R1.7 and R1.8 both land; the r14 P0 bounds stand.
- R1.7 is the bigger lever and should land first or together with R1.8.
- R1.8: tell Cursor and Claude before the run that the 1.75× rule is expected to miss S2_0269. Claude decides
  whether to (a) accept a recorded FAIL, (b) validate on the realised loft (the r16 P2 method is exact and takes
  about 17 s per design), or (c) re-register. A 1.78–1.80 factor trades the miss for > 3 % false refusals.
