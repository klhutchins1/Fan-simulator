# Round 19, Task B (R2.1 / R2.2): how good is fansim's BEMT on a prop with known sections?

Prereg `cab2825` (before any BEMT run or digitising). Fansim at master 1c86f65 (code identical to 46a3408), with
`fansim.propeller.bemt.analyze` as shipped, n_elem 24 and default ρ.

- **Data:** `docs/qa/r19/r19-B-bemt-vs-measured.csv` (every case, J, backend, variant and error),
  `r19-B-tud-benchmark-geometry-digitised.csv` and `r19-B-tud-benchmark-measured-digitised.csv`.
- **Scripts:** `handoff/2026-10-20_from-qa-19/scripts/`.

## Headline: TU Delft benchmark prop (NACA 4412, CC BY 4.0), 5000 rpm
**Fansim's shipped BEMT (`table` backend) AGREES:**

| J | C_T BEMT / meas | e_CT | C_P BEMT / meas | e_CP |
|---|---|---|---|---|
| **0 (static)** | 0.1104 / 0.1161 | **−4.9 %** | 0.0474 / 0.0472 | **+0.5 %** |
| 0.12 | 0.1057 / 0.1077 | −1.8 % | 0.0519 / 0.0498 | +4.2 % |
| 0.24 | 0.0954 / 0.0943 | +1.2 % | 0.0532 / 0.0503 | +5.8 % |
| **0.40 (mid J)** | 0.0721 / 0.0777 | **−7.1 %** | 0.0483 / 0.0481 | **+0.3 %** |
| 0.48 | 0.0576 / 0.0667 | −13.6 % | 0.0428 / 0.0451 | −5.2 % |
| 0.60 | 0.0340 / 0.0447 | −24.1 % | 0.0312 / 0.0356 | −12.3 % |
| 0.72 / 0.80 | ΔC_T −0.009 / −0.009 (absolute; C_T ≈ 0) | | | |

- **AGREE** (C_T ±15 %, C_P ±20 % at J 0 and 0.4, every element converged).
- It still agrees under every sensitivity setting: twist ±0.5°, chord ±2 %, ρ 1.18, n_elem 48. The worst is twist
  −0.5°: −12.4 % C_T at J 0.4.
- **NeuralFoil backend: DISAGREE.**
  - C_T is +16.8 % static and +13.2 % at J 0.4; C_P is +18.1 % / +14.7 %.
  - The static C_T is just outside ±15 %.
  - **Every** J point has at least one element that hit the 60-iteration cap (`converged = False`) → QA-51.

## The section question
- Pre-registered G = e_CT(J 0.4) − e_CT(J 0):
  - **known section −2.2 pp** (table) / −3.7 pp (NeuralFoil);
  - fansim's generic section (camber 0.04, thickness 0.06, which the table maps to its `e387` family): −4.4 pp
    (table) / +17.5 pp (NeuralFoil).
  - By the pre-registered rule that is **MIXED** for the table (neither section grows between 0 and 0.4 on this prop)
    and SECTION-DRIVEN for NeuralFoil.
- **Plain reading:**
  - With a known section and the shipped polars, fansim's BEMT is within 5–7 % on C_T and 1 % on C_P at static and
    J 0.4, so the BEMT physics is fine there.
  - The generic section happens to agree on this prop too (+8 % / +4 % C_T). So the generic section is not wrong in
    itself; the APC SF deficit comes from the generic section being unlike APC's real thin, cambered section.
  - **The deficit does reappear toward zero thrust, even on known sections:** −14 % at J 0.48 and −24 % at 0.60.
    That is a roughly constant absolute offset, ΔC_T ≈ −0.009 to −0.011 from J 0.48 to 0.80, which grows in
    relative terms as C_T → 0.
  - So part of APC SF's growth with J (−13 % → −29 % at J 0.43, ΔC_T ≈ −0.015) is a BEMT near-zero-thrust offset
    that a known section doesn't remove. It's about 0.01 in C_T.
- Board wording for R2.1: "On a known-section prop, C_T is within 7 % and C_P within 1 % at static and J 0.4. Toward
  zero thrust (J ≥ 0.5) C_T reads about 0.01 low, so % errors grow there."

## Secondary: UIUC DA4002 9×6.75, report only (licence is citation-only; SDA1075 maps to fansim's `naca2412`)
| case (5028 rpm unless noted) | static e_CT / e_CP | J 0.4 e_CT / e_CP | verdict |
|---|---|---|---|
| design geometry, table | −15.4 % / −27.3 % | −17.3 % / −14.9 % | DISAGREE |
| surveyed geometry, table | −18.0 % / −31.1 % | −12.4 % / −10.9 % | DISAGREE |
| design, NeuralFoil | −8.7 % / −17.1 % | −8.0 % / −11.5 % | DISAGREE (non-converged elements; numbers inside the band) |
| surveyed, NeuralFoil | −12.2 % / −17.9 % | −5.7 % / −9.0 % | DISAGREE (non-converged) |
| design, table, 3030 rpm (Re ~3.8×10⁴) | −12.8 % / −36.1 % | −14.6 % / −14.9 % | DISAGREE |

- On DA4002 the J-growth G is small too (−1.9 to +6.5 pp).
- The shipped table backend under-reads C_T by 12–18 % and static C_P by 27–41 %. That is the same sign as APC SF's
  static C_P −21 % known fail.
- The section here is only approximated (SDA1075 is 12 % thick with 1.95 % camber at 0.33c, run through fansim's
  `naca2412` family), so this does not overturn the TUD result.
- It does say: on thick low-camber sections at Re 2.5–6×10⁴, the static C_P deficit remains.
- The DA4002 rows of the CSV hold only BEMT values and errors. The UIUC files are on the box only.

## Deviation from the prereg (recorded, before any verdict was written)
- The prereg assumed C_T = T/(ρn²D⁴) and C_Q = Q/(ρn²D⁵) "not stated in the paper — assumed and sanity-checked",
  and read the axes as ×10 / ×10².
- **The sanity check failed:** that reading gives Q = 0.40 N·m at J 0, over the stand's 0.18 N·m torque cell.
  - A 400-dpi crop shows the labels are **C_T × 10²** and **C_Q × 10³**.
  - The paper does state its convention in §5: dividing by ρΩ²πR⁴ and ρΩ²πR⁵ (pdftotext garbles Ω² as "2").
  - Corrected reading: T = 8.0 N and Q = 0.155 N·m, both inside the cells' ranges.
- The correction was applied the same way to every case (`b_tud_forces.py`, ×π³/4 and ×π³/8).
- Under the wrong normalisation every TUD case had read DISAGREE, with C_P −55 to −61 %. That result came from the
  unit error, not from the model, and it is not used.
- No tolerance, rule or BEMT setting was changed.

## Caveats
- One rpm only.
- The open-jet tunnel's jet is 4× the rotor area. The paper flags this as an effect on rotor loading at J > 0 and
  will quantify it later.
- The geometry comes from a raster figure (u ±0.001 c/R, ±0.19° twist). The ±0.5° twist sensitivity covers it.
- `PropPerf` rounds power to 0.1 W and thrust to 1 mN. On DA4002 at 3030 rpm (about 5–6 W) that is up to about 1 %
  of C_P (→ QA-52); it's negligible on TUD (about 80 W).
