# §14.7 cockpit: mission control and mission plots

**Date:** 2026-09-23  
**Status:** approved in chat (2026-09-23); written spec awaiting review  
**Approach:** A — one mission select on the existing Optimize button, two new figures  
**Parent:** roadmap §14.7 (checkbox stays open until this slice lands, then it is checked)  
**Related:** `fansim/cockpit/prop_tab.py`, `fansim/cockpit/figures.py` (`prop_scatter_figure`), `fansim/propeller/optimize.py` (`run_prop_study`)

## Plain language

The search can already run as quiet thrust, hover endurance, or range. The cockpit still always asks for thrust and grams per watt, and it always draws thrust against noise. This slice adds a mission choice to Optimize and draws minutes or kilometres when that is what was optimized.

## Goal

1. Optimize sends `mission` and the vehicle fields into the existing `run_prop_study`. The default mission stays `thrust_efficiency`.
2. `thrust_efficiency` and `quiet_thrust` keep the current thrust-versus-noise figure.
3. `hover_endurance` plots hover minutes against thrust. `range` plots kilometres against thrust. Hover text on those points includes the relative noise score and shaft power.
4. After this slice, roadmap §14.7 is checked.

## Success criteria

| # | Criterion |
|---|-----------|
| 1 | The prop tab has a mission select with `thrust_efficiency`, `quiet_thrust`, `hover_endurance`, and `range`. The stored default is `thrust_efficiency` |
| 2 | Visible fields: all-up weight in newtons, rotor count, battery watt-hours, cruise speed in metres per second, and an optional minimum hover minutes. Defaults are 5 N, 4 rotors, 50 Wh, 15 m/s, and a blank minutes floor |
| 3 | `thrust_efficiency` calls `run_prop_study` with only the mission (plus the power cap and trial count it already passes). It does not send `min_hover_minutes` |
| 4 | `quiet_thrust` sends `min_hover_minutes` only when the field is a positive number. A blank floor is omitted. When the floor is set, it also sends the weight, rotor count, and battery |
| 5 | `hover_endurance` sends `all_up_weight_n`, `n_rotors`, and `battery_wh`. `range` sends those plus `cruise_mps`. A non-positive required field shows the `ValueError` text in `prop_msg` and does not start a study |
| 6 | Resume stays available for `thrust_efficiency` only. Any other mission always writes a new run directory, so a resumed `prop` study is not reopened under different directions |
| 7 | `prop_scatter_figure` is unchanged and is used when the selected mission is `thrust_efficiency` or `quiet_thrust`, including rows whose `mission` key is missing |
| 8 | `prop_mission_figure(pareto, user_points, y_key, y_title)` plots `thrust_g` on x and `y_key` (`hover_minutes` or `range_km`) on y. Marker color is `eff_g_per_w`. Hover text includes `rel_dba` and `power_w`. `customdata` is the row index in the same study-then-user order as `prop_scatter_figure`. Rows missing `y_key` are omitted |
| 9 | The prop tab calls `prop_mission_figure` for `hover_endurance` (`hover_minutes`, axis title `hover (min)`) and `range` (`range_km`, axis title `range (km)`) |
| 10 | A figure test builds both y keys from two-row inputs and checks the trace x, y, and hover text. Existing `test_prop_scatter_figure_accepts_user_points` still passes |
| 11 | Roadmap §14.7 is checked and points at this spec and `docs/superpowers/plans/2026-09-23-prop-mission-cockpit.md` |

## Non-goals

- A second optimizer or a change to mission physics, noise, or `hover_power_budget`
- Absolute dB(A)
- Changing the CROR or mixed-flow plots
- Searching weight, rotor count, or battery size
- A new Analyze path. Analyze points stay on the thrust-noise figure

## Approach choice

| Option | Summary | Trade-off |
|--------|---------|-----------|
| **A (chosen)** | One select, the existing Optimize button, and one extra figure function for the two new y axes | Quiet thrust keeps the plot the cockpit already has |
| B | Three separate Optimize buttons | Three ways to start the same study |
| C | Always plot thrust versus noise and put minutes in the hover text only | Endurance and range would not show the quantity that was optimized |

## Architecture

| Piece | Change |
|-------|--------|
| `fansim/cockpit/figures.py` | Add `prop_mission_figure`. Leave `prop_scatter_figure` as it is |
| `fansim/cockpit/prop_tab.py` | Mission select and the five fields. `run_prop_study` keyword arguments follow the mission. `_refresh_prop_figure` picks the figure from the selected mission |
| `tests/test_prop_persist.py` | Figure test for minutes and kilometres |
| `docs/roadmap.md` | Check §14.7 |

The select labels are the mission ids: `thrust_efficiency`, `quiet_thrust`, `hover_endurance`, `range`. No second name for the same mission.

## Error handling

`run_prop_study` already raises `ValueError` for a bad vehicle input. The existing Optimize `except` writes that into `prop_msg`. Do not add a second error path. Client-side, a non-positive required number is treated as missing and the call is not made; `prop_msg` names the field.

## Testing

CI only. No Docker. No browser pass is required for the figure test. The figure test does not start Trame.
