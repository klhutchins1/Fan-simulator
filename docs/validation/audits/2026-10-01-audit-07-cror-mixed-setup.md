# Audit #7: CROR, mixed-flow and volute CFD setup (2026-10-01)

Question: do the non-axial machine types turn their rotors the way they are designed to in CFD,
and does each MRF zone cover its blades? Audit #1 found the axial rotor solved backwards. Roadmap
19.2 left CROR and mixed-flow unwired, and the volute was never checked.

The work started 2026-09-29 and stopped at the usage limit. It was ported to the 2026-10-01 master
and finished here.

## Plain-language verdict

**All three were set up wrong. They are fixed and checked by geometry.**

| machine | before | after |
|---|---|---|
| mixed-flow | built with axial handedness (designed ω_z +1, pumps −Z) but solved **as built at spin −1**: rotor turned backwards. MRF zone (analytic ±z_span/2 + 2 mm) too short for the blade overhang. | CFD copy flipped 180° about X (`prepare_axial_cfd`, builder source) at spin −1, MRF fitted to the STL |
| CROR | both rotors solved **as built**: front (designed +1) at −1, rear (designed −1) at +1, so **both backwards**. Inner zone edges could leave blade tips in the inter-rotor gap as stationary wall. | `prepare_cror_cfd`: flipped copy, zones from `cfd_dual_mrf_dict` (upstream = former rear, +ω; downstream −ω), inner edges grown to the real blades, `check_cror_blades_in_zones` refuses any blade vertex outside both zones |
| volute | spin **−1**, so the flow ran down the shrinking scroll toward the tongue | `VOLUTE_SPIN = +1`: the scroll widens toward +θ (θ CCW from +X, MRF axis +Z), so the swirl must be CCW |

## Proofs (`tests/audit/test_cror_mixed_setup_audit.py`, 12 tests, geometry only)

1. **CROR direction.** Each rotor is meshed alone, exactly as `build_cror` places it. The mesh-only
   direction proof reads front (+1, −Z) and rear (−1, −Z): CONCLUSIVE, a counter-rotating pair
   delivering to the same side. On the flipped CFD copy, each rotor's proved ω sign equals the
   omega written for its zone, and both pump +Z.
2. **CROR sections.** The rear is the exact t → −t mirror of the front: same chord, stagger and camber
   position (0.4, the recipe value), opposite LE angle, LE on the same face. Each LE leads for its
   own ω. This confirms the 3a577c6 exemption for negative stagger.
3. **CROR placement.** The flipped STL sits inside the fitted zones, the zones do not overlap, and a
   zone chopped by 4 mm is refused.
4. **Mixed-flow direction.** As built: CONCLUSIVE (+1, −Z). Oriented: (−1, +Z) at spin −1. The
   conical hub's small eye faces the −Z inlet.
5. **Mixed-flow placement.** The analytic MRF zone fails `check_placement` on a 10 mm span. The
   fitted one passes with a 2 mm margin.
6. **Volute.** The flat radial blades read INCONCLUSIVE, correctly: they have no concave side. The
   scroll radius grows with +θ, so the spin is +1, and the MRF zone sits inside the scroll bore.

All of the CROR/mixed/volute tests and the related existing tests pass (175 + 12). Two mocked
mixed-flow tests now stub the orientation step because their STL is fake.

## What this invalidates

Earlier CFD results for these machine types were solved backwards and should not be used:

- `runs/campaign_mixed_vs_axial/summary.md` (2026-09-05): mixed-flow 39.3 CFM free, **5.3%
  efficiency, unconverged**. Its conclusion, "default mixed-flow does not beat axial", needs a
  re-run before it means anything.
- `runs/cror_smoke/notes.md` (2026-09-06): **~93% efficiency**, which is unphysical.
- Any mixed / CROR / volute cockpit or optimizer scores.

`docs/validation/keep_cut_board.md` keeps these scaffolds "secondary to the A12x25 band". That
decision still stands, but it rested partly on the mixed-flow campaign above.

## Proof 3: CFD, designed vs reversed rotation (2026-10-01)

`scripts/audit_archetype_direction_cfd.py` meshes each machine once in its production setup and
solves free air at both spins on that same mesh. The rule was fixed before any run: PASS needs
designed ≥ 1.10× reversed on CFM and on CFM/W, with both solves converged.

