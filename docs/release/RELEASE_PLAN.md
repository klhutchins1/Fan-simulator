# Release plan: Fan Simulator v0.1.0 on GitHub

Owner: Kimball. Written by Claude, 2026-10-17; pruned to live open work 2026-11-28 (Epic #169 P2.2).
Rules for every agent are in [`AGENTS.md`](../../AGENTS.md). Completed M0–M3, RV-0–RV-5, UX-1/UX-2, and Print-Session-1
history lives in [`RELEASE_DONE.md`](RELEASE_DONE.md).

**Active v0.1.0 close-out epic:** [`docs/release/EPIC_V010.md`](EPIC_V010.md) · GitHub tracking issue
[#169](https://github.com/klhutchins1/Fan-simulator/issues/169).

**Definition of done for v0.1.0 (Kimball, 2026-10-17):**
- every surface we ship is validated against published data, with a pre-registered tolerance;
- anything not validated is either fixed, hidden, or labelled "experimental, not validated" in both the UI and the
  README;
- no rig measurements are needed for v0.1.0. They come in v0.1.1.

Status legend: `ready`, `blocked (<id>)`, `in progress (<agent>, <date>)`, `paused (<agent>)` + **Resume** note,
`needs Kimball`, `done <commit>`.

CPU: `day` = light, any time except 4–9 PM. `night` = heavy, a Scheduled Task between 9 PM and 3:30 PM.

---

## Milestone Summary

| milestone | what it means | status |
|---|---|---|
| **M0 Trustworthy flow card** | the card's rows measure what they claim and are mesh-robust | `done` (R0.1–R0.4; see [`RELEASE_DONE.md`](RELEASE_DONE.md)) |
| **M1 Axial validated** | Fan tab matches two independent published fans; optimizer explores the right space | `done` (R1.1–R1.11; see [`RELEASE_DONE.md`](RELEASE_DONE.md)) |
| **M2 Every other tab decided** | Prop BEMT validated; Prop CFD, CROR, Mixed-flow, Volute labelled experimental | `done` (R2.1–R2.7; see [`RELEASE_DONE.md`](RELEASE_DONE.md)) |
| **M3 Releasable repo** | clean export, packaging, install guide, CI, UI tests, validation page | `done` (R3.1–R3.9; see [`RELEASE_DONE.md`](RELEASE_DONE.md)) |
| **Review & safety nets** | RV-0 ledger, RV-1 snapshot, RV-2 scoreboard, RV-3/RV-4/RV-5, UX-1/UX-2, CI-1 | `done` (see [`RELEASE_DONE.md`](RELEASE_DONE.md)) |
| **M4 Release candidate** | clean-clone install & test on Linux and Windows, refreshed release notes, tag | **open** (R4.1–R4.4 below) |

### Decision (Kimball, 2026-11-15): ship v0.1.0 with four surfaces labelled, not validated

**Propeller CFD, volute, mixed-flow and CROR ship as "Experimental: not validated against published data"** (R2.7 `616aa33`).
Their validation moves to v0.1.1 (frozen for v0.1.0: R2.2a″ A0c / R2.2c–d, R2.3a–b CROR vs Shigemitsu, R2.4 Mixed,
R2.5a–c Volute vs EPJ). What ships validated: the axial Fan tab (M0, M1) and the propeller **BEMT** fast estimate
(R2.1 + Epic #169 P1B `04c4d4c`).

---

## Open Work for v0.1.0

### Work outside the repo: Windows PC rescue (W1)

- **W1 Get every stranded piece on the Windows PC into the repo.** Lane: Kimball + Cursor (Windows). CPU: none.
  Status: `needs Kimball` (Windows-only drives `T:/Projects/*` are unreachable from Linux).
  - Check: `scripts/stray_work.py` must list nothing on the Windows PC.
  - **`T:/Projects/fansim-merge-master` (`stock-outline`):** 17 local commits + uncommitted files; commit, push, add a board task.
  - **`T:/Projects/fansim-a0c-wake` (`r22a-wake-aspect`):** ~500 uncommitted lines in `scripts/prop_section_2d.py` + test; commit & push so v0.1.1 A0c work is not lost.
  - **Main checkout `T:/Projects/Fan Simulator`:** commit/archive any remaining local handoffs/research not on GitHub, then return checkout to clean `master`.
  - **`T:/Projects/fansim-p1-glyphs`** and **`T:/Projects/fansim-r110-g2-merge`:** keep anything absent from `master`, push/drop, remove worktrees.
  - Loose October debug scripts/logs in `T:/Projects/` (`dbg_*.py`, `*.log`) can be deleted.

### M4: Release candidate

- **R4.1 Clean-clone install and test on Linux.** Lane: Cursor / grok. Status: `ready` (re-verify from current release export after Phase 1 & Phase 2 merges — Epic #169 P3.2).
  - Previous check (2026-11-26): `scripts/export_release.py` (1314/2738 files), `uv sync --extra dev`, `fansim-cockpit --help`, 26/26 core tests, HTTP 200 headless cockpit start.
- **R4.2 Windows install and one Assess.** Lane: Kimball (Cursor/Claude on standby). CPU: night for Assess. Status: `needs Kimball`.
- **R4.3 Release notes v0.1.0 refresh.** Lane: Cursor drafts, Claude checks claims. Status: `ready` (initial draft landed `0b9c792` PR #108; refresh for `CFD_VERSION=7`, FW-H, perf, and Epic #169 P1A–P1D math fixes — Epic #169 P3.1).
  - Sync `docs/release/RELEASE_NOTES_v0.1.0.md`, `docs/VALIDATION.md`, `docs/validation/scoreboard.md`, and `CHANGELOG.md` (`## Unreleased` until R4.4 tags `v0.1.0`).
- **R4.4 Tag, publish and create the GitHub release from the export.** Lane: Kimball. Status: `blocked (W1, R4.1–R4.3)`.

---

## Print session 1 (non-blocking; runs beside v0.1.0)

Completed items (P1/§28.3 `2bfde35`, P2 `f60d234`, P3, P4a `0beb057`, N1) are archived in [`RELEASE_DONE.md`](RELEASE_DONE.md).
Pre-registration: `docs/validation/audits/2026-11-09-first-print-tach-phone-prereg.md` (T1–T6).

- **P4 The session.** Lane: Kimball. Status: `needs Kimball` (in progress). T2 27.41 g record-only; T1/T3 failed on old H7MQ8 opening/glyph size; still open: full impeller with 37.25 mm opening, T4 tach/phone, T5 12 V rpm, T6 bag.
- **P5 Write up.** Lane: Claude or Cursor. Status: `blocked (P4)`. Fill Results table in the pre-registration after P4 completes.
- **P6 Enlarge print-id glyphs (T3 coupon).** Code `done 2bfde35`; **needs Kimball** to print `exports/H7MQ8_id_coupon_20261111-190250.stl` (marked face on bed, no supports) and re-test T3.

---

## After v0.1.0 (parked for v0.1.1 / v0.2; not release work)

- **Frozen CFD validations:** R2.2a″ A0c / R2.2c–d (Prop CFD), R2.3a–b (CROR vs Shigemitsu 2018), R2.4 (Mixed-flow), R2.5a–c (Volute transient + EPJ 2018).
- **Deferred QA polish (Epic #169 P2.1):** `UI-23`, `UI-26`–`UI-29`, `QA-77` (triaged `deferred v0.1.1` in `docs/QA_REVIEW.md`).
- **Physics / solver v0.2:** `#86` (open), `#90`, `#93`–`#96` (axial Fan BEM calibration), `#125` item 1 (`tonal.py` Curle/A-weighting), `#185` (`CFD_VERSION=7` reference refresh if needed).
- **Rig measurements & print session 2:** roadmap §28.4 (record by `print_id`), grok lead 15 balance tolerance (`docs/qa/notes/balance-tolerance-proposal.md`), grok lead 16 tap-test calibration of `FDM_E_K` (`docs/qa/notes/tap-test-calibration-proposal.md`).
