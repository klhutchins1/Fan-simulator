# Prop forward-flight solver vs published data (roadmap §23.18 / UI-5), 2026-10-09

**Verdict: worth-it/proposed.**
- The thrust and power solver is basically right. The 2087 g / 743 W on the PROP tab is what a
  3-blade 5" prop really does at the **30,000 rpm** the tab assumes; APC's own published numbers
  for similar props bracket it.
- There is one real bug, and it is in the forward-flight polar: the efficiency formula divides by
  an extra 2π. Every η the PROP tab prints for V∞ > 0 is therefore **6.3× too low** (about 6 %
  where it should be about 35 %).
- The J = 0 row showing "η = —" is correct, because efficiency is undefined when the prop is
  standing still.
- A secondary weakness: the static thrust coefficient creeps up with rpm (+60 % from 4k to 30k
  rpm), while the measurements are flat. The absolute static number at 30k rpm still lands
  inside the APC band. No patch for this one yet.

## Where things are
- Solver: `fansim/propeller/bemt.py` `analyze()`.
- Polar / non-dimensionalisation: `fansim/propeller/polar.py` `nondim()` and `run_bemt_polar()`.
- Cockpit: `fansim/cockpit/prop_tab.py`.
  - The default preset is `state.prop_model = "fpv_5inch"` (l.173).
  - Analyze runs `bemt_analyze(params, rpm=spec.rpm_max)` (l.448/510).
  - The polar line is built at l.472–476.
- Preset `fpv_5inch` (`fansim/prop_spec.py` l.82):
  - 5×4.3, 3 blades, rpm_max 30,000, hub Ø 12 mm.
  - Chord 0.20 / 0.26 / 0.10 R, 4 % camber, twist from pitch.
  - Its own "typical" figures are 1850 g / 650 W @ 30k.

## Data used (in `/workspace/fansim/research/prop_data/`)
- **UIUC Propeller Database**, full archive
  https://m-selig.ae.illinois.edu/props/download/UIUC-propDB.zip (md5 a41e484f…, matches the site).
  - Extracted to `uiuc/`: geometry, static and J-sweep files for:
    - GWS Direct-Drive 5×4.3 (2 blades), files gwsdd_5x4.3_*: same diameter and pitch as the
      preset;
    - DA4022 5×3.75 with 2 and 3 blades;
    - DA4002 5×4.92;
    - APC FF 4.2×4.
  - Each file's URL is https://m-selig.ae.illinois.edu/props/volume-2/data/<file>.
