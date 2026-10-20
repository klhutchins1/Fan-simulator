# Round 17, Task B (R2.3, R2.5): digitised Shigemitsu 2018 (CROR) and EPJ WoC 180:02023 (centrifugal)

Prereg a212b29 (`prereg/round17`), before any figure was looked at. Claude's comparison prereg
(`docs/validation/audits/2026-10-18-cror-centrifugal-validation-prereg.md`) was committed before this note, and
**no model is compared here**. The PDFs were downloaded to the box only (`qa/r17_src`, sha256 below) and are not
committed. The EPJ site blocks scripted fetches (captcha), so I took the PDF from the Wayback Machine copy of the
publisher's PDF URL; its title, DOI and licence line match the publisher's page.
- Shigemitsu: `1de8a870…a883a98`, 14 pp. EPJ: `f7065ec8…0d2220d1e`, 5 pp.
- CSVs: `docs/qa/r17/r17-B-shigemitsu2018-digitised.csv`, `r17-B-epj2018-02023-digitised.csv`,
  `r17-B-reread-check.csv`. Scripts and calibration JSON: `handoff/2026-10-19_from-qa-17/`.

## Licence (B-lic), confirmed from each PDF's own first page
- Shigemitsu 2018: "This work is licensed under the Creative Commons Attribution International License (CC BY 4.0)".
  **PASS.**
- EPJ 180:02023: "This is an open access article distributed under the terms of the Creative Commons Attribution
  License 4.0". **PASS.**
- Neither is NC or ND. The CSVs carry the citation in their first line. They are my readings of the figures, not the
  authors' data.

## Method and uncertainty
- **Shigemitsu** Figs 7 and 8 are embedded JPEG rasters (1223×1304 and 1194×1262 px, about 480 ppi).
  - Method 1: the axes are calibrated from the detected grid lines. Red open circles are found by Hough plus a
    ring score and a least-squares circle fit. After that I added a marker-size consistency filter, r = 13.0 ± 0.35 px
    (true markers measure 12.7–13.1 px), to drop 5 false circles made by line segments. Black markers are found by
    morphological opening and classed by fill and centroid (circle, up- or down-triangle).
  - Method 2: manual reads on calibrated zoom crops (`scripts/b_overlay.py`).
- **EPJ** Figs 6–8 are vector (Excel). Method 1 takes the bbox centre of each stroked marker path, with axes from
  the vector grid lines (exact). Method 2 is a manual read on a 600 dpi render.
- u = √(u_cal² + u_pick²), where u_pick = half the marker size (always larger than 2 px at 600 dpi).
  - Shigemitsu Fig 7: u_Q ±0.0165 m³/min, u_ΔP ±11 Pa. Fig 8: u_η ±1.85 points.
  - EPJ Figs 6 and 8 (linear): ±4.4 L/min / ±9.6 Pa and ±2.8 L/min / ±3.1 Pa.
  - EPJ Fig 7 (log-log): about ±5 % in Q and ±9 % in ΔP.
  - This is the conservative rule as registered. The vector centres themselves are exact to < 0.01 pt.
- **B-cal: PASS on all 5 figures.** Max tick residual: Shigemitsu 0.0002 m³/min and 0.34 Pa; EPJ ≤ 0.06 L/min and
  0.13 Pa.
- **B-rep: PASS** (every re-read within 2u, 63/63).
  - Shortfalls against "≥ 5 per curve": Shigemitsu Fig 8 has 4 of 5 re-read per CFD curve. The Q = 0.22 rear and
    total markers overlap, so method 1 merged them, and they are entered as `m2_manual_only`.
  - EPJ Fig 6 curve A (constant current): only 3 of 25 could be re-read, because its markers hide behind curve B.
  - EPJ Fig 7 at 9000 rpm is the same test as Fig 6 B, replotted. The two agree within 0.27 L/min and 0.85 Pa on all
    25 points, which I used as its re-read (a deviation).
- **B-text: PASS, 5/5** (Shigemitsu, each within 2u):
  - peak 509.7 Pa at 0.550 against "510 Pa at Q_o = 0.55";
  - last point 1.082 against "Q = 1.08";
  - CFD total 499.9 Pa at Q_o against "500 Pa";
  - CFD rear share 77.2 ± 2.7 % against "about 77 %";
  - CFD η_s,total 46.8 % against "46.7 %".
  - EPJ states no curve values in its text.

## What the curves are (important for the comparison prereg)
- **Shigemitsu Fig 7:** only `exp_total` (21 points, 0–1.082 m³/min, peak 509.7 Pa at 0.55, 0 Pa at 1.082) is
  **measured**. The front, rear and total "Cal." points (5 each, at 0.4/0.7/1.0/1.3/1.6 Q_o) are the authors' own
  ANSYS-CFX URANS. **Fig 8 efficiency is CFD only.** The 77 % rear share is a CFD result, so prereg S1 would compare
  our CFD with theirs (→ QA-47).
