# Provenance risks — reconstructed / recovered `fansim` files

**Purpose:** Phase 0 gate for **absolute CFM** (and loaded CFM / shut-off pressure derived from the same stack). Files tagged `# RECONSTRUCTED`, `# RECOVERED-FROM-CHAT`, or `# --- spliced` may not match the lost `E:` tree. Do not treat optimizer or BEM numbers as product claims until the listed pytest gate passes (and see [north-star-staged.md](./north-star-staged.md) for hardware).

**Inventory source (2026-09-14):**

```powershell
rg -n "RECONSTRUCTED|spliced from transcript|RECOVERED-FROM-CHAT" fansim -g "*.py" `
  | Out-File -Encoding utf8 docs/validation/_provenance_rg.txt
```

Raw ripgrep output is kept locally as `docs/validation/_provenance_rg.txt` (not committed). Fast-suite context: [suite_baseline_2026-09-14.md](./suite_baseline_2026-09-14.md) — 602 passed, 6 failed.

**Trust legend**

| Trust | Meaning for absolute CFM |
|-------|---------------------------|
| **None** | Reconstructed or transcript-spliced; treat as wrong until gate test is green and code is reconciled to a real copy. |
| **Conditional** | Verbatim chat recovery; may lag post–drive-death Cursor edits. Ranking/shape tests OK; absolute CFM still needs CFD tier or measurement. |
| **Conditional+splice** | Recovered file with spliced blocks (same as **None** for the spliced API surface). |

**Ranking:** Highest risk = closest to free-delivery CFM, shut-off ΔP, tip gap, and watertight geometry fed into BEM/CFD.

---

## Top 15 files (ranked)

| Rank | File | Provenance | Trust | CFM / physics lever | Gate test (must pass before absolute CFM claims) |
|------|------|------------|-------|---------------------|--------------------------------------------------|
| 1 | `fansim/geometry/blade.py` | `# RECONSTRUCTED` + LE/TE/shroud/tip_z **spliced** | **None** | Swept area, shroud ring, tip LE/TE, all BEM/CFD geometry | `tests/test_shroud.py::test_ring_wall_contains_every_tip_section_point` |
| 2 | `fansim/fan_bem.py` | `# RECOVERED-FROM-CHAT` | **Conditional** | Direct free-delivery & shut-off from `pq_curve` | `tests/test_fan_bem.py::test_reference_free_delivery_in_band` |
| 3 | `fansim/optimize/objectives.py` | `# RECOVERED-FROM-CHAT` | **Conditional** | `evaluate_candidate` → stamped `cfm_free` / `cfm_load` | `tests/test_optimize.py::test_evaluate_candidate_gate_is_cheap_and_infeasible` |
| 4 | `fansim/optimize/search_space.py` | Recovered + **multiple splices** + `# RECONSTRUCTED` (test-contract) block | **None** / splice | Tip cap, shroud, guided camber/blade count → geometry → CFM | `tests/test_search_space.py::test_shroud_drops_cap_by_ring_thickness` |
| 5 | `fansim/optimize/system_curve.py` | `# RECONSTRUCTED-FROM-CURSOR-TRANSCRIPT` + **spliced** | **None** | Loaded operating point & hose scoring (`k`, probe Pa) | `tests/test_system_curve.py::test_probe_on_hose_is_exact_op` |
| 6 | `fansim/cfd/metrics.py` | `# RECOVERED-FROM-CHAT` | **Conditional** | Parses OpenFOAM logs → reported CFM | `tests/test_cfd.py::test_parse_fan_metrics` |
| 7 | `fansim/cfd/domain.py` | `# RECOVERED-FROM-CHAT` | **Conditional** | Rig size, `OPTIMIZER_TIP_GAP_MM`, placement vs frame | `tests/test_cfd.py::test_rig_dimensions_and_operating_point` |
| 8 | `fansim/geometry/_build_worker.py` | `# RECOVERED-FROM-CHAT` | **Conditional** | Subprocess STL/CAD build on eval/CFD path | `tests/test_isolated_job.py::test_run_worker_module_success` |
| 9 | `fansim/optimize/_eval_worker.py` | Recovered + **spliced** kwargs/load_pa | **Conditional+splice** | Isolated eval passes load/refine into objectives | `tests/test_isolated_eval.py::test_eval_kwargs_from_job_pass_load_pa` |
| 10 | `fansim/fan_spec.py` | `# RECOVERED-FROM-CHAT` | **Conditional** | Reference hub/frame/RPM limits for calibration | `tests/test_fan_spec.py::test_a12x25_power_budget` |
| 11 | `fansim/cfd/runner.py` | `# RECOVERED-FROM-CHAT` | **Conditional** | Executes CFD that backs absolute tier | `tests/test_cfd.py::test_case_build_files` |
| 12 | `fansim/cfd/templates.py` | `# RECOVERED-FROM-CHAT` | **Conditional** | Case topology → inlet/outlet areas affecting parsed Q | `tests/test_cfd.py::test_case_build_files` |
| 13 | `fansim/catalog.py` | Recovered + **spliced** `results_for_hub` / `curve_provenance` | **Conditional+splice** | UI/catalog CFM and wall-curve metadata | `tests/test_catalog.py::test_build_indexes_finalists_across_runs` |
| 14 | `fansim/geometry/features.py` | Recovered + **spliced** `features_from_flat` | **Conditional+splice** | Bio features change sections → BEM input | `tests/test_features.py::test_featured_impeller_is_watertight` |
| 15 | `fansim/optimize/study.py` | `# RECOVERED-FROM-CHAT` | **Conditional** | Pareto rows aggregate objective CFM fields | `tests/test_shroud.py::test_pareto_summary_carries_shroud_thick` |

