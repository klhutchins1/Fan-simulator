# Prop Mission Cockpit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the prop cockpit Optimize button run a mission preset and plot minutes or kilometres when that is the objective.

**Architecture:** A module-level `prop_mission_kwargs` builds the `run_prop_study` arguments. `prop_scatter_figure` stays the thrust-versus-noise plot. `prop_mission_figure` plots thrust against hover minutes or range. The tab selects the figure from the mission id.

**Tech Stack:** Python 3.12 (`uv`), pytest, Plotly, Trame/Vuetify. No Docker.

**Spec:** `docs/superpowers/specs/2026-09-23-prop-mission-cockpit-design.md`

## Global Constraints

- Mission ids are `thrust_efficiency`, `quiet_thrust`, `hover_endurance`, `range`. Default is `thrust_efficiency`.
- Field defaults: all-up weight 5 N, 4 rotors, 50 Wh, cruise 15 m/s, minutes floor blank.
- `thrust_efficiency` passes `mission` only (plus the power cap and trial count already passed). It does not send `min_hover_minutes`.
- `quiet_thrust` sends `min_hover_minutes` only when the field is a positive number, and then also sends weight, rotor count, and battery. A blank floor omits all four.
- `hover_endurance` sends `all_up_weight_n`, `n_rotors`, and `battery_wh`. `range` also sends `cruise_mps`.
- A non-positive required field does not call `run_prop_study`. `prop_msg` names the field.
- Resume is honored only for `thrust_efficiency`. Any other mission uses a new run directory.
- `prop_scatter_figure` is unchanged. Use it for `thrust_efficiency` and `quiet_thrust`.
- `prop_mission_figure(pareto, user_points, y_key, y_title)` plots `thrust_g` on x and `y_key` on y. Color is `eff_g_per_w`. Hover includes `rel_dba` and `power_w`. `customdata` is the study-then-user index. Rows missing `y_key` are omitted.
- Endurance axis title is `hover (min)`. Range axis title is `range (km)`.
- Do not change CROR plots, mixed-flow plots, Analyze, noise, or `hover_power_budget`.
- Check roadmap §14.7 and point at this spec and `docs/superpowers/plans/2026-09-23-prop-mission-cockpit.md`.
- On Windows, pytest may exit `-1073741819`, `-1073740940`, or `3221226356` after a printed pass line. Treat the pass line as success.
- PowerShell: do not chain commands with `&&`.
- Commit only the files a task lists. Do not stage `.superpowers/sdd/progress.md`, `catalog/catalog.db`, or `runs/`.

## File map

| File | Role |
|------|------|
| `fansim/cockpit/figures.py` | `prop_mission_figure` |
| `fansim/cockpit/prop_tab.py` | `prop_mission_kwargs`, mission select, figure switch |
| `tests/test_prop_persist.py` | Figure test and kwargs tests |
| `docs/roadmap.md` | Check §14.7 |

---

### Task 1: Mission figure and study kwargs

**Files:**
- Modify: `fansim/cockpit/figures.py`
- Modify: `fansim/cockpit/prop_tab.py` (module-level function only; do not edit `setup_prop_tab` in this task)
- Test: `tests/test_prop_persist.py`

**Interfaces:**
- Consumes: row keys `thrust_g`, `eff_g_per_w`, `rel_dba`, `power_w`, `hover_minutes`, `range_km`
- Produces: `prop_mission_figure(pareto, user_points=(), *, y_key: str, y_title: str) -> go.Figure`
- Produces: `prop_mission_kwargs(mission: str, weight_n, n_rotors, battery_wh, cruise_mps, min_minutes) -> dict`

`prop_mission_kwargs` returns `{"ok": True, "kwargs": {...}}` or `{"ok": False, "message": "..."}`. It does not include `n_trials`, `max_power_w`, `out_dir`, or `prop_model`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_prop_persist.py`:

```python
def test_prop_mission_figure_plots_minutes_and_range():
    from fansim.cockpit.figures import prop_mission_figure

    rows = [
        {"thrust_g": 1000.0, "eff_g_per_w": 4.0, "rel_dba": 50.0, "power_w": 200.0,
         "hover_minutes": 12.0, "range_km": 8.0},
        {"thrust_g": 800.0, "eff_g_per_w": 5.0, "rel_dba": 45.0, "power_w": 150.0},
    ]
    minutes = prop_mission_figure(rows, y_key="hover_minutes", y_title="hover (min)")
    xs = list(minutes.data[0].x)
    ys = list(minutes.data[0].y)
    assert xs == [1000.0]
    assert ys == [12.0]
    assert "noise" in minutes.data[0].hovertext[0]
    assert "W" in minutes.data[0].hovertext[0]
    ranged = prop_mission_figure(rows, y_key="range_km", y_title="range (km)")
    assert list(ranged.data[0].y) == [8.0]
    assert ranged.layout.yaxis.title.text == "range (km)"


