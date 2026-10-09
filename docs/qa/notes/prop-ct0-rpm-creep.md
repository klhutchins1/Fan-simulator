# Prop static CT0 creeps up with rpm: diagnosis (QA, 2026-10-09)

## Plain-language summary (for Kimball)
- **What's wrong:** the prop model says a prop gets about 60 % "better at making thrust" (CT0)
  between 4,000 and 30,000 rpm. Real measurements (UIUC) and APC's published numbers stay flat.
- **Why, mostly:** the model swaps the airfoil data it uses as the prop speeds up.
  - At low speed it uses a rough backup formula. On a 5" prop, that covers every rpm below about
    10,000 rpm.
  - Above that it uses the proper airfoil tables, which give noticeably more lift and less drag.
  - So about half the creep is just the model changing data sources, not physics.
- **The rest:**
  - About 45 % comes from the airfoil tables themselves improving at higher speed (Re 40k →
    120k). That is real airfoil behaviour, but no measurement here can confirm how much of it a
    5" prop shows.
  - About 15 % comes from the Mach (compressibility) correction near the tip at 30k rpm. That is
    expected physics.
- **Does it affect the 2087 g headline?** Not much. At 30,000 rpm the model already uses the
  tables, and the number sits inside APC's range. The creep mainly makes **low-rpm** predictions
  too low: −17 % for the preset at 4,000 rpm, and −5 % to −23 % against UIUC measurements at
  1.5k–7.4k rpm.
- **Fix?** Not yet. The obvious one-line fix (use the lowest table instead of the backup formula)
  makes static thrust match UIUC almost perfectly. However, it makes the forward-flight thrust
  sweep worse: CT rms rises from 0.010 to 0.024. It also leaves +35 % creep, because the table
  trend remains. Under the rules I wrote down before testing, that means no patch. A proper fix
  should blend the two data sources smoothly; see the end of this note.

## Setup
- Branch `qa-fixes-2026-10-09` @ d781894. The prop code is identical to 961f953 apart from the
  η fix (`polar.py`).
- Monkeypatch experiments only; no source edits.
  - Script: `handoff/2026-10-09_from-qa/scripts/creep.py`.
  - Raw output: `creep.json` next to it.
  - Plot: `docs/qa/notes/prop-ct0-rpm-creep.png`.
- Decision rules pre-registered **before** the experiments:
  - File: `docs/qa/notes/prop-ct0-rpm-creep-criteria.md`, sha256
    `428c808ea9aa720cd3538e6db6f3493a6931a8b3397feb43a9a0eb91b700cea4`.
  - Committed as `3bc79d76` at 2026-10-09T11:00:11-06:00 on branch `prereg/ct0-creep` in the QA
    research clone.
- Props:
  - The cockpit preset `fpv_5inch` (5×4.3×3, default flat). The polar family picked is **e387**,
    with tables at Re 4e4 / 8e4 / 1.6e5.
  - The UIUC GWS 5×4.3 2-blade geometry, compared with its UIUC static file (files in
    `handoff/2026-10-09_from-qa/uiuc_gws_5x4.3/`).
- Reynolds number at 0.75 R:
  - Preset: 15.7k at 4,000 rpm, 31k at 8k, 59k at 15k, 86k at 22k, 118k at 30k.
  - GWS: 6.7k to 35k over the whole UIUC static file, so all of it is below the lowest table.

## Mechanisms switched off one at a time
- **M:** the Mach correction (`bemt._compressibility_cl_cd`).
- **F:** the analytic fallback below the lowest table Re. `polars.py:151-152`
  (`if r < res[0]: return None`) makes `bemt._section_aero` (`bemt.py:104-110`) fall back to
  `_analytic_section`. With F off, the section is clamped to the 4e4 table instead.
- **T:** the Re trend inside the tables, removed by evaluating every section at one fixed Re.

