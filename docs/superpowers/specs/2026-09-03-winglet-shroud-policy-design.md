<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# Winglet × shroud interaction policy

**Date:** 2026-09-03
**Status:** accepted
**Approach:** Couple the two levers at geometry-assembly time — a winglet applies only when the tip has a leakage path (open or TE-anchored partial ring); a full-span ring forces it off. Make `shroud_height_frac` a searchable optimizer DOF so the search can find the partial-ring sweet spot.
**Roadmap:** §7.5 remainder (winglet × shroud policy). Closes the tip-shroud thread. Not circular AMCA, not BEM winglet modelling.
**Amends:** `docs/superpowers/specs/2026-09-02-ring-to-frame-gap-design.md` and `2026-09-02-partial-shroud-design.md` (the optimizer now *searches* `shroud_height_frac`; that was a cockpit-only slider / a per-spec non-goal before).

## Plain language

A **winglet** curls the outer tip span to fight tip leakage. A **shroud** is a
ring around the tip that blocks that same leakage. The open literature (§7.5)
finds they interact: a winglet **helps** a partially-shrouded fan but **hurts**
a fully-shrouded one — a full ring already kills the leak, so the winglet just
adds blockage and depth. "Winglets are the fallback when the tip gap can't be
tightened."

Today `--winglet` and `--shroud` are independent optimizer flags with no
coupling, and `--shroud` always stamps a **full-span** ring. So `--shroud
--winglet` produces **100% full-shroud-plus-winglet** designs — exactly the bad
combination — and our slip-wall RANS can't correctly penalize it (with a full
ring there is no tip gap for the RANS to resolve the winglet's cost).

This cycle couples them. The ring's height becomes a search DOF, and a winglet
is applied only when the ring leaves a leakage path.

## Why the coupling is binary on `shroud_is_full`

Our ring is **TE-anchored partial *axial* height** (`shroud_height_frac`,
`shroud_axial_range`). A partial ring covers the trailing part of the tip chord
and leaves the **leading** part unshrouded — that unshrouded chord is where tip
leakage still happens, so a winglet there has a real leak to fix. A **full**
ring covers the whole chord: no leakage path, so a winglet is pure blockage.
That makes `shroud_is_full(params)` (already defined: `thick > 0 and frac >=
1 - eps`) the physically-honest switch. A continuous winglet-vs-clearance taper
was rejected as false precision — the slip-wall RANS can't resolve the graded
benefit, so any curve would be invented.

## Problem

`suggest_params` (`fansim/optimize/search_space.py`):

```text
if with_winglet:  apply_winglet(bp, sweep=..., lean=...)   # independent
if with_shroud:   bp.shroud_thick_mm = SHROUD_DEFAULT_MM   # full ring, frac defaults 1.0
```

The two branches never see each other, and `shroud_height_frac` is never
sampled, so every `--shroud` trial is full-span. `blade_from_flat` re-applies a
winglet from the stored `winglet_sweep`/`winglet_lean` params regardless of the
shroud, so even if sampling skipped the winglet, a rebuild would regrow it.

## Goal

One rule, enforced identically wherever geometry is assembled:

> **A winglet applies only when `not shroud_is_full(params)`.**

1. **Search space.** `--shroud` samples `shroud_height_frac` in `[0.30, 1.0]`
   (TE-anchored; `1.0` = full, still reachable). Ring **thickness** stays fixed
   at `SHROUD_DEFAULT_MM` (not searched). Winglet DOFs are **still always
   sampled** under `--winglet` (static NSGA-II space), but **applied only when
   the sampled ring is not full**. Set shroud fields → test `shroud_is_full` →
   conditionally `apply_winglet`.
2. **Rebuild parity.** `blade_from_flat` applies the winglet under the **same**
   `not shroud_is_full` gate, reading `shroud_height_frac` from the flat dict.
   A full-ring row with winglet params rebuilds with **no** winglet.
