# QA round 20 pre-registration (grok, QA bot)

Written 2026-10-21 MDT, before any round-20 data. Brief: `handoff/2026-10-20_to-qa-20/CLAUDE_TO_QA.md` (repo-r20,
master 027ebcb). Rulings: `docs/validation/audits/2026-10-20-rulings-r18-r19-rungA.md`.

**Repo state recorded before any data:**
- The brief says `r33-install-guide` is unmerged. In fact master 027ebcb already merges it (fe899cd).
- `git diff fe899cd 027ebcb -- fansim pyproject.toml uv.lock tests README.md` is empty. Code, tests and README are
  therefore identical on both, and testing master tests the branch.
- Kimball's PC working tree is on `r33-install-guide`. That is only noted; nothing on it is run.

**Seen before writing this (format only, no values read):**
- the TMR NACA 0012 validation page text, which names the Ladson TM-4074 tripped data as the reference;
- the README install section (the object of Task D).

## A. Feature-design JSON and built hang on all 10 r18 designs (R1.8; QA-43/44/49)
**Designs:** S2_0269, S5_0207, S5_0073, S5_0112, S5_0023, G_0502, S1_0461, S1_0534, S3_0173, S4_0242. These are
the r18 selection, unchanged.

**A1. JSON.** Write `docs/qa/r20/r20-A-feature-designs.json` for the 4 feature designs (S5_*).
- Each design gets `{"flat": r7 flat + section_wrap "cylinder", "features": r7 features}`, exactly as r18 built it
  (`blade_from_flat(dict(flat, section_wrap="cylinder"), Features(**features))`), plus a `_source` note.
- The top-level layout matches `tests/data/hub_hang_designs.json`.
- **Gate A1:** reload the JSON in a fresh process with Cursor's recipe:
  - `blade_from_flat(d["flat"], Features(**d["features"]))`, then
  - `mount_hub_params(p, get_fan_spec("a12x25").motor_mount)[0]`, then
  - `blade_hang_built_mm`.
  - The result must equal the r18 reference within 1e-6 mm.
  - Also, all `BladeParams` fields must equal the r18 build, except `section_wrap` being set the same way.

**A2. Built hang on all 10.** Measure `blade_hang_built_mm(mount_hub_params(p, MOUNT)[0])` on master. For the 6
feature-free designs, measure both with my r18 params and with Cursor's `tests.test_one_hub._r16` recipe.
- **Pass (QA-49 verified):** all 10 match `docs/qa/r18/r18-A-built-hang-reference.csv` `built_hang_ref_mm` within
  ±0.05 mm.
- **Fail:** any design off by more than 0.05 mm. I report it and do not re-tune anything.
- **Also report:**
  - the agreement against the r18 vertex and mesh values;
  - the `mount_hub_params` hub (hub height 15 mm, top face unchanged within 1e-6 mm, z_face equal to r18 within
    1e-4 mm).

**A3. QA-43 (two-stage refusal) on the 10 designs at the mount hub.**
- **Stage 1:** does `validate_blade_params` refuse with "printed blade would hang"?
  - Expected from r18: refuse exactly when 1.75 × designed hang > 2 mm, i.e. designed hang > 1.1429 mm.
- **Stage 2:** does `_refuse_if_built_hang_past_limit` refuse on the built solid?
  - Expected: refuse when built hang > 2 mm, which is 6/10 from r18.
- **End to end:** `build_impeller_parts` is run on the designs that pass stage 1. The prediction is refusal exactly
  when built hang > 2.
- **QA-43 verified:**
  - both stages give exactly the expected decision on all 10;
  - no design with built hang > 2 mm gets through `build_impeller_parts`.

**A4. QA-44 (one hub) on the 10 designs.** Compare the hub z range and the built hang from:
- (i) `evaluate_candidate`'s hub, `mount_hub_params(p, mount)`, read through the same call it makes;
- (ii) the Export flat, `prepare_export_flat(blade_to_flat(p), spec, fit_frame=False, features, fit_hub=True)`
  rebuilt with `blade_from_flat`.

