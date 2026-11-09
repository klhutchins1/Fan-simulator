
## ui-hunt-1 (grok, 2026-11-09): exploratory UI bug hunt on master 83681c2

**Build:** master `83681c2`, clone `/workspace/fansim/repo-r26-g2`. **Prereg:** `prereg/ui-hunt-1` cf2c813, committed 2026-11-09 08:46 MST, before data. Headless cockpit, empty run. Assess, Sweep, Optimize, Export and Randomize were never clicked. No CFD, Docker or OpenFOAM. No source edits. Note: `docs/qa/notes/ui-hunt-1-2026-11-09.md`.

- **UI-39 (MED, new): Sweep "steps" has no validation and no cap.**
  - Empty or "1e9" make Run fail silently (`int()` ValueError, `fan_assess.py:448`).
  - Any large count queues that many full CFD Assess runs.
  - Patch: `docs/qa/patches/ui-hunt-1-UI39-UI40-steps-trials.patch` (2–12 with a visible refusal).
- **UI-40 (MED, new): Optimize "Trials" accepts −5, 100 or 1e9 silently, then runs 2–40 (`fan_optimize.py:130-133`).** Same patch: the label reads "Trials (2–40)", with min/max on the field.
- **UI-41 (LOW, new): Fan number boxes (Seed CFM, ΔP and RPM; arrow Scale) show no validation state and store typed text.** Errors surface only on click (Seed) or as a silent clamp (Scale 0.2–20).
- **UI-42 (LOW, new): slider readouts are unrounded with cryptic units** ("18.7018 mm", "0 0–1", "0 c", "0 t"; `fan_widgets.py:35`).
- **QA-70 (LOW, new): the G2 Expert noise-hint row is dropped when a run has no turbulence SWL** (`fan_flow_report.py:146`), though the hint needs only tip speed + CFM. Patch: `docs/qa/patches/ui-hunt-1-QA70-noise-hint-row.patch`, with a test that fails without the fix (21 passed on scratch).
- **G2 noise row visual: verified** (template render with injected rows: shown in Expert, hidden in Simple).
- **No bug found in:**
  - page errors (0);
  - HTTP errors (UI-15's 405 only);
  - overflow or clipping at 1366/1920 (0);
  - tooltip images (3/3 load);
  - links;
  - state across a tab switch or reload;
  - Simple/Expert toggling;
  - the Expert-only-tab → Simple fallback.
- **Re-checked, still open:**
  - UI-26: shown 2.2 s after load on a warm cache. After an edit, the caption stays "Stock reference loaded" until Preview.
  - UI-27: 957/768 and 1172/1080.
  - UI-29: 12 px.
  - UI-32, UI-33, UI-34, UI-36 (0/8).
  - UI-35 (20/58, unchanged).
  - UI-37: inventory identical to r25b.
  - UI-38: picking a design still silently resets settings.
- **ID changes:** new UI-39, UI-40 (MED), UI-41, UI-42 and QA-70 (LOW).
