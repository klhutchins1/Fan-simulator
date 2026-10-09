# Browser re-test, round 3: master @ e48a32d (2026-10-09)

**Setup:**
- The cockpit runs from `/workspace/fansim/repo-r3` (master e48a32d) at http://127.0.0.1:8080/ with an empty run dir (`/workspace/fansim/qa/runs/qa_empty_r3`).
- Use **one tab** at your usual zoom.
- No Assess / Sweep / Optimize / CFD.
- Save screenshots to `docs/qa/screenshots/2026-10-09-r3/<row>_*.png`.
- Report `verified` / `reopened: <why>` per row.

## What changed (git log, commit `0354b3c` unless noted)
- **UI-4 (B1):**
  - `state.preview_motor_cup` now defaults to **False** (`fan_core.py`). The switch is in the **Export options** panel (corrected 2026-10-09; the changelog says 'Assess & print'), and Export still carves the cup.
  - The bar starts determinate: `progress_caption(None)` → 2 % and "starting build process" (`isolated.py`, `fan_viz.py`).
  - The worker writes `stage 1/5 · loading CAD kernel` before importing CadQuery (`_build_worker.py`). The stages are now 5: loading CAD kernel → reading design → realising chords → build/(carving motor cup) → writing mesh/STL.
  - The value is `max(prev_pct, …)`, so it never decreases. The bar is indeterminate only while `preview_pct` is 0.
- **UI-9 (B3):** all five tabs' 3-D viewer cards use `VTK_VIEW_STYLE` = `width:100%; aspect-ratio:3/2; min-height:400px; max-height:75vh` (`tab_shell.py`). This was a fixed 400 px. Camera fitting is unchanged from d781894.
- **UI-20 (B7):**
  - The Design `VSelect` has a `selection` slot: while `edited_stale`, the shown value reads `✎ Edited copy of <item title>` in warning colour.
  - The field label reads `✎ Edited copy (not saved) — based on:`.
- **UI-23:** triaged as upstream (trame-client unload-time rejection). `9482929` adds `FANSIM_WS_GUARD=0` to turn the ws guard off; there is no UI change.

## Rows

| # | item | steps | pass if |
|---|---|---|---|
| B1a | UI-4 default Preview | Fan tab, Stock, motor cup switch left at default. Check that it's **off** in the **Export options** panel. Click **Preview** and time it to "Preview (orange)". | The bar shows a sliver plus "starting build process" right away, then `stage k/5 · <label>` with k = 1→5 in order. It never sweeps or jumps back. No "carving motor cup" stage. Time is about 10–20 s (Windows: ~15 s). Note the time. |
| B1b | UI-4 motor-cup Preview | Turn the motor cup switch **on** → Preview again. Time it. | Same bar rules. A motor-cup stage appears. It can take about 1 min, but the bar keeps moving forward with no backwards jump (round 2: 65 % → 50 %). Note whether the UI stays responsive (round 2: frozen for seconds). |
| B1c | UI-4 second run | Click Preview once more straight after B1b finishes. | The bar starts again from the sliver; it does not start at the previous run's stage 5/5. |
| B3a | UI-9 framing, normal width | Normal reload (F5), Fan tab, before clicking anything. Screenshot. | The viewer is about 3:2, not a wide strip. The fan fills most of the viewer width (round 2: only ~1/3), centred. |
| B3b | UI-9 framing, second width | Resize the window to about half width (or zoom 67 % ↔ 100 %), then reload. Screenshot. | Still 3:2 (or capped at 75 % of window height) and the fan still fills most of the viewer. Repeat a quick look on Mixed / Volute / Prop / CROR: all viewers 3:2, none clipped. |
| B7 | UI-20 dropdown value | Fan tab, Stock → **Randomize** (or drag one slider). Look at the Design dropdown's **selected value** (the big text, not the caption). Then click **Reset**. | While edited, the value reads `✎ Edited copy of ◆ Reference · Noctua A12x25 (published)` in warning colour, and the label reads `✎ Edited copy (not saved) — based on:`. After Reset, it returns to plain `◆ Reference · …`. |
| B10 | UI-23 / sanity | With **one** tab open: reload 3 times, opening DevTools console first. Visit all 5 tabs. | No `TypeError: n[i[e]] is not a function`. If it appears, note how many tabs were connected and when (during load or unload). Only the known `POST /paraview/ 405` otherwise. |

## Results (browser pass, master e48a32d, 2026-10-09 ~14:40 MDT)
Screenshots: `docs/qa/screenshots/2026-10-09-r3/`. Diagnosis of B1: `docs/QA_REVIEW.md`, section "Round 3 browser results".

| # | result | notes |
|---|---|---|
| B1a | **REOPENED** | 'starting build process' 2 % for 0–2.2 s, then 'stage 4/5 · lofting blades + hub' 60 % at 3.4 s, done ~6.8 s. Stages 1/2/3/5 never seen (~1 s sampling). Never backwards, no freeze. The label wasn't in the changelog's stage list. The motor-cup switch is under 'Export options'. |
| B1b | **REOPENED** | 2 % at 0 s → 'stage 4/5 · building + carving motor cup' 60 % from 3.2 s to ~53 s → 'stage 5/5 · writing STL' 80 % → done ~65 s. Stages 1–3 never shown. The timer stalled 0:53→0:56 over ~7–10 s of wall time and the bar lost its numeric value (`B1b_bar_midrun.png`). |
| B1c | **REOPENED** | Restarts from 2 % (pass), but the same pattern and a ~7 s freeze at 0:57 during writing STL (`B1c_bar_midrun_0m06.png`). |
| B3a | **VERIFIED** | 1102×735 = 3:2 at 100 %; fan fills ~2/3 of the width, centred (`B3a_framing_zoom100.png`). |
| B3b | **VERIFIED** (Fan) | Fan OK at 75 % zoom. Mixed/Volute/Prop/CROR frames are 3:2 and not clipped; their model framing wasn't judged because nothing was previewed (`B3b_framing_*.png`). |
| B7 | **VERIFIED** | Edited value and label as specified; Reset restores both. The first scripted Reset click did nothing; a real click worked (likely tooling). |
| B10 | **STILL OPEN** (UI-23) | The TypeError fired on every reload (3/3) with **one** tab connected, from `invokeConnectionClose` at unload. Otherwise only the known 405 and the trame-vtk 'Set value to model directly labels' warning (`B10_console_after_3_reloads.png`). |
