# Archived one-off scripts (RV-4, 2026-11-25)

Moved out of `scripts/` because nothing in `fansim/`, `tests/`, or other scripts imported
them, and the review plan listed them as unreferenced. Kept in git under `archive/` (already
in `RELEASE_EXCLUDE`) so history is not lost.

| script | why archived |
|---|---|
| `_fit_a12x25_slices.py` | one-off slice fit; superseded by geometry tooling |
| `_split_fan_tab_ui.py` | one-off UI split helper; work already landed |
| `compare_sections.py` | ad-hoc section compare |
| `dedup_designs.py` | ad-hoc catalog dedupe |
| `design_uneven_spacing.py` | ad-hoc spacing experiment |
| `overnight_wrapup.py` | superseded by `morning_check.py` / night queue |
| `run_cror_optimization.py` | CROR Optimize entry; not wired to cockpit/CI |
| `run_feature_minmax.py` | feature study driver; no callers |
| `run_spacing_study.py` | spacing study driver; no callers |
| `run_stall_study.py` | stall study driver; no callers |
| `run_stator_vs_frame.py` | stator/frame study; no callers |
| `run_tip_noise.py` | tip-noise study; no callers |
| `run_winglet_study.py` | winglet study; no callers |
| `score_all_noise.py` | bulk noise score; no callers |
| `screen_r3_cfd.py` | R3 screen helper; no callers |
| `test_reproducibility.py` | loose script, not under `tests/` |
| `what_helps.py` | ad-hoc “what helps” summary |

| `_profile_build_impeller.py` | one-off build profiler |
| `_smoke_ui_review_after.py` | one-off UI smoke after review |
| `a12x25_recipe_sensitivity.py` | recipe sensitivity campaign; no callers |
| `ab_assess_speed.py` | Assess speed A/B; no callers |
| `assess_bem_top5.py` | one-off BEM top-5 assess |
| `audit_bem_vs_cfd.py` | ad-hoc BEM vs CFD compare |
| `audit_bemt_polar_ab.py` | ad-hoc BEMT polar A/B |
| `calibrate_from_store.py` | ad-hoc store calibrate |
| `cfd_sanity.py` | superseded by audit ledger checks |
| `direction_crosscheck_2_check.py` | one-off direction cross-check |
| `dump_field_snapshot.py` | ad-hoc field dump |
| `export_finalists.py` | ad-hoc finalist export |
| `fan_noise_probes.py` | probe experiment; no callers |
| `fit_fuse_open_linux.py` | one-off fuse fit |
| `import_prop_stls.py` | ad-hoc prop STL import |
| `run_lbm_geometry_ab.py` | LBM geometry A/B; no callers |
| `score_feature_noise.py` | feature noise score; no callers |
| `score_finalists_noise.py` | finalist noise score; no callers |
| `set_flow_reference.py` | one-off flow reference stamp |
| `stock_surface_distance.py` | ad-hoc surface distance |
| `ws_stall_probe.py` | stall probe experiment |

Rule going forward: no code that produces a validation verdict lives only in `scripts/`
(see `docs/review/2026-11-24-review-plan.md` RV-4).
