# Prop power budget + optional PyThrust matching (Track A, stage 1)

**Date:** 2026-09-21  
**Status:** approved (2026-09-21)  
**Approach:** Add a **thin, optional** electrical / hover-power layer for drone props. Keep
`fansim` BEMT as the geometry→aero screen. Soft-depend on **PyThrust**
(`setuav-pythrust==0.2.3`, Apache-2.0) for motor–prop–battery operating points against
**empirical CT/CP catalogs** (bundled APC). Do not put PyThrust inside Optuna or CFD.
Treat external tools and measured catalogs as a **quorum of witnesses** that our formulas
and process are correct — not as a second production BEMT to maintain.
**Roadmap:** Track A research (efficiency / power); complements §4.3 CFD, does not replace it.

## Plain language

We already report BEMT thrust, g/W, and figure of merit. What drone builders actually ask next
is: *how many watts from the pack*, *will this motor pull too much current*, and *roughly how
long will it hover*. PyThrust already solves the Drela-style motor + catalog-prop equilibrium
and ships APC tables. Stage 1 wires that in behind an adapter (so we can pin / swap / degrade
gracefully) and adds a pure-fansim hover watt/Wh estimate that works **without** the extra for
custom blades.

Separately: we will **not** rewrite BEMT, FoM, or motor math “just because another repo has
it.” We **will** run a small set of independent checks so that when our numbers look sane, that
is because multiple trusted sources agree — a quorum, not a duplicate codebase.

## Goal

### 1. Optional dependency

- Add `pyproject.toml` extra: `propulsion = ["setuav-pythrust==0.2.3"]` (exact pin).
- Core install / CI default **must not** require PyThrust.
- Import only inside adapter functions; never at top of `bemt.py` / `cfd.py` / cockpit package init.
- Helper: `fansim.propeller.power.pythrust_available() -> bool`.

### 2. Adapter module — `fansim/propeller/power.py`

Public, stable surface (ours), mapping to PyThrust when present:

| API | Behavior |
|-----|----------|
| `pythrust_available()` | `True` if import succeeds |
| `list_catalog_props(*, manufacturer="APC")` | IDs / size hints from bundled DB; empty + clear error if unavailable |
| `find_catalog_prop(diameter_in, pitch_in, *, blade_count=2)` | Closest catalog entry metadata |
| `solve_catalog_operating_point(...)` | Motor + battery + throttle + airspeed → operating-point dict |
| `hover_power_budget(...)` | **Always available** (no PyThrust): AUW → per-rotor thrust → shaft/elec power → minutes |

**`solve_catalog_operating_point` inputs (minimum):**

- Motor: `kv_rpm_per_v`, `resistance_ohm`, `no_load_current_a`, `current_max_a`
- Battery: fixed pack voltage (stage 1); rate-map batteries deferred
- System: `resistance_ohm` (ESC/wiring lump; default `0.02`)
- Prop: catalog id **or** diameter_in + pitch_in lookup
- Condition: `throttle` (0–1), `airspeed_mps` (0 = hover), `rho` (default 1.225)

**Result dict (stamps required):**

```text
rpm, thrust_n, thrust_g, torque_nm,
shaft_power_w, motor_power_w, battery_power_w,
motor_current_a, battery_current_a,
motor_efficiency, is_feasible, infeasible_reason,
source="pythrust", pythrust_version="0.2.3",
prop_id, throttle, airspeed_mps
```

If PyThrust missing → raise `PropulsionExtraMissing` with install hint  
(`uv sync --extra propulsion` / `uv add --optional …`). Do **not** silently fake numbers.

### 3. Hover power budget (A1 — no extra required)

`hover_power_budget(*, all_up_weight_n, n_rotors, tip_radius_m, figure_of_merit, *, eta_elec=0.70, battery_wh=None, usable_frac=0.8) -> dict`

Physics (document in docstring):

1. Per-rotor thrust `T = W / n_rotors` (hover).
2. Ideal induced power `P_i = T^{1.5} / sqrt(2 ρ A)` with `A = π R²`.
3. Shaft power `P_shaft = P_i / FM` (clamp FM to `(0.05, 1.0)`).
4. Electrical `P_elec = P_shaft / η_elec` (default 0.70 — NASA Ames small-ESC ballpark; stamp the assumption).
5. If `battery_wh` given: `hover_minutes = 60 * battery_wh * usable_frac / P_elec_total`.

