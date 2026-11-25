# RV-4 script triage draft (2026-11-25)

Cursor, worktree `runs/worktrees/rv4-script-triage`. Auto-inventory of `scripts/*.py`; buckets are a
starting proposal, not yet applied (no moves in this commit).

Total scripts: **129**.

## promote (3)

| script | lines | why |
|---|---:|---|
| `fan_noise_curle.py` | 137 | produces / rewrites validation maths (plan) |
| `fan_noise_cv.py` | 138 | produces / rewrites validation maths (plan) |
| `prop_section_2d.py` | 1676 | produces / rewrites validation maths (plan) |

## keep (66)

| script | lines | why |
|---|---:|---|
| `analyze_fan_recording.py` | 74 | has test or test import |
| `audit_archetype_direction_cfd.py` | 255 | has test or test import |
| `audit_direction_cfd.py` | 312 | has test or test import |
| `audit_direction_geometry.py` | 116 | has test or test import |
| `audit_prop_cfd.py` | 236 | has test or test import |
| `audit_status.py` | 71 | operational tool named in RV-4 plan / process |
| `calibrate_prop_datasheet.py` | 59 | has test or test import |
| `capture_convergence.py` | 109 | has test or test import |
| `catalog.py` | 102 | has test or test import |
| `cockpit.py` | 140 | has test or test import |
| `design_flow_mesh_repeats.py` | 145 | has test or test import |
| `evaluate_cror.py` | 95 | has test or test import |
| `evaluate_des_fwh.py` | 210 | has test or test import |
| `evaluate_mixed_flow.py` | 72 | has test or test import |
| `evaluate_noise.py` | 186 | has test or test import |
| `evaluate_prop_cfd.py` | 249 | has test or test import |
| `evaluate_prop_cfd_polar.py` | 128 | has test or test import |
| `evaluate_prop_polar.py` | 76 | has test or test import |
| `evaluate_prop_power.py` | 113 | has test or test import |
| `evaluate_volute.py` | 69 | has test or test import |
| `export_cfd_dataset.py` | 113 | has test or test import |
| `export_cror.py` | 33 | has test or test import |
| `export_hub_fit_coupon.py` | 60 | has test or test import |
| `export_id_coupon.py` | 75 | has test or test import |
| `export_mixed_flow.py` | 34 | has test or test import |
| `export_prop_pythrust_csv.py` | 60 | has test or test import |
| `export_release.py` | 123 | has test or test import |
| `export_volute.py` | 35 | has test or test import |
| `extract_design_rules.py` | 168 | has test or test import |
| `fit_recipe_to_stl.py` | 207 | has test or test import |
| `freeze_prop_cfd_fixture.py` | 100 | has test or test import |
| `gate.py` | 130 | operational tool named in RV-4 plan / process |
| `grid_convergence_stl.py` | 121 | has test or test import |
| `migrate_section_wrap.py` | 93 | has test or test import |
| `morning_check.py` | 243 | operational tool named in RV-4 plan / process |
| `night_queue.py` | 221 | operational tool named in RV-4 plan / process |
| `outline_hub.py` | 74 | has test or test import |
| `outline_match.py` | 122 | has test or test import |
| `outline_z.py` | 251 | has test or test import |
| `physics_snapshot.py` | 40 | operational tool named in RV-4 plan / process |
| `prop_cfd_jsweep.py` | 119 | has test or test import |
| `pytest_chunks.py` | 127 | operational tool named in RV-4 plan / process |
| `refine_mixed_pareto.py` | 63 | has test or test import |
| `rescore_designs.py` | 457 | has test or test import |
| `rig_logger.py` | 160 | has test or test import |
| `run_a12x25_validation.py` | 820 | has test or test import |
| `run_baseline.py` | 141 | has test or test import |
| `run_fan01.py` | 440 | has test or test import |
| `run_fan_curve.py` | 141 | has test or test import |
| `run_grid_convergence.py` | 125 | has test or test import |
| `run_loaded_ladder.py` | 369 | has test or test import |
| `run_optimization.py` | 292 | has test or test import |
| `run_prop_ami_smoke.py` | 151 | has test or test import |
| `run_prop_grid_convergence.py` | 204 | has test or test import |
| `run_prop_obj2_wall.py` | 150 | has test or test import |
| `run_prop_optimization.py` | 65 | has test or test import |
| `run_surrogate_search.py` | 44 | has test or test import |
| `screen_rank_audit.py` | 263 | has test or test import |
| `stock_flow_mesh_repeats.py` | 113 | has test or test import |
| `stock_flow_repeats.py` | 163 | has test or test import |
| `stray_work.py` | 101 | operational tool named in RV-4 plan / process |
| `test_bistability.py` | 124 | has test or test import |
| `validate_a12x25.py` | 125 | has test or test import |
| `validate_lt120.py` | 196 | has test or test import |
| `validate_stl.py` | 130 | has test or test import |
| `volute_convergence_sweep.py` | 183 | has test or test import |

## archive (17)

