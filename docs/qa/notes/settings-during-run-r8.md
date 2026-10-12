# Settings changed while a job runs: round-8 re-verification (QA round 8, Task A)

- **Code:** master `f86df9a` (fix `e5bdb81`, roadmap 25.11). Clean clone `/workspace/fansim/repo-r8`.
- **Harness:** round 7's `docs/qa/settings_during_run/harness.py`, unchanged. It monkeypatches
  `fan_assess.evaluate_candidate_isolated` (the call *inside* `_blocking_eval`) with `**kw`, so the new
  `_blocking_eval(flat, features, workdir, rs)`, `_assess(..., rs, ...)` and `_assess_existing(..., rs, ...)`
  signatures needed no adaptation. Run: `python docs/qa/settings_during_run/harness.py 4`
  (4 s fake job; only ordering matters). Output: `harness_output_r8.json` (round 7's stays in
  `harness_output.json`). Side-by-side printer: `compare_outputs.py`.
- Prereg: round 7's `settings-during-run-prereg.md` verdict key (a)-(e) applies unchanged.

## Before (r7, `5980677`) and after (r8, `f86df9a`)

Start state in every scenario: a12x25, PETG, hose `case` (8 Pa), refine off.

| scenario | change made mid-run | r7 saved | r7 class | r8 saved | r8 class |
|---|---|---|---|---|---|
| A0 none | – | as clicked | d | as clicked | d |
| A1 slider | camber +0.03 | clicked camber | d | clicked camber | d |
| A2 material/hose/refine | PLA, legacy, refine on | PLA / legacy / 1 Pa / refine **on** (run used PETG/8 Pa/off) | b (QA-22) | PETG / case / 8 Pa / off | **d** |
| A3 fan model | a12x25 → delta_afc1212de | fan_model **delta** (+ "motor-limited" tag vs Delta rpm) | b (QA-22) | a12x25, no motor-limited tag | **d** |
| A4 select other design | select #4242 (legacy, refine on) | legacy / 1 Pa / refine on | b (QA-23) | case / 8 Pa / off | **d** |
| A5 library switch | LIB_X → LIB_Y | parent **LIB_Y** | b (QA-24) | parent LIB_X | **d** |
| A6 Assess-existing + select other | select #4301 | result on #4300 (right design), `material` **None** | d (+ missing stamp) | result on #4300, `material` **PETG** stamped | **d**, material now stamped |
| A7 Sweep, material changed after step 1 | PETG → PLA | steps 2-3 **ran** with PLA, all 3 stamped PLA | a+b (QA-25) | all 3 steps ran and stamped PETG | **d** |
| P1 Preview, camber + cup changed | camber +0.03, cup toggled | caption shows live camber 0.113 (built 0.083) | QA-26 | **unchanged**: caption 0.037/0.113/0.097 for a 0.0834 build | unchanged, as expected (27.5) |
| E1 Export, hub/mirror/select changed | hub +3 mm, mirror on, select #4400 | file from snapshot; view jumps to #4400; message reads live hub | QA-26 | **unchanged** (same) | unchanged, as expected (27.5) |

Mixed Assess (code reading only, `mixed_tab.py:356-358`, `:464`, `:546-547`): hose and refine are now taken
at the click and the saved `extra` uses those locals. Consistent with the fix; not run in the harness.

**Result: PASS.** A2-A5 and A7 are class d; Assess-existing stamps `material`; P1/E1 unchanged.
QA-22, QA-23, QA-24, QA-25 → fixed (verified). QA-26 → still open (27.5).

## New finding: QA-29 (LOW, display) the "Done" message is overwritten by the progress ticker
In every r8 Assess scenario the final `assess_msg` is `Running Assess… 0:04 (typically 30-40 min …)`
**after** the job finished, instead of `Done ◆#9000: free … load … eff …`. Round 7's run showed "Done".

- Cause (`fansim/cockpit/fan_assess.py`): `on_assess` sets the Done message (`:374-388`), then
  `await _bake_viz_for_design(d)` (`:389`), which awaits `run_in_executor`. The ticker task
  `_assess_progress_ticker` (`:154-167`) loops `while state.assess_busy`, so as soon as the bake yields
  it rewrites `assess_msg` with the busy caption. `ticker.cancel()` only runs in `finally` (`:405`),
  after the overwrite. The Done text, the "vs stock" line and the score caption are lost.
- Pre-existing, not caused by `e5bdb81`: the same code is in `5980677`. Round 7 saw "Done" by timing
  luck (the ticker slept through the short bake). `harness_bake_race.py` makes the bake take 3 s:
  both `5980677` and `f86df9a` then end on "Running Assess… 0:06"; with an instant bake `f86df9a`
  still ends on "Running Assess… 0:04".
- In real use the bake (midplane + glyphs) takes seconds, so the user most likely always sees a frozen
  "Running Assess…" caption after the run is done.
- Fix idea (proposal only): cancel the ticker before writing the Done message (or have the ticker
  stop when a `done` flag is set), and/or have the bake append to the final message after the ticker
  is gone.
