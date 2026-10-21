# Round 18, Task A (R1.8 stage 2): built-hang reference values, 10 designs, export hub

Prereg `5df5059` (`prereg_r6` branch `prereg/round18`, 08:17 MDT, before any data). Master 1c86f65; the fansim code is
identical to 46a3408 (empty `git diff -- fansim pyproject.toml uv.lock`), so the run used `qa/run_r17`.

- **Table:** `docs/qa/r18/r18-A-built-hang-reference.csv`.
- **Scripts:** `handoff/2026-10-20_from-qa-18/scripts/a_select.py`, `a_built.py`, `a_diag.py`, `a_finalise.py`.

## Method (M2, the reference)
1. **Hub (R1.7 semantics):**
   - when the auto hub is shorter than need = max(min_hub_height 15, cavity + wall) = 15 mm (a12x25), use
     `p_x = replace(p, hub_height_mm=need, blade_hub_z_mm=bias + Δh/2)`;
   - the top face is fixed (asserted to 1e-6 mm), and all growth goes below the blades;
   - the hub face is z_f = `_hub_axial_range(p_x)[0]`.
2. **Solid:** `build_blade_solid(p_x)` with default flags. This is exactly what `build_impeller_parts` builds before
   `clip_blade_below`: realised loft chords via `prepare_loft_chords` (including `correct_clipped_sections`), the
   feature-raised span and chord resolution, and the tip-cylinder trim.
3. **Lowest point:** z_min from OCCT `BRepBndLib.AddOptimal_s(shape, box, False, False)`, which is exact (no
   triangulation, no tolerance padding).
4. **Result:** signed s = z_f − z_min, and **built hang h = max(0, s)**. The rule is to refuse when h > 2 mm.

## Gates (all PASS)
| gate | result |
|---|---|
| A-run | 10/10 built, 0 errors |
| A-self | M3 B-rep vertex min and fine-mesh (0.005 mm) min agree with M2 to 1e-7 mm |
| A-rep | S2_0269, S5_0207 and G_0502 rebuilt in a fresh process: identical, Δ = 0 |
| A-repro | S2_0269 at the auto hub = 2.2524 mm (r16/r17: 2.252) |
| clip | after `clip_blade_below` at z_f every blade ends within 0.01 mm of the face |

## Reference values (export hub, R1.7). These are what Cursor's stage-2 measurement must match within 0.05 mm
| id | features | Δh below (mm) | built hang h (mm) | stage 2 | r17 section-point value (mm) |
|---|---|---|---|---|---|
| S2_0269 | no | 2.324 | **0.000** (s = −1.050) | pass | not built (designed 0) |
| S5_0207 | yes | 2.230 | **2.829** | refuse | 2.618 |
| S5_0073 | yes | 3.488 | **2.303** | refuse | 2.029 |
| S5_0112 | yes | 1.376 | **2.626** | refuse | 2.256 |
| S5_0023 | yes | 0 | **7.322** | refuse | 7.184 |
| G_0502 | no | 0.283 | **1.936** | pass | 1.986 |
| S1_0461 | no | 0 | **2.090** | refuse | 2.090 |
| S1_0534 | no | 0 | **0.991** | pass | 0.991 |
| S3_0173 | no | 0 | **1.169** | pass | 1.169 |
| S4_0242 | no | 2.464 | **5.359** | refuse | 5.359 |

- The signed s is in the CSV too, so Cursor can match the signed value, which includes S2_0269's −1.050 mm.
- **S2_0269** builds 2.252 mm at today's auto hub, so it is refused there. With growth below the blades (R1.7) the
  hub face drops 2.32 mm below the blade, and it **doesn't hang at all**. Its stage-2 acceptance value only means
  something once R1.7 is in.

## Findings
- **The section-point shortcut is not good enough for stage 2** (→ QA-49).
  - On feature designs, the r17/r16 P2 value (section points at the params' `n_span` = 18) reads **0.14–0.37 mm
    low**.
  - Features raise the loft to 31–43 span sections (`required_span_sections`), and the lowest point sits at
    r/R = 0.5, between the 18 sampled sections. At the build's own resolution, the section points reproduce M2
    exactly (`a_diag.json`).
  - On G_0502 the lowest point is at the tip. The section method includes the untrimmed last wire (placed just
    outside R), which the tip-cylinder trim removes, so it reads **0.050 mm high**. That is already at the
    tolerance.
  - So stage 2 should measure the built (trimmed) solid. Replicating the build's span/chord resolution and the
    tip trim is the alternative.
- **Hub semantics matter.** Supplementary columns (post-hoc, not pre-registered):
  - *Auto hub:* the hang is 2.25–10.06 mm on the same designs.
  - *Today's `mount_hub_params`:* it grows the hub symmetrically (`hub_height_mm = need`, no bias shift, so the top
    also rises 0.14–1.74 mm). S5_0207 then hangs **4.853 mm**, not 2.829, and S2_0269 0.305 mm.
  - The table above is only the acceptance table under R1.7 semantics. A stage-2 test run on today's export path
    would legitimately disagree by up to 3.2 mm (S5_0073: 5.345 vs 2.303).
- **Stage 1 vs stage 2 on these 10** (report only):
  - Stage 1 (1.75 × designed hang at the export hub > 2) refuses 5/10: S5_0073, S5_0112, S5_0023, S1_0461 and
    S4_0242.
  - Stage 2 refuses those 5 plus S5_0207 (designed 0.862 → 1.51, built 2.829), the feature tail that stage 2 exists
    to catch.
  - G_0502 (designed 1.134 → 1.98, built 1.936) passes both.
