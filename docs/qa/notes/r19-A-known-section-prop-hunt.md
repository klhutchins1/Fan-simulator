# Round 19, Task A (R2.2): a measured small prop with fully specified airfoil sections

Prereg `cab2825` (`prereg_r6` branch `prereg/round19`, 08:32 MDT). The full table, with URLs, licences,
completeness, Re and format, is `docs/qa/r19/r19-A-prop-candidates.csv`. Source PDFs and data files stay on the box
(`qa/r19_src/`); none are committed.

## Pick: the TU Delft low-Re benchmark propeller (CC BY 4.0)
- **Source:** D. Casalino, E. Grande, G. Romani, D. Ragni, F. Avallone, "Definition of a benchmark for low Reynolds
  number propeller aeroacoustics", *Aerospace Science and Technology* 113 (2021) 106707, doi:10.1016/j.ast.2021.106707.
  - Licence: **CC BY 4.0**, from the article's own licence line and the TU Delft repository record.
  - The PDF hash is sha256 9a5c4323…ee01, file `qa/r19_src/casalino2021_ast.pdf` (box only).
- **Geometry:**
  - D 0.30 m (11.8″), 2 blades, CNC aluminium, so it is stiff and doesn't deform.
  - **NACA 4412 at every station** (an elliptical root inside r = 10 mm), hub radius 12.5 mm.
  - Chord and twist come from Fig 4: c/R 0.18 (root) → 0.229 (0.4 R) → 0.067 (tip); twist 43.3° → 12.2°. The twist
    at 0.75 R is 15.7°, against 15.8° for the APC 9×6 pitch the planform comes from, a consistency check.
  - Fansim represents NACA 4412 exactly (camber 0.04, position 0.4, thickness 0.12). That is both its NeuralFoil
    `naca4412` and its vendored `naca4412` polar tables.
- **Measured:**
  - C_T and C_Q at 5000 rpm over J = 0–0.8 (9 points, Figs 19–20, vector, so the digitising is exact to the line
    width);
  - Re 4.6×10⁴–1.06×10⁵ over span and J (Table 1); Re(0.75 R) ≈ 9×10⁴ static.
- **Limits:**
  - one rpm, so "static" is J = 0 at 5000 rpm, not an rpm sweep;
  - the geometry is only a raster graph (u ≈ ±0.001 c/R, ±0.19°);
  - an open-jet tunnel with a jet only 4× the rotor area (the paper says it will quantify this later);
  - no force uncertainty is given.
- **Watch the normalisation.** The paper's coefficients are C_T = T/(ρΩ²πR⁴) and C_Q = Q/(ρΩ²πR⁵), and the axes
  read "C_T × 10²" and "C_Q × 10³". To get the propeller convention (ρn²D⁴), multiply by π³/4 and π³/8. At J = 0 that
  gives T = 8.0 N and Q = 0.155 N·m, inside the stand's 22.2 N load cell and 0.18 N·m torque cell. (Reading them as
  ρn²D⁴ would give 0.40 N·m, over the torque cell's range.) → see the r19-B deviation note.

## Runner-up: UIUC DA4002 9×6.75 (licence is citation-only)
- Rectangular, c/R 0.18, the SDA1075 section full-span (12.0 % thick, 1.95 % camber at 0.33c, from the Table 4
  coordinates), true D 9.05″.
- Design and surveyed geometry tables, a static rpm sweep, and J sweeps at about 2000–5000 rpm (Re 2.5–6.3×10⁴).
- It's the better test for rpm and Re dependence, but:
  - UIUC gives no licence beyond "please cite";
  - the SDA1075 coordinates are © the authors (published by AIAA with permission);
  - fansim can't represent SDA1075 exactly (it maps to its `naca2412` family).
- Run report-only in r19 B; no raw UIUC values are committed.

## Excluded
- TUD-XPROP family: CC BY-NC-ND, files restricted.
- The 2022 dynamometer paper: 14–18″, outside 5–12″.
- APC: no named section.
- NR640 and DA4052: the section varies along the span, which fansim averages. NR640's thickness is only plotted.
- Polito 2025: the same TUD blade, but its data are only "on request".

## What to pre-register for prop CFD validation (proposal for Claude)
- **Case:**
  - the TUD benchmark blade from `docs/qa/r19/r19-B-tud-benchmark-geometry-digitised.csv`, NACA 4412 per station;
  - hub r 12.5 mm, R 150 mm, 2 blades, 5000 rpm;
  - free stream at J = 0 / 0.24 / 0.40 / 0.60 (V = 0, 6, 10, 15 m/s).
- **Reference:** the measured C_T and C_P in `docs/qa/r19/r19-B-tud-benchmark-measured-digitised.csv`, in the
  propeller convention.
- **Suggested gates:**
  - C_T within ±15 % and C_P within ±20 % at J 0 and 0.4;
  - J 0.6 reported only, as an absolute ΔC_T, because C_T falls to 0.045 there;
  - the sign of dC_T/dJ.
  - Fansim's own BEMT already meets those gates on this prop (r19 B), so the CFD has a clean target. An SST failure
    would then be the CFD's own problem, not the section's.
- **Before the run, state:** the NACA 4412 build (closed TE vs the builder's TE-thickness rule), the root ellipse
  (treat r < 0.193 R as hub), and the free-stream vs open-jet choice.