**QA-44 verified:** z_face and z_top agree within 1e-6 mm, and the built hang agrees within 0.01 mm. Any `hub_radius`
change made by `fit_hub` is reported as a separate finding.

## B. Ladson NACA 0012 reference (rung A0 pass reference, R2.2)
**Source:** Ladson, NASA TM-4074 (1988; NASA work, US public domain), from NTRS 19880019495.
- The licence is checked on NTRS and recorded.
- Cross-check: the TMR file `CLCD_Ladson_expdata.dat` (NASA TMR, public domain).

**Values:** C_l and C_d at Re 6×10⁶, M 0.15, tripped.
- Use the report's tables for each trip grit tabulated at that Re and M (80, 120 and 180 grit, if present).
- At α 0°, 5° and 10°, interpolate linearly between the two nearest tabulated α. No curve fit, and no extrapolation
  beyond 0.5°.

**Reference value:** the mean over the grit cases.

**Uncertainty (1 band, reported in parts):**
- half the range across grits;
- the difference between linear and nearest-point interpolation;
- the report's stated measurement accuracy, if given; otherwise I write "not stated".
- The band is the root sum of squares of the three.

**Also report:**
- C_l at 0° (expected ≈ 0, by symmetry);
- the tunnel or α corrections as the report states them;
- the TMR file versus my table read (must match within the last printed digit);
- context only: Abbott & von Doenhoff (untripped) and McCroskey's C_l slope.

**Pass reference for A0**, restated from the ruling: C_l ±5 % at 5° and 10°, and C_d ±20 % at 0°.
- If the reference band itself is more than 2 % of C_l or 10 % of C_d, I flag it.

## C. TU Delft prop: CFD-build details only
**Source:** Casalino et al. 2021, AST 113:106707 (CC BY 4.0), the box copy (sha 9a5c4323…ee01).
- Secondary sources only if they are open-licence and cited, and each is flagged as secondary.
- Chord, twist and C_T/C_Q are not redone.

**Items to list, each with a figure, table or page:**
- hub/spinner diameter and length;
- tip shape;
- blade root (the r/R where NACA 4412 starts, and what lies inside it);
- rig: open jet or wind tunnel, nozzle size, nacelle/motor body diameter and length, sting or support, balance.

Anything the paper does not state is reported as "not stated", never estimated. A value read off a drawing is
labelled "scaled from figure".

## D. R3.3 install-guide dry run (README "Install", master 027ebcb = fe899cd)
**Clean box:**
- a throwaway user `fsdry` with an empty HOME and its own fresh git clone of the bundle in a new `mktemp -d`;
- run with `env -i HOME=… PATH=/usr/bin:/bin`, so the box's `/usr/local/bin/uv` is not visible, as on a clean
  machine;
- system Python is 3.13 (Debian 13), and git and curl are present;
- no Docker is installed, and I install none.

**Follow the guide literally:**
- step 1: the uv install curl, "restart the shell", `uv --version`;
- step 2: clone, cd, `uv sync --extra dev`;
- step 3 (Docker): a "would run" check only. I report what the Linux bullet requires and confirm that `docker` is
  absent. Nothing is installed.
- step 4: run the cockpit command.
  - Pass: it prints a URL, and an HTTP GET of that URL returns 200 within 300 s.
  - Assess (needs Docker): a "would run" check only. I statically confirm the troubleshooting text matches the
    message the code gives without Docker.
- Optional UI test: run it.
- Optional full fast suite: run only if MemAvailable ≥ 10 GB at that moment; otherwise it is "not run (memory)".

**Grade each step:**
- PASS: it works as written;
- AMBIGUOUS: I had to make an assumption, which is logged;
- FAIL: it does not work as written.

**On the first FAIL:** I record it as the brief's stop point. Then I apply the smallest obvious workaround, log it, and
continue so that every later step is also graded, each labelled "after workaround".

**Timing:** each step is timed with time.monotonic, and long steps run with setsid nohup.

## E. R3.1 export leak check
R3.1 has not landed, so this task is waiting and nothing is run.
