# r23 B: draft spec for a "near the knee" warning on a design's loaded point (proposal only)

QA bot, 2026-10-31. Master **3b92eea**. Prereg **0006f9b** (`prereg_r6`, branch `prereg/round23`,
`qa_r23/PREREG_R23.md` §B, committed 12:19 MDT before any data). Roadmap item: "Loaded-point fidelity near the knee".
- Scripts: `handoff/2026-10-31_from-qa-23/scripts/b_bem.py` (BEM `pq_curve` only, 4.7 s), `b_knee_rule.py` (scoring) and
  `b_k4_expl.py` (exploratory).
- Data: `handoff/2026-10-31_from-qa-23/data/b_*.json`.
- No CFD, no Assess, no source edits.

## Verdict: **needs more data**

- The OR rule has **1 miss** (lt120 13.71 Pa) and 0 false flags. The prereg bar for "worth landing" is 0 misses and ≤ 1 false flag.
- Only K1 (probe did not converge) catches anything. K2 and K3 add nothing on these cases.

## Rule R23-KNEE (as pre-registered; a flag is any of the three)

- **K1:** the loaded probe did not converge or failed.
- **K2:** φ = Q1/Q0 ≤ 0.60, where Q0 is the free-air CFD flow and Q1 the loaded probe flow.
- **K3:** P ≥ 0.60 × BEM `shutoff_dp_pa`. `pq_curve` default (Euler, as in `bem_screen_cfm`), design rpm, 0.5 mm gap.

**BEM shut-off (`b_bem.json`):**

| fan | Euler | axial_force |
|---|---|---|
| A12x25 Stock recipe | 38.87 Pa | 22.97 Pa |
| lt120 (frozen params) | 45.21 Pa | 27.32 Pa |
| FAN-01 | n/a: STL-only case, no BladeParams | n/a |

## Cases and results

**Ground truth:**
- bad = not converged, or more than 15 % off, or bistable;
- good = converged and within ±10 %.

**References:**
- A12x25 (close-ref STL run, audit-02 §4, which matches the brief's "5/10 held"): Cybenetics 100 % PWM, interpolated, cited
  only. The report terms are unclear, so the table is not stored and only % errors are given.
- lt120: `curve.csv`.
- FAN-01: `fan01_report.md`.

| case | P (Pa) | conv | CFD vs ref | label | φ | P/shutoff (Euler) | K1 | K2 | K3 | OR | outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A12x25 | 5 | yes | +8.9 % | good | 0.88 | 0.13 | – | – | – | – | clear |
| A12x25 | 10 | yes | +1.9 % | good | 0.69 | 0.26 | – | – | – | – | clear |
| A12x25 | 15 | **no** | (+10 %) | bad | n/a | 0.39 | ✔ | – | – | ✔ | **hit** |
| A12x25 | 20 | **no** | (−56 %) | bad | n/a | 0.51 | ✔ | – | – | ✔ | **hit** |
| lt120 | 6.85 | yes | +6.7 % | good | n/a (no free CFD) | 0.15 | – | – | – | – | clear |
| lt120 | 13.71 | yes | **+24.5 %** | bad | n/a (no free CFD) | 0.30 | – | – | – | – | **MISS** |
| FAN-01 | 7 | yes | +2.6 % | good | n/a | n/a | – | – | – | – | clear |
| FAN-01 | 64 | yes | +3.1 % | good | n/a | n/a | – | – | – | – | clear |
| FAN-01 | 126 | **no** | (−17 %) | bad | n/a | n/a | ✔ | – | – | ✔ | **hit** |
| FAN-01 | 135 / 205 / 253 | **no** | stall / collapse | bad | n/a | n/a | ✔ | – | – | ✔ | **hit ×3** |

Counts over the 12 scored points (5 good, 7 bad; no grey or unlabelled):

| component | hit | miss | false flag | clear |
|---|---|---|---|---|
| K1 | 6 | 1 | 0 | 5 |
| K2 | 0 | 7 | 0 | 5 |
| K3 | 0 | 7 | 0 | 5 |
| **OR** | **6** | **1** | **0** | **5** |

The lt120 6.2 mm mesh gives the same labels (+9.5 % good, +27.0 % bad). The FAN-01 135/205/253 Pa points have no usable
reference, but count as bad because they did not converge.

**False-flag risk:** 0 false flags on the 5 good points. Share of each fan's published stable branch that K2/K3 would flag:
- **lt120:** K3 0 %, because the threshold is 27.1 Pa, above all of 6.85–13.71 Pa. K2 cannot be evaluated (no CFD free point).
- **A12x25:** K3 0 % (threshold 23.3 Pa). K2 flags Q1 ≤ 35.9 CFM, about 37 % of the 24–56 CFM stable branch. None of the
  scored converged points fall there.
- **FAN-01:** K2/K3 n/a.

The risk is low, but only because K2/K3 almost never fire.

## Why it misses lt120 13.71 Pa

- The bad point **converged**, so K1 cannot see it.
- No free-air CFD exists for lt120 or FAN-01, so K2 is n/a.
  - Exploratory: with the BEM free delivery as Q0, φ = 0.80. With the 7 Pa point as FAN-01's Q0, φ = 0.55 at 126 Pa, which
    is already a K1 hit.
- K3 sits at 0.30 of shut-off: the knee is at a low pressure ratio on this fan (measured plateau at 13.7–14.7 Pa with
  34 Pa near shut-off).
- From A, the CFD itself has no plateau there; it is steep through 17 Pa. So a second CFD probe at P ± ΔP would **not**
  reveal the knee either. A CFD-only local-slope check would also miss it.

## Exploratory (post-hoc, not scored, not a recommendation to land): K4x, BEM flattening

The ratio is |dP/dQ| of the BEM curve at P divided by its mean |dP/dQ| over 0.5–1.0 × Q_free (`b_k4_expl.json`):

| case | ratio | would flag at < 0.5 |
|---|---|---|
| lt120 13.71 Pa | **0.51** | – |
| A12x25 15 Pa | 0.47 | ✔ |
| A12x25 20 Pa | 0.85 | – |
| A12x25 5 / 10 Pa, lt120 6.85 Pa | 1.2–1.5 | – |

BEM does show some flattening where the measured knee is, but the margin is too thin to land. It would be a candidate for
a new prereg with a threshold fixed in advance and more cases.

## Proposed spec (draft, for Claude/Cursor; no code)

1. **Land K1 now as the warning** (it is the only part with evidence: 6/6 non-converged bad points flagged, 0 false flags).
   Show "loaded point unconverged: likely near the knee or stall; treat the CFM as unreliable".
   - This overlaps R1.2 (status `ready`), which plans to stop the P–Q display at the last converged point.
2. **Keep K2/K3 as report-only fields** (φ, P/shutoff) on the Assess card. Do not flag on them; the thresholds are untested.
3. **Wording for converged loaded points on any fan:** "loaded-point flow can be off by 25 % even when converged, if the
   point is near the fan's knee". There is no Assess-only signal for this yet (lt120 13.71 Pa).

**What would decide it ("needs more data"):**
- a free-air CFD solve for lt120 (gives K2 a real Q0);
- more loaded points (converged and not) with measured curves, from the other fans in `docs/qa/benchmarks` (5 Delta fans
  and nv150) once CFD runs exist for them; at least 3 more converged-but-wrong points are needed;
- a pre-registered K4-type BEM-shape threshold tested on them.

## C: waiting

The R3.1 export leak check and the r21 A re-run wait for R3.1/R1.10. Not run.
