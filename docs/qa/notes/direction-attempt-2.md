# Direction check, attempt 2: review of option (a) (round 6, Task B; design review, no patch)

Code reviewed at master `31228d0`:
- `fansim/cfd/orientation.py` (`_resolve_direction`, `check_rotor_direction`);
- `fansim/audit/direction.py` (`prove_direction`);
- every caller of both.

The evidence is the failed attempt's 46-design result in `docs/validation/audits/2026-10-09-direction-crosscheck.md`.

**Status: done on partial data.** Task A's stress run was stopped at **n = 120 of 801 planned designs**, so the stress counts below come from 15 % of the planned population. P3a, P3b and P5 need a patch or a build, so they are not tested.
`handoff/2026-10-09_from-qa-5/scripts/direction_option_a_count.py` produced the counts. No builds were run here.

## Q1. Removed false refusals and mirrors still caught
**Option (a) as I'd implement it:**
- Refuse if the proof is CONCLUSIVE and chirality ≠ −1 (the mirror rule, unchanged).
- Also refuse if the proof is CONCLUSIVE, |design camber| ≥ 0.02, and the (ω, pump) split differs from what the **sign** of the design camber implies:
  (+1, −1) for positive camber, (−1, +1) for negative.
- For "design camber", use the largest-magnitude of `camber_root/mid/tip`, falling back to `max_camber`.

**On the evidence available now (46 builder STLs: Stock, 16 cfd_designs and 30 screen-r3 designs):**
- Today's rule refuses 2: 9605 (camber 0.004, lean 26°) and 9606 (camber 0.016, lean 42°). Both have |camber| < 0.02 and correct
  chirality, so **option (a) removes 2 of 2**.
- Mirrors: P2 of the failed attempt refused all 4 y-mirrored parts (Stock, t9005, bem_9504, 9605) on chirality. Option (a)
  keeps that rule unchanged, so it **catches 4 of 4**. A mirror flips chirality, which doesn't depend on camber.
- **Stress population (Task A, `/workspace/fansim/qa/r6_stress/run/designs.jsonl`, n = 120 of 801 planned):**
  - Task A stores nested records without a chirality field. I flattened them with
    `handoff/2026-10-09_from-qa-5/scripts/flatten_stress.py`, setting chirality = ω·pump (the identity the proof uses for its own
    cross-check) and design camber = `meas.inputs.max_camber`.
  - K5 today: 88 PASS, **7 FAIL**, **24 INCONCLUSIVE**, and 1 record with no K5 (S5_0007, no build result).
  - **All 7 FAILs pass under option (a): 7 removed, 0 remaining.** Each one read the split as (ω −1, pump +1), so chirality is still −1
    and the part is not a mirror. Each has |design camber| 0.0008–0.0164, below 0.02. The 7 are S3_0002 and CTL_0001–0004
    (11 blades), plus **S4_0005 (8 blades) and S4_0012 (9 blades)**. So the pattern is low camber with high tip lean
    (22–42°), not specifically 11 blades.
  - **New refusals under option (a): 0.**
  - **Mirrors:** all 95 conclusive K6 mirrors flip ω and are refused on chirality, **95 of 95; none missed**.
  - **24 INCONCLUSIVE: option (a) does not change them.** It only acts on a CONCLUSIVE proof.
    - These are not refusals on the builder path today.
    - On the external-STL path they still cannot be used, and need an explicit orientation.
    - Causes: no cambered sections, a single radius, or sections that disagree.
    - 8 of the 24 have |camber| ≥ 0.02, so a "sections disagree" reading on a properly cambered blade is a separate proof weakness worth a look.
  - **Caveat:** chirality was derived rather than recorded. So the "95 of 95 caught" result tests the rule's logic on the recorded
    (ω, pump), not the proof's independent chirality reading. Chirality misreads cannot be counted from this data. Ask Task A to log `chirality`.