- **APC PER3 performance files** (APC's own vortex-theory predictions, not measurements), in `apc/`:
  - https://www.apcprop.com/files/PER3_5x4E-3.dat (3 blades);
  - https://www.apcprop.com/files/PER3_5x37E-3.dat (3 blades);
  - https://www.apcprop.com/files/PER3_5x43E.dat;
  - https://www.apcprop.com/files/PER3_5x45E.dat;
  - https://www.apcprop.com/files/PER3_51x50E-3.dat.
  - APC's header states `Pe = Ct*J/Cp` with `Cp = P/(rho n^3 D^5)`, which confirms the η formula.

## Results
Scripts: `proto/prop/validate.py`, `static_plot.py`, `preset.py`, `re_effect.py`, `apc.py`.
JSON: `prop_data/results_master.json` and `results_fixed.json`.

**Matched geometry vs UIUC measurements** (camber assumed 4 %; the real airfoils are unknown or DA4022):

| prop | static CT0 BEMT / meas. | static CP0 BEMT / meas. | J-sweep CT rms | peak η meas. | BEMT T·V/P | polar η printed (old) |
|---|---|---|---|---|---|---|
| GWS 5×4.3 2b @ 7.4k | 0.142 / 0.149 (−5 %) | 0.064 / 0.075 (−14 %) | 0.009–0.014 | 0.65 @ J 0.57 | 0.60 | **0.097** |
| DA4022 5×3.75 2b @ 6.9k | 0.160 / 0.152 (+5 %) | 0.084 / 0.092 (−9 %) | 0.023–0.030 | 0.64 | 0.63–0.68 | 0.10 |
| DA4022 5×3.75 3b @ 6.6k | 0.228 / 0.211 (+8 %) | 0.133 / 0.133 (0 %) | 0.030–0.034 | 0.62 | 0.59 | 0.095 |

**Cockpit preset at 30,000 rpm, static:** BEMT gives 2087 g / 743 W (CT0 0.257, CP0 0.147). APC
publishes these for 3-blade 5" props at 30k:
- 5×3.7E-3: 1849 g / 599 W;
- 5×4E-3: 2256 g / 817 W.

So the preset sits inside the band. It is +13 % against the preset's own "typical" 1850 g. Real
loaded 6S motors seldom hold 30k rpm on a 3-blade; at 27k the same model gives about 1690 g.

**Forward flight at 30k rpm** (preset vs APC 5×4E-3 / 5×3.7E-3):

| J | η after the fix | η printed today | APC 5×4E-3 / 5×3.7E-3 |
|---|---|---|---|
| 0.16 | 0.25 | 0.04 | 0.26 / 0.26 |
| 0.24 | 0.35 | 0.06 | 0.34 / 0.39 |
| 0.31 | 0.44 | 0.07 | 0.42 / 0.46 |

Plots:
- `prop_data/bemt_vs_uiuc_master.png`: CT/CP/η vs J. The red dashed line is the old printed η.
- `prop_data/bemt_vs_uiuc_fixed.png`: the same after the fix.
- `prop_data/static_ct_cp_vs_rpm.png`: static CT0/CP0 vs rpm for UIUC, APC, BEMT and the preset.

## Candidate causes checked
| candidate | result |
|---|---|
| units (rpm→rad/s, mm→m, g vs N) | OK: `bemt.py:132-134` (ω = rpm·2π/60, mm/1000) and `:203` (g = T/9.80665·1000) |
| cockpit rpm default | Uses `rpm_max` = 30,000 (the top of the band). This is plausible thrust for that rpm, but the label should make clear it is full-rpm static, not a typical loaded number. A UI wording suggestion, not patched. |
| CT/CP normalisation | OK: CT = T/(ρn²D⁴), CP = P/(ρn³D⁵) with n in rev/s (`polar.py:97-98`) |
| **η formula** | **BUG, `fansim/propeller/polar.py:99`**: `eta = j*ct/(2π*cp)`, which should be `j*ct/cp`. The 2π belongs to the ω-based C_Q form. η is 1/2π = 15.9 % of the true value. The bug is locked in by `tests/test_prop_polar.py:43`, and it also feeds the PyThrust export's η column (`pythrust_export.py:85`). |
| J = 0 handling | Correct. η is None at J = 0, and the tab prints "—". |
| tip-loss sign | OK. F is in [0.15, 1] and multiplies the momentum term; matched-geometry CT error is −5 to +8 %. |
| induced-velocity solve | OK. It converges, and the J-sweep CT rms is 0.009–0.034. |
| polar / Reynolds | **Weakness, not patched.** CT0 rises with rpm in BEMT (preset 0.158 → 0.257 from 4k to 30k; matched UIUC props +15–30 % over 1.5k–7k), while the measurements and APC are flat to within a few %. Two causes: `polars.py:151` returns None below the lowest table Re (4e4), so low-rpm sections fall back to the analytic polar; and the e387 tables gain a lot of cl_max from 4e4 to 1.6e5. Mach adds +6 % at 30k (`_compressibility_cl_cd`). |
| minor | `analyze` rounds power to 0.1 W (`bemt.py:202`), so tiny props at low rpm get CP0 = 0 (GWS at 1530 rpm). |

## Fix (patch `patches/prop-solver-fix.diff`)
- `polar.py:99`: η = J·CT/CP (= T·V/P), and the docstring is fixed.
- `tests/test_prop_polar.py`:
  - The identity test is corrected.
  - New: the BEMT polar η at the GWS 5×4.3 UIUC point (6047 rpm, J 0.572, measured η 0.646) must
    match within **±0.10 absolute**. With the fix it gives 0.608; the old code gives 0.097 and
    fails.
  - New: static CT0 within ±15 % of the UIUC value at 7407 rpm. It gives 0.142 against 0.149.
- Checks:
  - Verified that both new η assertions fail on master and pass with the patch.
  - `git apply --check` is clean on a fresh bundle clone.
  - test_prop_polar, test_bemt, test_propeller, test_pythrust_export_propulsion and
    test_prop_reference_line all pass (30 passed, 1 skipped).
- Not in the patch (follow-ups):
  - Fix the rpm creep in CT0: use table extrapolation or a gentler blend below Re 4e4.
  - Relabel the PROP headline as "@ 30,000 rpm (max), static".
  - Regenerate any PyThrust exports, since their η column was 2π low.
