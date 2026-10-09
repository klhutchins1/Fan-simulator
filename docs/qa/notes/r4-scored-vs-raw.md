# Round 4, request 3: scored vs raw, recomputed by hand (stock, t9005, bem_9504)

Pre-registration: `r4-prereg-axial-crosscheck-eff-audit.md` (sha256 `1252f73f…acaf`). Input `cfd_designs.csv`, sha256 `cb8955e9…ae624`.
Script: `handoff/2026-10-09_from-qa-3/scripts/scored_vs_raw.py`; output in `results/scored_vs_raw.json`.

**Verdict (plain language):** every scored number can be explained by the documented code steps, and the implied hidden values are
plausible. But **none of the three can be reproduced from the CSV alone**. Each needs at least one raw CFD value the CSV doesn't carry:
- the CFD torque, which sets the motor derate;
- the free-delivery residual static pressure;
- the free and probe η.

Several of the steps are documented only in code comments or `docs/roadmap.md`, nowhere a user would look.

## Steps the code applies (objectives.py → system_curve.py → print_penalty.py)
1. **Motor derate:** λ = min(1, (budget / max(shaft_free, shaft_probe))^⅓), with budget = 12 V × 0.14 A × 0.40 = 0.672 W. Flow is scaled ×λ and pressure ×λ².
2. **Free endpoint:** p_free = the measured CFD residual static pressure at zero back-pressure × λ² (*not* 0, unlike the BEM).
3. **Load:** the straight fan line (Q_free·λ, p_free) – (Q_probe·λ, 8λ²) intersected with ΔP = kQ², where k = 8 Pa at 50 CFM. The line is
   **extrapolated past the probe** when the op is at lower flow than the probe (t > 1).
4. **η:** linear in flow between η_free and η_probe, clamped at η_probe when t > 1. η does not change with the derate.
5. **Print:** CFM × 0.95 × k_fsi; η × k_eta.
   - k_fsi = max(0.90, 1 − 0.5·deflection/gap).
   - k_eta = 0.92 → 0.96, scaled with tip t/c between 0.04 and 0.10.

## Hand numbers
| | stock | t9005 | bem_9504 |
|---|---|---|---|
| raw free / probe CFM | 54.794 / 41.75 | 74.021 / 59.468 | 67.652 / 54.654 |
| tip t/c → k_eta | 0.0727 → 0.9418 | 0.0379 → 0.9200 | 0.0681 → 0.9388 |
| tip deflection / gap → k_fsi | 0.0007 / 0.50 mm → 0.9993 | 0.0032 / 0.50 → 0.9968 | 0.0010 / 0.53 → 0.9990 |
| **implied derate λ** (from scored_free) | **0.9537** (1,907 rpm) | **0.9391** (1,878 rpm) | **0.9341** (1,868 rpm) |
| implied CFD shaft power at rated rpm | 0.775 W | 0.811 W | 0.825 W |
| scored_free: hand = raw × λ × 0.95 × k_fsi | 49.611 = 49.611 (by construction) | 65.822 | 59.976 |
| scored_load, hand with p_free = 0 | 40.27 vs **40.698** (−1.1 %) ✗ | 49.67 vs **48.646** (+2.1 %) ✗ | 47.01 vs **46.621** (+0.8 %) ✗ |
| implied p_free (rated rpm) that reproduces it | 1.74 Pa | 3.18 Pa | 2.66 Pa |
| op position t (0 = free, 1 = probe) | 0.755 (interpolated) | **1.33 (extrapolated past probe)** | **1.16 (extrapolated)** |
| scored_eff ÷ k_eta = raw η at op | 18.99 % | 34.76 % (= η_probe, clamped) | 30.44 % (= η_probe, clamped) |

All implied values pass the pre-registered plausibility test (0.80 ≤ λ ≤ 1, 0 ≤ p_free < 8λ²), so they are **consistent but not reproducible from the CSV**.
To make the table reproducible, add these columns to the CSV / `result.json` export:
- `shaft_power_rated_w` (already in `raw`);
- `derate`;
- `p_free_pa`;
- `eta_free`, `eta_load`;
- `print_k_cfm`, `print_k_eta`.

The cockpit's `raw` stamps already hold most of these.

## Undocumented steps (where a user could not find them)
| step | where it is documented | flag |
|---|---|---|
| print knockdown (CFM × 0.95, η × 0.92–0.96) | `print_penalty.py` docstring, `docs/roadmap.md` §7.6 | **not in README or cockpit help.** Users see 49.6 CFM for a 54.8 CFM CFD run with no hint why |
| FSI tip factor k_fsi | code plus roadmap only | tiny here (≤ 0.3 %) but undocumented |
| motor derate, and the **assumed 0.40 motor efficiency** behind the 0.672 W budget | roadmap §12.0f; "motor-limited: N RPM" note in the result `reason` (I didn't check the UI) | **all three rows are derated 5–7 %, Stock included**, even though a real A12x25 holds 2000 rpm. The 0.40 isn't stated anywhere a user reads |
| free endpoint uses the measured residual static (not 0) | code comment in `objectives.py` | undocumented. It moves load CFM by 1–2 % |
| fan line **extrapolated** past the probe (t > 1) | none | **undocumented.** For the two best designs, load CFM is an extrapolation, not between measured points |
| η linear in flow, clamped at the probe | none | **undocumented.** It biases scored η against designs whose op falls between free and probe (Stock), see request 2 |
| "load is estimated from two points" | cockpit tooltip for `assess_refine_op` | partially documented |