- The measured curve has the positive-slope (stall) region the paper describes, at 0.25–0.35 and 0.50–0.55 m³/min.
  The stable branch is 0.55–1.08.
- **EPJ:**
  - Fig 6: plastic wheel at 9000 rpm, curve A (constant current, rpm drifts) and curve B (constant rpm, 25 points,
    13–278 L/min, peak 429.9 Pa at 85 L/min, 208 Pa at 278 L/min).
  - Fig 7: plastic wheel at 6000 (15 points, peak 189 Pa, last 93 Pa at 183 L/min), 9000 (= Fig 6 B) and 11 000
    (32 points incl. repeats, peak 645 Pa at 106 L/min, last 310 Pa at 340 L/min).
  - Fig 8: plastic wheel 0 at 9000, a separate test (23 points, peak 425.9 Pa at 73.5 L/min, 207 Pa at 279 L/min).
  - **No curve reaches ΔP = 0.** The paper says the stand's flow resistance stops it (→ QA-48). The y quantity is
    the "working pressure p_b" measured in the outflow tube. No efficiency is given.
  - Repeated markers (the same Q twice) are real repeats in the figure and are kept.

## Geometry the papers give, and what is missing (for step 0 of the 2026-10-18 prereg)
**Shigemitsu R40W-A (Table 1 + text)**

| item | front | rear | source |
|---|---|---|---|
| D_hub / D_mid / D_tip (mm) | 25 / 31.1 / 37.2 | 26 / 31.1 / 37.2 | Table 1 |
| blades | 7 | 5 | Table 1 |
| solidity hub/mid/tip | 1.61 / 1.40 / 1.22 | 1.03 / 1.17 / 1.10 | Table 1 |
| stagger hub/mid/tip (°) | 18.2 / 31.2 / 36.0 | 40.6 / 40.0 / 45.5 | Table 1 |
| chord c = σπD/Z (mm), derived | 18.1 / 19.5 / 20.4 | 16.8 / 22.9 / 25.7 | derived from Table 1 |
| rpm | 15 000 | 14 000 | text |
| tip clearance, casing | 0.6 mm; 40 mm square casing with curved inlet/outlet corners and a circular diffuser/nozzle between the rotors | | text, Fig 4 |
| spokes | 3 downstream of each rotor | | text |
| design flow | Q_o = 0.55 m³/min | | text |

- Missing:
  - **blade camber, or inlet/outlet angles** (not covered by any step-0 rule, which needs angles or camber; → QA-47);
  - the **stagger convention**: the paper doesn't say whether the angle is from the axis or the rotation plane. The
    values rise hub → tip, which suggests the angle is from the axis, i.e. fansim stagger = 90° − value. Claude
    should fix this before the freeze;
  - thickness (rule: 0.8 mm);
  - the axial gap: Fig 4 is a shaded CAD cutaway with no scale or dimensions, so the "read from the drawing ±0.5 mm"
    rule can only use the 40 mm casing as a scale. I did not read it; the 0.25 × chord fallback needs Claude's yes;
  - spoke sections (not given, so leave them out by rule), sweep/lean, and hub axial lengths.

**EPJ 180:02023 (text, Table 1, Fig 1 schematic)**

| item | value | source |
|---|---|---|
| d2 | 60 mm (moulded wheel 0), printed 59.95–60.1 | Table 1 |
| b2 (outlet width) | **3.86 mm** (wheel 0); printed 4.02–4.21 | Table 1 |
| b1 | > b2. Printed b1 is "about 0.2 mm, i.e. 3 %" bigger, which implies b1 ≈ 6.7 mm (derived) | text |
| d1/d2 | ≈ 0.5 (symbol decoded from the PDF's Symbol font), so d1 ≈ 30 mm | text |
| blades | 12, long, backward-curved | text |
| axial position c | 1.8 mm (fixed for all wheels); gap t is named but not given | text, Fig 1 |
| speeds | 6000 / 9000 / 11 000 rpm, constant-rpm control | text |
| stand | suction chamber → wheel → outflow tube with orifice (ISO 5167-1), throttled at the exit; p_b in the tube | text, Fig 5 |

- Missing:
  - blade inlet/outlet angles and the blade shape. Fig 1 is a 3-D render; the meridional sketch is unscaled (it
    reads d1/d2 = 0.38, against the stated 0.5);
  - blade thickness (rule: 0.8 mm), the hub/shroud profile and the gap t;
  - **volute/diffuser dimensions:** Fig 2 is a perspective render with no scale, so the log-spiral fallback with a
    0.1 D cut-water applies (Claude to confirm Fig 2 doesn't count as "a drawing at its scale");
  - the motor/hub.
- The r15 note's "4 mm blade width" is b2 = 3.86 mm (moulded) or about 4.1 mm (printed).

## Not done
No model run, and no S/A metric evaluated. Fig 9 (b2-corrected), Figs 10–11 (wheel 7, c sweep) and the other 7
wheels in Fig 8 were not digitised (out of the prereg's scope); they are listed for completeness.
