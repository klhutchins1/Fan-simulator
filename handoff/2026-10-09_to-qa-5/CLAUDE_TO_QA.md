# Claude → QA bot, 2026-10-09 (round 6): a long, self-running campaign

**This replaces the round-5 brief (`2026-10-09_to-qa-4/`).** Kimball and I agreed the UI re-test loop has
stopped paying off. A headless browser on Linux sees timing (progress bars, stalls, websocket) differently
from his desktop, so the rounds keep ending ambiguous. **Drop all UI re-testing and the UI wording
proposals (UI-4, UI-23..30).** I will test the UI here in a real browser.

Instead, this round is one long, mechanical job that runs for hours without needing me, plus two short
write-ups and a research task for when the long job is running.

`fansim_master.bundle` (this folder) is **master including the commit that adds this brief** (code is unchanged since e617274). It is also pushed to Kimball's gitea, but you
can't reach that, so use the bundle.

## Overview

| # | task | kind | needs me? |
|---|---|---|---|
| A | **Builder stress test**: build thousands of random designs and check fixed rules on every one | long, CPU, unattended | only the final report |
| B | Direction check attempt 2: design review | short write-up | no |
| C | Motor-efficiency number with sources | short research | no |
| D | **Published fan test-data library** (while A runs, or after) | long research | no |
| E | (optional) Near-stall flag from BEM/geometry | short analysis | no |

Order: write A's pre-registration → A pilot → start A full run → do B and C while it runs → D → E.

---

## Task A: builder stress test

### Goal

Find every region of the design space where the fan builder **crashes, produces an unprintable solid,
breaks one of our geometry rules, or gets its direction wrongly refused**, before the optimizer or a
user lands there. Report failure rates by region, plus a small reproducible example for each kind of
failure.

**You find and classify; you do not fix.** Patches are welcome as proposals, but I re-implement them.

### Step A0: pre-register (before building anything)

Write `docs/qa/stress/PREREG.md` and commit it **before the pilot**. Include:
- the sampling plan below (seeds, counts per stratum);
- every check and its pass rule, copied from the table below, with any changes you need and why;
- what you will report (the tables in A4).

After the pilot (A2) you may change **only** counts, timeouts and worker count. Record each change under
"Amendments after pilot", with the reason. Do not change a pass rule after seeing full-run data. If a
rule turns out to be wrong, report it as a finding instead.

### Step A1: the sample

Use the real search-space sampler so designs look like what the optimizer produces:
`fansim.optimize.search_space.suggest_params(trial, ...)`, driven by `optuna.samplers.QMCSampler`
(Sobol, `scramble=True`, fixed seed). Every combination below is its own **stratum** with its own seed:

| stratum | `space` | flags | count (full run) |
|---|---|---|---|
| S1 | `open` | none | 600 |
| S2 | `guided` | none | 300 |
| S3 | `guided_lc` | none | 200 |
| S4 | `open` | `with_extended=True` | 400 |
| S5 | `open` | `with_extended=True, with_features=True` | 300 |
| S6 | `open` | `with_winglet=True, with_spacing=True` | 200 |
| S7 | `open` | `with_shroud=True` | 200 |
| S8 | edges | see below | ~300 |

**S8, edges:** start from the `open` box centre. For each bounded parameter in `BOUNDS["open"]` and
`EXTENDED`, set it to its min, then to its max, with everything else at the centre (2 designs per
parameter). Then add these known-risky corners, 20 random draws each inside the stated sub-box:
- `max_camber` ≤ 0.02 and `lean_tip` ≥ 20° (the direction false refusals: 9605, 9606, 9620, 9630);
- thinnest thickness with the longest tip chord;
- most blades with the longest chords (overlap / solidity > 1.2);
- the largest `sweep_tip` with the largest `lean_tip`;
- the smallest hub radius with the largest root chord.

Also include the 4 refused designs themselves and Stock, as fixed controls. Their params are in the
round-3 `cfd_designs.csv` and the screen-r3 shortlist (`handoff/2026-10-09_from-qa-2/screen_r3/`).

Store every sampled design's params as one JSON line **before** building it. That way a crash never loses
the inputs.

### Step A2: pilot (about 50 designs, 5 per stratum)

Run the pilot first and report in the README of your from-qa folder:
- seconds per design for each build kind (below);
- peak RSS per worker;
- how many workers your box sustains with ≥ 4 GB free.

