# UI regression tests (round 12 Task E): proposal

File: `handoff/2026-10-14_from-qa-12/tests/test_ui_says_what_it_does_r12.py`. It is not in tests/, because the brief's edit paths do not allow that.
The tests run headless: the fixture is from test_fan_tab_setup_smoke, with stubs on the worker boundary. There is no CFD and no 3-D. About 4 s total.

| test | catches | on 143d5a8 |
|---|---|---|
| test_export_material_follows_picker | PLA+ picked → the export worker's spec.material (README, temps, sidecar) | **FAIL** (PETG), intended: QA-36 |
| test_preview_fit_grams_follow_picker | Preview "fits … g" weighed in the picked filament (checked at the weight call, since the caption rounds) | **FAIL** (PETG), intended: QA-36 |
| test_export_caption_print_id_matches_file | 28.2: caption code == file-name prefix, valid check char | PASS |
| test_picker_offers_only_registered_materials | every dropdown value exists in MATERIALS, and PLA+ is offered | PASS |

Run: `PYTHONPATH=<repo> python -m pytest -q handoff/2026-10-14_from-qa-12/tests/`. Output: `data/e_pytest.txt`.
Disclosure: pytest 9.1.1 (the uv.lock pin) was installed into repo-r9/.venv, which had no pytest. The first draft of the grams
test failed for the wrong reason (its test cylinder was out of spec, then the rounding hid the difference). I fixed the test
before recording the result above.
