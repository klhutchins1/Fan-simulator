# Prop Mission Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `run_prop_study` run as quiet thrust, hover endurance, or range without adding a second optimizer.

**Architecture:** One `mission` argument selects two NSGA-II directions. The default mission stays maximize thrust and maximize grams per watt. Physical fields live on trial user attributes. `pareto_rows_from_study` is the only row builder and drops infeasible trials.

**Tech Stack:** Python 3.12 (`uv`), pytest, Optuna. No Docker.

**Spec:** `docs/superpowers/specs/2026-09-23-prop-missions-design.md`

## Global Constraints

- `mission` defaults to `"thrust_efficiency"`. Directions are maximize, maximize. Existing `tests/test_prop_optimize.py` assertions stay as they are.
- `quiet_thrust` maximizes `thrust_g` and minimizes `rel_dba`. `hover_endurance` maximizes `hover_minutes` and `thrust_g`. `range` maximizes `range_km` and `thrust_g`.
- Unknown `mission` raises `ValueError` naming `thrust_efficiency`, `quiet_thrust`, `hover_endurance`, and `range`.
- Infeasible objective pair: `0.0` on a maximize axis, `1e6` on a minimize axis. Mark `feasible=False`. Omit those trials from the front.
- `max_power_w` still compares static shaft power on every mission.
- `hover_endurance` and `range` require `all_up_weight_n > 0`, `n_rotors >= 1`, and `battery_wh > 0`. `range` also requires `cruise_mps > 0`. `quiet_thrust` requires those three only when `min_hover_minutes` is set. `min_hover_minutes` on any other mission raises `ValueError`.
- Lift is `static.thrust_n * n_rotors >= all_up_weight_n` at `spec.rpm_max` and `v_forward=0`.
- Hover minutes and the quiet floor call `hover_power_budget` with `shaft_power_w` set. Do not use the momentum figure-of-merit path. Do not pass a new `eta_elec` or `usable_frac`.
- `range_km = cruise_mps * minutes * 0.06` from the cruise shaft-power budget. Cruise is a second `analyze` at `spec.rpm_max` and `v_forward=cruise_mps`.
- Noise is `estimate_prop_noise` on the static point. It is an objective only for `quiet_thrust`.
- Study name `prop` for `thrust_efficiency`. Other missions use `prop_<mission>`.
- Row fields come from user attributes. The stored efficiency attribute stays `eff` (existing key). The row key is `eff_g_per_w`. `hover_minutes` and `range_km` are `None` when not computed.
- Sort every front by descending `thrust_g`.
- Do not change `suggest_prop`, `estimate_prop_noise`, `hover_power_budget`, BEMT, CFD, or the cockpit.
- Do not check the §14.7 box.
- On Windows, pytest may exit `-1073741819`, `-1073740940`, or `3221226356` after a printed pass line. Treat the pass line as success.
- PowerShell: do not chain commands with `&&`.
- Commit only the files a task lists. Do not stage `.superpowers/sdd/progress.md`, `catalog/catalog.db`, or `runs/`.

## File map

| File | Role |
|------|------|
| `fansim/propeller/persist.py` | `pareto_rows_from_study` reads user attributes and drops infeasible trials |
| `fansim/propeller/optimize.py` | Mission argument, constraints, two objectives |
| `tests/test_prop_persist.py` | User-attr rows and the values fallback |
| `tests/test_prop_optimize.py` | Mission validation, empty floor, lifting endurance and range |
| `docs/roadmap.md` | One sentence under §14.7. Checkbox stays open |

---

### Task 1: Read Pareto rows from user attributes

**Files:**
- Modify: `fansim/propeller/persist.py` (`pareto_rows_from_study`)
- Test: `tests/test_prop_persist.py`

