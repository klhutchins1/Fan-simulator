# CFD Sanity Checks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Every fan CFD result carries cheap physics and setup sanity checks (PASS / WARN / FAIL / SKIP)
that catch the class of setup bugs found so far. The optimizer **flags** suspect designs, and never
rejects them (user decision A).

**Architecture:**
- `build_case` writes a small `constant/case_meta.json` (patch areas, domain shape) and two extra
  function objects (`inletFlow`, `yPlus`).
- `fansim/cfd/sanity.py` holds pure check functions over the case's postProcessing, its logs and that
  sidecar.
- A CLI checks any existing case, and the pipelines attach the results to their outputs.

**Design (user-approved 2026-09-27):**

| check | data | PASS | WARN | FAIL |
|---|---|---|---|---|
| mass_balance | inletFlow + outletFlow tail means | ≤1% | ≤5% | >5% |
| energy_total | Q·(p_out + ½ρ(Q/A_out)² − 0) vs shaft P | η_total <1 | — | ≥1 |
| power_sign | Mz·ω_signed when Q>0 | <0 | — | ≥0 |
| thrust_direction | sign(Fz) vs sign(Q) when Q>0 | Fz<0 | — | Fz≥0 |
| inlet_bookkeeping | p_in vs −½ρ(Q/A_in)² (inlet total = 0) | ≤5% | ≤15% | >15% |
| mesh_quality | checkMesh.log | "Mesh OK" | — | failed checks |
| y_plus | yPlus on impeller, average | 30–300 | otherwise | — |
| regime | tip Mach = ω·r_tip/343 | <0.3 | ≥0.3 | — |
| converged | FanMetrics.converged (rule A) | yes | no | — |
| duct_shape | case_meta | round bore | square tunnel (open corners bypass the tip gap) | — |

Missing data gives SKIP, with a note. The overall status is the worst of FAIL > WARN > PASS; SKIP is
ignored.

## Global Constraints

- Additive only. Metrics, `CFD_VERSION`, solver settings and existing function objects are unchanged.
  The new function objects only add outputs.
- The direction fix stays intact, and `check_placement` is never weakened.
- Optimizer policy: a sanity FAIL sets `sanity_status="FAIL"` plus reasons in the result and trial
  attributes, and appends to the reason text. It never makes a design infeasible.
- Branch `master`. Commit per task with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  Do not commit `runs/` or `.superpowers/`.
- A URANS CFD run is using the CPU. Do NOT run CFD or Docker. Run only focused pytest files (not the
  whole suite), and judge them by the summary line.
- ρ = 1.2 (`RHO_AIR`), c₀ = 343 (`fansim.physics.air.C0_AIR`).

---

### Task 1: Case metadata sidecar + `inletFlow` / `yPlus` function objects

**Files:** `fansim/cfd/openfoam_case.py`, `fansim/cfd/templates.py`. Test: `tests/test_case_meta.py`.

- **Sidecar.** `build_case` writes `constant/case_meta.json` with:
  - `{"duct_shape": "round" | "square", "box_half_width_m": H, "inlet_area_m2", "outlet_area_m2", "casing": bool, "plenum": bool, "duct_radius_m", "tip_radius_m", "hub_radius_m", "rpm", "spin", "cfd_version"}`;
  - areas: with a casing, the inlet is π·duct_radius² and the outlet is (2H)²; without a casing, both are (2H)²;
  - `plenum` is True when the casing ends before `domain_z_max`. Detect it from the casing STL bounds, or add a `plenum: bool = False` build_case parameter that the ladder passes. Prefer detecting it from the casing STL z_max < `domain_z_max` − 1 mm;
  - `tip_radius_m = duct_radius − tip_gap`;
  - `cfd_version` from `fansim.cfd.metrics.CFD_VERSION`.
- **Function objects.** Add two entries to `T.CONTROL_DICT` `functions`, keeping the existing ones:
  - `inletFlow`: the same shape as `outletFlow` with `name inlet;`;
  - `yPlus`: `{ type yPlus; libs (fieldFunctionObjects); writeControl writeTime; }`.
- The URANS overlay reuses the steady `CONTROL_DICT`, so it gets both automatically. Confirm that
  `tests/test_urans_overlay.py` still passes; its exactly-once replacements must not break.
- **Tests:**
  - the sidecar exists with correct areas for no casing (square), a casing (round) and a plenum casing
    (`plenum` True);
  - the controlDict contains `inletFlow` and `yPlus` blocks.
