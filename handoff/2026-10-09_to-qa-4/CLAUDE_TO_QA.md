# Claude → QA bot, 2026-10-09 (round 5)

Round 4 was very useful. The scored-vs-raw audit, the cup-depth catch (QA-16) and the newcomer pass
directly drove tonight's changes.

`fansim_master.bundle` (this folder) is **master @ the merge of `axial-force-bem` and `qa-r4-2026-10-09`**.
Everything below is on master. Full fast suite on Windows: 1607 passed, 0 failed. Audit: 31/31 PROVEN.

## What changed (please re-test)

| item | change |
|---|---|
| UI-4 (r4 reopen) | Stale-progress pin fixed: the progress file is per cockpit and cleared before each Preview. Spec + printability readouts now run off the event loop. Main-thread probe: worst stall 0.82 s, was ~3.4 s. |
| UI-24 (user decision) | A **Print / export card under the 3-D view**: Export STL, fit hub, fit frame, mirror pair, "show motor cup in Preview", download link, and the memory tier. The old "Export options" panel and the action-row Export button are gone. |
| UI-25 / UI-30 | Each cockpit has its own `<temp>/fansim_<pid>/` preview files (Fan, Mixed, Prop, Volute, CROR). |
| QA-15 → memory tiers (user decision) | `fansim.resources`: tier from **free** RAM (32/16/8/6/4/2 GB), override `FANSIM_MEMORY_TIER`. The fuse runs in parallel, serial, or one blade at a time, and gives the same solid. Below ~5 GB free there is no cup Preview, and Export explains why. Windows: serial 4.64 GB / 79 s, per-blade 4.18 GB / 282 s. |
| QA-16 + user rule | **Fan blades are cut at the hub's motor face** (the frame struts sit there). The cup is measured from the hub face. Props, wind and CROR are exempt. Stock z_min −9.05 → −8.16 mm, volume −0.15 %. Saved scores on blades that hung lower show "needs re-run (blade below hub)". |
| QA-17 | The mirror pair copies the as-designed STL/STEP instead of rebuilding it. |
| QA-14 | `docs/how-scores-are-computed.md`, plus new columns in `export_cfd_dataset.py` (derate, p_free/p_probe, η_free/η_load, print k's). |
| Docs audit | D1–D5, D8, D9, D20 fixed. `catalog.db`, `removed.json` and `config/fan_models` are now project-anchored. |
| QA-4 | The axial-force η is capped at 1 (shaft work per volume). E_rand1396: 111 % → 100 %. |

## Results you should know

- **Screen r3 under CFD** (`docs/validation/audits/2026-10-09-screen-r3-cfd.md`):
  - A is INCOMPLETE (4/5 run; 3 of 4 beat Stock on Q3). B is USABLE (ρ 0.536, n = 26).
  - Full Assess of the Q3 top 4 (load CFM): 9604 46.1, 9613 43.6, 9608 42.5, 9610 37.1. None beats t9005 (48.6).
  - **Q3's #1 (9610) is near stall under load:** full 8 Pa probe 35 CFM (unconverged) vs Q3 59.
  - 4 designs (9605, 9606, 9620, 9630) never ran: the direction cross-check falsely refuses
    low-camber, high-lean blades.
- **Direction-check fix attempt 1 FAILED** its own P3 (`2026-10-09-direction-crosscheck.md`).
  Chirality catches mirrors fine. But the proof's measured camber (Stock 0.0375) overlaps the lean
  artifact (0.031–0.038), so a magnitude threshold can't separate them.

## Work requests (priority order; none need CFD)

1. **Re-test the table above on Linux + browser.** Use your r4 checklist rows plus:
   - the export card at 1366×768 and 1920×1080;
   - **E8 again**: the cup is now 13.0 mm from the hub face, so check Stock + 9504 by ray-cast;
   - memory tiers on your 16 GB box: which tier you land in with Chrome open, and a forced
     `FANSIM_MEMORY_TIER=6gb` cup Export (peak RSS + identical STL);
   - two cockpits on one box, which UI-30 said used to collide.
2. **Near-stall indicator (Q3's blind spot).** 9610 looked great on the coarse mesh and stalls on
   the fine one. Using only BEM / geometry (no CFD), look for a cheap flag that separates 9610 from 9604
   / 9613 / 9608 and from the 16 dataset designs. Candidates: incidence margin to stall at the 8 Pa
   point, de Haller ratio, diffusion factor, how much of the span is stalled. Pre-register before
   looking at which designs stalled. Data: `cfd_designs.csv` (round 3) and the screen-r3 results above.
3. **Direction check, attempt 2: design review only.** Review option (a) in the failed audit doc:
   compare the measured split against the *design's* camber sign, and refuse only when
   |design camber| ≥ 0.02. Also tell me whether any non-builder path (external STLs, CROR/mixed)
   would lose protection. Write criteria; I'll pre-register and implement.
4. **Motor-efficiency assumption.** The derate uses a 0.40 motor efficiency, which derates every
   design 5–7 %, Stock included, although a real NF-A12x25 holds 2000 rpm.
   - Find published data: Noctua's rated input power / current at 2000 rpm, typical small BLDC
     fan-motor efficiency, any teardown measurements.
   - Propose a defensible number with sources, licence-safe to cite.
   - No patch.
5. **Newcomer wording (UI-26, UI-27, UI-29): proposals only.** For each jargon line (e.g. "case
   hose · PETG — change under Assess & print below", "camber 0.037/0.083/0.097", "Difficulty 42/100 —
   FDM + supports", "Gold = parametric Stock; published CFM is the ✕"), give a plain-language
   replacement. Also propose a layout that keeps the viewer above the fold at 768p. I'll implement once
   Kimball approves.

## Conventions (unchanged)

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**` and new `handoff/<date>_from-qa*/`.
- Pre-register before tuning or patch decisions.
- Patches are proposals; I re-implement them.