def test_prop_mission_kwargs_follow_the_mission():
    from fansim.cockpit.prop_tab import prop_mission_kwargs

    default = prop_mission_kwargs("thrust_efficiency", 5, 4, 50, 15, "")
    assert default["ok"] is True
    assert default["kwargs"] == {"mission": "thrust_efficiency"}
    quiet = prop_mission_kwargs("quiet_thrust", 5, 4, 50, 15, "")
    assert quiet["kwargs"] == {"mission": "quiet_thrust"}
    floored = prop_mission_kwargs("quiet_thrust", 5, 4, 50, 15, "2")
    assert floored["kwargs"]["min_hover_minutes"] == 2.0
    assert floored["kwargs"]["all_up_weight_n"] == 5.0
    assert floored["kwargs"]["n_rotors"] == 4
    assert floored["kwargs"]["battery_wh"] == 50.0
    endurance = prop_mission_kwargs("hover_endurance", 5, 4, 50, 15, "")
    assert set(endurance["kwargs"]) == {"mission", "all_up_weight_n", "n_rotors", "battery_wh"}
    ranged = prop_mission_kwargs("range", 5, 4, 50, 15, "")
    assert ranged["kwargs"]["cruise_mps"] == 15.0
    bad = prop_mission_kwargs("range", 5, 4, 50, 0, "")
    assert bad["ok"] is False
    assert "cruise" in bad["message"]
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_persist.py::test_prop_mission_figure_plots_minutes_and_range tests/test_prop_persist.py::test_prop_mission_kwargs_follow_the_mission -q --tb=line`

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement the figure and the kwargs helper**

Add `prop_mission_figure` to `fansim/cockpit/figures.py` after `prop_scatter_figure`. Copy the marker and `customdata` pattern from `prop_scatter_figure`: study rows first, then user rows offset by `len(study)`. Skip a row when `y_key` is missing or `None`. `customdata` stays a scalar row index, the same study-then-user numbering `prop_scatter_figure` uses. Do not put noise and power in `customdata`; the click handler reads `customdata` as the index. Build `hovertext` as a list of strings, one per kept point: `"{thrust:.0f} g thrust<br>{y:.2f}<br>noise {rel:.0f} (rel)<br>{power:.0f} W"`. Set `hoverinfo="text"`. Compute the index before dropping rows that lack `y_key`.

Add this function at module level in `fansim/cockpit/prop_tab.py`, above `setup_prop_tab`:

```python
def prop_mission_kwargs(mission, weight_n, n_rotors, battery_wh, cruise_mps, min_minutes) -> dict:
    """Arguments for ``run_prop_study`` besides trials, power cap, directory, and model."""
    mission = str(mission or "thrust_efficiency")
    if mission == "thrust_efficiency":
        return {"ok": True, "kwargs": {"mission": mission}}
    if mission == "quiet_thrust":
        text = str(min_minutes).strip()
        if text == "":
            return {"ok": True, "kwargs": {"mission": mission}}
        try:
            floor = float(text)
        except (TypeError, ValueError):
            return {"ok": False, "message": "minimum hover minutes must be a positive number"}
        if floor <= 0.0:
            return {"ok": False, "message": "minimum hover minutes must be a positive number"}
        vehicle = _vehicle(weight_n, n_rotors, battery_wh)
        if not vehicle["ok"]:
            return vehicle
        return {"ok": True, "kwargs": {"mission": mission, "min_hover_minutes": floor, **vehicle["fields"]}}
    vehicle = _vehicle(weight_n, n_rotors, battery_wh)
    if not vehicle["ok"]:
        return vehicle
    fields = {"mission": mission, **vehicle["fields"]}
    if mission == "hover_endurance":
        return {"ok": True, "kwargs": fields}
    if mission == "range":
        try:
            cruise = float(cruise_mps)
        except (TypeError, ValueError):
            cruise = 0.0
        if cruise <= 0.0:
            return {"ok": False, "message": "cruise speed must be positive"}
        fields["cruise_mps"] = cruise
        return {"ok": True, "kwargs": fields}
    return {"ok": False, "message": f"unknown mission {mission}"}


def _vehicle(weight_n, n_rotors, battery_wh) -> dict:
    try:
        weight = float(weight_n)
        rotors = int(float(n_rotors))
        battery = float(battery_wh)
    except (TypeError, ValueError):
        return {"ok": False, "message": "weight, rotors, and battery must be numbers"}
    if weight <= 0.0:
        return {"ok": False, "message": "all-up weight must be positive"}
    if rotors < 1:
        return {"ok": False, "message": "rotor count must be at least 1"}
    if battery <= 0.0:
        return {"ok": False, "message": "battery watt-hours must be positive"}
    return {"ok": True, "fields": {
        "all_up_weight_n": weight, "n_rotors": rotors, "battery_wh": battery,
    }}
```

- [ ] **Step 4: Run the persist tests**

Run: `uv run python -m pytest tests/test_prop_persist.py -q --tb=line`

Expected: PASS, including `test_prop_scatter_figure_accepts_user_points`.

- [ ] **Step 5: Commit**

```powershell
git add -- fansim/cockpit/figures.py fansim/cockpit/prop_tab.py tests/test_prop_persist.py
git commit -m @"
feat(prop): plot mission minutes and range beside the noise scatter

