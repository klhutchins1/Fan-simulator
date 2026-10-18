# QA-12 data hunt: measured small-prop CT0 at Re(0.75R) 6e4–1.5e5, and low-Re polars (QA round 14, Task D)

Master 9562574. Research only: nothing downloaded is committed. The UIUC propDB zip already on the box
(`research/prop_data/UIUC-propDB.zip`, outside the repo) was scanned by
`handoff/2026-10-16_from-qa-14/scripts/d_uiuc_re.py` → `data/d_uiuc_re.json`.
Re(0.75R) = 0.75·Ω·R · c(0.75R) / ν, ν = 1.5e-5 m²/s, with c from each prop's `*_geom.txt` (c/R at r/R 0.75).
That is the same Re basis UIUC uses on its CT0 plots.

## What the 5" preset needs
The prop BEMT matches sections to vendored tables in `fansim/data/polars/`: e387, sd7032, s1223, NACA 0012/2412/4412,
each at Re 4e4 / 8e4 / 1.6e5. **Finding (doc note):** these files are "condensed representative polars" that
"follow UIUC LSAT trends" (polars/README.md). They are not measured rows. For example, e387 at 8e4 has a
perfectly linear cl = 0.35 + 0.10·α. So the QA-12 Re effect is resting on hand-shaped tables. Measured data
for e387 in this Re range does exist and is public domain (source 1 below).

## Candidates

