# Round 15, Tasks A–C (board R2.3 / R2.4 / R2.5): published data for CROR, mixed-flow and centrifugal fans

Research only (prereg `prereg/round15` 336211b, selection rule fixed before the search). Nothing downloaded is
committed. The licence is quoted as each page states it. "Cite-only" = no open licence: cite it and keep any
digitised numbers out of the repo (or ask the authors).

## A. R2.3 CROR (≤ 200 mm), P–Q or thrust/torque vs rpm, with modelable geometry

| # | Source | URL | Licence | Size / type | Measured | Geometry given | Missing | Redistributable? |
|---|---|---|---|---|---|---|---|---|
| A1 | Shigemitsu, Miyazaki, Hirosawa, Fukuda (2018), *Performance and Internal Flow of Contra-Rotating Small-Sized Cooling Fan*, Open J. Fluid Dyn. 8:181–194 | https://doi.org/10.4236/ojfd.2018.82013 | **CC BY 4.0** (SCIRP article page) | 40 mm square casing, Ø37.2 mm rotors (San Ace-type "R40W-A"), front/rear hub 25/26 mm, tip clearance 0.6 mm, 15 000 / 14 000 rpm | total and per-rotor static-pressure–flow curves (Q up to ~1.1 m³/min, ΔPs max ~510 Pa) | Table 1 "primary dimensions of rotors" (an image: blade counts, chord/stagger values per the paper), hub/tip, rpm, clearance | blade sections (camber/thickness), axial gap: read Table 1/figures; spokes (3 per stage) and inter-rotor casing shape | **Yes** (CC BY, with attribution); curves need digitising from figures |
| A2 | Shigemitsu et al. (2016), *PIV measurement of inlet and outlet flow of contra-rotating small-sized cooling fan*, IJFMS 9(2):175 | https://doi.org/10.5293/ijfms.2016.9.2.175 | IJFMS: free to read on J-STAGE, copyright with the societies, **no CC licence** | same R40W-A | P–Q (ΔPs max 510 Pa at 0.55 m³/min) + PIV | as A1 | as A1 | Cite-only |
| A3 | Shigemitsu, Fukutomi, Okabe (2010), *Performance and flow condition of contra-rotating small-sized axial fan at partial flow rate*, IJFMS 3(4):271 | https://doi.org/10.5293/ijfms.2010.3.4.271 | as A2 (no CC) | Ø100 mm, hub/tip 45/98 mm, R and RR rotor types | P–Q for single and contra-rotating (Q 0.0064–0.0192 m³/s, design ΔP ~14 Pa) | rotor design table (in paper) | sections | Cite-only |
| A4 | Gallo, de Decker, Haezebrouck, Zarri, Schram (2023), *H2020 ENODISE: Experimental dataset of configuration C VKI* (single + contra-rotating 2-blade Mejzlik 13×4.2 props) | https://doi.org/10.5281/zenodo.8334930 | **CC BY 4.0** (Zenodo) | **330 mm** props (above the 200 mm limit), spacing 0.02–0.04 m, 4000–7000 rpm, static | thrust + torque per rotor, far-field noise | commercial prop model named; no blade geometry in the record (technical PDF to check) | blade chord/twist | Yes, but oversize and no geometry |
| A5 | Floros & Kang (2021), *Experimental Evaluation of Coaxial Micro-UAS Propellers*, VFS Forum 77 | https://doi.org/10.4050/f-0077-2021-16705 | VFS, copyrighted (US Army authors, but published by VFS: check) | 6–9" coaxial props, spacing down to 0.116 R | thrust/torque, trimmed | commercial props | blade geometry | Cite-only unless shown to be a US-Gov work |
| A6 | Ravelet / Nouri / Bakir (Arts et Métiers) CRS fans, e.g. HAL hal-00967902 | https://hal.science/hal-00967902 | HAL deposit; licence per record (not shown as CC on the abstract) | **Ø375 mm** | ΔPs, ηs vs Q, spacing and speed ratio sweeps | full design method and blade tables in the related papers | — | Oversize; cite-only unless the HAL record carries CC |

