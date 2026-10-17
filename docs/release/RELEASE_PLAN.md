# Release plan: Fan Simulator v0.1.0 on GitHub

Owner: Kimball. Written by Claude, 2026-10-17. Rules for every agent are in [`AGENTS.md`](../../AGENTS.md).
The backlog behind this is in [`docs/roadmap.md`](../roadmap.md). This board is the *ordered* subset that gets us to
a release.

**Definition of done for v0.1.0 (Kimball, 2026-10-17):**
- every surface we ship is validated against published data, with a pre-registered tolerance;
- anything not validated is either fixed, hidden, or labelled "experimental, not validated" in both the UI and the
  README;
- no rig measurements are needed for v0.1.0. They come in v0.1.1.

Status legend: `ready`, `blocked (<id>)`, `in progress (<agent>, <date>)`, `paused (<agent>)` + **Resume** note,
`needs Kimball`, `done <commit>`.

CPU: `day` = light, any time except 4–9 PM. `night` = heavy, a Scheduled Task between 9 PM and 3:30 PM.

---

## The path (milestones in order)

| milestone | what it means | gate |
|---|---|---|
| **M0 Trustworthy flow card** | the card's rows measure what they claim and are mesh-robust | R0.1–R0.4 done |
| **M1 Axial validated** | the Fan tab's numbers match two independent published fans, and the optimizer explores the right space | R1.1–R1.6 done |
| **M2 Every other tab decided** | each of propeller, CROR, mixed-flow and volute is validated against published data, or hidden / labelled | R2.x gates |
| **M3 Releasable repo** | anyone can install it from GitHub and run it; the repo is clean, licensed and CI-tested | R3.1–R3.9 done |
| **M4 Release candidate** | a clean-clone install and test pass on Linux (grok) and Windows (Kimball), plus release notes and the tag | R4.1–R4.4 done |

M3 does not depend on M1 or M2, so Cursor can run it in parallel from day one.

---

## M0: Trustworthy flow card

- **R0.1 Push and plane fix (27.3e)**. Lane: Claude. CPU: day. Status: `in progress (Claude, 2026-10-17)`.
  - The card's fixed planes cut through blade rows, so push tracked swirl rather than airflow. The planes are
    now blade-relative, `FLOW_REPORT_VERSION` 4, branch `push-planes-27-3e`.
  - Pre-registered checks F1–F4: `docs/validation/audits/2026-10-17-push-row-planes.md`.
  - Runner: `scripts/push_planes_checks.py`.
- **R0.2 Re-derive the card margins on v4 metrics**. Lane: Claude decides, Cursor implements. CPU: day.
  Status: `blocked (R0.1)`.
  - Re-run `scripts/stock_flow_repeats.py --analyze`, `scripts/stock_flow_mesh_repeats.py --analyze` and
    `scripts/design_flow_mesh_repeats.py --analyze` on v4 (no CFD).
  - Apply the 27.3b rule: 2σ, never tighten, stop lines 0.15 / 3 dB.
  - Kimball approves any constant change in `fansim/cfd/flow_verdicts.py`.
- **R0.3 "Too close to call" state (27.3d)**. Lane: Cursor, from Claude's spec. CPU: day. Status: `blocked (R0.2)`.
  - A row whose design-vs-Stock difference is within the two-run mesh scatter shows "too close to call" (–), not
    ✓ or ⚠.
  - Scatter = √2 × the 2σ of Stock's five-mesh runs, per metric (spec to be written by Claude in R0.2's output).
  - Tests: one synthetic case per row; the 27.3d cases m1–m5 must give no flipping verdicts.
- **R0.4 Noise hint review (27.3c)**. Lane: Claude. CPU: day. Status: `ready`.
  - Cursor's tip-speed + CFM hint (`fansim/acoustics/tip_loading.py`) only varies with CFM, because rpm and tip
    radius are fixed for a12x25. As written, a fan that moves more air reads "louder".
  - Decide: keep it as Expert-only information, or replace it with a loading-based estimate. Test the candidates
    on the 15 runs.