## Q2. Paths that lose protection, and what each should fall back to
| path | how direction is set today | does option (a) apply? | recommended fallback |
|---|---|---|---|
| Axial builder (`objectives.py`, `quick_screen.py`, the axial scripts) | `prepare_axial_cfd(source="builder")` → `_resolve_direction` | yes: the flat/params are at hand | option (a) |
| **Mixed flow** (`centrifugal/evaluate.py:182`) | the **same** builder path | yes, if `params.max_camber` is passed in. Mixed-flow cylindrical cuts cross an inclined, conical blade, so lean-like curvature is *more* likely | option (a) with `max_camber`. If the params aren't passed, use the chirality-only rule (option c) |
| **External STL** (`validate_stl.py`, FAN-01, `run_a12x25_validation.py --stl`) | `source="external"`: proof must be CONCLUSIVE, and the **split decides the direction** | no: no design camber | This is the risky one. A lean artifact here doesn't refuse, it **silently sets the wrong spin**. Suggested: if the median measured camber ratio of the readings is < 0.045 (the zone where lean and camber overlap: lean artifacts 0.031–0.038, real Stock 0.0375), refuse and ask for explicit `orientation=` + `spin=`. Longer term, option (b): cut normal to the stacking line |
| **CROR** (`cror/evaluate.py`, `prepare_cror_cfd`) | convention spins; `proof_verdict: "per-rotor (tests/audit)"`. **No runtime proof at all** | nothing to lose | When front and rear are exported separately, run the chirality-only check on each against its expected chirality |
| **Volute** | `VOLUTE_SPIN = +1`, no proof | nothing to lose | none needed beyond the tests |
| Props | `propeller/direction.py`: spin = chirality | unaffected (already chirality-based) | n/a |

**Correction to the brief:** at `31228d0`, `check_rotor_direction` has **no callers** outside `tests/test_axial_direction_source.py`.
CROR doesn't use it (no per-rotor STL), and mixed flow uses `_resolve_direction`. So option (a) doesn't need to touch it. Either
wire it into CROR when rotors are exported separately, or delete it.

## Q3. Pass criteria to pre-register (P1–P5)
| id | rule |
|---|---|
| P1 | **No false refusals:** every builder STL among Stock, the 16 cfd_designs and the 30 screen-r3 designs passes. That includes 9605 and 9606. **Also**, on Task A's full stress population, false refusals with |design camber| < 0.02 = 0. |
| P2 | **Mirrors caught:** x- and y-mirrored STLs of Stock, t9005, bem_9504 and 9605 are refused (chirality). On the stress population, every K6 pair where the mirrored proof is CONCLUSIVE is refused. |
| P3a | **Mesh–design mismatch caught (replaces the old P3):** Stock's STL built with all station cambers negated, but checked against **Stock's own params** (design camber +0.08), is refused. This simulates a builder that flips camber. |
| P3b | **Backwards design caught at parameter level:** `validate_blade_params` (or the CFD entry) refuses, or warns loudly on, any design with a station camber ≤ −0.02. Test: negated-camber Stock params. Note that `validate_blade_params` (`geometry/blade.py`) has no camber-sign check today, so this is new behaviour. |
| P4 | **No new refusals:** on the stress population, no design that passes today is refused under option (a), except a K6 mirror. |
| P5 | **Existing direction tests green:** `tests/audit/test_direction_geometry.py`, `tests/test_cfd_orientation.py`, `tests/test_axial_scripts_oriented.py`, `tests/test_axial_direction_source.py`, plus the registered checks `audit_status.py` marks CHANGED/AFFECTED. |

Plus one **reported** number, not a pass rule: how many K5 refusals are chirality misreads. Option (a) cannot fix those.
If it is > 0, the proof has a second bug.

## P1–P5 verdicts (stress n = 120 of 801 planned)
The criteria above were written before Task A's data existed. They were **not** hashed or committed in my clone at the time, which is a
late-registration gap. The Q3 section is unchanged since then; its sha256 at evaluation is `e2f85b57b1040777e296dbebe06153ec79d36051d32c863c4120081026d85be6`.

| ID | Verdict | Basis |
|---|---|---|
| P1 | **PASS** | All 7 stress K5 false refusals and the 2 refusals among the 46 designs (9605, 9606) pass under option (a); 0 remain. |
| P2 | **PASS (partly derived)** | 95 of 95 conclusive K6 mirrors refused, plus the 4 y-mirrors from the 46-design evidence. The stress-data chirality is derived from ω·pump (see Q1 caveat). The x-mirror cases were not in the data. |
| P3a | **NOT TESTED** | Needs a negated-camber Stock build; not in Task A's data, and no builds are allowed here. |
| P3b | **NOT TESTED** | New `validate_blade_params` behaviour; there is no patch (design review only). |
| P4 | **PASS** | 0 new refusals among the 88 that pass today. |
| P5 | **NOT RUN** | There is no patch to test. |
| reported | chirality misreads: **not countable** | Task A did not record chirality. |