Also accept optional override: pass `shaft_power_w` from BEMT/`analyze` instead of FoM-based ideal when evaluating a **designed** blade at a known RPM/thrust (document which path was used via `power_model="momentum_fm" | "bemt_shaft"`).

### 4. CLI smoke

`scripts/evaluate_prop_power.py`:

- `--mode catalog` — requires extra; `--prop-id` or `--dia-in`/`--pitch-in`; motor/battery knobs; prints JSON.
- `--mode hover-budget` — always works; AUW / rotors / R / FM / optional Wh.
- `--dry-run` for catalog = resolve prop id + print inputs without solve (still needs extra to list DB).

### 5. Cockpit (minimal)

On Prop Analyze readout, **if** `pythrust_available()`:

- One line: “Catalog match available (extra propulsion)” with optional small panel later.

Stage 1 does **not** require a full motor picker UI — CLI + library API first. Cockpit may call `hover_power_budget` using current BEMT FoM + user AUW/Wh fields if those widgets already exist or are cheap to add; otherwise defer UI to stage 1.1 and ship CLI only.

**Decision for stage 1:** CLI + library + unit tests. Cockpit hover-budget fields only if a Prop tab AUW/Wh input already fits in &lt;1 hour; otherwise explicitly out of stage 1.

### 6. Tests

| Test | Extra? |
|------|--------|
| `hover_power_budget` FoM path finite, minutes scale with Wh | No |
| `hover_power_budget` bemt_shaft override path | No |
| `pythrust_available` False path / missing raises | No (monkeypatch import) |
| Catalog solve smoke APC 5×4.5E-class point feasible | **Yes** — mark `@pytest.mark.propulsion` and skip if extra absent |
| CLI declares `--mode` flags | No |

CI default stays green without the extra. Optional job or local `uv run --extra propulsion pytest -m propulsion` documented in the plan.

### 7. Quorum / cross-check (correctness without duplication)

**Intent:** Keep a single production implementation of each method inside `fansim`. Use other
software, papers, and measured tables as **independent witnesses**. If witnesses disagree with
us beyond a stated band, we investigate and fix *our* code (or document a known bias) — we do
not average sources or ship a second BEMT.

**Rule of thumb**

| Do | Do not |
|----|--------|
| Compare outputs on the same inputs | Copy a second BEMT/motor solver into the tree |
| Pin witness versions and cite them | Silently trust a single number |
| Fail or warn on quorum breach in tests | “Blend” fansim and PyThrust results for users |
| Prefer measured catalogs (UIUC/APC) as ground | Treat another simulation as gospel |

**Quorum members (stage 1)**

| ID | Witness | What it checks | When |
|----|---------|----------------|------|
| Q1 | Analytic identity | Our FoM definition: `FM = T^{3/2} / (P √(2ρA))` rearranges consistently with `hover_power_budget` | Always (unit test, no extra) |
| Q2 | Drela / literature motor equations | Documented mapping: adapter inputs ↔ Drela first-order motor model (Kv, Ri, I0) | Spec + docstring audit; link bib |
| Q3 | PyThrust catalog solve | Same motor + APC prop + throttle → our adapter fields match PyThrust native fields 1:1 (wrapper integrity) | `@pytest.mark.propulsion` |
| Q4 | Momentum vs catalog static power | At a fixed hover thrust T from APC static CT/CP at a chosen RPM: `P_i/FM_catalog` vs catalog shaft power — band check on *process*, using catalog FM | `@pytest.mark.propulsion` |
| Q5 | UIUC / APC static table (fixture) | One frozen prop (e.g. APC 5×4.5E or UIUC static row): CT₀/CP₀ at J=0 within literature-typical band of our BEMT *only if* we have matching geometry; otherwise compare **catalog-only** FoM sanity (0.5–0.8) and stamp “geometry not matched” | Stage 1: catalog FoM sanity; full BEMT-vs-UIUC = **A3** |

**Stage 1 pass bands (honest, not datasheet-tight)**

| Check | Pass if |
|-------|---------|
| Q1 | Relative error &lt; 1e-9 on rearrangement |
| Q3 | Field-wise equality within float tolerance (adapter must not mutate physics) |
| Q4 | Catalog-derived `P_shaft` and `P_i / FM` agree within **±15%** at the chosen static point (momentum idealization + table noise) |
| Q5 (stage 1) | Catalog static FoM in **[0.50, 0.85]** for the chosen APC hover-ish RPM; outside → fail with diagnostic |

