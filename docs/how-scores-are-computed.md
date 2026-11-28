# How a design's scores are computed

The cockpit shows three numbers per assessed design: **free CFM**, **load CFM** and **efficiency (η)**.
They are not raw CFD output. Five documented steps turn the CFD result into the score, so a design
that the CFD measured at 54.8 CFM can show **49.6 CFM**. This page lists every step so you can
reproduce a score by hand. Example numbers below are the Stock A12x25 recipe (Assess, 2026-10-09).

`scripts/export_cfd_dataset.py` writes every value used here into one CSV row per design.

## 1. Two CFD solves at the design speed

The CFD runs the fan twice at its rated speed (A12x25: 2000 rpm):

| solve | back-pressure | Stock result |
|---|---|---|
| **free** | none (open duct) | 54.79 CFM; the duct still reads a small residual static rise, 1.74 Pa |
| **probe** | 8 Pa (the "case" load preset) | 41.75 CFM |

Each solve also gives the shaft torque. That gives the shaft power and the raw efficiency
η = air power ÷ shaft power.

> **Note (`CFD_VERSION = 7`, #86):** The 2026-10-09 Stock walkthrough numbers above were scored
> under `CFD_VERSION = 6` duct static-to-static pressure rise `(p_out - p_in) * rho` (which left
> `1.74 Pa` and `6.9 %` static efficiency at free delivery from inlet dynamic head). From
> `CFD_VERSION = 7`, `static_pressure_rise_pa` reports AMCA 210 / ISO 5801 fan static pressure
> `P_s = p_s2 - p_t1` (`0 Pa` and `0 %` static η at free delivery, `8 Pa` at the 8 Pa probe),
> so both endpoints of the fan line share the same pressure convention.

## 2. Motor power limit (derate)

A real fan motor can only deliver so much shaft power. The budget is
**12 V × rated current × motor efficiency**. For the A12x25 that is 12 V × 0.14 A × **0.40** =
0.672 W. If the design needs more than that at full speed (Stock needs 0.775 W), the motor can't
reach full speed. The speed is scaled down by the cube-root rule:

    derate λ = min(1, (budget / shaft power at rated speed)^(1/3))      Stock: λ = 0.954 → 1907 rpm

Flow scales with λ and pressure with λ². Efficiency does not change.

**Assumption to know about:** the 0.40 motor efficiency is a placeholder, not a measurement. With
it, even Stock is derated by about 5 %, although a real A12x25 holds 2000 rpm. The derate is
applied the same way to every design, so it shifts all scores together rather than reordering
them.

## 3. Load CFM: where the fan line meets the case

The fan's pressure–flow line is drawn through the two derated points: (free CFM × λ, residual
pressure × λ²) and (probe CFM × λ, 8 Pa × λ²). The case is modelled as a hose curve ΔP = k·Q², with
k set so the case gives 8 Pa at 50 CFM. **Load CFM** is where the two cross.

- For most designs the crossing lies between the two measured points.
- For strong designs it can lie *beyond* the probe point (lower flow, higher pressure). The line
  is then **extrapolated** past the last CFD point. That is less certain than interpolation. The
  best designs so far (t9005, bem_9504) are in this case.
- Assess has an option ("refine the operating point") that runs a third CFD solve at the
  crossing instead of relying on the line.

## 4. Efficiency at the operating point

The efficiency shown is η at the load operating point. It is taken **linearly in flow** between
η_free and η_probe, and held at η_probe when the crossing lies past the probe. This is an estimate
between two measured points, not a third measurement. Stock's crossing sits 75 % of the way from
free to probe, so its η at the operating point (19.0 % before step 5) comes from that
interpolation.

## 5. Printed-part knockdown

A printed blade is rougher and less exact than the smooth CFD surface:

| factor | value | applied to |
|---|---|---|
| print_k_cfm | 0.95 × a small tip-flex factor (0.90–1.00; Stock 0.9993) | free and load CFM |
| print_k_eta | 0.92 (thin tips) → 0.96 (thick tips, t/c ≥ 0.10); Stock 0.942 | η |

Source and reasoning: `fansim/optimize/print_penalty.py`.

## Putting Stock together

    free  = 54.79 CFM × λ 0.954 × 0.95 × 0.9993              = 49.6 CFM
    load  = fan line ∩ case curve, derated, × 0.95 × 0.9993  = 40.7 CFM
    η     = 18.99 % (at the op, interpolated) × 0.942        = 17.9 %

## Where to check each value

| CSV column | meaning |
|---|---|
| `cfd_free_cfm`, `cfd_load_cfm` | raw CFD flow of the free and probe solves |
| `shaft_power_rated_w` | shaft power at rated speed (sets the derate) |
| `derate`, `actual_rpm` | step 2 |
| `p_free_pa`, `p_probe_pa` | the fan-line end points after derate (step 3) |
| `eta_free_pct`, `eta_load_pct` | raw η of the two solves (step 4) |
| `print_k_cfm`, `print_k_eta`, `print_k_fsi` | step 5 |
| `scored_free`, `scored_load`, `scored_eff` | what the cockpit shows |

Numbers come from `fansim/optimize/objectives.py` (steps 1–4), `fansim/optimize/system_curve.py` (the
fan line and hose curve) and `fansim/optimize/print_penalty.py` (step 5).
