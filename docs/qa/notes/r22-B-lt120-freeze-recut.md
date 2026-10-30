# r22 B: lt120 freeze re-cut at the 10 table radii (R1.1a, QA-60; no CFD)

QA bot, 2026-10-29. Master **b3d5543**. Prereg **715891f** (`prereg_r6`, branch `prereg/round22`,
`qa_r22/PREREG_R22.md` §B, committed before any data). Script: `handoff/2026-10-29_from-qa-22/scripts/b_lt120_recut.py`
(adapted from r21 `c_lt120.py`). Data: `handoff/2026-10-29_from-qa-22/data/b_lt120_recut.json`, `r22-B-lt120-recut.csv`.
Run time 2.7 s. No rebuild, no outside STL, no source edits.

## Verdict: **B PASSES** (r = 23 N/M, 9/9 PASS) · matches r21 S · **QA-60 closed**

**Input:** the committed `validation/reference/lt120/lt120.stl`, cut as committed.
- sha256 `6f93f231…1112f63`, 1 960 084 bytes. `geometry_freeze.json` records no STL hash, so there is nothing to compare it with.
- Mesh: watertight, 1 body, 7 blades, rmax 60.000 mm, z −7.47 … +16.16 mm, volume 47 318.9 mm³, 39 200 faces.
- Direction: `prove_direction` CONCLUSIVE, ω sign +1 (0.2 s).
- `params.json` = the table params + `reference_build: true`, `section_wrap: "cylinder"`; `clip_below_hub` stays true.

**Gate:** chord within 3 % of the table, camber within ±0.005 of `_ref`, stagger within ±1.5° of `_ref`. This is the same
gate and the same `_ref` reading (`_measure_loop`) as r21 C.

| r mm | chord table → meas | err | stagger meas / ref | err | camber meas / ref | err | verdict | Δ vs r21 S | Δchord vs r21 P |
|---|---|---|---|---|---|---|---|---|---|
| 23.0 | 18.6 → – | – | – | – | – | – | **N/M** (0 blades) | – | – |
| 26.7 | 21.2 → 21.18 | −0.08 % | 40.19 / 40.19 | 0.000° | 0.0292 / 0.0294 | −0.0002 | PASS | 0 | +0.01 % |
| 30.4 | 23.6 → 23.63 | +0.11 % | 39.97 / 39.97 | −0.003° | 0.0298 / 0.0299 | −0.0000 | PASS | 0 | +0.16 % |
| 34.2 | 26.2 → 26.01 | −0.73 % | 39.75 / 39.76 | −0.007° | 0.0306 / 0.0307 | −0.0001 | PASS | 0 | −0.76 % |
| 37.9 | 28.9 → 28.46 | −1.52 % | 39.33 / 39.35 | −0.013° | 0.0307 / 0.0307 | −0.0000 | PASS | 0 | −1.45 % |
| 41.6 | 31.6 → 30.99 | −1.93 % | 39.01 / 39.04 | −0.030° | 0.0317 / 0.0315 | +0.0002 | PASS | 0 | −1.90 % |
| 45.3 | 34.2 → 33.53 | −1.95 % | 38.60 / 38.64 | −0.042° | 0.0316 / 0.0317 | −0.0001 | PASS | 0 | −1.92 % |
| 49.1 | 36.6 → 35.79 | −2.21 % | 38.08 / 38.14 | −0.055° | 0.0320 / 0.0321 | −0.0001 | PASS | 0 | −2.12 % |
| 52.8 | 39.1 → 38.27 | −2.13 % | 37.38 / 37.44 | −0.063° | 0.0322 / 0.0321 | +0.0001 | PASS | 0 | −2.03 % |
| 56.5 | 41.6 → 40.66 | −2.26 % | 36.38 / 36.44 | −0.060° | 0.0321 / 0.0321 | −0.0001 | PASS | 0 | −2.15 % |

- Worst case: chord −2.26 % (75 % of the 3 % gate), stagger 0.063°, camber 0.0002.
- **Comparison with r21 S:** Δ = 0.00 % / 0.000° / 0.0000 at every radius, so it matches.
  - The freeze volume equals r21 S exactly.
  - The STL bytes differ from both r21 S (sha `0121e3e1…`) and r21 P (sha `81792da6…`). This is a byte-level difference only; the geometry is the same as S.
- **Comparison with r21 P (clip off; report-only):** from 34 mm outward the clip-on reference is 0.8–2.2 % shorter in chord.
  - For R1.1b, note that the frozen reference sits 2.0–2.3 % under the table chord from 41.6 mm to the tip.
  - That is inside the gate, but it is systematic and not centred on zero.

## QA-60 sub-items (freeze files + code, read only)

| # | Sub-item | Status | Evidence |
|---|---|---|---|
| 1 | `reference_build` skips only the hang checks; clip stated | closed | `blade.py:908-911` skips only the `validate_blade_params` hang test; `blade.py:974` `_refuse_if_built_hang_past_limit` returns early. `clip_below_hub` is untouched. `tests/test_lt120_reference.py` asserts the clip stays on. `fansim/validation/lt120.py:44-47` |
| 2 | r = 23 recorded as embedded | closed | `geometry_freeze.json` `r_23_mm`: "embedded root station, not cuttable (inside hub 25 mm)". Matches the N/M cut |
| 3 | folder present | closed | `validation/reference/lt120/` holds `lt120.stl`, `geometry_freeze.json` and `params.json` |
| 4 | tip extrapolation 56.5 → 60 mm recorded | closed | `tip_to_60_mm`: "last table station (r 56.5 mm) reused at r_frac 1; no extra extrapolation" |
| 5 | which build is the reference | closed | freeze `clip_below_hub: true`, `reference_build: true` (clip on). Its `cut_check` numbers equal mine |

**QA-60 verdict: closed.** B passes 9/9 with r = 23 N/M, and all 5 sub-items are closed. The board line at
RELEASE_PLAN:81 ("reference_build=True skips hang only (clip stays on) … QA-60 closed") is true as written.

No new IDs. One report-only follow-up for R1.1b: the reference is the clip-on build and runs 2–2.3 % short in chord
outboard. If R1.1b compares against LT120 table chords, say which one it uses.