**Interfaces:**
- Consumes: Optuna `best_trials` with user attributes `thrust_g`, `eff`, `power_w`, `fm`, `n_blades`, `rel_dba`, `tip_mach`, `hover_minutes`, `range_km`, `mission`, `feasible`
- Produces: `pareto_rows_from_study(study) -> list[dict]`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_prop_persist.py`:

```python
def test_pareto_rows_prefer_user_attrs_over_values():
    import optuna
    from fansim.propeller.persist import pareto_rows_from_study

    study = optuna.create_study(directions=["maximize", "minimize"])

    def objective(trial):
        trial.set_user_attr("thrust_g", 900.0)
        trial.set_user_attr("eff", 3.5)
        trial.set_user_attr("power_w", 200.0)
        trial.set_user_attr("fm", 0.6)
        trial.set_user_attr("n_blades", 3)
        trial.set_user_attr("rel_dba", 70.0)
        trial.set_user_attr("tip_mach", 0.5)
        trial.set_user_attr("hover_minutes", None)
        trial.set_user_attr("range_km", None)
        trial.set_user_attr("mission", "quiet_thrust")
        trial.set_user_attr("feasible", True)
        return 900.0, 70.0

    study.optimize(objective, n_trials=1)
    rows = pareto_rows_from_study(study)
    assert rows[0]["thrust_g"] == 900.0
    assert rows[0]["eff_g_per_w"] == 3.5
    assert rows[0]["rel_dba"] == 70.0
    assert rows[0]["mission"] == "quiet_thrust"
    assert rows[0]["hover_minutes"] is None
    assert rows[0]["range_km"] is None


def test_pareto_rows_drop_infeasible_and_fall_back_when_thrust_missing():
    import optuna
    from fansim.propeller.persist import pareto_rows_from_study

    study = optuna.create_study(directions=["maximize", "maximize"])

    def objective(trial):
        if trial.number == 0:
            trial.set_user_attr("feasible", False)
            trial.set_user_attr("thrust_g", 1.0)
            trial.set_user_attr("eff", 1.0)
            return 0.0, 0.0
        return 400.0, 5.0

    study.optimize(objective, n_trials=2)
    rows = pareto_rows_from_study(study)
    assert len(rows) == 1
    assert rows[0]["thrust_g"] == 400.0
    assert rows[0]["eff_g_per_w"] == 5.0
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_persist.py::test_pareto_rows_prefer_user_attrs_over_values tests/test_prop_persist.py::test_pareto_rows_drop_infeasible_and_fall_back_when_thrust_missing -q --tb=line`

Expected: FAIL. The quiet row's `eff_g_per_w` is `70.0` (taken from `values[1]`) or the infeasible trial is still present.

- [ ] **Step 3: Implement the builder**

Replace `pareto_rows_from_study` in `fansim/propeller/persist.py` with:

```python
def pareto_rows_from_study(study) -> list[dict]:
    """Extract the NSGA front. Physical fields come from user attributes.

    When ``thrust_g`` was not stored, fall back to ``values[0]`` and ``values[1]``
    so an older default study still reloads. Infeasible trials are omitted.
    """
    pareto = []
    for t in study.best_trials:
        if t.values is None:
            continue
        attrs = t.user_attrs
        if attrs.get("feasible") is False:
            continue
        if "thrust_g" in attrs:
            thrust = attrs.get("thrust_g")
            eff = attrs.get("eff_g_per_w", attrs.get("eff"))
        else:
            thrust = t.values[0]
            eff = t.values[1]
        pareto.append({
            "thrust_g": thrust,
            "eff_g_per_w": eff,
            "power_w": attrs.get("power_w"),
            "fm": attrs.get("fm"),
            "n_blades": attrs.get("n_blades"),
            "rel_dba": attrs.get("rel_dba"),
            "tip_mach": attrs.get("tip_mach"),
            "hover_minutes": attrs.get("hover_minutes"),
            "range_km": attrs.get("range_km"),
            "mission": attrs.get("mission"),
            "params": dict(t.params),
            "source": "optimize",
            "trial": int(t.number),
        })
    pareto.sort(key=lambda r: -float(r["thrust_g"]))
    return pareto
```

- [ ] **Step 4: Run the persist tests**

Run: `uv run python -m pytest tests/test_prop_persist.py -q --tb=line`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- fansim/propeller/persist.py tests/test_prop_persist.py
git commit -m @"
fix(prop): read Pareto rows from trial attributes

"@
```

