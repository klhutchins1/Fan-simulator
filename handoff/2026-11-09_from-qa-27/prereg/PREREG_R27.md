# Round 27 pre-registration (grok)

**Written:** 2026-11-09 MST, before any r27 diff, grep, test, probe or render output.
**Code under test:** fresh clone `/workspace/fansim/repo-r27` of `handoff_in/master_9869116.bundle` (sha256 0f8e06e0…1d92, verified),
HEAD 9869116 (the commit after the one that added `handoff/2026-11-09_to-qa-27/`; brief file identical to the brief zip copy).
**Seen before writing:** CLAUDE_TO_QA.md; QA_REVIEW header + Next-round table + tracker rows UI-39..42, QA-69, QA-70; COORDINATOR_STATUS;
commit subjects 41e2dc9..9869116; the diffstat (cockpit files changed: fan_copy.py, fan_tab_ui.py, figures.py only); audit §G4; RELEASE_PLAN G4 line.
**Committed from a separate worktree** (`qa/prereg_wt_r27`); the shared prereg working copy is not switched.
**Rules:** no Docker/CFD/OpenFOAM; no Assess/Sweep/Optimize/Export/Randomize clicks (Sweep Run never clicked); no edits/commits in the snapshot.
Evidence: **behavioural** (test/probe executed), **rendered** (headless cockpit, empty run), **static** (grep/code/diff).
Status words: verified / still open / partly fixed / not re-tested.

## A. QA-57 closeout (Volute Assess label)
- **verified** if `volute_tab.py` Assess copy lines and the Assess result readout carry "ranking only, unvalidated (CFD not yet converged)"
  (static), the label renders on the Volute tab Assess copy (rendered), a test covers it and fails when the label is removed (red check).
- **still open** if the Assess lines / readout are unchanged since 41e2dc9 (diff empty) and the patch `g3-QA57-volute-assess-label.patch` still applies.
- Mixed side: not re-tested (C22/C24/C25 not re-proved).

## B. UI-39 / UI-40
- **UI-39 verified** if Sweep steps refuses empty, non-int ("abc", "2.5", "1e9") and out-of-range (1, 13, 100) with a visible message and never
  starts a sweep: behavioural via the handler's validation path with Sweep/CFD stubbed (only if the handler can be driven without starting CFD),
  else static + rendered field attributes. **still open** if `fan_assess.py:448` is unchanged.
- **UI-40 verified** if the Trials field shows "2–40" (rendered) and out-of-range is refused with a message, not clamped (static/behavioural as above).
  **still open** if `fan_optimize.py:130-133` and the label are unchanged.
- Re-probe the expressions with ui-hunt-1's `seed_probe.py` if unchanged. Run is never clicked.

## C. QA-70
- **verified** if `build_report` (I/O faked, ui-hunt-1 `flowcard_hint_probe.py`) emits the Expert noise row for hint-only (no SWL) runs and a test covers it.
  **still open** if `fan_flow_report.py` is unchanged and the probe still drops the row. G2 not re-tested.

## D. G4 (+ QA-58, QA-69), only if merged (it is reported merged a56dcb0)
- D1 `figures.py`: no "~2×"; says CFD static ceiling is a little below the datasheet (~10 %).
- D2 `fan_tab_ui.py` intro: "Assess runs two CFD solves (free air and a loaded point), about 20–40 min" (or same meaning) — static + rendered.
- D3 `fan_copy.py`: no "~0.6×"; BEM "ranking only; coarse; can't separate close designs" — static + rendered tooltip if cheap.
- D4 no "~3–5 %" discretization in `design-rules.md` / `adversarial-review.md`; "GCI ≈ 21 %" wording present.
- D5 `design-rules.md`: "more blades raise airflow" gone.
- D6 `a12x25-reference.md`: close-reference STL wording at :24; :30 lists what is still open instead of "every gap closed".
- D7 README "Known limits" list has the six items incl. R1.4's "about 5 % less airflow than the real A12x25".
- D8 QA-69: `design-rules.md` and `scripts/extract_design_rules.py` no longer label the LBM noise objective "dB(A)"; label says estimate.
  Behavioural if the label dict can be read without running the extractor on CFD data.
- D9 tests: `tests/test_r110_g4_stale_numbers.py` passes; red check (restore one stale string in scratch → fails).
- **G4 verified** if D1–D9 pass (static parts named); **partly fixed** with the list otherwise. QA-58 / QA-69 closable on the same basis.
- Repo-wide grep for "~2×", "0.6×", "3–5 %", "dB(A)" next to LBM noise in user-facing copy reported as found.

## Also (not in the brief's table, user-asked): UI-41 / UI-42 code-unchanged check only (diff); no new renders.
## Output: per CLAUDE_TO_QA.md — notes `docs/qa/notes/r27-*.md` + a "Round 27" section appended to master's `docs/QA_REVIEW.md`.
