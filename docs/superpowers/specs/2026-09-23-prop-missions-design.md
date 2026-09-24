# §14.7 search: prop mission presets

**Date:** 2026-09-23  
**Status:** approved in chat (2026-09-23); written spec awaiting review  
**Approach:** A — one `mission` argument on `run_prop_study`  
**Parent:** roadmap §14.7 (the checkbox stays open; cockpit plots are the next slice)  
**Related:** `fansim/propeller/optimize.py` (`run_prop_study`), `fansim/propeller/power.py` (`hover_power_budget`), `fansim/propeller/noise.py` (`estimate_prop_noise`), `fansim/propeller/persist.py` (`pareto_rows_from_study`)

## Plain language

The propeller search already maximizes thrust and grams per watt. Noise, hover time, and range are computed nearby and then ignored. This slice lets one study run as quiet thrust, hover endurance, or range. It does not add a second optimizer, and it does not change the cockpit.

## Goal

1. `run_prop_study(..., mission="thrust_efficiency")` is today's search. Existing callers that omit `mission` keep that behavior.
2. `quiet_thrust`, `hover_endurance`, and `range` are the other three presets. Each one still uses NSGA-II, the same blade sampler, and two objectives.
3. A design that fails a mission constraint is not on the returned front.
4. Roadmap §14.7 gains a sentence that the search presets exist. The checkbox stays open.

## Success criteria

| # | Criterion |
|---|-----------|
| 1 | `mission` defaults to `"thrust_efficiency"`. Directions are maximize thrust grams and maximize grams per watt. `tests/test_prop_optimize.py` passes without changing those assertions |
| 2 | `quiet_thrust` maximizes `thrust_g` and minimizes `rel_dba`. `hover_endurance` maximizes `hover_minutes` and `thrust_g`. `range` maximizes `range_km` and `thrust_g` |
| 3 | An unknown `mission` raises `ValueError` and names the four legal values |
| 4 | Every returned row stores `thrust_g`, `eff_g_per_w`, `power_w`, `fm`, `n_blades`, `rel_dba`, `tip_mach`, `params`, `hover_minutes`, `range_km`, and `mission` from trial user attributes. `hover_minutes` and `range_km` are `None` when that mission did not compute them. `thrust_g` and `eff_g_per_w` are not read from `trial.values` when the attributes are present. The list is sorted by descending `thrust_g` |
| 5 | `pareto_rows_from_study` is the only builder `run_prop_study` uses. If `thrust_g` is missing on a trial, that builder falls back to `values[0]` for thrust and `values[1]` for grams per watt so an older default study still reloads |
| 6 | Infeasible trials are marked `feasible=False` and are omitted from the front. On a maximize axis the returned objective is `0.0`. On a minimize axis it is `1e6`. The static `max_power_w` cap still makes a trial infeasible for every mission |
| 7 | `hover_endurance` and `range` require `all_up_weight_n > 0`, `n_rotors >= 1`, and `battery_wh > 0`. `range` also requires `cruise_mps > 0`. Missing or non-positive values raise `ValueError`. `quiet_thrust` requires those vehicle inputs only when `min_hover_minutes` is set. `min_hover_minutes` on any other mission raises `ValueError` |
| 8 | Lift uses the static BEMT point at `spec.rpm_max`: `thrust_n * n_rotors >= all_up_weight_n`. A design that cannot lift is infeasible. Hover minutes and the quiet-thrust floor use `hover_power_budget` with `shaft_power_w` set to that static shaft power, so the momentum figure-of-merit path is not used |
| 9 | Range uses a second BEMT point at the same RPM with `v_forward=cruise_mps`. `range_km = cruise_mps * hover_minutes * 0.06`, where `hover_minutes` is the budget's minute field at the cruise shaft power. Electrical efficiency and usable fraction stay the defaults already on `hover_power_budget` (0.70 and 0.80) |
| 10 | Noise is always `estimate_prop_noise` on the static point. It is an objective only for `quiet_thrust` |
| 11 | The Optuna study name stays `prop` for `thrust_efficiency`. The other missions use `prop_<mission>`, so a resumed default study does not load a different pair of directions |
| 12 | A test with a tiny battery-and-weight case returns a non-empty endurance front and a non-empty range front whose rows lift the weight. A test with an unreachable hover-minutes floor returns an empty quiet front. `tests/test_prop_optimize.py` and `tests/test_prop_persist.py` pass |

