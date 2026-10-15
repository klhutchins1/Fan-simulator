# PLA+ material picker (round 12 Task D): report only

Prereg `42004b3`. Headless cockpit session (same as Task C). The real Preview and the real Export ran. Assess used a fake
`evaluate_candidate_isolated` (r7 harness pattern; no CFD). Cold open: chip PETG, Stock selected. Set `assess_material="PLA+"`
and never switched back. `active_spec().material` was **PETG** at every step: cold open, after PLA+, after Preview, after Export and after Assess.

| id | surface | says | evidence |
|---|---|---|---|
| M0 | dropdown / Actions chip | **PLA+** (follows) | state.assess_material stays PLA+ through Preview, Export and Assess |
| M1 | Preview "✓ fits … g" | **PETG** | `spec_status` → `estimate_weight_g(vol, spec.material)`. Caption reads "11 g". The preview volume gives 11.13 g for PETG and 10.87 g for PLA+, so rounding hides the difference on Stock |
| M2 | Export README + nozzle/bed | **PETG** | README: "Material: **PETG** (nozzle 240 °C, bed 80 °C …)". print_fit.json material PETG, index.jsonl material PETG (export HES4W) |
| M3 | Assess stamp | **PLA+** (follows) | the run received material="PLA+" (the spec it was passed still says PETG). Saved extra.material = PLA+ |
| M4 | optimizer argv | **PLA+** (follows) | `fan_optimize.py:152` passes `material=state.assess_material` → `cli_argv.py:195` adds `--material` |

**Cause:** yes, it is `active_spec().material`. The picker only feeds `run_settings`/optimizer. Preview grams (`fan_assess.spec_status`)
and Export (`fan_export.do_export`, which passes `spec.material` into the README, `recommend_print_settings`, the print_fit
sidecar and the registry) read the FanSpec, which is PETG for a12x25. So after PLA+ is picked, M1 and M2 still say PETG.
→ **QA-36**. No patch (brief). A fix probably means carrying `assess_material` into the spec handed to `_export_isolated` and
`spec_status`, or reading it there directly. Task E's tests pin both behaviours.
