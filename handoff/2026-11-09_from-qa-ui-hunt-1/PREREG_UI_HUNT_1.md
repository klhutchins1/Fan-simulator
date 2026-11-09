# ui-hunt-1 pre-registration (grok, self-initiated exploratory UI bug hunt)

**Written:** 2026-11-09 MST, before any ui-hunt-1 render, probe or screenshot.
**Code under test:** `/workspace/fansim/repo-r26-g2` (clean clone of `master_83681c2.bundle`, sha256 fdea337f…8736, HEAD 83681c2).
**Seen before writing:** QA_REVIEW ID table (UI-1…UI-38, QA-…QA-69); r25 harness scripts; fan_tab_ui flow-card template and
fan_flow_report.build_report (code reading only, to plan the G2 visual check).
**Run:** cockpit headless on the box (`scripts/cockpit.py --run <empty temp run> --port P`), Playwright + Chrome headless; stopped afterward.
**Hard rules:** never click Assess / Sweep / Optimize / Run / Export / Randomize-and-assess; Preview is allowed (geometry only, no CFD).
No Docker / CFD / OpenFOAM. No source edits or commits in the snapshot; fixes as patches under `docs/qa/patches/`.

## Coverage
- **Viewports × modes:** 1366×768 and 1920×1080, each in Simple and Expert (4 first views + per-tab shots at 1366 Expert and Simple; 1920 for layout checks only).
- **Screens:** every top-level tab (Fan · CFD, Prop, and any others rendered) and Fan sub-tabs Design / Results / Library;
  Assess, Sweep and Optimize setup panels (forms only); Trials/design list (dropdown); print/export card (no Export click);
  tooltips + images (hover sample, `e_*.png` loader requests); Simple/Expert switching both ways.
- **Inputs:** every visible numeric text field on Fan (Expert): empty, negative (−5), huge (1e9), non-numeric ("abc"); blur only, no Enter on action buttons.
  Record the resulting state value and any visible validation message.
- **Checks:** console errors + page errors + failed/4xx/5xx requests (images, links); `href`s on the page (HEAD-checked locally,
  external links listed not fetched); horizontal overflow (`scrollWidth > clientWidth` on body and cards) and clipped text
  (buttons/labels with `scrollWidth > clientWidth`); time from tab click to idle (> 3 s = slow); state kept after a tab switch
  and after a reload (mode, sub-tab, a changed slider).
- **G2 visual:** the flow card's Expert-only noise row is shown in Expert and hidden in Simple. If no run with flow data is
  available, rows are injected into the client state (`flow_rows` with one `expert_only` noise row) and the rendered DOM is read;
  this is reported as "template render with injected rows", not an end-to-end check. Plus a `build_report` probe of when the
  noise row is emitted at all.
- **Re-checks:** UI-26, UI-27, UI-29 (r25 `a_ui.py`), UI-32/33/34/36/38 (r25 `a_tooltips.py`), UI-35 (r25 `range_check.py`),
  UI-37 (r25 inventory/scan). Status words: verified / still open / partly fixed / not re-tested.

## What counts as a bug, and severity
- **HIGH:** wrong result or action (a control does something other than it says, a run uses different inputs than shown),
  data loss, or the app becomes unusable (crash, blank page, uncaught error that stops a control).
- **MED:** a control or text that misleads, invalid input accepted silently into a value that is used, state lost on
  tab switch/reload, a key control unreachable or clipped at 1366×768, a console error on a normal path, a broken image/link.
- **LOW:** cosmetic (overflow by a few px, spacing, inconsistent unit labels), a slow render (> 3 s) without a spinner,
  harmless console warnings.
- **Not a bug:** anything only reachable by running Assess/Sweep/Optimize; documented-benign UI-15 (POST /paraview/ 405).
- **Dedupe:** each finding is checked against UI-1…UI-38 / QA-1…QA-69; duplicates are logged under the old ID.
  New ones are numbered from UI-39 / QA-70.