## Non-goals

- A second optimizer, a new sampler, or a change to `suggest_prop` bounds
- Cockpit mission controls, a minutes plot, or a range plot (the next slice)
- Changing `estimate_prop_noise`, `hover_power_budget`, BEMT stall behavior, or any CFD path
- Searching RPM, propeller mass, rotor count, or battery size
- Absolute dB(A) (roadmap §1.4)
- Checking the §14.7 box

## Approach choice

| Option | Summary | Trade-off |
|--------|---------|-----------|
| **A (chosen)** | One `mission` argument. The default stays thrust and grams per watt. Three presets share the same trial loop | One optimizer. Existing studies keep their directions and study name |
| B | Ship `quiet_thrust` only | Endurance and range would become a second pass through the same loop |
| C | A new optimizer module | The roadmap forbids a second optimizer that can disagree with the first |

## Physics

Static performance is `analyze` at `spec.rpm_max` and `v_forward=0`. That point supplies thrust, shaft power, grams per watt, figure of merit, and noise.

Hover minutes are `hover_power_budget(..., shaft_power_w=static.power_w, battery_wh=battery_wh).hover_minutes`. The budget already converts shaft power, rotor count, electrical efficiency 0.70, and an 80% usable pack into minutes. Passing `shaft_power_w` selects the `bemt_shaft` model.

Range is the same conversion at cruise shaft power, turned into distance:

`range_km = cruise_mps * minutes * 0.06`

That is cruise speed in metres per second times endurance in hours, expressed in kilometres. It is a screening range at `rpm_max`, not a flight polar and not a CFD result.

The quiet floor compares that static hover-minutes number with `min_hover_minutes`. Omit the floor and quiet thrust has no endurance constraint.

`max_power_w`, when set, compares the static shaft power. It does not watch cruise power.

## Architecture

| Piece | Change |
|-------|--------|
| `fansim/propeller/optimize.py` | `run_prop_study` gains `mission`, `all_up_weight_n`, `n_rotors`, `battery_wh`, `cruise_mps`, and `min_hover_minutes`. One objective closure computes the static point, optional cruise point, constraints, noise, and the two return values. Infeasible trials set `feasible=False` |
| `fansim/propeller/persist.py` | `pareto_rows_from_study` reads the physical fields from user attributes and drops `feasible is False`. Fallback to `values[0]` / `values[1]` only when `thrust_g` was not stored |
| `tests/test_prop_optimize.py` | Missions, validation errors, empty floor, and a lifting endurance/range front |
| `docs/roadmap.md` | One sentence under §14.7. The checkbox stays open |

`save_prop_pareto` already writes the row dict through, so the new keys ride along. Do not add a parallel row builder inside `run_prop_study`.

Directions and study names:

| mission | directions | study name | objectives returned |
|---------|------------|------------|---------------------|
| `thrust_efficiency` | maximize, maximize | `prop` | `thrust_g`, `eff_g_per_w` |
| `quiet_thrust` | maximize, minimize | `prop_quiet_thrust` | `thrust_g`, `rel_dba` |
| `hover_endurance` | maximize, maximize | `prop_hover_endurance` | `hover_minutes`, `thrust_g` |
| `range` | maximize, maximize | `prop_range` | `range_km`, `thrust_g` |

## Error handling

`ValueError` for an unknown mission, a vehicle input the mission requires, a non-positive required input, or `min_hover_minutes` on a mission other than `quiet_thrust`. No new exception type.

An infeasible trial does not raise. It returns the worst objective pair from criterion 6 and is left off the front.

## Testing

CI only. No Docker. New mission tests use a small trial count (40 or fewer) and a fixed seed. Do not weaken `test_pareto_is_populated_and_ordered`, `test_power_cap_is_respected`, or `test_designs_are_physically_sane`.
