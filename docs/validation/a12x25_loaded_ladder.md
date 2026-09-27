# A12x25 loaded-branch diagnostic ladder (roadmap §19.6)

Spec: `docs/superpowers/specs/2026-09-26-loaded-branch-ladder-design.md` · `CFD_VERSION` 3 (designed
rotation) · Stock recipe, 2000 rpm, tip gap 0.5 mm, base_cell 5 mm, 1000 iters, 16 procs.

Pass criteria: shut-off within 22.9 ± 5 Pa, the loaded points converged, and free air within 60.1 ± 10%.
Raw data: `docs/validation/loaded_ladder/{plenum,frame}.json`.

## Results (CFM; "u" = unconverged under rule A; osc = tail peak-to-peak %)

| back-pressure | baseline (plain duct) | rung 1: plenum | rung 2: plenum + frame | Noctua |
|---|---|---|---|---|
| 0 Pa | 58.7 (osc 8%) | 59.9 u (osc 9%) | 49.9 u (osc 18%) | 60.1 |
| 5 Pa | 21.6 u (osc 11%) | 27.4 u (osc 5%) | **31.7** (osc 5%) | — |
| 10 Pa | −6.2 (osc 17%) | 5.1 u (osc 64%) | **13.5** (osc 10%) | — |
| 15 Pa | −72.5 | −3.6 u (osc 23%) | −0.9 u (osc 352%) | — |
| shut-off | 9.5 Pa | not computable | **13.7 Pa** | 22.9 Pa |
| verdict | FAIL | INCONCLUSIVE | FAIL | |

## What each rung did

- **Plenum (outlet chamber).** It removed a domain artifact. The large reverse flows at 15–20 Pa (−72 to
  −117 CFM) came from imposing a uniform static pressure on the swirling duct exit. With a plenum, the
  curve near shut-off sits around zero flow, as it physically should. Free air is unchanged (59.9 CFM).
  Every point is unconverged, though.
- **Frame (struts de-swirl the exit).** It adds real static-pressure recovery: 5 Pa rises 27 → 32 CFM,
  10 Pa rises 5 → 14 CFM, and those two points now converge. The shut-off rises to 13.7 Pa. But free air
  drops to 49.9 CFM (−17%, unconverged), and the published free-air figure *includes* the frame, so this
  opens a new gap.

## Reading

Steady RANS still cannot settle most operating points in this domain: oscillation is 5–18% and far higher
near shut-off. That is consistent with an unsteady, stall-prone regime.

The remaining shut-off gap (13.7 vs 22.9 Pa), and the free-air drop once the frame is present, are the
questions for the next rung (URANS). Rung 3 has **not been run yet**. With the 3× plenum box, a steady
point already costs about 1 h at 16 procs, so a 10-revolution URANS point is estimated at several hours.
The rung-3 scope needs a decision (see roadmap §19.6).

## Rung 3 (URANS) — attempted 2026-09-27, stopped

Trimmed scope (box 2×, frame on, points 0 and 10 Pa, 6 revs, maxCo 1.5, 16 procs). The adaptive time
step settled at ~3.4 µs (limited by the fine blade-surface cells); after 40 min of solving it had covered
0.0016 s of the 0.18 s needed (<1%), i.e. **~3 days per point**. Stopped as not viable. The partial 0 Pa
history was sane (sanity checks: power/thrust signs and inlet bookkeeping PASS).

Options if revisited: PIMPLE with outer correctors and maxCo 5–10, 2–3 revolutions, or a coarser
transient mesh. Parked in favour of the external benchmark and model audits (roadmap §19).

**Also note:** the baseline column above was solved in the default *square* tunnel (open corners around
the tips; see `docs/validation/cfd_sanity_baseline.md`), while the plenum/frame rungs used a round bore —
part of the rung-1 improvement may come from the duct shape, not only the plenum.
