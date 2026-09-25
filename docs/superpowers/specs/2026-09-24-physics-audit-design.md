# Physics & math audit — design

Date: 2026-09-24 · Roadmap: §19 · Status: approved design, not yet implemented

## Goal

Prove, with evidence, that the simulator's physics and math are right **for small fans and props
in room-temperature air at sea level**. The proof has to survive code changes, and a re-audit should
check only what actually changed. The audit exists so optimizer winners reflect good fans, not bugs
the optimizer learned to exploit.

**Out of scope:** optimization, random design sweeps, scheduled/weekly runs, startup checks. The
audit never searches a design space. It runs a few fixed reference cases with known answers.

## Who runs it and when

Claude runs it when the user asks ("validate the math" / "run the audit"), when physics code has
changed, or before a design is built or trusted. Fast checks also run with every normal `pytest`.

## Three layers (kept separate in every report)

1. **Verification.** Does the code solve its equations correctly? Units, conservation, sign
   conventions, analytic limits, grid convergence.
2. **Validation.** Are they the right equations for real hardware? Reference cases compared with
   measured data: Noctua NF-A12x25 datasheet P–Q, UIUC prop database thrust/power.
3. **Claims.** Do docs and cited papers match the code? This is a side-by-side review of each module
   against the paper and equation it cites (`docs/bibliography.md`), plus doc statements against
   code behaviour.

## Components

### 1. Unit registry: `fansim/audit/registry.yaml`

One entry per audited piece of physics ("unit"):

```yaml
- id: cfd.cfm_from_outlet_flow
  targets: [fansim.cfd.metrics:parse_fan_metrics]
  claim: "CFM = outletFlow [m³/s] × 2118.882; sign + = delivery toward the outlet"
  source: {kind: standard, ref: "unit conversion; AMCA 210 flow sign"}
  regime: {fluid: air, rho: 1.2, re_chord: [1e4, 2e5], mach_tip: [0, 0.3]}
  checks: [tests/audit/test_cfm_units.py, ref:a12x25_free_air]
  depends_on: [cfd.flow_direction_convention]
```

`kind` is one of `paper | datasheet | standard | derivation`. For a paper, `ref` names the
bibliography entry and equation number.

### 2. Fingerprint ledger: `docs/validation/audits/ledger.json`

For each unit that passed:
- the hash of its targets' **normalized AST** (comments, docstrings and whitespace stripped, so only
  logic changes count),
- the relevant library versions (numpy/scipy for BEM; the OpenFOAM image tag for CFD),
- the verdict date and a link to the evidence report.

The ledger is updated **only on PASS**.

### 3. Status command: `scripts/audit_status.py`

Sorts every unit into one of five states:

| State | Meaning | Action |
|---|---|---|
| PROVEN | hash + libs unchanged since PASS | skip |
| CHANGED | own code or library changed | re-audit |
| AFFECTED | a `depends_on` unit is CHANGED/NEW/FAIL | re-audit |
| NEW | registered, never passed | audit |
| UNREGISTERED | physics-looking code in `fansim/{cfd,acoustics,propeller,cror,centrifugal,volute,wind_turbine,structural,physics}` or `fan_bem.py` with no registry entry | register, then audit |

UNREGISTERED detection is a heuristic: public functions in those packages that are not covered by any
`targets`. False positives are resolved by an explicit `exempt:` list in the registry. A new paper or
library enters the audit as a new or changed registry entry.

### 4. Air-regime layer (the "are we on Earth?" checks)

- **One source of air properties:** `fansim/physics/air.py` holds ρ, ν, μ, c₀ and p₀ for
  room-temperature sea-level air. An audit test fails if any module defines its own copy.
  *Known finding:* 15 local copies exist today (e.g. `cfd/metrics.py`, `fan_bem.py`,
  `propeller/bemt.py`, `acoustics/proxies.py`), with ρ = 1.2 in fans/CFD and 1.225 in
  props/turbines. Both values are defensible (AMCA test conditions vs ISA). The fix is two named
  constants (`RHO_AMCA`, `RHO_ISA`) with the reason recorded, not silent copies.
- **Regime checks per reference case:** compute chord Reynolds number, tip Mach and advance ratio,
  reusing `fansim/physics/regime.py`, and assert that each lies in the band the unit's `regime:`
  declares.
- **End-to-end reality envelopes:** a 120 mm × 25 mm axial fan at 2000 rpm must land within the band
  that real fans of that class reach (free air and shut-off). A UIUC prop must land within tolerance
  of its measured C_T/C_P. A result outside the envelope fails loudly, even when self-consistent.

### 5. Evidence types

- **Fast checks:** `tests/audit/`, plain pytest, run every time. They lock in what an audit proved
  (e.g. "the blade geometry implies pumping toward X"), never merely what the code currently says
  (e.g. `assert rig.spin == -1` is not a proof).
