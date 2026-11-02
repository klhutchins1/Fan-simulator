# QA r24 C: does Assess already show K1 ("loaded probe did not converge")? (grok, 2026-11-01 MST)

- Prereg: **88c4e79**, section C. Code reading plus pure-function calls; no CFD. Proposal only; no source edited.
- Script: `handoff/2026-11-01_from-qa-24/scripts/c_k1_visibility.py`. Output: `data/c_k1.json`.

## Verdict: **PARTIAL**

K1 is shown only when a different trigger fires (the loaded probe reverses and Assess rejects the design). A design that scores but did not converge, which is the K1 case in r23 B, shows nothing in the cockpit.

## Path from flag to text

1. **Flag set:** `fansim/cfd/metrics.py:206,219`: `converged, drift = convergence(case_dir)` gives `FlowMetrics.converged`.
2. **Feasible result:** `fansim/optimize/objectives.py`:
   - `:602-606` builds `conv_note += "UNCONVERGED (free mean shift …; load mean shift …)"`;
   - it is returned as `ObjectiveResult.reason` (`:633`), with `raw["converged"]` (`:636`).
   - The module docstring (`:11-12`) says "unconverged results are flagged".
3. **Cockpit drops it:**
   - `fansim/cockpit/fan_assess.py:223-232`: `_assess` builds `Design(...)` without `reason=`. The default is `""` (`fansim/optimize/design.py`, `reason: str = ""`), and `design.json` writes `"reason": ""`.
   - `fan_assess.py:284`: `_assess_existing` sets `d.reason = ""` explicitly.
   - `fansim/cockpit/score_caption.py:74-77`: `stamp_score_extra` copies `near_stall*`, `beam_*` and `f1_bpf_margin`, but not `converged`.
   - The "Done ◆#…" message (`fan_assess.py:400-414`) gives free/load/eff, over-spec, vs-stock and `score_caption`. It says nothing about convergence.
   - Pure call: `score_caption(stamp_score_extra({}, raw))` gives the same string, "hose: case 8 Pa @ 50 CFM", for `converged` True and False.
   - No file in `fansim/cockpit/` reads `converged`. `fan_flow_report.py` and `cfd/flow_report.py` don't either, so the Results flow card is blind to it too.
4. **Reject path only (visible, different trigger):**
   - `objectives.py:117-157`: `_operating_point_reason(..., converged=False)` appends "; steady solve UNCONVERGED (…) — number is a solver artifact near stall".
   - `fan_assess.py:208-211` shows it as `"{label}: rejected — {reason}"`. The pure call confirms the text.
   - This fires only when the system-curve intersection fails (free or probe flow ≤ 0).
5. **Optimize trials:**
   - `fansim/optimize/study.py:229` stores `reason` as a trial user attribute, and `fansim/cockpit/data.py:146` loads it into `Design.reason`.
   - No cockpit view renders `Design.reason` for a feasible design, so it is not visible there either.

**Related, not K1:**
- The BEM near-stall flag (roadmap 25.10, `fansim/optimize/near_stall.py`) does reach the user:
  - in the Assess busy line (`fan_assess.py:337-346`);
  - as "⚠ near stall on this hose (…)" in `score_caption` (`score_caption.py:29-31`).
- It is a geometry/BEM rule (N1–N3), not the CFD convergence state. In r23 B terms it is closest to K3, which never fired.

## New bug

**QA-65 (MED):** Assess drops the UNCONVERGED note for feasible scores, contradicting `objectives.py:11-12`. Repro: steps 2–3 above.

## Proposal (patch only)

Patch: `docs/qa/patches/r24-C-k1-visible.patch`. It passes `git apply --check` on 23831da. It changes 2 files and adds 5 lines:
- keep `result.reason` on the Design, in both `_assess` and `_assess_existing`;
- add `converged` to the keys `stamp_score_extra` copies;
- have `score_caption` append "⚠ loaded point did not settle (CFD unconverged): loaded CFM is uncertain" when `extra["converged"] is False`.

Effects:
- With the patch, the pure call gives "hose: case 8 Pa @ 50 CFM · ⚠ loaded point did not settle (CFD unconverged): loaded CFM is uncertain" for False, and is unchanged for True.
- It shows in the Assess "Done" message, the selected-design info lines (`fan_trials.py:96-98` uses `score_caption`). Simple-mode visibility of those lines was not checked.

Suggested test: `stamp_score_extra` + `score_caption` with `raw={"converged": False}` contains "did not settle", and with True does not.

Not covered by the patch:
- older designs on disk have no `converged` stamp, so no warning until they are re-Assessed;
- the r23 caveat that a converged near-knee point can still be about 25 % off is not covered by K1.
