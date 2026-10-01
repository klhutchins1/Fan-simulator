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

## Not done

- **CFD both-ways confirmation** (proof 3 in Audit #1's sense): forward vs reversed free-air solves
  for mixed-flow (and the volute), where the designed sense must win on |CFM| and efficiency. This
  needs a pilot for timing and is queued (see roadmap 19.2). The unit's claim is about setup
  conventions, which the geometry proofs establish. The CFD run would confirm the performance
  consequence.
- CROR exports both rotors as one STL. The per-rotor proof meshes them separately in the test, not
  in the production path. That is fine while the builder handedness is fixed (the test pins it).

## Ledger

New unit `cfd.archetype_direction` (CROR/mixed/volute setup functions + `VOLUTE_SPIN`), recorded
PASS on the checks above.