- **Reference runs:** CFD/BEM on fixed cases, marked `docker`/`slow`, run during an audit:
  - `a12x25_free_air` and `a12x25_near_shutoff`: Stock recipe and close-ref STL, against Noctua.
  - `a12x25_spin_ab`: forward vs reversed, same mesh, both converged.
  - `uiuc_<prop>`: 1–2 props with measured static and advancing data.
- **Paper review:** a written code ↔ equation mapping in the report, covering symbols, units,
  assumptions and any deviations with reasons.

### 6. Reports: `docs/validation/audits/YYYY-MM-DD-<scope>.md` + `.json`

One row per unit checked, with:
- the claim,
- the method,
- the measured value, the expected value and the tolerance,
- a verdict: PASS, FAIL, DRIFT (passes, but the number moved beyond noise since the last PASS), INCONCLUSIVE or SKIPPED (see Error handling),
- evidence links (test id, CFD case directory, bibliography entry).

A report ends with a plain-language verdict and lists what it did **not** check. If a CFD-affecting
unit changed, the report also bumps `CFD_VERSION` (`fansim/cfd/metrics.py`) so §18 quarantines
old scores.

## Optimizer guard (audited, not part of the audit machinery)

Dead designs must be rejected by the optimizer, not scored. Dead means zero, negative or reversed
flow, or thrust below a floor. This is registered as a unit (`optimize.reject_dead_designs`, target
`fansim/optimize/objectives.py`), and its check shows that a known-dead geometry is refused.

## Audit #1: flow direction & sign conventions (first run)

**Scope:** the axial fan (Stock a12x25 + close-ref STL). The prop sign handling is included because
it shares the same failure mode.

**Freeze:** no changes to spin, flow direction, blade handedness or motor side until the verdict
(roadmap banner + §19.1).

**Evidence of the problem:**
- The spin A/B smoke gave `spin=-1` → +42.4 CFM (not converged) and `spin=+1` → −70.5 CFM
  (converged). The script picked by sign only.
- Written conventions disagree: ea96f40 says the blades pump −Z; `domain.py` says +Z; roadmap §16.1
  describes the reverted state; glyphs now draw +Z.
- `propeller/calibrate.normalize_metrics_sign` flips spin until thrust > 0, which can mask exactly
  this bug.

**Proofs required (all three must agree):**
1. **Geometric.** Measure pitch/stagger sign vs radius from both STLs and derive which rotation makes
   the LE lead, and therefore which way the blade pumps. No CFD involved. Also check the real-fan facts the user confirmed from a
   photo (2026-09-24). Seen from the open intake side (hub cap toward the viewer, struts behind),
   the rotor turns **counter-clockwise**, the **blade tips lead** the rotation, and air flows away
   from the viewer toward the struts. So the model must show real-fan chirality, tips leading its
   designed rotation, and the open motor cup on the exhaust side.
2. **Contract tests.** Pin the meaning of `spin`, `flow_sign`, the inlet/outlet BCs, the
   `outletFlow` sign, the thrust/torque signs and the glyph direction against the geometric proof.
3. **CFD matrix (bias-free).** The free-air BCs are asymmetric (total-pressure inlet at −Z, static
   outlet at +Z), so reversed through-flow gets easier BCs. The 2026-09-24 spin A/B is therefore not
   evidence. Run {as-built, flipped 180° about X} × {spin −1, +1} at free air on converged solves.
   A flip about X maps body rotation ω → −ω, so each physical rotation sense appears twice: once
   pumping +Z through the proper BCs ("proper run") and once pumping −Z ("improper run").
   - The designed sense must win on its proper run: at least 20% more CFM **and** higher CFM per shaft
     watt (static rise is ~0 at free air, so η is not usable).
   - It must match the geometric proof.
   - The report records improper − proper |CFM| per sense as the measured BC bias.

**After the verdict:**
- Make code, docs, glyphs and roadmap §16.1 agree.
- Replace `normalize_metrics_sign` masking with an explicit error or the derived direction.
- Bump `CFD_VERSION`.
- Re-run the Stock P–Q and re-state the gap in `a12x25_pq_report.md`.
- Lift the freeze.
- Roadmap §19.2–19.4 (direction derived from geometry, a permanent reverse-rotation check,
  CW/CCW mirror export) follow later and are not part of this spec's implementation.

## Implementation order

1. Registry schema, AST fingerprinting, ledger and `audit_status.py`, with tests.
2. The `fansim/physics/air.py` single source plus the duplicate-constant check. This is a finding
   list only: consolidating the copies is a separate change after Audit #1, because it moves
   numbers and would muddy the direction verdict.
3. Audit #1: geometric proof → contract tests → CFD A/B + axis-flip runs → report.
4. Register the remaining axial units (BEM, metrics, P–Q, shut-off), then acoustics, props and the
   other archetypes, one audit each.

## Error handling

- A reference run that fails to converge gives an **INCONCLUSIVE** verdict, never PASS.
- A missing Docker image or dataset gives **SKIPPED** with the reason. Neither counts as proof, and
  the ledger is not updated.
