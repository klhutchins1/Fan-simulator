## Task 4 fix — orphaned cockpit UI source-grep tests

**Status:** done  
**Branch:** `cockpit-tab-split`  
**Commit:** `00b69e5` — `test: drop orphaned cockpit UI source-grep after volute extract`

### Deleted (4 tests + 1 helper)

| File | Removed |
|------|---------|
| `tests/test_volute.py` | `test_cockpit_volute_copy_mentions_smooth_scroll` — grepped `app.py` for `stage3_smooth_scroll` copy now in `volute_tab.py` |
| `tests/test_mixed_flow_cockpit.py` | `_cockpit_src()` helper + `test_mixed_flow_tab_in_cockpit` — mixed tab UI moved to `mixed_tab.py` |
| `tests/test_mixed_optimize.py` | `test_mixed_cockpit_optimize_wiring` — optimize/resume/CFD UI strings moved to `mixed_tab.py` |
| `tests/test_mixed_persist.py` | `test_mixed_cockpit_wires_design_json_and_scatter` — scatter/trial wiring moved to `mixed_tab.py` |

### Kept (still valid — UI strings remain in `app.py`)

- `tests/test_prop_resume.py::test_cockpit_prop_resume_switch_present`
- `tests/test_shroud.py::test_cockpit_declares_shroud_height_slider`
- `tests/test_shroud.py::test_cockpit_caption_notes_winglet_auto_disabled`

No CROR cockpit `app.py` source-grep tests found.