"@
```

---

### Task 2: Wire the mission select into Optimize

**Files:**
- Modify: `fansim/cockpit/prop_tab.py` (`setup_prop_tab` and the Optimize card)

**Interfaces:**
- Consumes: `prop_mission_kwargs` and `prop_mission_figure` from Task 1. `run_prop_study` mission keywords from the search slice.
- Produces: state fields `prop_mission`, `prop_weight_n`, `prop_n_rotors`, `prop_battery_wh`, `prop_cruise_mps`, `prop_min_minutes`

- [ ] **Step 1: Add state defaults**

Inside `setup_prop_tab`, next to `state.prop_resume = False`, add:

```python
    state.prop_mission = "thrust_efficiency"
    state.prop_mission_items = [
        {"title": "thrust_efficiency", "value": "thrust_efficiency"},
        {"title": "quiet_thrust", "value": "quiet_thrust"},
        {"title": "hover_endurance", "value": "hover_endurance"},
        {"title": "range", "value": "range"},
    ]
    state.prop_weight_n = 5.0
    state.prop_n_rotors = 4
    state.prop_battery_wh = 50.0
    state.prop_cruise_mps = 15.0
    state.prop_min_minutes = ""
```

Bind `prop_mission_items` by state name. Do not pass a raw list to `items=`.

- [ ] **Step 2: Pass mission kwargs and skip resume for other missions**

In the Optimize handler, after `out_dir` is chosen:

```python
        mission_call = prop_mission_kwargs(
            state.prop_mission, state.prop_weight_n, state.prop_n_rotors,
            state.prop_battery_wh, state.prop_cruise_mps, state.prop_min_minutes,
        )
        if not mission_call["ok"]:
            state.prop_msg = mission_call["message"]
            return
        if str(state.prop_mission) != "thrust_efficiency":
            resume = False
            out_dir = prop_out_path(resume=False, last_dir=None, stamp=stamp, runs_root=root)
            mode = "new"
```

Add `**mission_call["kwargs"]` to the `run_prop_study(...)` call.

- [ ] **Step 3: Pick the figure**

Replace the body of `_refresh_prop_figure` with:

```python
    def _refresh_prop_figure():
        if hasattr(ctrl, "prop_fig_update"):
            mission = str(state.prop_mission)
            if mission == "hover_endurance":
                fig = prop_mission_figure(
                    prop_pareto_store, prop_user_store,
                    y_key="hover_minutes", y_title="hover (min)",
                )
            elif mission == "range":
                fig = prop_mission_figure(
                    prop_pareto_store, prop_user_store,
                    y_key="range_km", y_title="range (km)",
                )
            else:
                fig = prop_scatter_figure(prop_pareto_store, prop_user_store)
            ctrl.prop_fig_update(fig)
        state.prop_trial_items = design_dropdown_items(_prop_click_store(), by_index=True)
```

Import `prop_mission_figure` next to the existing `prop_scatter_figure` import.

- [ ] **Step 4: Add the controls**

In the Optimize card, after the trials / max-power row and before the resume switch, add a `VSelect` bound to `prop_mission` with `items=("prop_mission_items",)`, label `Mission`, and five compact number fields for weight (N), rotors, battery (Wh), cruise (m/s), and minimum hover minutes. The minutes field is text so a blank value stays blank. Change the card subtitle from `thrust ↔ efficiency` to `mission presets: thrust/efficiency, quiet, endurance, range`.

- [ ] **Step 5: Run the kwargs tests**

Run: `uv run python -m pytest tests/test_prop_persist.py::test_prop_mission_kwargs_follow_the_mission tests/test_prop_persist.py::test_prop_mission_figure_plots_minutes_and_range -q --tb=line`

Expected: PASS. This task does not start Trame.

- [ ] **Step 6: Commit**

```powershell
git add -- fansim/cockpit/prop_tab.py
git commit -m @"
feat(prop): choose a mission from the prop Optimize card

"@
```

---

### Task 3: Check roadmap §14.7

**Files:**
- Modify: `docs/roadmap.md` (the §14.7 checkbox and one sentence)

- [ ] **Step 1: Check the item**

Change `- [ ] **14.7 Prop missions:` to `- [x] **14.7 Prop missions:`. Under the sentence that already names the search presets, add:

```markdown
  Cockpit mission select and the minutes/km plots are in. Spec/plan:
  `docs/superpowers/specs/2026-09-23-prop-mission-cockpit-design.md`,
  `docs/superpowers/plans/2026-09-23-prop-mission-cockpit.md`.
```

Delete the sentence `Cockpit mission controls and the minutes/km plots are still open.` if it is present.

- [ ] **Step 2: Commit**

```powershell
git add -- docs/roadmap.md
git commit -m @"
docs(prop): mark prop mission presets done

"@
```