| variant | preset CT0 at 4k / 8k / 15k / 22k / 30k rpm | creep 4k→30k | GWS CT0 @ 7407 vs 0.149 | GWS model/meas. spread 2.5k–7.9k | GWS J-sweep CT rms @ 6047 |
|---|---|---|---|---|---|
| as is | 0.158 / 0.180 / 0.221 / 0.240 / 0.257 | **+62 %** | 0.142 (−5 %) | 0.161 (0.80→0.96) | 0.010 |
| M off | 0.158 / 0.180 / 0.218 / 0.233 / 0.242 | +53 % | 0.142 | 0.160 | 0.010 |
| F off (clamp to 4e4 table) | 0.190 / 0.191 / 0.219 / 0.240 / 0.256 | +35 % | 0.150 (+0 %) | **0.023** | 0.024 |
| M + F off | 0.190 / 0.190 / 0.216 / 0.232 / 0.241 | +27 % | 0.149 | 0.023 | 0.024 |
| M + F + T off (Re fixed 4e4) | 0.190 flat | 0 % | 0.149 | 0.023 | 0.024 |
| Re fixed 4e4, Mach on | 0.190 → 0.198 | +4 % | 0.150 | 0.023 | 0.024 |
| Re fixed 8e4 / 1.6e5, M off | 0.239 / 0.260 flat | 0 % | +25 % / +30 % | 0.017 / 0.020 | 0.029 / 0.033 |

## Attribution of the +62 points (preset, 4k → 30k rpm)
The three pieces add up: 27 + 27 + 8 ≈ 62.
- **F, the analytic fallback below Re 4e4: about 27 points (44 %). Responsible.**
  - The jump at the boundary is large. At α = 0°, cl goes from 0.230 to 0.320 and cd from 0.033
    to 0.020. At α = 4°, cl goes from 0.632 to 0.700 and cd from 0.033 to 0.027. Between Re
    39,999 and 40,000.
  - The analytic cd0 is 0.008 + 5/√Re (0.033 at 4e4 and 0.048 at 1.1e4), with a reduced lift
    slope.
  - This term alone explains **all** of the matched-geometry creep against UIUC. With F off, the
    model/measurement ratio is 0.99–1.01 from 2.5k to 7.9k rpm, compared with 0.80–0.96 today.
    Static CP0 at 7407 rpm also goes from 0.0644 to 0.0736, against 0.0749 measured.
- **T, the e387 table trend from 4e4 to about 1.2e5: about 27 points (44 %). Responsible, but
  unverified.**
  - This is genuine 2-D airfoil behaviour: the laminar bubble shrinks with Re.
  - The UIUC 5" data stop at Re ≈ 35k, so nothing here can confirm or refute it.
  - APC's PER3 curves (their own vortex model, not measurements) rise by ≤ 4 % over 4k–30k.
  - Fixing Re at 8e4 or 1.6e5 over-predicts the measured GWS CT0 by 25–30 %, so the high-Re
    tables are wrong for low-Re UIUC conditions, as expected.
- **M, Prandtl-Glauert on attached cl near the tip: about 8–9 points (about 15 %). Not
  responsible** under the one-third rule.
  - The tip Mach number is 0.58 at 30k rpm. A +6 % CT0 at 30k is plausible physics.

## Why no patch (pre-registered rule)
The single change "F off" (clamp below the lowest table):
- (i) creep ≤ 20 %: **fails** (+35 %);
- (ii) GWS CT0 @ 7407 within ±15 %: passes (+0 %);
- (iii) GWS spread reduced: passes (0.161 → 0.023);
- (iv) J-sweep CT rms ≤ 0.015: **fails** (0.024).

The clamped table over-predicts forward-flight CT at 6047 rpm: the mean bias is +0.024 against
+0.009 today. Today's good forward-flight match is therefore partly the fallback's high drag
cancelling something else. Do not "fix" one side without checking the other.

## Suggested next step (not done)
- Replace the hard switch at `polars.py:151` with a continuous low-Re extension. For example,
  scale the 4e4 table's cd by (4e4/Re)^0.5 and its lift slope by the analytic Re factor below 4e4,
  blended in over 2e4–4e4.
- Pre-register (i)–(iv) again, plus the full J sweeps for GWS and DA4022 (2- and 3-blade).
- For T, find measured CT0 for a small prop at Re 6e4–1.5e5. Candidates: UIUC vol 1 APC 8–9"
  props at 5–6k rpm, or a thrust-stand dataset for 5" props at 20–30k rpm.
- Until then, treat absolute 5" numbers below about 10k rpm as roughly 10–20 % low.
