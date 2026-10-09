# Slow tests, one process, Linux: master f238f54 (QA r4 request 4)

**Command** (from the repo-r4 root; 2026-10-09, started 15:31:55 MDT):

    RSS_NODEID_FILE=/tmp/pytest_current_nodeid RSS_PERTEST_LOG=$PWD/handoff/2026-10-09_from-qa-3/slow/pertest_rss.tsv \
    PYTHONPATH=$PWD/handoff/2026-10-09_from-qa-3/slow .venv/bin/python -m pytest -q -m "slow and not docker" \
      -p no:cacheprovider -p rss_nodeid_plugin --durations=0
    python rss_sampler.py <pytest pid> rss_samples.tsv      # 2 s /proc sampler (restarted ~1 min in; see note)
    python per_file_peaks.py rss_samples.tsv

**Result:**
- **22 passed, 2 skipped, 1592 deselected in 418 s (6 min 58 s).** No failures.
- The 2 skips are collection-time `importorskip('pythrust')`: `test_prop_power_propulsion.py` and `test_pythrust_export_propulsion.py`. The optional `propulsion` extra isn't installed by `--extra dev`.
- None of the 22 runs CFD. `test_prop_cfd` monkeypatches run_mesh/run_solve, and Docker is absent.
- **Overall peak RSS: 8003 MB HWM / 7998 MB sampled**, in `tests/test_objectives_orientation.py::test_build_case_gets_flipped_rotor_and_fitted_rig` (it builds the Stock impeller via fuse_impeller; this is the same 7.6 GB fuse as request 5).

| file | tests | time s (setup+call+teardown) | peak RSS MB | RSS before file MB | notes |
|---|---|---|---|---|---|
| tests/test_objectives_orientation.py | 1 | 51.8 | **7998** (HWM 8003) | 749 | Stock fuse |
| tests/test_blade_le_leads.py | 1 | 51.4 | 7400 (HWM 7399) | 7313 | Stock build. Most of the RSS was inherited from the previous file. |
| tests/audit/test_stock_handedness.py | 1 | 66.9 | 7334 (HWM 7342) | 2574 | Stock build |
| tests/test_features.py | 3 | 104.0 | 6777 | 613 | featured impellers (feat0 5100, feat1 6722, feat2 6777) |
| tests/audit/test_prop_builder_direction.py | 3 | 87.5 | 3210 (HWM; before the sampler started) | — | random prop flats 60.9 s |
| tests/test_prop_cfd.py | 1 | 17.6 | 1791 | — | |
| tests/test_tip_trim.py | 1 | 20.4 | 1511 | 569 | |
| tests/test_wind_turbine.py | 1 | 5.1 | 1215 | 570 | |
| tests/test_midplane.py | 4 | 4.3 | 762 | — | synthetic mesh |
| tests/test_cockpit_viz.py | 1 | 2.4 | 673 | — | |
| tests/test_spanwise.py | 1 | 1.4 | 587 | — | |
| tests/test_volute.py | 4 | 1.4 | 585 | — | |

**Files:**
- `pertest_rss.tsv`: nodeid, outcome, RSS after the test, process HWM, seconds.
- `rss_samples.tsv`: t, root, tree, nprocs, nodeid.
- `pytest_slow.log`: the full `--durations` output.
- The sampler died at the first launch (backgrounded without setsid) and was restarted about 1 min in. The first file's peak (prop_builder_direction) therefore comes from the per-test HWM column.
- RSS drops between files because of the conftest `malloc_trim` fixture.
