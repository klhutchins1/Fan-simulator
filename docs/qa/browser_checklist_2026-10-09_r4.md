# Browser re-test, round 4: master @ f238f54 (2026-10-09)

**Setup (three cockpits; all bind 127.0.0.1, empty run dirs, Linux box):**

| port | code | ws guard | run dir | used by |
|---|---|---|---|---|
| 8080 | master `f238f54` (`/workspace/fansim/repo-r4`) | on (default) | `/workspace/fansim/qa/runs/qa_empty_r4` | B1, B11, B12 |
| 8081 | `961f953` (pre-guard; `git archive` export in `/workspace/fansim/qa/r4_961f953`, repo-r4 venv; lockfile identical) | none (pre-guard code) | `/workspace/fansim/qa/runs/qa_empty_r4_961` | B10 |
| 8082 | master `f238f54` | **off** (`FANSIM_WS_GUARD=0`) | `/workspace/fansim/qa/runs/qa_empty_r4_noguard` | B10 |

- Use **one tab per cockpit** (they share state per server). Don't run Assess / Sweep / Optimize / CFD.
- Screenshots go in `docs/qa/screenshots/2026-10-09-r4/<row>_*.png`. Report `verified` / `reopened: <why>` per row, plus one `UI-n` row per new finding.

## What changed since r3 (git log)
- **UI-4, `5b342ba`:**
  - The parent (`build_stl_isolated`) writes **stage 1/4 "loading CAD kernel"** before it spawns the worker. Before this, the worker's own write landed only after `python -m` had imported CadQuery (~2.2 s).
  - There are now **four** stages, all of which take visible time: 1 loading CAD kernel → 2 preparing design (chord fit) → 3 build (or carving motor cup) → 4 writing mesh/STL. The old "reading design" and "realising chords" stages were merged.
  - The ticker polls every **0.5 s** (it was 1 s).
  - Claude measured stage 1 at 0.05 s (parent) and 5.6 s total (Stock, chords cached, Windows).
  - Unchanged from r3: the bar never goes backwards (`max(prev,…)`), it starts with a determinate sliver, and the motor-cup switch (Fan tab → **Export options**) defaults to off.
- **UI-23:** no code change. `FANSIM_WS_GUARD=0` (commit `9482929`) disables the per-socket send guard. `961f953` predates the guard entirely.
- **Commits since r3 that touch the UI:** none beyond the above. `6ab25f3` and `f238f54` are screen/CFD scripts.

## Rows

| # | item | steps | pass if |
|---|---|---|---|
| B1a | UI-4 Stock Preview (:8080) | Fan tab → Stock. Motor cup **off** (Export options). Click **Preview** with a stopwatch. Note the first caption and when it appears. | Within ≤ 0.5 s of the click: a determinate sliver and **"stage 1/4 · loading CAD kernel"** (no indeterminate stripe, no blank). Stages appear in order 1→2→3→4. You see at least 3 of the 4 captions. The % never decreases. Total about 5–15 s on this box (Claude: 5.6 s on Windows; the first Preview of a fresh process may add a ~20 s chord fit at stage 2, which must then *be shown* as stage 2). |
| B1b | UI-4 motor-cup Preview | Turn the motor cup **on** → Preview again. | The same rules apply. Stage 3 reads "carving motor cup"/build and may last ~1 min. The bar **does not freeze**: the elapsed counter still advances at least every 1 s throughout. The page stays responsive (scrolling/hover work). Note the duration. A freeze > 2 s is a fail. If it happens, note the time so it can be checked against box memory (cup worker peak ~7.6 GB, see QA_REVIEW r4 request 5). |
| B1c | UI-4 repeat | Preview again straight after B1b. | The bar starts again from stage 1/4. It does not start at the previous run's 4/4 or 100 %. |
| B10a | UI-23 pre-guard (:8081, 961f953) | Open a **fresh** tab at :8081 with DevTools Console open and "Preserve log" on. Wait until the fan renders, then reload (F5) **3×**, waiting for the render each time. | Record the count of `TypeError: n[i[e]] is not a function` (`invokeConnectionClose`) per reload. |
| B10b | UI-23 guard off (:8082) | The same as B10a, at :8082. | The same: record the count. |
| B10c | UI-23 guard on (:8080, control) | The same as B10a, at :8080. | The same: record the count. |
| B10 verdict | | | If the error fires on **:8081 or :8082** (with no guard) → **upstream** trame-client unload-time rejection: close UI-23 as wontfix/upstream. If it fires **only on :8080** → the guard causes it: reopen against `ws_guard.py` (its close/abort path). If it fires nowhere in 9 reloads → note it as "not reproduced on Linux Chrome" and keep it LOW/open. |
| B11 | Request 7: first-time user, **1366×768** (:8080) | Use DevTools device toolbar → Responsive 1366×768 (or resize the window). Pretend you've never seen the app. Goal: **open → pick Stock → Preview → Export a printable STL**, without reading the docs. Narrate each place you hesitate. | You reach a downloaded/written STL **without guessing**. **One row per finding** (`UI-24`, `UI-25`, …) with a screenshot, tagged **jargon** / **clipped** / **contrast** / **error** / **guess** / **layout**. Look out for:<br>- **Jargon** with no tooltip or plain-words gloss: **Q3**, **surf level**, **Load Pa@50CFM**, **derate**, **η**, GCI, BEM, MRF, stagger/lean/skew, "fit frame", "fit hub".<br>- **Clipped or truncated text**: labels, captions, chips, the Design select, slider units, especially at 768 px height (does Export need scrolling? is the button below the fold?).<br>- **Low-contrast text**, especially **orange/warning** text on white or grey (check it with DevTools' contrast picker; fail if under 4.5:1 for body text).<br>- **Unhelpful errors**: messages that don't say what to do next.<br>- **Where the STL went**: does the UI say the path or give a download link?<br>- **Anything you had to guess**: which panel holds Export, what the motor-cup switch does, what "Edited copy" means. |
| B12 | Request 7 at **1920×1080** | Repeat B11 from a fresh reload at 1920×1080. | Same. Also note anything that is fine at 1080p but broken at 768p (or the other way round), and any wasted space or a too-small 3-D viewer. |