| script | lines | why |
|---|---:|---|
| `_fit_a12x25_slices.py` | 104 | plan orphan; no code/test refs found |
| `_split_fan_tab_ui.py` | 86 | plan orphan; no code/test refs found |
| `compare_sections.py` | 127 | plan orphan; no code/test refs found |
| `dedup_designs.py` | 108 | plan orphan; no code/test refs found |
| `design_uneven_spacing.py` | 107 | plan orphan; no code/test refs found |
| `overnight_wrapup.py` | 74 | plan orphan; no code/test refs found |
| `run_cror_optimization.py` | 59 | plan orphan; no code/test refs found |
| `run_feature_minmax.py` | 120 | plan orphan; no code/test refs found |
| `run_spacing_study.py` | 117 | plan orphan; no code/test refs found |
| `run_stall_study.py` | 103 | plan orphan; no code/test refs found |
| `run_stator_vs_frame.py` | 290 | plan orphan; no code/test refs found |
| `run_tip_noise.py` | 124 | plan orphan; no code/test refs found |
| `run_winglet_study.py` | 114 | plan orphan; no code/test refs found |
| `score_all_noise.py` | 61 | plan orphan; no code/test refs found |
| `screen_r3_cfd.py` | 106 | plan orphan; no code/test refs found |
| `test_reproducibility.py` | 78 | plan orphan; no code/test refs found |
| `what_helps.py` | 76 | plan orphan; no code/test refs found |

## archive? (0)

| script | lines | why |
|---|---:|---|

## review (43)

| script | lines | why |
|---|---:|---|
| `_profile_build_impeller.py` | 101 | 0 code refs; docs=True |
| `_smoke_ui_review_after.py` | 368 | 0 code refs; docs=True |
| `a12x25_recipe_sensitivity.py` | 188 | 0 code refs; docs=True |
| `ab_assess_speed.py` | 73 | 0 code refs; docs=True |
| `assess_bem_top5.py` | 55 | 0 code refs; docs=True |
| `audit_bem_vs_cfd.py` | 88 | 0 code refs; docs=True |
| `audit_bemt_polar_ab.py` | 182 | 0 code refs; docs=True |
| `calibrate_from_store.py` | 50 | 0 code refs; docs=True |
| `cfd_sanity.py` | 49 | 0 code refs; docs=True |
| `clean_stale_cfd.py` | 110 | 0 code refs; docs=True |
| `cylinder_sections_cfd.py` | 117 | 0 code refs; docs=True |
| `cylinder_sections_checks.py` | 268 | 0 code refs; docs=True |
| `direction_crosscheck_2_check.py` | 169 | 0 code refs; docs=True |
| `dump_field_snapshot.py` | 36 | 1 code refs; docs=False |
| `evaluate_shutoff.py` | 179 | 1 code refs; docs=True |
| `export_a12x25_print_ready.py` | 146 | 1 code refs; docs=True |
| `export_finalists.py` | 144 | 0 code refs; docs=True |
| `fan_noise_probes.py` | 125 | 0 code refs; docs=True |
| `fit_fuse_open_linux.py` | 53 | 0 code refs; docs=True |
| `flow_report_checks.py` | 41 | 0 code refs; docs=True |
| `generate_control_images.py` | 242 | 0 code refs; docs=True |
| `import_prop_stls.py` | 38 | 0 code refs; docs=True |
| `measure_fuse_growth.py` | 81 | 1 code refs; docs=True |
| `migrate_chord_basis.py` | 106 | 3 code refs; docs=True |
| `outline_le_face.py` | 119 | 0 code refs; docs=True |
| `outline_te_face.py` | 174 | 1 code refs; docs=True |
| `overnight_checks.py` | 171 | 0 code refs; docs=True |
| `prune_runs.py` | 58 | 0 code refs; docs=True |
| `push_planes_checks.py` | 78 | 0 code refs; docs=True |
| `push_row_probe.py` | 49 | 0 code refs; docs=True |
| `push_row_probe_blade_planes.py` | 40 | 0 code refs; docs=True |
| `rederate_scores.py` | 196 | 0 code refs; docs=True |
| `refresh_stale_designs.py` | 159 | 6 code refs; docs=True |
| `run_feature_study.py` | 110 | 1 code refs; docs=True |
| `run_lbm_geometry_ab.py` | 145 | 0 code refs; docs=True |
| `run_mixed_vs_axial.py` | 367 | 0 code refs; docs=True |
| `run_tip_study.py` | 145 | 1 code refs; docs=True |
| `score_feature_noise.py` | 83 | 0 code refs; docs=True |
| `score_finalists_noise.py` | 63 | 1 code refs; docs=True |
| `set_flow_reference.py` | 29 | 0 code refs; docs=True |
| `stamp_hub_overhang.py` | 49 | 1 code refs; docs=False |
| `stock_surface_distance.py` | 38 | 0 code refs; docs=True |
| `ws_stall_probe.py` | 145 | 0 code refs; docs=True |

## Next

1. Human-confirm `archive?` and `review`.
2. Move confirmed archive to `archive/scripts/` with a one-line reason each.
3. For each promote: move maths into `fansim/` + test + ledger unit.
4. Add `scripts/audit_forensics.py` + test (plan item).
