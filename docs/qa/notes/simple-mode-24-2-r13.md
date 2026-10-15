# 24.2 Simple vs Expert in the browser (round 13 Task A)

Prereg `02584e6` (branch prereg/round13). Cockpit `scripts/cockpit.py --port 8080` ran from the run clone `/workspace/fansim/qa/run_r13`
(master 143d5a8). I drove it headless with Playwright and system Chrome 154 at 1366×768, in a fresh context with empty localStorage.
"Shown" means Playwright `is_visible()`. Script: `handoff/2026-10-14_from-qa-13/scripts/a_modes.py`. Data: `data/a_modes.json`.

| id | result | evidence |
|---|---|---|
| S0 | **PASS** | Cold open is `simple` (localStorage empty). Results: Glossary, Gold ✕, the fits-only paragraph and the "CFM scatter — up and right" caption are all hidden. The Fits / Declutter / Show stock switches and the Design select are shown. |
| S1 | **PASS** | Expert shows all 4 blocks and Simple hides them again. After choosing Expert and reloading, `ui_mode`=expert, localStorage `fansim.ui_mode`=expert, and all 4 blocks are shown. |
| S2 | **PASS** | Simple Design (panels expanded) shows "Hover any slider…", 48 sliders, and hub_fit_info ("…Current 21.5 mm ✓ fits — cup will carve."), tip_fit_info ("…built tip dia 109.0 mm … ✓ fits.") and the wall readout. All 8 dump paragraphs are hidden. |
| S3 | **PASS** | Expert Design shows all 8 paragraphs. Hovering the first slider shows its tooltip ("How many blades. More = more airflow…") in both modes. |
| S4 | report | At 768 px high, the Simple Results scatter (plotly div) starts at y=652 and ends at y=1284, so only its title and top ~115 px are above the fold. In Expert it starts at y=920, fully below. Screens: `screens/a_results_{simple,expert}_768.png` |

S4 note: at 768 px, "Keep the Results scatter above the fold in Simple" (ef31cc5) holds only partly. The plot's title is visible but its body is not.
The Design card (select + 3 info lines) and the "No scored designs yet…" caption sit above the plot. → **QA-38 (LOW)**.
Caveat: this is a headless check. A human desktop pass would add only a visual read of the pictures; every PASS rule above was measured.