## M1: Axial validated

- **R1.1 Second published axial case: lt120 (roadmap 25.7)**. Lane: Claude pre-registers, Cursor builds the case,
  night runs it. CPU: night. Status: `ready` for the pre-registration.
  - Data: `docs/qa/benchmarks/lt120/`.
  - Pre-register the tolerance (suggested: the same ±5 % CFM band as the A12x25 reference) before building.
  - Note: lt120 is refused by the 2 mm hub-hang limit as a *recipe*. Validate the published geometry as an
    external STL, not through the recipe.
- **R1.2 Loaded branch and shut-off honesty (19.6 / 1.5)**. Lane: Cursor (docs and UI). CPU: day. Status: `ready`.
  - Shut-off is 20–21 Pa against 22.9 published, and steady RANS does not converge at 15–20 Pa.
  - Make sure the UI and README never quote a number above the validated range. Add a test that the P–Q display
    stops at the last converged point.
- **R1.3 Optimizer space under wrap (27.7)**. Lane: grok data (round 14 Task C), Cursor implements, Claude reviews.
  CPU: day for the bounds, night for any re-find campaign. Status: `blocked (grok r14 C)`.
- **R1.4 Stock recipe gap**. Lane: Claude. CPU: day. Status: `ready`.
  - Stock v3 is 55.7 CFM against 58.3 for the reference STL (−4.5 %).
  - Either close the gap or state it in the UI and README as the recipe's known limit. Decide with Kimball.
- **R1.5 Structural and flutter labels**. Lane: Cursor. CPU: day. Status: `ready`.
  - The beam models are unvalidated on real blades (audit-05).
  - Label the structural and flutter outputs "estimate, not validated" in Simple and Expert, plus the README.
    Add a test that the label is present.
- **R1.6 Acoustics claims audit**. Lane: Cursor. CPU: day. Status: `ready`.
  - Grep the UI, export README and docs for any absolute dB(A) claim. Everything must say relative or ranking only
    (audit-06).
  - Add a test that greps the UI copy for "dB(A)" without the word "relative".

## M2: Every other tab decided

The same three steps for each tab:
1. grok finds published data and checks its licence;
2. Claude pre-registers the comparison and tolerance;
3. a night campaign runs it.

Pass ships the tab as validated. Fail means fix it, or ship it labelled "experimental", or hide it, and that choice is
Kimball's.

- **R2.1 Propeller BEMT**: validated against UIUC (C_T PASS; SF static C_P −21 % is a known fail).
  - Lane: Cursor labels the C_P limit; Claude confirms the claims list. Status: `ready`.
- **R2.2 Propeller CFD refine**: FAIL, −44 % C_T against UIUC (audit-08).
  - Recommendation: hide CFD refine for v0.1.0, keeping BEMT. Status: `needs Kimball` (hide, or fix through 4.3).
- **R2.3 CROR**: direction proof only.
  - Lane: grok data hunt for small counter-rotating fan or prop P–Q / thrust data. Status: `ready` (grok round 15).
- **R2.4 Mixed-flow**: no published comparison.
  - Lane: grok data hunt for mixed-flow fan curves at small diameter. Status: `ready` (grok round 15).
- **R2.5 Volute / centrifugal**: CFD is unconverged (17–23 % oscillation), a ±20 % proxy.
  - Lane: grok data hunt for a small centrifugal blower curve. Claude decides converge-or-label. Status: `ready`
    (grok round 15).
- **R2.6 Centrifugal (no tab) and wind turbine (scaffold)**: excluded from v0.1.0.
  - Lane: Cursor makes sure neither is reachable from the cockpit or the README quickstart. Status: `ready`.

## M3: Releasable repo (parallel, mostly Cursor)

