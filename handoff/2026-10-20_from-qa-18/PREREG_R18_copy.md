# QA round 18 pre-registration (grok, QA bot), 2026-10-20 MDT, written before any round-18 data

Repo: master 1c86f65 (`/workspace/fansim/repo-r19`). `git diff 46a3408 1c86f65 -- fansim pyproject.toml uv.lock` is
empty, so the r17 run clone `qa/run_r17` (46a3408, same venv) is code-identical and is reused. The brief is
`handoff_in/r18/CLAUDE_TO_QA.md`, with the rulings in `docs/validation/audits/2026-10-19-prereg-amendments-r17.md`.
Box only. No CFD, no fansim edits, nothing committed to repo-rN.

## A. Built-hang reference values for R1.8 stage 2 (10 designs)
**Selection** (`a_select.py`; deterministic, from the existing r17 file `c300_built.jsonl`, no new data):
1. S2_0269 (required).
2. Four feature designs:
   - S5_0207, the r17 miss;
   - the two other feature designs whose r17 export-hub built hang is closest to 2.0 mm;
   - one `random.Random(18001)` draw from the remaining feature designs.
3. Five feature-free designs:
   - the closest below 2.0 mm and the closest above;
   - one seeded draw each (same rng) from h ∈ (0, 1.0], (1.0, 1.8] and (2.5, ∞).

The result, recorded now:

| group | designs |
|---|---|
| required | S2_0269 |
| feature | S5_0207, S5_0073, S5_0112, S5_0023 |
| feature-free | G_0502, S1_0461, S1_0534, S3_0173, S4_0242 |

**Hub (R1.7 semantics):**
- `p_x = replace(p, hub_height_mm=need, blade_hub_z_mm=bias + Δh/2)` when the auto hub < need, with need =
  max(min_hub_height 15, cavity + wall) for a12x25.
- The top face is fixed (asserted to 1e-6 mm), and all growth goes below the blades.
- Hub face z_f = `_hub_axial_range(p_x)[0]`.

**Methods:**
- **M2 (reference, primary):** build the blade exactly as the impeller build does, with `build_blade_solid(p_x)`
  (default flags: realised loft chords via `prepare_loft_chords` including `correct_clipped_sections`,
  feature-raised span and chord resolution, tip trim). This is the solid before `clip_blade_below`.
  - z_min comes from OCCT `BRepBndLib.AddOptimal_s(shape, box, useTriangulation=False, useShapeTolerance=False)`.
  - Signed s = z_f − z_min; built hang h = max(0, s).
- **M3 (cross-check):** the minimum z over all B-rep vertices, plus a fine tessellation (tolerance 0.005 mm) of the
  same solid. Report both.
- **M1 (context):** the r17 section-point value (r16 P2 `sec_zmin` on n_span/n_chord), from r17 data where it
  exists, else recomputed.

**Gates:**
- **A-run:** all 10 build without error. A failure is reported, never substituted.
- **A-self:** |M2 − M3_vertex| ≤ 0.005 mm per design, and |M2 − M3_mesh| ≤ 0.02 mm.
- **A-rep:** a second build in a fresh process for S2_0269, S5_0207 and G_0502 gives an identical M2 within 1e-4 mm.
- **A-repro:** S2_0269 at the auto hub (no R1.7), M2 within 0.05 mm of r16/r17's 2.252 mm.
- **Report:** |M1 − M2| for each design. If any > 0.05 mm, it's a new QA item: the section-point method is not
  good enough for stage 2. The hang is also measured on the clipped blade (`clip_blade_below` at z_f), expected
  z_min ≥ z_f − 0.01.
- **Deliverable:** CSV with id, features, Δh, z_f, z_min, s, h (M2), M3s, M1, flags; this is Cursor's 0.05 mm
  acceptance table. Note in `docs/qa/notes/r18-A-built-hang-reference.md`.

## B. Shigemitsu stagger ruling (amendment §2): velocity triangles, report only
**Inputs** (Table 1 and text, via the r17 note):
- D hub/mid/tip: front 25 / 31.1 / 37.2 mm, rear 26 / 31.1 / 37.2 mm.
- Blades 7/5; σ front 1.61 / 1.40 / 1.22, rear 1.03 / 1.17 / 1.10.
- s front 18.2 / 31.2 / 36.0°, rear 40.6 / 40.0 / 45.5°.
- n front 15 000 rpm, rear 14 000 rpm (counter-rotating). Q_o = 0.55 m³/min.

**Kinematics:**
- c_ax = Q_o / annulus area (front 25–37.2 mm, rear 26–37.2 mm), uniform across the span.
- U = πDn/60. The front inlet has no pre-swirl.

**Conventions:**
- P (ruling, from the rotation plane): chord angle from the axis γ = 90° − s.
- X (from the axis): γ = s.
- Each convention is applied to both rotors.

**Incidence (primary):** i = β₁ − γ, with β₁ = atan(W_u / c_ax) the relative inlet angle from the axis.

**Secondary (generic camber, ruling §2):** NACA mean line, m = 0.04, p = 0.4.
- χ_LE = atan(2m/p) = 11.31°; χ_TE = atan(2m/(1−p)) = 7.59°; camber angle θ = 18.90°.
- i_LE = β₁ − (γ + χ_LE).

**Front exit swirl** (free vortex, geometry only):
- At mid-span, the blade outlet angle β₂′ = γ − χ_TE.
- Carter deviation δ = m_c·θ/√σ, with m_c = 0.23(2a/c)² + β₂′/500, a/c = 0.4, β₂′ in degrees.
- β₂ = β₂′ + δ, c_u2,mid = U − c_ax·tan β₂ (computed per convention).
- Free vortex: c_u2(r) = c_u2,mid · r_mid/r.
- Rear inlet: W_u = U_rear + c_u2(r), since the front swirl opposes the rear's rotation.
- If c_u2,mid ≤ 0 under a convention, that is reported as implausible for that convention.

**Sensitivity:**
- c_ax × 0.85 and × 1.15 (blockage and tip clearance);
- swirl × 0, × 0.5 and × 1.5.
- Euler sanity: ρU c_u2 at mid with ρ = 1.2, against the measured total 510 Pa at Q_o.

**Rules:**
- A station is consistent when |i| ≤ 15° (primary i, nominal).
- Verdict for P:
  - **ALL-SIX** if 6/6 pass;
  - **MID-ONLY** if both mid stations pass and at least one other fails;
  - **MID-FAILS** if either mid station fails.
- **"Clearly inconsistent"** (would be raised against the ruling) only if all of these hold:
  - P passes ≤ 3/6 at nominal;
  - X passes more stations than P;
  - both still hold at every sensitivity setting.
- Otherwise the result is report-only; the ruling stands.
- Also reported: the spanwise sign test, i.e. whether γ(tip) − γ(hub) has the same sign as β₁(tip) − β₁(hub)
  under each convention, with the rear rotor including swirl.
- **Deliverables:** CSV plus `docs/qa/notes/r18-B-shigemitsu-velocity-triangles.md`.

## C. R3.1 export leak check
**WAITING.** R3.1 hasn't landed (master 1c86f65). Nothing will be run.

## Run rules
Anything over a minute runs under setsid nohup, timed with time.monotonic and checkpointed per design (resumable).
New QA IDs start at QA-49.