## Results (browser pass 2026-10-09, reported 16:34 MDT; screenshots `docs/qa/screenshots/2026-10-09-r4/`, 12 png)

| # | result | notes / screenshot |
|---|---|---|
| B1a | **reopened** | Stale 'stage 5/5 · writing STL' at ~0.26 s. 'stage 1/4 · loading CAD kernel' at ~0.59 s (over 0.5 s) with the bar already ~80 %. Then only 3/4 'lofting blades + hub' (3–6 s); stages 2 and 4 never seen; done ~6.7 s. `B1a_stage1.png`, `B1a_done.png` |
| B1b | **reopened** | Cup on: 1/4 0–2 s, 3/4 'building + carving motor cup' 2–48 s, 4/4 'writing STL' 48–51 s, done ~54 s. Stage 2 missing. Elapsed counter froze at 0:51 for ~3.4 s. `B1b_stage3_cup.png`, `B1b_done.png` |
| B1c | **reopened** | 'stage 4/4 writing STL' and a near-full bar from the previous run at 0.16 s; stage 1/4 at 0.6 s. `B1c_starts_at_stage4.png` |
| B10a | 0 errors | :8081 (961f953): 0, 0, 0. `B10a_console_8081.png` |
| B10b | 0 errors | :8082 (guard off): 0, 0, 0. `B10b_console_8082.png` |
| B10c | 0 errors | :8080 (master): 0, 0, 0. Sometimes `Uncaught (in promise) {code:-32099, viewport.image.push … connection not open}` at unload (:8080 only in the console; the script saw unnamed rejections on all ports). One reload hung blank ~20 s. `B10c_console_8080.png`, `B10c_8080_uncaught_rpc_on_unload.png` |
| B10 verdict | not reproduced | Fired nowhere in 9 reloads (r3: 3/3 on master). Intermittent; UI-23 stays LOW/open. |
| B11 | findings | UI-24 HIGH (Export options ~2 screens below Export STL), UI-25 MED (carved mesh persists after cup off, across reloads, no stale marker), UI-26 MED (jargon by the action buttons), UI-27 MED (viewer below the fold at 768p; long intro banner), UI-28 LOW (pale disabled Cancel / Randomize). `B11_1366x768_first_view.png`, `B11_1366x768_export_options_far_below.png` |
| B12 | findings | UI-29 LOW (narrow controls column, tiny text, empty space; 'Start here' tiny grey). `B12_1920x1080_first_view.png` |
| Export | not run | Export click not allowed this round, so where the STL lands wasn't checked. |

**B1 diagnosis:** see the UI-4 row in `docs/QA_REVIEW.md`. In short:
- The box-global `/tmp/fansim_cockpit_preview.stl.progress.json` is never cleared, and the ticker's first tick reads it before the executor writes stage 1.
- `max(prev_pct, …)` then pins the bar at 75–80 % for the rest of the run.
- Stage 2 lasts milliseconds when chords are cached.
- `_draw` + `spec_status` + `view_update` block the event loop after the build (the ~3.4 s freeze).
- New, from the same code reading: UI-30, all cockpits share the /tmp preview paths.