- **R3.1 Release export hygiene**. Lane: Cursor. CPU: day. Status: `ready`.
  - Extend `RELEASE_EXCLUDE` and `scripts/export_release.py` to drop `archive/`, `memory/`, `handoff/`,
    `docs/qa/screenshots`, `*.bak`, chat-recovery dumps and any `C:\Users\…` / `E:\…` paths.
  - Test: an export of master contains none of them, and the grep for user paths is empty.
- **R3.2 Packaging**. Lane: Cursor. CPU: day. Status: `ready`.
  - `pyproject.toml`: licence, authors, URLs, readme, classifiers, and a `[project.scripts]` entry point
    `fansim-cockpit = …` (wrapping `scripts/cockpit.py`).
  - Test: `uv build` works, and the installed entry point starts the server with `--help`.
- **R3.3 Install guide**. Lane: Cursor. CPU: day. Status: `ready`.
  - A README install section for Windows and Linux: uv, Docker Desktop / Engine, `docker pull opencfd/openfoam-default:2406`,
    the first Assess, and troubleshooting (WSL2 memory, Docker not running).
  - Test: grok round 15 follows it on a clean Linux box.
- **R3.4 Docker/OpenFOAM readiness badge and first-run check (21.2g)**. Lane: Cursor. CPU: day. Status: `ready`.
  - The cockpit shows "CFD ready / Docker not running / image missing" with the fix in plain words.
- **R3.5 GitHub Actions CI**. Lane: Cursor. CPU: none (cloud). Status: `ready`.
  - Port `.github/workflows/ci.yml` for GitHub: ubuntu fast suite in 3 chunks, plus a Windows job for the fast
    geometry and export subset.
  - Widen ruff to the default rule set on changed files only.
- **R3.6 CHANGELOG, CONTRIBUTING, issue templates**. Lane: Cursor. CPU: day. Status: `ready`.
  - CONTRIBUTING points to `AGENTS.md`'s rules (pre-registration, tests first).
- **R3.7 Cockpit UI regression tests (29.2)**. Lane: Cursor writes, grok proposes cases. CPU: day. Status: `ready`.
  - Headless "we say X, we do Y" tests (`tests/test_ui_says_what_it_does.py`), at least one per tab that ships.
- **R3.8 Validation page**. Lane: Cursor drafts, Claude checks the numbers. CPU: day. Status: `blocked (M1, M2)`.
  - `docs/VALIDATION.md`: per surface, what it was validated against, the tolerance, the result and the known limits.
    Every number links to its audit.
- **R3.9 Large files**. Lane: Cursor. CPU: day. Status: `ready`.
  - Decide per file between Git LFS, a release asset, or out of the export: `validation/reference/fan01/*.stl`
    (11 MB), `cad_model.zip` and `a12x25_impeller.stl`. Keep the CC-BY attribution in `THIRD_PARTY.md`.

## M4: Release candidate

- **R4.1 Clean-clone install and test on Linux**. Lane: grok. Status: `blocked (M3)`.
  - From the release export: follow README install, run the fast suite and one headless cockpit start.
- **R4.2 Windows install and one Assess**. Lane: Kimball, with Claude or Cursor on standby. CPU: night for the Assess.
  Status: `blocked (M3)`.
- **R4.3 Release notes v0.1.0**. Lane: Cursor drafts, Claude checks the claims. Status: `blocked (R3.8)`.
- **R4.4 Tag, publish and create the GitHub repo from the export**. Lane: Kimball. Status: `blocked (R4.1–R4.3)`.

---

## Budget notes

- **Claude** (runs out early in the week): R0.1, the R0.2 decision, R0.4, the R1.1 pre-registration, R1.4, the R2.x
  pre-registrations and the R3.8 number check. Everything else is Cursor or grok.
- **Cursor**: all of M3, the implementation halves of M0 and M1, and any labels.
- **grok**: round 14 (queued), then round 15 = the R2.3–R2.5 data hunts plus R3.3 install-guide dry run.
- **Night**: R1.1 lt120 campaign, R2.x campaigns, any optimizer re-find (R1.3).