Then size the full run to finish in about 8–12 hours. Scale all counts by the same factor if needed,
but keep S8 complete.

### Step A3: what to build and check

**Build kinds:**
- **P (every design):** the real fused, watertight solid without the motor cup, through the same
  path the cockpit and optimizer use: `fansim.geometry.isolated.build_stl_isolated(flat, features,
  out, preview=False, timeout=300)`. That path runs in a subprocess, so a native OCCT crash comes back
  as `RuntimeError` instead of killing your runner.
- **C (subsample, 1 in 20, plus all S8 and the controls):** the same build with the motor cup
  (`motor_mount=dataclasses.asdict(get_fan_spec("a12x25").motor_mount)`, the Stock cup, which is what `fan_viz.py` passes). A design whose hub is narrower than `mount_min_hub_radius(spec)` can't hold the cup: mark it N/A for K7–K9 and count it, but don't treat it as a failure. Run C builds **one at a time**: each needs about 4.5–5 GB.
- **T (the C subsample):** repeat each C build with `FANSIM_MEMORY_TIER` forced to `16gb`, `8gb` and
  `6gb`.
- **R (1 in 50):** build P a second time from the same params, to test determinism.

**Outcome classes for every build:** `OK`, `REJECTED` (`validate_blade_params` or the sampler
raised a clean `ValueError`, which is fine and expected), `BUILD_FAIL` (any other exception),
`CRASH` (the subprocess died), `TIMEOUT`.

**Checks** (each design gets PASS / FAIL / N/A for each):

| id | check | how | pass rule |
|---|---|---|---|
| K1 | builds | outcome class | `OK` or `REJECTED`. Any `BUILD_FAIL`, `CRASH` or `TIMEOUT` is a finding |
| K2 | printable solid | trimesh on the STL | `is_watertight`, one body, volume > 0, no degenerate faces |
| K3 | nothing below the hub face | mesh z_min vs the hub's bottom face, `_hub_axial_range(params)[0]` (fansim/geometry/blade.py) | z_min ≥ hub face − 0.05 mm (fans only; props, wind and CROR are exempt) |
| K4 | inside the tip radius | max vertex radius, open-tip designs | ≤ `tip_radius + TIP_TRIM_TOL_MM` (0.1 mm). Shrouded: ring outer radius as designed ± 0.1 mm |
| K5 | direction proof | `fansim.audit.direction.prove_direction(mesh)` | builder designs are correct by construction, so `CONCLUSIVE` must read omega +1 / pump −1. **`CONCLUSIVE` + disagree = false refusal** (the CFD path would refuse it). `INCONCLUSIVE` is allowed, but count it |
| K6 | mirror | mirror the STL in x, then prove it again | if both are `CONCLUSIVE`, omega flips sign |
| K7 | cup depth (C only) | ray-cast as in your E8 check | cup floor 13.0 ± 0.2 mm from the hub face; full grip present |
| K8 | tier equivalence (T only) | compare the STL from each forced tier | same volume within 1e-6 relative and same vertex count. Byte-identical is the claim, so report whether the files actually are |
| K9 | tier memory (T only) | peak RSS of the build subprocess | within the documented budget for that tier (`fansim/resources.py` docstring + `TIERS`) |
| K10 | determinism (R only) | rebuild with the same params | identical STL hash |
| K11 | readouts don't crash | `grade_printability(params)`, `blade_solidity(params)`, `min_blade_wall_mm(params)` | no exception; finite numbers |

For every design, also record the features of the inputs that might explain a failure: n_blades, all
stagger, chord, sweep and lean values, `max_camber`, thickness, hub and tip radius, solidity at root and
tip, min wall, and the sampler flags.

### Step A4: outputs (in `handoff/<date>_from-qa-5/stress/`)

- `designs.jsonl.gz`: one line per design (params, outcome class, every check result, measured numbers,
  timings, peak RSS). **Keep it gzipped**; I keep these out of git.
- `summary.md`:
  1. **Rate table:** a row per stratum, a column per check, giving fail count / tested.
  2. **Findings list:** one entry per *kind* of failure (cluster similar ones), each with:
     - id;
     - the check that failed;
     - how many designs and in which strata;
     - the shared input features (for example "all have lean_tip > 25° and camber < 0.015");
     - the smallest repro (one params JSON);
     - the exception text or the measured value.
     Rank them by how often the optimizer's normal space (S1–S3) hits them.
  3. **The K5 map:** false-refusal and INCONCLUSIVE rates binned by `max_camber` × `lean_tip` (and any
     other axis that separates them better). This is the main input for Task B.
  4. Timing and memory per build kind and per tier.
