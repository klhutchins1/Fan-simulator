# Browser click-through: branch `qa-fixes-2026-10-09` @ d781894 (2026-10-09)

**Setup:**
- The cockpit is already running on the box from `/workspace/fansim/repo` (branch checked out) at http://127.0.0.1:8080/, with an empty run dir (`/workspace/fansim/qa/runs/qa_empty_final`).
- Use **one browser tab only** (single-user app).
- Don't click Assess / Sweep / Optimize / CFD (no Docker on the box).
- Take a screenshot for each item and save it to `docs/qa/screenshots/2026-10-09_<id>_*.png`.
- Report each item as `verified` / `reopened: <why>`.

Already verified headlessly (no browser step needed): UI-5 solver numbers, UI-16, UI-17, UI-18, UI-19 serving, QA-11, §23.32.

| # | item | steps | pass if |
|---|---|---|---|
| B1 | UI-4 Preview progress | Fan tab → Stock design → **Preview**. Watch the bar and caption until it's ready, and note the time. Then turn on **motor cup** and Preview again (slow path). | The caption reads `stage k/4 · <label>` and k only goes up. The bar fills forward and never jumps back or sweeps. It ends full or hidden when ready. Note both durations. |
| B2 | UI-8 slider thumb vs side label | Fan tab, Stock. Drag **Chord root** a little and let go. Read the thumb tooltip and the side label. Repeat on one stagger slider and one Prop slider. | The thumb shows the same value as the side label (Stock Chord root 17.75 on both before dragging). The tooltip doesn't cover the label. |
| B3 | UI-9 first-load framing | Hard reload (Ctrl+Shift+R) and look at the Fan tab 3-D view before clicking anything. | The fan fills most of the viewer, centred, with the cue ring visible, not a small fan inside an arrow cloud. No |U| colour bar on Stock first load is by design. |
| B4 | UI-13 Prop Stop | Prop tab before any Optimize. Look at the **Stop** button, then hover over it. | Stop is neutral or grey (not pink/red) and visibly disabled while nothing is running. Other disabled buttons are also faded. |
| B5 | UI-5 Prop η display | Prop tab, `fpv_5inch` preset → Analyze. Read the forward-flight polar or readout. | η at J ≈ 0.16 / 0.24 / 0.31 is about 0.25 / 0.36 / 0.44 (not about 0.04–0.07). The J = 0 row shows `—`. Static is 2087 g / 743 W. |
| B6 | UI-19 / UI-6 Export download | Fan tab, Stock → **Export** (wait ~1–1.5 min) → click the download link. | The link is `/fansim_exports/<clear name>.stl` and it downloads. The file appears under `/workspace/fansim/repo/exports/`. |
| B7 | UI-20 dropdown after edits | Fan tab, Stock → **Randomize** (or drag any slider). Look at the Design dropdown. | It reads `✎ Edited copy of this design (not saved)`, not `◆ Reference · Noctua A12x25 (published)`. Reset brings back the reference label. |
| B8 | UI-21 CFD refine look | Mixed tab → Preview. Look at **CFD refine** (top N = 0). Repeat on the Prop tab. | The button is tonal, not solid orange, and doesn't look like a primary action while top N = 0. Don't click it. |
| B9 | UI-22 Mixed Preview timer (Linux) | Mixed tab → Preview. Watch `Running Preview… m:ss`. | It shows `0:00` within about 1 s of the click and ticks about once per second. If not, note the delay. |
| B10 | Sanity / regression | Switch through all tabs (Fan, Mixed, Volute, Prop, CROR) once, then reload the page twice. | Every tab renders, no new console errors other than the known `POST /paraview/ 405`, and the page reconnects after each reload. |
