# Toroidal / Sharrow-style prop — Stage 1 investigate

**Date:** 2026-09-30  
**Status:** approved (Stage 1 only)  
**Approach:** Literature + printability + analysis-path note. **No geometry, no cockpit knobs, no CFD campaign.**  
**Roadmap:** §4.5 Stage 1. Stage 2 stays parked per the go/no-go below.

## Plain language

A toroidal (Sharrow-style) propeller replaces open tips with a continuous blade loop that rejoins at or near the hub. In fansim that would be a **new Prop topology**, not a loft tweak on the existing open-blade `BladeParams` path. Stage 1 answers whether we should build that topology now. Verdict: **no — park Stage 2.**

## What it is (our context)

- **Topology:** each “blade” is a closed ribbon: root → tip arc → return → hub join, so there is **no free tip**. Commercial Sharrow props market tip-vortex / noise benefits from that loop.
- **Not:** a tip shroud/ring bolted onto open blades (§2.1), a duct, or a multi-blade open Prop with more sweep.
- **Would live under:** Prop archetype as an alternate builder (CadQuery solid + STL), then open-air CFD. It does **not** drop into today’s station loft (`build_prop` / span stations / tip round) without a separate surface definition.
- **Claims we care about later (not Stage 1):** hover thrust / g/W / relative noise vs an open blade of similar diameter and print mass — only after geometry + CFD exist.

## Printability (FDM)

| Constraint | Implication |
|------------|-------------|
| **Continuous loop** | One watertight manifold; no open tip. Mesh must be printable without non-manifold joins at the tip turn. |
| **Hub join** | Loop roots must fuse into the hub with enough wall for torque and layer adhesion (same FDM anisotropy story as §1.3). Thin “kiss” joins will fail in flight even if CFD looks fine. |
| **Tip loop / overhang** | The outboard U-turn is an overhang machine. Flat-on-hub orientation needs supports under the loop; standing on tip is worse for hub strength. Expect support scars on pressure/suction faces → roughness vs smooth-wall CFD. |
| **vs open blade** | Open Prop already has a known print path (bore, hub, blade thickness gates). Toroidal adds support volume, harder visual QA, and a second failure mode (loop crack at join). |

Stage 2, if ever greenlit, must treat **print orientation + min join thickness + support strategy** as first-class Design knobs, not afterthoughts.

## Analysis path: BEMT vs CFD

**BEMT is unsuitable as the primary screen for a closed loop.**

- Our prop BEMT (`bemt.analyze`) assumes **independent radial stations**, free tips (Prandtl / tip-loss style corrections), and a wake that does not reconnect through a continuous tip ribbon.
- A toroidal surface has **no tip in the BEMT sense**; loading near the loop is strongly 3-D; spanwise “stations” along a loop are not the same as open-blade elements.
- Compressibility / stall-cap work in §4.4 improves **open-blade** BEMT; it does not make BEMT a closed-loop model.

**Therefore: CFD-first.** Reuse the §4.3 open-air **MRF** prop path (smoke → optional refine → GCI stamps) once a printable STL exists. Do **not** invent a toroidal BEMT for screening. Park absolute noise / AMI for this topology until geometry is real (same as roadmap §4.5). Absolute dB(A) stays §1.4 regardless.

Cheap ranking without CFD would require a new reduced-order model we do not have; that is out of scope and not a reason to start Stage 2.

## Go / no-go

**Recommendation: NO-GO on Stage 2 for now. Park implementation.**

Rationale:

1. **Recommended sequence** already puts archetype CFD depth after Validation P–Q and print+measure (§5). Toroidal does not unblock free-air CFM honesty or loaded-branch fidelity.
2. **Open-blade Prop** already has BEMT screen + MRF CFD + missions + cockpit Design. Toroidal cannot reuse that screen; every design eval is a CFD (or a guess).
3. **Print risk** is higher than open blades for little near-term product value inside this repo’s north star (a12x25 / hardware loop).
4. No strong go signal found: no customer-critical toroidal requirement, no existing STL pipeline waiting for knobs, and §4.3/§4.4 still have higher-value open-prop CFD honesty work (AMI parked on purpose; datasheet / forward-flight still open).

**Revisit Stage 2 only when** (all soft gates, not a schedule promise):

- Hardware P–Q / §5 path is moving, **or** open-prop MRF screening is clearly “good enough” and capacity opens for a novelty topology; **and**
- Someone accepts CFD-first cost (no BEMT prescreen) plus FDM loop print trials.

Until then: **do not** start CadQuery toroidal geometry, cockpit Design knobs, or toroidal CFD smokes.

## Non-goals (this note / Stage 1)

- Implementing Stage 2 geometry, STL export, or Design UI
- Running CFD on any toroidal mesh
- Extending BEMT for closed loops
- Absolute noise, AMI, or datasheet claims for toroidal props

## What lands

1. This design note under `docs/superpowers/specs/`.
2. Roadmap §4.5 → Partial: Stage 1 DONE 2026-09-30; Stage 2 parked per this note.