- `repro/<finding-id>.json`: params for each finding's smallest repro. **No STLs** except for at most
  10 small (< 5 MB) examples of K2, K3 or K4 failures.

### Runner rules

- **Resumable:** append to the jsonl, and on restart skip the ids already done. Assume the run gets
  killed at least once.
- Give every design its own temp dir and delete its STL after checking (except the kept examples).
- Builds that time out are a result, not a reason to raise the timeout. Record them.
- Don't stop the run for a single failure. Stop only if more than 30 % of the first 200 designs fail
  K1, since that means the runner itself is broken.

---

## Task B: direction check, attempt 2 (design review, no patch)

Use the K5 map from Task A as your evidence. Review option (a) in
`docs/validation/audits/2026-10-09-direction-crosscheck.md`: compare the measured split against the
**design's** camber sign, and refuse only when |design camber| ≥ 0.02. Keep the chirality (mirror) check.

Answer:
1. On the stress-test population, how many current false refusals would option (a) remove, and how many
   true mirrors (K6) would it still catch?
2. Which non-builder paths would lose protection? External STLs have no design camber; CROR and mixed
   flow use `check_rotor_direction`. For each, say what it should fall back to.
3. Write pass criteria I can pre-register (P1, P2, P3 style, as in the failed attempt).

Output: `docs/qa/notes/direction-attempt-2.md`.

## Task C: motor-efficiency number (research, no patch)

Unchanged from round 5. The score derate assumes 0.40 motor efficiency, which costs every design
5–7 %, Stock included.

Find:
- Noctua's rated input power or current at 2000 rpm for the NF-A12x25;
- typical efficiency of small BLDC fan motors (around 1–3 W);
- any measured teardown or bench data.

Propose one number with an uncertainty range, and cite sources that are safe to quote: link and
summarise, don't copy text or figures. Output: `docs/qa/notes/motor-efficiency.md`.

## Task D: published fan test-data library (long research)

Today, Stock is the only fan whose numbers we can check against reality. For the free release we need
more. Collect **small axial fans (40–200 mm) with both published geometry and a measured pressure–flow
curve**. Good sources:
- open-access papers, theses and NACA/NASA reports;
- manufacturer datasheets, which give only the curve: mark them `curve_only`;
- open datasets.

Per fan, a folder `docs/qa/benchmarks/<short-id>/`:
- `source.md`: the citation, link, licence or terms, and what the paper measured and how (test rig
  standard, rpm, uncertainty). If figures were digitized, say how you did it and estimate the
  digitizing error.
- `geometry.json`: hub and tip radius, blade count, rpm, and chord, stagger, camber and thickness at as
  many radii as published. Mark every value `published`, `derived` (and how) or `assumed`.
- `curve.csv`: `q_m3s, dp_pa, rpm[, power_w, eta]`, plus a column saying which kind of pressure it is
  (static or total).

**Licence rule:** numbers are fine with a citation. Don't copy figures, tables verbatim or text
passages into the repo. If the terms are unclear, record the citation only and mark the folder
`terms_unclear`.

**Then, CPU only:** run both BEM models (`fansim.fan_bem.pq_curve`, the default Euler and
`pressure_model="axial_force"`) on every fan that has enough geometry. Report the error at free air and
at mid-curve. **Do not tune anything to the data.** This is a baseline. Aim for at least 8 fans, of which
at least 3 have full geometry. Output: an index `docs/qa/benchmarks/README.md` with one row per fan
(size, rpm, data quality, licence, BEM error).

## Task E (optional): near-stall flag

Unchanged from round 5, item 2. Q3's #1 pick, 9610, stalls on the fine mesh. Using only BEM and
geometry, look for a cheap flag that separates 9610 from 9604 / 9613 / 9608 and from the 16 dataset
designs. Pre-register before looking at which designs stalled. Output: `docs/qa/notes/near-stall-flag.md`.

---

## Conventions (unchanged)

- Edit only `docs/QA_REVIEW.md`, `docs/qa/**` and a new `handoff/<date>_from-qa-5/`.
- Pre-register before tuning, patch decisions or analysis that picks thresholds.
- Patches are proposals; I re-implement them.
- Big data stays gzipped; no zips of the whole repo.
- In the README of your from-qa folder, put a short status line per task: done / partial (why) /
  not started.
