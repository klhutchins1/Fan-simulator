# G3 re-check pre-registration (grok, self-initiated): R1.10 G3 / QA-57 / R2.4 on master 41e2dc9

**Written:** 2026-11-09 MST, before any G3 diff, grep, test, probe or render output.
**Code under test:** fresh clone `/workspace/fansim/repo-r26-g3` of `handoff_in/master_41e2dc9.bundle`
(sha256 f999d7de…5939, verified), HEAD 41e2dc9. G3 fix 5945620 (merged dd13be7 → c2333b5 → 41e2dc9).
**Seen before writing:** commit subjects 83681c2..41e2dc9; COORDINATOR_STATUS.md (changed-path list); RELEASE_PLAN R1.10 G3
and R2.4 entries; audit 10-29 §G3; QA_REVIEW QA-57 repro; r21 CSV rows C22, C24, C25.
**Committed from a separate git worktree** so the shared prereg working copy is not switched.
**Scope:** G3 only + a regression pass on UI-39..42 / QA-70. Not G4/G5, R3.1, R3.5b; the 668/568/683 gate counts are not re-run.
**Rules:** no CFD/Docker/OpenFOAM; no Assess/Sweep/Optimize/Export/Randomize clicks; no edits/commits in the snapshot.
Evidence classes: **behavioural** (executed test/probe), **rendered** (live headless cockpit DOM, empty run), **static** (grep/code).

## G3 criteria (audit §G3, R2.4, QA-57 repro)
- **G3-1 (C22, `mixed_tab.py:765`):** no "honest MRF" wording in Mixed; Mixed Assess text says
  "runs MRF CFD (not validated against published data)" or same meaning. Static + rendered (Mixed Expert panel).
- **G3-2 (C24, C25, `volute_tab.py:164, 691`):** no "honest (radial MRF) CFD"; Volute says "ranking only, unvalidated (CFD not yet
  converged)" or same meaning. Static + rendered.
- **G3-3 (R2.4 tab title, `app.py:187-191`):** the Mixed tab is labelled experimental (not "Mixed · estimate"); rendered tab text.
- **G3-4 (R2.4 results):** Mixed Assess/Optimize results text carries "Experimental: not validated against published data".
  Static (results only appear after a run); rendered if visible without a run.
- **G3-5 (R2.4 README + export):** README feature list / Known limits say Mixed is experimental; the exported README/sidecar
  for mixed-flow parts carries the label — behavioural via the export text builder if callable without CFD/Export click, else static.
- **G3-6 (QA-57 `fan_tab_ui.py:495`):** the Fan intro no longer calls the other tabs honest CFD; static + rendered.
- **G3-7 repo-wide:** grep `fansim/`, README, docs/ user-facing copy for "honest" next to MRF/CFD on Mixed/Volute: 0 unqualified hits.
- **G3-8 tests:** `tests/test_r110_g3_mixed_volute_copy.py`, `tests/test_simple_mode_copy.py` pass; red check: reverting one
  G3 string in a scratch clone makes a G3 test fail (if cheap).
- **Verdict:** QA-57 **verified, closable** if G3-1..3, G3-6..8 pass and G3-4/5 pass (static parts named as inspected).
  **partly fixed** with the list otherwise. R1.10 stays open regardless (G4/G5, release re-audit).

## Regression pass (UI-39, UI-40, UI-41, UI-42, QA-70)
Each is **fixed** only if the code path changed and a probe/render shows the new behaviour; **still open** if the
ui-hunt-1 code is unchanged (diff 83681c2..41e2dc9 on the cited lines) and, where cheap, the same probe repeats.