---

### Task 2: Mission presets on `run_prop_study`

**Files:**
- Modify: `fansim/propeller/optimize.py` (`run_prop_study`)
- Test: `tests/test_prop_optimize.py`

**Interfaces:**
- Consumes: `pareto_rows_from_study` from Task 1. `analyze`, `estimate_prop_noise`, `hover_power_budget`, `suggest_prop`, `evaluate_prop`.
- Produces: `run_prop_study(spec, n_trials=200, seed=0, max_power_w=None, out_dir=None, prop_model=None, mission="thrust_efficiency", all_up_weight_n=None, n_rotors=None, battery_wh=None, cruise_mps=None, min_hover_minutes=None) -> tuple[study, list[dict]]`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_prop_optimize.py`:

```python
import pytest


def test_unknown_mission_names_the_legal_four():
    spec = get_prop_spec("fpv_5inch")
    with pytest.raises(ValueError, match="quiet_thrust") as exc:
        run_prop_study(spec, n_trials=1, seed=0, mission="louder")
    text = str(exc.value)
    for name in ("thrust_efficiency", "hover_endurance", "range"):
        assert name in text


def test_endurance_and_range_require_vehicle_inputs():
    spec = get_prop_spec("fpv_5inch")
    with pytest.raises(ValueError):
        run_prop_study(spec, n_trials=1, seed=0, mission="hover_endurance")
    with pytest.raises(ValueError):
        run_prop_study(spec, n_trials=1, seed=0, mission="range",
                       all_up_weight_n=2.0, n_rotors=1, battery_wh=50.0)
    with pytest.raises(ValueError):
        run_prop_study(spec, n_trials=1, seed=0, mission="thrust_efficiency",
                       min_hover_minutes=1.0)


def test_quiet_floor_can_empty_the_front():
    spec = get_prop_spec("fpv_5inch")
    _, pareto = run_prop_study(
        spec, n_trials=20, seed=0, mission="quiet_thrust",
        all_up_weight_n=2.0, n_rotors=1, battery_wh=50.0,
        min_hover_minutes=1.0e9,
    )
    assert pareto == []


def test_endurance_and_range_fronts_lift_the_weight():
    spec = get_prop_spec("fpv_5inch")
    _, endurance = run_prop_study(
        spec, n_trials=30, seed=0, mission="hover_endurance",
        all_up_weight_n=2.0, n_rotors=1, battery_wh=50.0,
    )
    assert endurance
    assert all(r["hover_minutes"] > 0 for r in endurance)
    assert all(r["mission"] == "hover_endurance" for r in endurance)
    _, ranged = run_prop_study(
        spec, n_trials=30, seed=1, mission="range",
        all_up_weight_n=2.0, n_rotors=1, battery_wh=50.0, cruise_mps=15.0,
    )
    assert ranged
    assert all(r["range_km"] > 0 for r in ranged)
    assert all(r["thrust_g"] * 9.80665 / 1000.0 >= 2.0 for r in ranged)
    thrusts = [r["thrust_g"] for r in ranged]
    assert thrusts == sorted(thrusts, reverse=True)
```

Add `import pytest` once. `thrust_g` is rounded grams, so `thrust_g * 9.80665 / 1000` is the rounded newtons. The lift check in the implementation uses unrounded `thrust_n`. The test's gram conversion can sit a hair under 2.0 because `thrust_g` is rounded. Compare with a 1 gram tolerance:

```python
    assert all(r["thrust_g"] * 9.80665 / 1000.0 >= 2.0 - 0.01 for r in ranged)
```

Use that tolerance line, not the stricter one.

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_optimize.py::test_unknown_mission_names_the_legal_four tests/test_prop_optimize.py::test_endurance_and_range_require_vehicle_inputs tests/test_prop_optimize.py::test_quiet_floor_can_empty_the_front tests/test_prop_optimize.py::test_endurance_and_range_fronts_lift_the_weight -q --tb=line`

Expected: FAIL. `run_prop_study` does not accept `mission` (`TypeError`).