| # | Source | URL | Licence (as stated) | What | D / pitch | rpm | Re(0.75R) | Format | Redistributable? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | NASA TM-4062, McGhee, Walker & Millard 1988, *Experimental results for the Eppler 387 airfoil at low Reynolds numbers in the Langley LTPT* | https://ntrs.nasa.gov/citations/19890001471 (PDF: https://ntrs.nasa.gov/api/citations/19890001471/downloads/19890001471.pdf) | NTRS: "Work of the US Gov. Public Use Permitted." | E387 2-D section: cl, cm (pressures), cd (wake survey), separation/reattachment | airfoil | n/a | chord Re 6e4–4.6e5, M 0.03–0.13 | tabulated in the PDF (needs transcription) | **Yes** (US-Gov work, public domain) |
| 2 | UIUC LSATs, *Summary of Low-Speed Airfoil Data* Vol 5 (Williamson et al. 2012), E387(E) validation runs; also Vols 1–3 and the Williamson MS thesis | https://m-selig.ae.illinois.edu/pd.html · https://m-selig.ae.illinois.edu/uiuc_lsat.html · terms: https://m-selig.ae.illinois.edu/pd/pub/lsat/volume03/readme.TXT | Copyrighted, **GPL-style**: free for any use including commercial; cite the volume and where to get it; no extra charge; recipients may copy and redistribute; the licence, copyright notice and LSATs Manifesto must ship with the data. Not NC, not ND. | E387 and the other families: cl, cd, cm | airfoil | n/a | ~4e4 (thesis) / 6e4–5e5 | ASCII polars | Yes, but **copyleft on the data files**: if vendored, ship GPL.TXT + MANIFEST.TXT next to them. Keeping it local plus a citation is simplest. |
| 3 | UIUC Propeller Data Site Vol 1 (Brandt 2005–08): APC Slow-Flyer 9×4.7 static (`apcsf_9x4.7_static_kt1032`) + geometry | https://m-selig.ae.illinois.edu/props/propDB.html | No licence on the page, only a requested citation (Brandt & Selig 2011; Brandt MS thesis). Not NC/ND. Treat as "cite, keep local". | measured static CT0, CP0 vs rpm | 9" / 4.7" | 2763–6768 | 3.8e4–9.2e4 (10 points in band) | ASCII | Unclear (no explicit grant). Do not vendor, cite only. |
| 4 | same, GWS Slow-Flyer 9×4.7 (`gwssf_9x4.7_static_kt0965`), 9×7 (`kt0972`); APC SF 9×6 (`kt0979`); DA4022 9×6.75 (Vol 2, `0767rd`, Deters) | as 3 | as 3 | CT0, CP0 | 9" | ~1.3k–6.8k | to 8.8e4–9.3e4 (8–9 points in band) | ASCII | as 3 |
| 5 | same, 10–11" Slow-Flyers that do reach the upper band: APC SF 11×3.8 (`kt0542`, Re to 1.35e5, 13 pts), GWS SF 11×4.7 (`jb0563`, to 1.29e5), APC SF 11×4.7 (`pg0526`, to 1.22e5), APC SF 10×4.7 (`kt0835`, to 1.09e5) | as 3 | as 3 | CT0, CP0 + geometry | 10–11" | ~1.7k–6.5k | 3.4e4–1.35e5 | ASCII | as 3 |
| 6 | FPV-DB open dataset (motor thrust tables, incl. 5" props) | https://fpv-db.com/data/ · https://github.com/fpvdb/fpv-db-data | Declared **CC BY 4.0** (credit "FPV-DB" with a link) | manufacturer bench tables (thrust, rpm, current) copied from vendor pages | 5" etc. | ~10k–30k | 5" at 20–30k rpm ≈ 6e4–9e4 (chord assumed ~9 mm, **no geometry**) | JSON/CSV | Licence OK on its face, but the rows are vendor marketing numbers (unknown stand and conditions) and there is no blade geometry. **Not usable** for a CT0-vs-Re test. |
| — | Tyto Robotics database | https://www.tytorobotics.com/ | Site ToS, no open licence | 5" thrust-stand uploads | | | | web | **No**: no licence. Excluded. |

Scan facts (UIUC propDB, all 4 volumes): 250 static files, 121 with geometry. Every 4.5–5" prop with geometry
tops out at Re(0.75R) ≤ 4.0e4 (max rpm ~10k). Vols 3 and 4 (Dantsker) have no geometry files.
7–8.5" props have no geometry. **So no UIUC 5" data reaches 6e4.** 9" props cover 6e4–9.3e4, and only
10–11" Slow-Flyers reach 1.1e5–1.35e5. Nothing in UIUC static data reaches 1.5e5 with geometry.
Licence doc note: THIRD_PARTY.md's "public use with citation" for propDB isn't backed by an explicit licence on
the UIUC prop pages (they ask only for a citation). The propDB regression files already in the repo (GWS,
`e7d8174`) should stay as-is with their citation, but should not be read as an explicit grant.

## Best 1–2 and what we would pre-register
1. **NASA TM-4062 E387 (public domain), at chord Re 6e4 / 1e5 / 2e5.** Transcribe the tables (QA, by hand,
   double-entered). Pre-register: compare the vendored `e387_re{8e4,1.6e5}` tables, log-Re interpolated to
   1e5 / 2e5, against measured cl(α), cd(α) for α −2…8°. Pass bands (proposal): |Δcl| ≤ 0.10 and cd within 25 %
   where attached. Report the 6e4 laminar-bubble drag rise separately, because TM-4062 shows it and a linear
   table cannot. If it fails, replace the tables with TM-4062 rows (US-Gov, redistributable, no copyleft).
   This targets the "~44 % real table Re effect" part of QA-12 directly.
2. **UIUC APC SF 9×4.7 (kt1032) + APC SF 11×3.8 (kt0542), cite-only and kept local.** Pre-register: BEMT CT0
   with the measured geometry at each measured rpm. PASS iff the measured CT0 (flat within ~±4 % across the
   band) is matched, with modelled CT0 creep across Re 4e4→1.3e5 ≤ the measured change + 5 percentage points.
   This is the measured "flat" reference QA-12 cites, now inside 6e4–1.35e5 rather than below 4e4.
No 5"-specific measured CT0 with geometry and an open licence was found. A 5" check would need our own stand data.
