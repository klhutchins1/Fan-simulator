# 2026-11-14 session 2 — cockpit says what it does

Write this session into `docs/qa/rounds/r30.md` before you start session 3. Headless first. Use a browser only if this machine has a display. Do not click Assess, Sweep, Optimize, or Run.

| # | task | board |
|---|---|---|
| D | Run `tests/test_ui_says_what_it_does.py`, `tests/test_qa51_neuralfoil_expert.py`, and `tests/test_r26_hide_scaffolds.py`. Simple mode must not offer NeuralFoil. Expert title contains "experimental". Centrifugal-only and wind-turbine flows stay out of the cockpit and the README Quickstart. Mixed and Volute stay. | QA-51, R2.6, R3.7 |
| E | On this branch, re-check these still-open rows and say fixed or still open. Do not patch. UI-26 (Gold = parametric Stock on first view), UI-27 (viewer cut off at 1366×768), UI-31 (surrogate-guided Optimize still skips CFD / `synthetic_label`), UI-33 (Optimize does not say it ignores the Design sliders), QA-40 (Simple mode still shows a noise line with no Stock reference), QA-42 (Preview grams do not name the material). | UI-26, UI-27, UI-31, UI-33, QA-40, QA-42 |