- [ ] **Step 3: Implement the mission switch**

In `fansim/propeller/optimize.py`, import `hover_power_budget` from `fansim.propeller.power`.

Add these helpers above `run_prop_study`:

```python
_MISSIONS = ("thrust_efficiency", "quiet_thrust", "hover_endurance", "range")
_WORST_MIN = 1.0e6


def _mission_directions(mission: str) -> list[str]:
    if mission == "quiet_thrust":
        return ["maximize", "minimize"]
    if mission in ("thrust_efficiency", "hover_endurance", "range"):
        return ["maximize", "maximize"]
    raise ValueError(
        f"unknown mission {mission!r}; known: {', '.join(_MISSIONS)}"
    )


def _require_vehicle(mission: str, all_up_weight_n, n_rotors, battery_wh, cruise_mps, min_hover_minutes):
    if min_hover_minutes is not None and mission != "quiet_thrust":
        raise ValueError("min_hover_minutes is only valid for quiet_thrust")
    needs_vehicle = mission in ("hover_endurance", "range") or (
        mission == "quiet_thrust" and min_hover_minutes is not None
    )
    if not needs_vehicle:
        return
    if all_up_weight_n is None or float(all_up_weight_n) <= 0.0:
        raise ValueError(f"{mission} requires all_up_weight_n > 0")
    if n_rotors is None or int(n_rotors) < 1:
        raise ValueError(f"{mission} requires n_rotors >= 1")
    if battery_wh is None or float(battery_wh) <= 0.0:
        raise ValueError(f"{mission} requires battery_wh > 0")
    if mission == "range" and (cruise_mps is None or float(cruise_mps) <= 0.0):
        raise ValueError("range requires cruise_mps > 0")


def _worst(directions: list[str]) -> tuple[float, float]:
    return tuple(_WORST_MIN if d == "minimize" else 0.0 for d in directions)
```

Replace `run_prop_study` with a version that validates first, picks directions and `study_name = "prop" if mission == "thrust_efficiency" else f"prop_{mission}"`, and uses this objective. Keep the storage / `load_if_exists` block, but pass `directions=_mission_directions(mission)` and that study name. Build the front with `pareto_rows_from_study(study)` instead of the inline list. Keep the `save_prop_pareto` call.