- Run `uv run pytest tests/test_case_meta.py tests/test_urans_overlay.py tests/test_cfd.py tests/test_plenum_casing.py tests/audit/test_cfd_direction_contract.py -q`.
- Commit with the message `feat(cfd): case metadata sidecar + inletFlow/yPlus function objects`.

### Task 2: `fansim/cfd/sanity.py`

**Files:** Create `fansim/cfd/sanity.py`. Test: `tests/test_cfd_sanity.py`.

**Interfaces:**
- `SanityCheck(name: str, status: str, value: float | None, limit: str, note: str)`, a frozen dataclass.
- `run_sanity(case_dir: Path, *, metrics: FanMetrics | None = None, omega_signed: float | None = None) -> list[SanityCheck]`
- `overall(checks) -> str`
- `summarize(checks) -> str` returns one line, for example `sanity WARN: y_plus avg 4.1 (30-300); duct_shape square`.

Implementation notes:
- Read the tail means with the existing `metrics._tail_mean_row` / `_pp_file`.
- **inletFlow:** phi on the inlet is negative for inflow, so mass imbalance = |Q_in + Q_out| / |Q_out|.
- **yPlus.dat:** find the newest `postProcessing/yPlus/*/yPlus.dat`. Its columns are time, patch, min,
  max, average. Take the impeller rows, using the latest time.
- **checkMesh:** `logs/checkMesh.log`. PASS if it contains "Mesh OK."; FAIL if "Failed" appears in a
  "***" line. Record `max non-orthogonality` and `Max skewness` values in the note.
- `omega_signed` defaults to `case_meta` rpm·spin·2π/60.
- If `metrics` is None, parse it with `parse_fan_metrics(case_dir, omega_rad_s=|omega|)`.

Tests use synthetic cases in `tmp_path`: write the `.dat` files, a `case_meta.json` and a fake
`checkMesh.log`. Cover PASS and FAIL for each check, plus SKIP when the files are missing. Important
cases:
- a mass imbalance of 8% gives FAIL;
- η_total ≥ 1 gives FAIL;
- Mz·ω > 0 with Q > 0 gives FAIL;
- a square duct gives WARN;
- tip Mach 0.35 gives WARN.

Run `uv run pytest tests/test_cfd_sanity.py -q`. Commit with the message `feat(cfd): sanity checks over CFD cases`.

### Task 3: CLI + pipeline integration + audit unit

**Files:**
- Create `scripts/cfd_sanity.py`.
- Modify `fansim/optimize/objectives.py`, `scripts/run_a12x25_validation.py`, `scripts/run_loaded_ladder.py`, `scripts/audit_direction_cfd.py` and `fansim/audit/registry.yaml`.
- Test: `tests/test_cfd_sanity_integration.py`.

- **CLI:** `uv run python scripts/cfd_sanity.py <case_dir> [--json]` prints a table (name, status, value, limit, note) and the overall status. Exit 0 always; this is a report, not a gate.
- **Optimizer** (`evaluate_candidate`): after each metrics parse on the free-air and load solves, run the sanity checks. Store `sanity` (a list of dicts) and `sanity_status` in the result raw/stamps and the trial attributes. When the status is FAIL, append `summarize(...)` to the reason/conv note. Never infeasible.
- **Validation / ladder / audit runner:** add `"sanity": [...]` and `"sanity_status"` to every row they write.
- **Registry:** a new unit `cfd.sanity_checks`, targeting `fansim.cfd.sanity`, with checks `tests/test_cfd_sanity.py`, claim "Cheap physics/setup invariants on every fan CFD result", and source derivation "mass/energy conservation; Euler turbomachinery power sign; AMCA inlet bookkeeping".
- **Integration test:** mock the pipeline pieces, as the existing `tests/test_evaluate_candidate_feasible.py` does, so `evaluate_candidate` runs without CFD. Assert `sanity_status` is present and that a synthetic FAIL leaves the design feasible but flagged.
- Run the focused tests. Commit with the message `feat(cfd): sanity checks on every fan CFD result; optimizer flags, never rejects`.

### Task 4 (controller)

Run `scripts/cfd_sanity.py` on the existing cases:
- `runs/validate_a12x25_dirfix`,
- `runs/loaded_ladder/{plenum,frame}`,
- `runs/audit_direction/stock/{as_built,flipped}` (only the last solve survives in each case dir).

Record the findings in `docs/validation/cfd_sanity_baseline.md`. The `inletFlow` and y+ checks will say
SKIP on old cases.
