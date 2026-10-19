# Claude → QA bot, 2026-10-19: round 17

**What's new for you:** this folder. `fansim.bundle` is **master at the commit that added this folder**. Clone it fresh: your Saturday copy predates
this round. The same text is at the top of `docs/QA_REVIEW.md` in the bundle.

**Decisions on your r16 findings (Kimball, 2026-10-17):**
- **QA-43: yes.** The 2 mm limit is for the printed blade, checked as 1.75 × the designed hang. Board R1.8; Cursor implements.
- **QA-44: yes.** One hub for search, score and export, with the export's extra hub height placed below the blades.
  Board R1.7; Cursor implements.
- Neither has landed yet. The install guide (R3.3) isn't written yet either, so Task D waits.

Also new since your copy: R0.3 "too close to call" is merged; the night queue (`night/queue.json`) exists; and there are
pre-registrations for prop CFD, CROR/centrifugal and lt120 in `docs/validation/audits/2026-10-1[78]-*`.

---

## ▶ Next round for the QA bot: round 17 (queued by Claude 2026-10-17)

> **To grok (2026-10-19):** round 17 has been waiting here since Saturday 2026-10-17 (`4c2e4b7`). Your last notes
> name "master 9562574", but that was the tip of Cursor's `too-close-r03` branch, not master, so please pull
> **`master`** fresh. Decisions on your r16 findings (Kimball 2026-10-17):
> - **QA-43: yes.** The 2 mm limit is for the printed blade, checked as 1.75 × designed hang (board R1.8, for Cursor).
> - **QA-44: yes.** The export's extra hub height goes below the blades, and search, score and export use one hub
>   (R1.7, for Cursor).
> - Neither has landed yet. The install guide (R3.3) isn't written yet either, so your Task D waits too.
> - Task C below (numbers for both options) is what lets R1.3 move.

Rounds 14, 15 and 16-hang are **DONE**; results are below. Thank you, they were excellent. Rules: `AGENTS.md`. Board:
`docs/release/RELEASE_PLAN.md`. Build: master after this commit; there is no bundle, so clone from the usual remote copy.
Pre-register A–C in one commit before any data.

| # | task | board |
|---|---|---|
| A | **Reference polars for prop CFD rung A** (prereg `docs/validation/audits/2026-10-17-prop-cfd-fix-prereg.md`). The prop builder's generic section is 6 % thick with camber 0.04; get the exact coordinates from the builder used by `scripts/audit_prop_cfd.py`. Produce C_l and C_d against α 0–10° at Re 6×10⁴, 8×10⁴ and 1.2×10⁵ from NeuralFoil and from XFOIL (Ncrit 9 and 5) if you can run it. Add the nearest **measured** low-Re polar (e.g. Selig/Lyon wind-tunnel E387 or SD-series) as a sanity anchor. Pre-register how far apart the references may be before we call the reference itself uncertain. Output: CSV + note | R2.2a |
| B | **Digitise the two datasets you found** in r15: Shigemitsu 2018 CROR (40 mm) and EPJ WoC 180:02023 centrifugal (60 mm). Give P–Q (and efficiency if given) as CSV with a digitising uncertainty, every geometry number the paper gives, what is missing to build it, and the licence confirmed from the paper itself. Nothing downloaded is committed except your CSVs and notes, with a citation | R2.3, R2.5 |
| C | **Numbers for R1.3 after QA-43/44.** On your 300 r16 designs: the hang-refused share if (i) the check uses 1.75 × designed hang, and (ii) the search uses the export hub (`min_hub_height`, growth below the blades), separately and together. Then say whether your r14 proposed bounds still keep refusals under ~5 % | R1.3, R1.7, R1.8 |
| D | (when it lands) **Release export leak check:** run `scripts/export_release.py` on master after Cursor's R3.1 and grep the export for user paths, `archive/`, `memory/`, `handoff/`, `.bak`, NC data, and files over 5 MB | R3.1 |

Notes to `docs/qa/notes/r17-*.md`, plus a "Round 17" section below.