```python
def run_prop_study(spec: PropSpec, n_trials: int = 200, seed: int = 0,
                   max_power_w: float | None = None,
                   out_dir=None, prop_model: str | None = None,
                   mission: str = "thrust_efficiency",
                   all_up_weight_n: float | None = None,
                   n_rotors: int | None = None,
                   battery_wh: float | None = None,
                   cruise_mps: float | None = None,
                   min_hover_minutes: float | None = None):
    """NSGA-II over the prop blade. ``mission`` picks the two objectives."""
    from pathlib import Path

    from fansim.propeller.persist import pareto_rows_from_study

    _require_vehicle(mission, all_up_weight_n, n_rotors, battery_wh, cruise_mps, min_hover_minutes)
    directions = _mission_directions(mission)
    study_name = "prop" if mission == "thrust_efficiency" else f"prop_{mission}"
    worst = _worst(directions)

    storage = None
    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        storage = f"sqlite:///{(out / 'study.db').as_posix()}"
        study = optuna.create_study(
            directions=directions,
            sampler=optuna.samplers.NSGAIISampler(seed=seed),
            storage=storage,
            study_name=study_name,
            load_if_exists=True,
        )
    else:
        study = optuna.create_study(
            directions=directions, sampler=optuna.samplers.NSGAIISampler(seed=seed))

    def _budget_minutes(shaft_power_w: float, tip_radius_mm: float) -> float:
        from fansim.propeller.power import hover_power_budget
        budget = hover_power_budget(
            all_up_weight_n=float(all_up_weight_n),
            n_rotors=int(n_rotors),
            tip_radius_m=float(tip_radius_mm) / 1000.0,
            figure_of_merit=0.7,
            battery_wh=float(battery_wh),
            shaft_power_w=float(shaft_power_w),
        )
        return float(budget["hover_minutes"])

    def objective(trial):
        params = suggest_prop(trial, spec)
        perf = evaluate_prop(params, spec)
        noise = estimate_prop_noise(params, spec.rpm_max, perf)
        hover_minutes = None
        range_km = None
        feasible = True
        if max_power_w is not None and perf.power_w > max_power_w:
            feasible = False
        lifts = True
        if mission in ("hover_endurance", "range") or min_hover_minutes is not None:
            lifts = perf.thrust_n * int(n_rotors) >= float(all_up_weight_n)
            if not lifts:
                feasible = False
            else:
                hover_minutes = _budget_minutes(perf.power_w, params.tip_radius)
                if min_hover_minutes is not None and hover_minutes < float(min_hover_minutes):
                    feasible = False
        if feasible and mission == "range":
            cruise = analyze(params, rpm=spec.rpm_max, v_forward=float(cruise_mps))
            range_km = float(cruise_mps) * _budget_minutes(cruise.power_w, params.tip_radius) * 0.06
        trial.set_user_attr("feasible", feasible)
        trial.set_user_attr("thrust_g", perf.thrust_g)
        trial.set_user_attr("eff", perf.efficiency_g_per_w)
        trial.set_user_attr("power_w", perf.power_w)
        trial.set_user_attr("fm", perf.figure_of_merit)
        trial.set_user_attr("n_blades", params.n_blades)
        trial.set_user_attr("rel_dba", noise["rel_dba"])
        trial.set_user_attr("tip_mach", noise["tip_mach"])
        trial.set_user_attr("hover_minutes", hover_minutes)
        trial.set_user_attr("range_km", range_km)
        trial.set_user_attr("mission", mission)
        if not feasible:
            return worst
        if mission == "quiet_thrust":
            return perf.thrust_g, noise["rel_dba"]
        if mission == "hover_endurance":
            return hover_minutes, perf.thrust_g
        if mission == "range":
            return range_km, perf.thrust_g
        return perf.thrust_g, perf.efficiency_g_per_w

    study.optimize(objective, n_trials=n_trials)
    pareto = pareto_rows_from_study(study)
    if out_dir is not None:
        from fansim.propeller.persist import save_prop_pareto
        save_prop_pareto(Path(out_dir), pareto, prop_model=prop_model or getattr(spec, "name", None))
    return study, pareto
```

`params.tip_radius` is millimetres. `_budget_minutes` divides it by 1000. `figure_of_merit=0.7` is ignored because `shaft_power_w` is set. Do not omit that argument; `hover_power_budget` requires it.

- [ ] **Step 4: Run the optimizer tests**

Run: `uv run python -m pytest tests/test_prop_optimize.py tests/test_prop_persist.py tests/test_prop_resume.py -q --tb=line`

Expected: PASS. `test_prop_resume.py` resumes a default study named `prop`.

- [ ] **Step 5: Commit**

```powershell
git add -- fansim/propeller/optimize.py tests/test_prop_optimize.py
git commit -m @"
feat(prop): add quiet, endurance, and range missions to the prop search

"@
```

---

### Task 3: Note the presets on the roadmap

**Files:**
- Modify: `docs/roadmap.md` (§14.7 only)

**Interfaces:**
- Consumes: the missions from Task 2
- Produces: one sentence under the §14.7 item. The checkbox stays `- [ ]`

- [ ] **Step 1: Add the sentence**

Under the §14.7 paragraph that begins `One search.`, add:

```markdown
  Search presets are on `run_prop_study`: `thrust_efficiency` (default), `quiet_thrust`, `hover_endurance`, and `range`. Spec/plan:
  `docs/superpowers/specs/2026-09-23-prop-missions-design.md`,
  `docs/superpowers/plans/2026-09-23-prop-missions.md`.
  Cockpit mission controls and the minutes/km plots are still open.
```

Leave the checkbox unchecked.

- [ ] **Step 2: Commit**

```powershell
git add -- docs/roadmap.md
git commit -m @"
docs(prop): note the prop mission presets on the roadmap

"@
```