**Best:** **A1** (only open-licensed, in range, measured P–Q with a rotor-dimension table). Second: **A3** for
a 100 mm case (cite-only).
**What we'd pre-register (A1):** model R40W-A with the direction-proof CROR path at 15 000 / 14 000 rpm in a 40 mm
square duct. Compare only the *shape* first, because blade sections must be inferred: (i) rear rotor carries
> 50 % of total ΔPs at Q_o = 0.55 m³/min (paper: ~77 %); (ii) total-ΔPs peak within ±15 % of Q_o; (iii) free
delivery within ±20 %. The absolute ΔPs at Q_o (±25 %) is report-only until the sections are known. This is direction
proof plus a shape check (matches R2.3's "direction proof only" status), not a calibration.

## B. R2.4 Mixed-flow (40–150 mm)

| # | Source | URL | Licence | Size | Measured | Geometry | Missing | Redistributable? |
|---|---|---|---|---|---|---|---|---|
| B1 | Treder et al., *Experimental investigations of mixed flow fans with various downstream angles*, FAN 2018 (paper 86) | https://www.fan2025.org/archives/fan2018/papers/FAN2018-86-TREDER.pdf | No licence on the conference archive | Ø85 mm, 10 backward-curved constant-thickness blades, hub/shroud arcs R150/R80, downstream angle 68°, 1500 rpm (and more) | dimensionless performance curves | meridional arcs, blade count, angles | blade-angle distribution in detail; inlet/outlet widths (check paper) | Cite-only |
| B2 | (same group) *Remarks on the meridional design of mixed flow fans*, ETC 2017 paper 059 | https://www.euroturbo.eu/paper/ETC2017-059.pdf (doi:10.29008/etc2017-059) | "OPEN ACCESS … Copyright © by the Authors" (no CC) | Ø85 mm, "Pfleiderer" blades, 5000–11 000 rpm, shroud radii R80–R150 compared (R130 best) | ΔP, Q, η curves at several speeds | meridional contours, blade count, angles | full blade coordinates | Cite-only |
| B3 | Fan, Zhang, Zhang, Liu (2020), Energies 13:2819 | https://doi.org/10.3390/en13112819 | CC BY 4.0 (MDPI) | **Ø39 mm** outlet shroud, 9-blade impeller + 11-blade diffuser, 500 W, ~7 kPa | only an efficiency comparison curve vs CFD | Table 1 main dims | blade angles of the original (only the optimised ranges) | Licence OK, but out of class (vacuum-motor stage) and pressure curve not given. Not useful |
| B4 | JSME, *Performance of mixed flow multiblade fan as small duct fan* (kikaib.63.611_2386), and *Effects of parameters of mixed flow multiblade fan impeller* (kikaib.64.1413) | https://doi.org/10.1299/kikaib.63.611_2386 | JSME copyright | ~100 mm duct fan | P–Q | partial | — | Cite-only |

**Best:** **B2/B1** (same 85 mm rig, several shrouds and speeds, measured), cite-only. No CC-licensed small
mixed-flow fan with a measured P–Q curve was found.
**What we'd pre-register:** rebuild the R130 / 68° variant from the paper's meridional data, compare the
dimensionless ψ(φ) peak location (±15 % in φ) and the ranking R130 > R80 > R150 at the design φ (rank only).
Absolute ψ is report-only because the blade angles must be inferred.

## C. R2.5 Centrifugal / volute (impeller ≤ 120 mm)

| # | Source | URL | Licence | Size | Measured | Geometry | Missing | Redistributable? |
|---|---|---|---|---|---|---|---|---|
| C1 | *Experimental investigation of centrifugal fans for personal protection equipment – effect of used 3D printing technologies*, EPJ Web Conf. 180, 02023 (EFM 2018) | https://doi.org/10.1051/epjconf/201818002023 | EPJ Web of Conferences, open access under **CC BY 4.0** (journal standard; confirm on the article page, which our fetch tool could not render) | **Ø60 mm**, 12 long backward-curved blades, 4 mm blade width; 1 moulded + 7 printed wheels | pressure vs flow at 6000 / 9000 / 11 000 rpm | diameter, blade count, width; drawings in paper | blade angles / inner diameter / volute dims to read from figures | Yes (CC BY) if confirmed |
| C2 | follow-up: *Experimental investigation of fan for personal protection equipment – influence of number of blades* (Univ. West Bohemia repository) | http://hdl.handle.net/11025/36276 | repository record; licence not checked → cite-only | Ø60 mm, 4 mm width, blade-count sweep (12 best) | P–Q per blade count | as C1 | as C1 | Cite-only until checked |
| C3 | Probst, Pritz, Bauer (KIT), *Towards a FAIR centrifugal fan database (openCeFaDB)*, FAN 2022 | https://publikationen.bibliothek.kit.edu/1000152222/149590525 · https://github.com/MatthiasProbst/openCeFaDB | paper **CC BY 4.0**; data repo licence to check | 9-blade backward-curved fan in an acrylic spiral casing (industrial size, **> 120 mm**) | performance curves + PIV (HDF5) | technical drawings promised in the repo | size out of range | Paper yes; data per repo |
| C4 | MDPI Processes 12:353 (2024), PAPR centrifugal fan | https://www.mdpi.com/2227-9717/12/2/353 | CC BY 4.0 (MDPI) | Ø68 mm, 48 blades, 23 mm height | outlet velocity / flow and pressure validation (not a full curve) | blade count, height, thickness | blade angles | Licence OK, data thin |
| C5 | Matheuscp98/CentrifugalFanData (CFD runs, CC BY 4.0) | https://github.com/Matheuscp98/CentrifugalFanData | CC BY 4.0 | industrial | **CFD only** | parametric | — | Not measurement: excluded by the rule |

**Best:** **C1** (CC BY, 60 mm, three speeds, printed wheels, which suits this project's FDM use case). Second:
**C4** (CC BY, 68 mm, but no full curve).
**What we'd pre-register (C1):** model the 60 mm, 12-blade, 4 mm-wide wheel at 9000 rpm with the volute
geometry read from the paper. Compare (i) the shut-off-to-free-delivery P–Q shape: the peak static-pressure
location within ±20 % in Q; (ii) the speed scaling ΔP ∝ n² between 6000 and 11 000 rpm (measured ratio vs model,
±10 %); (iii) absolute ΔP at the measured best point is report-only. This lets Claude decide R2.5
converge-or-label against a measured curve rather than the current ±20 % proxy.

## Notes
- No NC/ND source was used. All "cite-only" items stay out of the repo.
- J-STAGE/IJFMS and JSME: free to read, but copyright is held by the societies with no CC grant, so cite-only.