**On quorum failure**

1. Test fails with which witness disagreed and by how much.  
2. Do **not** auto-switch the product to the witness’s number.  
3. Triage: math bug vs wrong inputs vs known model limit → fix or widen band with a written note in the test docstring / honesty section.

**CLI**

`scripts/evaluate_prop_power.py --mode quorum` (requires extra for Q3–Q5): runs the stage-1
checks, prints a small JSON report (`pass` / `fail` per ID, deltas). Useful for humans; CI uses
pytest.

**Later quorum (not stage 1, but reserved)**

- **A3:** BEMT vs UIUC CT/CP for a digitized or approximate geometry (tighter band once geometry match is honest).  
- Optional third witness: `qprop.c` or Drela QPROP on one frozen case (method check only; GPL Fortran not vendored).  
- CFD thrust/power vs BEMT on the same STL (already §4.3 spirit) as a high-cost witness.

## Non-goals

- Replacing BEMT or compressible prop CFD  
- Maintaining a fork of PyThrust / qprop / SizingLab as a parallel production path  
- OpenMDAO co-design / motor database search UI (PyThrust can do this later)  
- Rate-map / Peukert battery discharge (A4)  
- Exporting custom-blade CT/CP into PyThrust CSV (bridge = stage 2)  
- Absolute datasheet claim vs Gemfan/HQ  
- Hard dependency on PyThrust for any existing prop Analyze / Optimize path  
- Averaging or voting at runtime to produce user-facing “consensus” numbers  

## Architecture

```text
PropSpec / BladeParams ──► BEMT (fansim) ──► thrust, FoM, P_shaft
                                    │
                                    ▼
                         hover_power_budget() ──► Wh / minutes
                                    │
COTS dia×pitch / prop_id ──► power adapter ──► PyThrust (optional)
                                    │
                                    ▼
                         solve_catalog_operating_point()
                                    │
                                    ▼
                         rpm, I, P_batt, feasibility

Quorum (tests / --mode quorum):
  fansim math  ←→  analytic identity (Q1)
  adapter      ←→  PyThrust native (Q3)
  momentum_fm  ←→  APC catalog static (Q4–Q5)
  [later] BEMT ←→  UIUC / qprop / CFD
```

Adapter isolates PyThrust API churn. Pin `==0.2.3`. If upstream breaks, we bump pin or vendor formulas later without rewriting cockpit/CLI.

## Honesty

- Catalog aero ≠ lofted geometry. Stamp `source=pythrust` and `prop_id`.  
- Default `η_elec=0.70` is a **placeholder** until calibrator / stand data; stamp it on every budget result.  
- Single-maintainer upstream: pin + adapter + skip-when-missing are the risk controls.  
- Hover minutes ignore avionics draw and reserve; label as “propulsion-only estimate”.  
- Quorum bands are **process confidence**, not marketing accuracy. Passing Q4/Q5 does not mean
  a custom lofted prop will match a Gemfan datasheet.

## Defaults

| Knob | Default |
|------|---------|
| Extra pin | `setuav-pythrust==0.2.3` |
| `eta_elec` | 0.70 |
| `usable_frac` | 0.80 |
| `system.resistance_ohm` | 0.02 |
| Catalog | APC from PyThrust bundled `apc_202602` |
| Stage 1 UI | CLI first |
| Q4 band | ±15% |
| Q5 FoM window | 0.50–0.85 |

## Done when

- Spec reviewed / approved  
- Implementation plan written (`docs/superpowers/plans/…`)  
- Extra + adapter + hover budget + CLI + tests as above  
- Quorum Q1 always in CI; Q3–Q5 behind `@pytest.mark.propulsion` + `--mode quorum`  
- Research canvas Track A slices A1–A2 marked “specced”  
- Bibliography note: PyThrust + Drela motor model + UIUC PropDB links under prop power  

## Follow-ons (explicitly later)

- **A3** UIUC CT/CP harness vs BEMT (geometry-honest quorum)  
- **A4** endurance integral / rate-map battery  
- **Stage 2** BEMT → CT/CP table export for custom props in PyThrust  
- Cockpit motor/prop catalog picker  
- Optional third-witness smoke (`qprop.c`) if license/use stays clean  
