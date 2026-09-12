# Ring-to-frame gap in optimizer CFD

**Date:** 2026-09-02  
**Status:** draft  
**Approach:** A — pin the existing square duct to `spec.tip_dia_mm[1]`; leftover gap = frame/2 − built r; refuse leftover < `--tip-gap`  
**Roadmap:** §7.5 remainder (CFD clearance). Not winglet×shroud policy, not circular AMCA.  
**Amends:** `docs/superpowers/specs/2026-09-01-honest-cfd-design.md` (optimizer no longer grows a 0.5 mm custom duct)

## Plain language

The square CFD duct is a stand-in for the **inside of the fan frame**, not a
custom tunnel around each impeller and not the PC case. Today every trial —
open or shrouded — gets a duct sized to **built OD + 0.5 mm**, so a small
rotor is scored as if you printed a tight housing around it. `--shroud`
already shrinks blades to fit the 110 mm A12x25 envelope, but CFD never
sees that fixed barrel.

This cycle pins the duct to the spec frame ID. Filling the barrel tightens
the leak; an undersize impeller is punished. Leftover tighter than 0.5 mm
(stock A12x25 clearance) is refused, not meshed.

## Problem

`rig_for_impeller` sets

```text
duct_r = open_tip_rmax_mm + shroud_thick_mm + tip_gap_mm
```

`evaluate_candidate` always passes `tip_gap_mm = 0.5`. Growing the rotating
ring grows the tunnel. The four-bar `frame.stl` is exhaust struts only;
there is no barrel around the rotor. Remaining leak after a full ring is
**ring-to-frame**, and screening never scores it as leftover space in a
fixed housing.

## Goal

Every spec-backed CFD run (optimizer `evaluate_candidate` and cockpit
Assess):

1. Pins the square duct ID to `spec.tip_dia_mm[1]` (110 mm on a12x25,
   119 mm on generic_120).
2. Sets remaining gap = `casing_id/2 − built r` (built r includes the
   rotating ring when it is on).
3. Treats `--tip-gap` as the **minimum leftover** (default **0.5 mm**).
   Below that, or overlapping the wall → infeasible, no mesh.
4. Passes that leftover into open/partial BEM (`K_TIP_LEAK`). A full ring
   still uses Prandtl `F = 1` (ring-to-frame leak stays CFD-only).
5. Stamps `tip_gap_mm` (actual leftover), `casing_id_mm`, and
   `tip_gap_floor_mm` on the trial.

`--shroud` still only stamps the hoop. It does not change the casing rule.

## Non-goals (this spec)

- Circular AMCA 210 / ISO 5801 duct, venturi inlet, extra barrel STL
- Winglet auto-zero or a winglet×shroud search policy
- Searching gap, ring thickness, or `shroud_height_frac`
- Changing `check_build` 110 mm (CFD floor is separate: scored max ≈ 109 mm
  on a12x25)
- Catalog backfill of old custom-duct scores
- Third CFD solve / mesh refinement of a 0.5 mm gap (still under-resolved,
  same as §1.1)
- Changing `rig_for_impeller`'s growing-duct default for callers that pass
  no spec (validation / printed-part scripts)
- Changing BEM `DEFAULT_TIP_GAP_MM` (0.5 mm stays the no-spec default)
- Propeller tab

## Casing

The square screening duct stays. Pinning `duct_radius` to
`spec.tip_dia_mm[1] / 2` means every a12x25 trial shares a **110×110 mm**
square, so CFM from inlet velocity is comparable. Today a larger impeller
also got a larger tunnel.

```text
today:      duct = built OD + 0.5 mm      (gap always 0.5)
this spec:  duct = spec frame ID          (gap = leftover, if ≥ floor)
```

Shared helper (section-point walk, no CadQuery):

```text
remaining_tip_gap_mm(params, casing_id_mm) -> float
  built_r = open_tip_rmax_mm(params) + shroud_thick_mm
  return casing_id_mm / 2 − built_r
```

`rig_for_impeller(..., casing_id_mm=None)`:

- `None` (default): today’s growing duct (`envelope + tip_gap_mm`).
- Set: `duct_radius = casing_id_mm / 2`; `TestRig.tip_gap` is the leftover.
  The caller is responsible for the floor check.

Validation scripts (`validate_a12x25.py`, `rig_for_impeller` without a spec)
keep the growing path. Four struts still span to `duct_radius − 0.1 mm`, so
they match the pinned barrel.

## Gap floor

`--tip-gap` on `scripts/run_optimization.py` is the **minimum leftover**,
not a growing-duct clearance. Default remains `OPTIMIZER_TIP_GAP_MM` (0.5).
Cockpit Assess uses the same 0.5 mm floor (no new slider).

On every spec-backed eval:

1. `remaining = remaining_tip_gap_mm(params, spec.tip_dia_mm[1])`
2. If `remaining < tip_gap_floor` (including ≤ 0 / overlap) → infeasible.
   Reason names the frame and both numbers. No STL, no BEM, no mesh.
3. Else pin the rig to the spec ID and use `remaining` as the CFD gap.

Gate order: mountable → printability → stress → **gap floor** → BEM
prescreen → geometry → `check_build`.

`check_build` still allows a 110 mm OD (or 110 + leeway). CFD will not:
leftover 0.4 mm is refused. Effective scored max on a12x25 is **109 mm**.
Cockpit leeway past 110 mm also fails this gate; score a bigger rotor on
`generic_120` (119 mm casing).

Default `BladeParams()` (`tip_radius = 56.5 mm`, old 120 mm envelope) is
infeasible on a12x25 by this gate — cheap, before CAD. Today it only dies
after an STL that fails `check_build`.

CLI help: minimum leftover to the frame. `--shroud` help must not say
clearance follows the old growing gap. No `★`.

## Trial / catalog

No backfill. New meaning of `tip_gap_mm` on spec-backed rows:

| Field | Meaning |
|---|---|
| `tip_gap_mm` | leftover actually used, or the leftover that failed the floor |
| `casing_id_mm` | frame ID we pinned to |
| `tip_gap_floor_mm` | the `--tip-gap` floor |

Old rows keep `tip_gap_mm = 0.5` with no `casing_id_mm` — that still means
“custom growing duct.”

## BEM

Open and partial tips (`not shroud_is_full`) pass `tip_gap_mm=remaining`
into `pq_curve` / `operating_point` so `--bem-prescreen` knocks a small
open impeller in the same direction CFD will.

A **full** ring still sets `F = 1` and skips `K_TIP_LEAK`. Ring-to-frame
leak stays CFD-only (stage 1 tip-shroud spec).

`pq_curve` / `operating_point` default stays `DEFAULT_TIP_GAP_MM` (0.5)
when nobody passes a spec. No new cockpit fan-BEM readout. Propeller BEMT
is unchanged.

## Tests (no CFD)

- Helper leftover = `casing_id/2 − (open_tip_rmax + shroud thick)`
- Pin: `casing_id_mm=110` → `duct_radius == 55 mm`; undersize leftover > 0.5;
  packed 109 mm leftover 0.5
- No `casing_id_mm`: growing duct unchanged (`test_cfd.py`, `test_frame.py`)
- `evaluate_candidate` a12x25 leftover 0.4 mm or overlap → infeasible, no STL
- Default `BladeParams()` infeasible on a12x25 by the gap gate (before geometry)
- `test_bem_prescreen_rejects_below_floor_before_geometry` uses a blade that
  already fits (leftover ≥ 0.5) so it still fails on the CFM floor
- BEM: same open blade, leftover 2 mm screens worse than 0.5 mm; full ring
  still beats open at the same leftover
- `--tip-gap` / `--shroud` help text; no `★`
- Feasible trial attrs: actual leftover, `casing_id_mm`, `tip_gap_floor_mm`.
  Old Pareto rows with only `tip_gap_mm = 0.5` still load

## Success

`--shroud` and open-tip a12x25 campaigns sit in a 110 mm barrel. Filling it
tightens the leak; a small rotor is punished. Tighter than 0.5 mm is refused,
not meshed. BEM prescreen points the same way. Validation scripts that never
pass a spec keep today’s growing duct.