---

## Secondary gates (same stack, run with rank 1–5)

These pytest nodeids further pin shut-off, tip clearance, and LE/TE splicing called out in recovery notes:

| Concern | Gate test |
|---------|-----------|
| BEM shut-off with shroud vs open tip | `tests/test_shroud.py::test_bem_shrouded_shutoff_beats_open_tip` |
| Partial shroud height / tip_z span (blade splice) | `tests/test_shroud.py::test_full_frac_matches_tip_z_span` |
| LE/TE blunt splice at tip | `tests/test_le_te_thick.py::test_te_blunt_is_capped_below_le_nose` |
| Export tip gap after flat placement | `tests/test_placement.py::test_prepare_export_flat_on_shrinks_oversize_tip` |
| Sickle / flat round-trip through search_space | `tests/test_sickle.py::test_blade_from_flat_sickle_mm_round_trips` |

---

## Explicit non-gates

- **Propeller** stack (`fansim/propeller/bemt.py` spliced compressibility): gate with `tests/test_prop_bemt_gate.py` — not on the axial A12 CFM path.
- **Acoustics / cockpit-only** recovered modules: do not use for CFM; noise proxies are separate from flow claims.
- **Six baseline failures** (2026-09-14): none of the gate tests above are in that failure list except `test_results_for_hub_hides_foreign_envelope` (catalog splice UX, not BEM CFM). Re-run the full fast suite after any edit to ranked files.

---

## Recommended command before citing CFM

```powershell
uv run --extra optim --extra viz --extra surrogate --extra dev `
  python -m pytest `
    tests/test_fan_bem.py::test_reference_free_delivery_in_band `
    tests/test_shroud.py::test_bem_shrouded_shutoff_beats_open_tip `
    tests/test_shroud.py::test_ring_wall_contains_every_tip_section_point `
    tests/test_le_te_thick.py::test_te_blunt_is_capped_below_le_nose `
    tests/test_system_curve.py::test_probe_on_hose_is_exact_op `
    tests/test_cfd.py::test_parse_fan_metrics `
    -q
```

Absolute CFM still requires [north-star-staged.md](./north-star-staged.md) measurement or CFD tier sign-off — software gates alone are necessary, not sufficient.
