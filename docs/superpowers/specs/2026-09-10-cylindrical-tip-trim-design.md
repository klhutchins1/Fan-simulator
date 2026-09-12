# Cylindrical tip trim (match cover radius)

**Date:** 2026-09-10  
**Status:** accepted — shipped (default on).  
**Approach:** Optional **boolean intersect** of each lofted blade with a cylinder of radius `tip_radius` (true cylindrical tip face). Toggle on `BladeParams` (default **on**). Not Tip Round (chord petal). Not stream-radius shrink (that hollowed tips). Not a separate Tip OD slider.  
**Roadmap:** §2.7 — tip-geometry honesty vs circular casing / Noctua-like constant tip gap.

## Plain language

Today each tip section sits on a cylinder of radius `tip_radius`, but the LE↔TE edge is a **straight chordal cut** in the section plane. Lean/stagger make LE/TE corners **bulge** past that radius. **Tip Round** shrinks chord into a petal — it does **not** follow the fan-cover circle.

Designers want the outer tip edge to be an **arc of constant radius** (same OD as Tip radius / length) so clearance to the frame ID is even. Turn the trim **off** when you want the old square / bulging tip.

## Problem

```text
Tip Round (apply_tip_shape):  taper chord → petal tip (wrong round for cover match)
Section placement:            mid-chord at r ≈ tip_radius; LE/TE corners can hypot > tip_radius
No op:                        clip tip face to cylinder R = tip_radius
```

## Decisions (locked)

| Choice | Decision |
|---|---|
| When | Toggle — not every design needs it |
| Default | **On** (`cylindrical_tip=True`) |
| Trim radius | **`tip_radius`** only |
| Tip Round | **Both** — Tip Round first; trim clips OD after |
| Implementation | **A** — clamp section points (no CadQuery boolean) |
| Optimize NSGA | **Not** a new search variable this cycle |

## Goal

1. **Field on `BladeParams`**

```text
cylindrical_tip: bool = True   # False = legacy straight / bulging tip edge
```

2. **Trim after loft** (sections stay planar / unchanged):

```text
blade = makeLoft(wires)
if cylindrical_tip:
    blade = blade ∩ cylinder(R=tip_radius)   # CadQuery intersect; keep largest solid
```

Do **not** shrink stream radius or clip section wires before loft — that collapsed / hollowed tips in preview.

Envelope helpers (`open_tip_rmax_mm`, `tip_section_points`) cap/clamp to `tip_radius` when the flag is on so Fit matches the cut solid.

Honesty: tip face is a true cylinder segment from the boolean. Tip Round still petals planform before the cut.

3. **Order of ops** (unchanged stamps, then loft + cut):

```text
stations → tip_round / winglet / sickle / notches (as today)
loft sections (unchanged planar wires)
if cylindrical_tip: intersect with tip_radius cylinder
```

Tip Round still inserts outer stations and tapers chord; the cylinder cut only removes radial overshoot.

4. **`blade_from_flat` / `blade_to_flat`**

```text
cylindrical_tip: bool   # default True when key absent (new default matches BladeParams)
```

Absent key → on (so old flats get cover-matching tips). Explicit `false` / `0` turns it off.

5. **Cockpit**

- Checkbox near Tip round: **Cylindrical tip (match cover)** ↔ `e_cylindrical_tip`.
- Help text: clips the tip edge to Tip radius so it follows the casing circle; Tip Round still petals the planform inside that circle.
- Round-trip in edit flat / load / randomize (preserve or default on).

6. **Fit envelope / tip-radius cap / features (product rule — locked 2026-09-11)**

**Decision:** cylindrical tip caps **measure, Fit, and CFD duct** the same way as the **solid**
boolean cut. `open_tip_rmax_mm` reports `min(section_rmax, tip_radius)` when trim is on;
`blade_max_dia` / Fit / `rig_for_impeller` all go through that helper. Bio-features
(tubercles, etc.) that would push past `tip_radius` are **cut**, so they do **not** force
Fit to shrink `tip_radius` further when trim is on. With trim **off**, features and LE/TE
corners still enlarge measured OD and Fit accounts for them.

With trim on, Cap / Fit may allow a longer `tip_radius` for the same planform than the
untrimmed bulge case. No change to the 0.5 mm leftover rule or `CLEARANCE_MM`.

7. **Loft resolution**

No mandatory `n_span` bump. Optional: when `cylindrical_tip` and tip chord is wide, existing tip-round / notch bumps already raise outer resolution; leave as-is unless tests show a faceted tip edge that fails the hypot check at mid-edge (loft between clamped wires is still on/near the cylinder).

## Honesty

This is a **faceted cylindrical tip** from clamped loft wires, not a true NURBS cylinder face and not digitised Noctua CAD. Tip Round remains a separate planform control. Do not claim tip-gap CFD gains until measured.

## Tests (no Docker mesh)

- Default `BladeParams()`: `cylindrical_tip is True`.
- Trim **off**, high lean + wide tip chord: `open_tip_rmax_mm(p) > tip_radius` (bulge still exists).
- Trim **on**, same planform: every tip-section point (and `open_tip_rmax_mm`) ≤ `tip_radius + 1e-6`.
- Tip Round + trim on: still ≤ `tip_radius + 1e-6`; solid builds (one blade watertight).
- `blade_from_flat({..., "cylindrical_tip": False})` → off; absent key → on.
- Cockpit flat includes the key when building from editor state.

## Files

| Path | Responsibility |
|---|---|
| `fansim/geometry/blade.py` | field, clamp in section pipeline, thread through loft / tip helpers |
| `fansim/optimize/search_space.py` | `blade_from_flat` / `blade_to_flat` |
| `fansim/cockpit/app.py` | checkbox, help, edit_flat / load |
| `fansim/cockpit/placement.py` | if it rebuilds sections itself, pass the flag |
| `tests/test_hub.py` or `tests/test_geometry.py` | hypot / round-trip / solid |
| `scripts/generate_control_images.py` | optional control pair for the checkbox |

Do not add Python dependencies. Do not commit `catalog/catalog.db`. Do not re-open tip-round / bio-feature NSGA.

## Non-goals

- Stream-radius shrink / pre-loft wire mutation (proven to hollow tips)
- Separate Tip OD / tip-gap slider
- NSGA variable for `cylindrical_tip`
- Changing Tip Round semantics
- Mixed-flow / CROR / prop-specific tip trim (axial loft path only this cycle)
- Claiming quieter BPF or better efficiency from the trim alone