| machine | designed | reversed | verdict |
|---|---|---|---|
| mixed-flow (250k cells) | **+73.3 CFM**, 0.80 W, converged | **−44.3 CFM** (pumps backwards), 0.66 W, converged | **PASS** |
| CROR (309k cells, Delta AFC1212DE spec, 3900 rpm) | **+209.0 CFM**, 9.47 W, converged; each rotor does work (front M_z·ω −4.31 W, rear −5.16 W) | **−186.1 CFM** (pumps backwards), 4.66 W, converged | **PASS** |
| volute (102k cells) | 29.7 / 30.5 CFM (two runs), 3.70 W, converged | 24.7 / 25.0 CFM, 3.42 W, oscillating (20–24%), drift 6.5% on the second run | **INCONCLUSIVE** (reversed unconverged) |

- **Mixed-flow:** spun backwards, the rotor drives air against the duct. The old 2026-09-05 campaign
  ran exactly that way and got 39.3 CFM at 5.3% efficiency. Solved the designed way, free air is
  73.3 CFM.
- **Volute:** both runs put designed ~20% above reversed. The reversed blower settles into a steady-RANS
  limit cycle, so by the rule this is not a CFD proof. The direction rests on the scroll geometry
  (proof 6), which is first-principles. Flat radial blades do the same ideal (Euler) work either way,
  so only the scroll can decide.

Evidence: `docs/validation/audits/direction_cfd_mixed.json`, `direction_cfd_volute.json`.

### Bugs this proof found

1. **Sanity treated the volute as an axial duct.** With no `case_meta.json`, `_infer_case_meta`
   assumed a uniform duct inlet, so inlet bookkeeping FAILed on a misapplied formula. Volute cases
   are now recognised (`constant/volute_domain.json`), and the duct-only checks SKIP.
2. **The volute "outlet area" was the stub section (5.6 cm²), but the solver's outlet patch is the
   whole +X face (59.4 cm², measured from the mesh).** The stub ends 12 mm short of the face. With the
   stub area the energy check read η_total = 1.43 on the designed solve, which is impossible. (An
   earlier, interim reading of ~0.92 came from the same error.) The check now uses the measured
   patch, giving η_total 0.008: at free air the jet dissipates in the box before reaching the outlet
   face. Volute scoring never used this area; only the new sanity path did. The designed row in
   `direction_cfd_volute.json` still shows the old energy FAIL, which is this bug.
3. **CROR shaft power counted only the net torque.** Both rotors shared one `impeller` patch, so their
   opposite reaction torques cancelled. On the designed CROR solve the net M_z is 0.0021 N·m, against
   0.0106 + 0.0127 N·m per rotor, so the old bookkeeping read **0.85 W instead of 9.47 W (11× low)**.
   That explains the 2026-09-06 smoke's ~93% efficiency. Dual-MRF cases now split the surface at the
   inter-rotor gap into `impeller` (upstream) and `impellerRear` (downstream, a rotating wall with its
   own `forcesRear` monitor). Torque is the sum of |M_z| over both rotors, and `power_sign` checks
   each rotor against its zone ω. A mesh dry run confirmed both patches (5314 / 4495 faces).
4. **The result file crashed on an infinite ratio** when reversed pumped backwards. The ratio is now
   null and `reversed_pumps_backwards` is true.

## Follow-up: domain (2026-10-01, commit 32d3b95)

The proof-3 runs above used the mixed-flow / CROR evaluate setup as it stood: the **v4
full-length tube** (`export_casing_stl(stepped=False)`, ~0.7 m of pipe friction, −34 % on the
A12x25 in Audit #2) and a fixed default mesh. The direction verdicts compare the two spins *within*
one domain, so they stand. The absolute CFM numbers (73.3 / 209 CFM) are v4-domain values and are
**not** performance claims. `evaluate_mixed_flow`, `evaluate_cror` and the direction script now
use the axial optimizer's validated setup: the sealed 25 mm ring plus wall-sized mesh refinement.

## Not done

- **Volute CFD confirmation: closed as INCONCLUSIVE (2026-10-02).** A finer mesh (base 4 mm,
  220k cells, `direction_cfd_volute_fine.json`) gave designed 27.2 vs reversed 22.3 CFM (1.22×).
  Across three runs on two meshes, designed beats reversed by 1.20–1.22× every time. But both
  spins oscillate 17–23 % (tongue/scroll unsteadiness that steady RANS cannot settle), and each
  mesh leaves one solve just outside the 2 % rule. **The volute direction rests on the scroll
  geometry proof, with a consistent but unconverged CFD trend. Volute absolute numbers are a
  ~±20 % proxy.** Converging it would need transient CFD.
- CROR exports both rotors as one STL. The per-rotor proof meshes them separately in the test, not
  in the production path. That is fine while the builder handedness is fixed (the test pins it).

## Ledger

New unit `cfd.archetype_direction` (CROR/mixed/volute setup functions + `VOLUTE_SPIN`), recorded
PASS on the checks above.