3. **Cockpit.** The build / Assess path inherits the same gate (honest scored
   numbers). A one-line note by the winglet controls says it is ignored while
   the ring is full-span.

Gate order is unchanged (mountable → printability → stress → gap floor → BEM →
geometry → check_build); this policy lives inside geometry assembly, before any
of that.

## The shared rule

A single predicate, so the three assembly sites can't drift:

```text
winglet_allowed(params) -> bool
    return not shroud_is_full(params)
```

Applied at:

| Site | File | Today | After |
|---|---|---|---|
| optimizer sample | `search_space.py::suggest_params` | winglet always | winglet iff `winglet_allowed` |
| stored-trial rebuild | `search_space.py::blade_from_flat` | winglet iff params present | winglet iff params present **and** `winglet_allowed` |
| cockpit build/Assess | `fansim/cockpit/*` | winglet independent | winglet iff `winglet_allowed` |

Winglet DOFs stay sampled on full-ring trials (inert), so the search space is
static — no conditional-parameter penalty for NSGA-II. `shroud_height_frac` is
a real suggested float, so it lands in `trial.params` and rebuilds for free (no
extra user-attr, unlike `shroud_thick_mm` which is stamped after sampling).

## CFD / ring-to-frame gap — unchanged

Built OD = `open_tip_rmax_mm(params) + shroud_thick_mm`, independent of
`shroud_height_frac`. The pinned-frame-ID duct, leftover-gap floor, and strut
`frame.stl` from the ring-to-frame spec are untouched. CFD just builds the (now
correctly winglet-free) full-ring geometry when the search picks one.

## BEM — unchanged

`operating_point` keys tip loss on `shroud_is_full`: full → `F = 1` (no tip
loss); partial/open → Prandtl + `K_TIP_LEAK` on the leftover gap. A **partial**
ring is therefore scored like an **open** tip (no shroud credit) — conservative
for a pre-screen, so it can only under-predict a partial-shroud design, never
wrongly inflate one. The winglet is not modelled in the BEM at all, so this
policy does not touch it. Left as a known conservatism; not fixed here.

## Non-goals (this spec)

- Searching ring **thickness** (`shroud_thick_mm` stays `SHROUD_DEFAULT_MM`).
- A continuous winglet↔clearance taper (rejected: false precision for slip-wall RANS).
- Modelling the winglet in the BEM, or giving partial rings BEM shroud credit.
- Changing `apply_winglet` internals, the winglet DOF bounds, or `SHROUD_DEFAULT_MM`.
- Circular AMCA 210 / ISO 5801 duct; a third CFD solve.
- Graying/animating cockpit sliders beyond the one-line note.
- Propeller tab / prop BEMT (unchanged).

## Tests (no CFD)

- `suggest_params(with_shroud=True)` samples `shroud_height_frac` inside `[0.30, 1.0]`.
- Full-ring trial (frac ≈ 1.0) with high sampled `winglet_sweep`/`winglet_lean`
  → the built stations carry **no** winglet shoulder (station count / tip
  deflection matches the no-winglet build).
- Partial-ring trial (frac < 1.0) under `--winglet` → winglet **is** applied.
- `blade_from_flat` parity: `{shroud_thick_mm>0, shroud_height_frac=1.0,
  winglet_sweep>0}` rebuilds with **no** winglet; same dict at
  `shroud_height_frac=0.5` rebuilds **with** the winglet.
- `winglet_allowed` / `shroud_is_full` boundary at `frac = 1 - eps`.
- `--shroud` / `--winglet` CLI help names the coupling; no `★`.
- Existing `test_shroud.py`, winglet cases in `test_placement.py`, and
  `test_search_extended.py` stay green.

## Success

`--shroud --winglet` now searches partial rings and only curls the tip where a
leakage path exists; a full ring never carries a winglet, in the optimizer, in
a rebuild, or in the cockpit. The tip-shroud thread (§2.1 → §7.5) is closed
except the circular-rig / absolute-pressure work tracked elsewhere.
