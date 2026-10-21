# QA round 19 pre-registration (grok, QA bot), 2026-10-20 MDT, written before any round-19 BEMT run or digitising

Repo: master 1c86f65 (the fansim code is identical to 46a3408, so the run clone is `qa/run_r17`). Brief:
`handoff_in/r19/CLAUDE_TO_QA.md`. Box only. No CFD, no fansim edits, nothing committed to repo-rN.

**Disclosure.** Before writing this, I opened the candidate papers and files to check licence and format:
- I saw the plotted measured C_T and C_Q curves in Casalino et al. 2021 (Figs 19–20) and the first 3–4 rows of the
  UIUC DA4002 files.
- No BEMT has been run and no number has been extracted or compared.
- The tolerances are the brief's suggested ones, unchanged.

## A. Candidate hunt (report)
- Candidates and licences are listed in the r19-A note. The choice criteria were fixed before any comparison: an
  open licence, D within 5–12″, chord + twist + named section all given, and measured C_T and C_P at static and
  over J.
- **Primary: the TU Delft low-Re benchmark propeller.** D. Casalino, E. Grande, G. Romani, D. Ragni, F. Avallone,
  "Definition of a benchmark for low Reynolds number propeller aeroacoustics", *Aerospace Sci. Technol.* 113
  (2021) 106707, doi:10.1016/j.ast.2021.106707, **CC BY 4.0** (stated in the article).
  - D = 0.30 m (11.8″), 2 blades, an APC 9×6 planform re-sectioned with **NACA 4412**.
  - Hub radius 12.5 mm; an elliptical root up to r = 10 mm.
  - CNC aluminium, 5000 rpm, J = 0 / 0.24 / 0.4 / 0.6 / 0.8.
- **Secondary (report-only): UIUC DA4002 9×6.75**, 2 blades (UIUC Propeller Database Vol 2, Deters; Deters, Ananda
  & Selig AIAA 2014-2151).
  - Rectangular planform, c/R 0.18, the SDA1075 section full-span; true D 9.05″.
  - Licence: UIUC asks for citation and gives no formal licence. The SDA1075 coordinates are © the authors
    (published by AIAA with permission). So it is used on the box only, and no raw values are committed.

## B. BEMT against measurement
**Geometry, primary (TUD):**
- c/R(r/R) and twist β(r/R) come from the **vector paths** of Fig 4 (pdfplumber; the axes are calibrated from the
  tick labels).
- Calibration gate B-cal: tick residual ≤ 0.5 % of the axis span.
- Resampled to r/R = first digitised point … 1.0 in steps of 0.05, with the last point at the curve's own end.
- Hub at the first station, which is fansim's `load_uiuc_geometry_blade` convention.
- Stations: `RadialStation(r_frac, c, β, thickness 0.12, camber 0.04, camber_pos 0.4)`, i.e. NACA 4412 exactly.
- `BladeParams(n_blades=2, hub_radius=r0·R, tip_radius=150 mm)`.

**Geometry, secondary (DA4002):** the design `da4002_geom.txt` and the surveyed `da4002_9x6.75_geom.txt`.
- Section camber is the maximum of the mean line (y_u + y_l)/2, with both surfaces interpolated on a common x; thickness is
  max(y_u − y_l), both from Table 4 (SDA1075).
- R = 9.05″/2.

**Measured, primary:**
- The "Measurements" curves of Fig 19 (C_T × 10) and Fig 20 (C_Q × 10²), as vector vertices at the five J values.
- C_T = T/(ρn²D⁴), C_Q = Q/(ρn²D⁵) (the standard definitions; not stated in the paper, so they are assumed and
  sanity-checked), and C_P = 2π·C_Q.
- Digitising u = half the line width plus the tick residual.

**Measured, secondary:**
- static `da4002_9x6.75_static_1107rd.txt` at its row nearest 5000 rpm;
- the J sweeps `_1104rd_5028.txt` (primary rpm) and `_1101md_3030.txt` (lower Re), interpolated to
  J = 0.24 / 0.4 / 0.6.

**BEMT:**
- `fansim.propeller.bemt.analyze(params, rpm, v_forward = J·n·D)` with default ρ, n_elem 24;
- nondimensionalised with `fansim.propeller.polar.nondim` on the true D;
- backends `table` (the shipped default) and `neuralfoil` (`set_polar_backend`).

**Judged points:** J = 0 (static) and J = 0.4 (mid J). J = 0.24 and 0.6 are reported.
- A point whose measured |C_T| < 0.02 (J = 0.8 expected) is reported in absolute terms only, not as %.

**Agreement rule (as the brief suggests):**
- AGREE needs |e_CT| ≤ 15 % **and** |e_CP| ≤ 20 % at **both** J = 0 and J = 0.4, where e = BEMT/meas − 1.
- Verdict per backend. **Headline = the `table` backend** (fansim as shipped); `neuralfoil` is reported alongside.
- A non-converged BEMT point (`converged = False`) counts as a miss and is flagged.
- Otherwise the verdict is DISAGREE, with the failing points named.

**Diagnostic, the section question (report-only, rules fixed now):**
- Rerun the primary with fansim's **generic** prop section, i.e. the loader default (camber 0.04, thickness 0.06),
  the section used on APC SF.
- J-growth G = e_CT(J = 0.4) − e_CT(J = 0) in percentage points, for the known (4412) and generic sections.
  - **SECTION-DRIVEN** if |G_known| ≤ 10 pp and |G_generic| ≥ |G_known| + 10 pp;
  - **NOT-SECTION** if |G_known| > 10 pp in the same direction as APC SF (negative);
  - else MIXED.
- For reference, APC SF table backend: −13 % static, −20 % at J 0.30, −29 % at 0.43 (board R2.1).

**Sensitivity (report-only):** twist ±0.5° (digitising and manufacturing), chord ±2 %, ρ 1.18 / 1.225, n_elem 48.

**Deliverables:**
- `docs/qa/r19/r19-B-*.csv` (my own digitised TUD values, CC BY with attribution, plus BEMT outputs). For DA4002,
  only BEMT outputs and % errors, no raw UIUC values.
- Notes `docs/qa/notes/r19-A-*.md` and `r19-B-*.md`.

## Run rules
Anything over a minute runs under setsid nohup, timed with time.monotonic and checkpointed. QA IDs continue after
QA-50.
