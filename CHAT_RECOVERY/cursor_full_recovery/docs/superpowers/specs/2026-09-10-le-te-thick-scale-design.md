# LE / TE thickness scale (chordwise bias)

**Date:** 2026-09-10  
**Status:** accepted — stage 1 shipped; **PARKED 2026-09-11** (TE blunt still looks backwards under stagger). See roadmap §2.9.  
**Approach:** Two global scales on `BladeParams` multiply local airfoil thickness by a LE↔TE blend of chord fraction. Thickness root/mid/tip unchanged. Not spanwise LE/TE stations. Not NSGA.  
**Roadmap:** §2.9 — airfoil honesty for tip LE bluntness / TE thinness vs CFM / print / strength. Un-park only with a new agreed TE geometric model (not more face-lip tweaks).

## Plain language

Today **Thickness root/mid/tip** set one NACA max-thickness at each span. Designers also want to fatten the **nose** or thin the **trailing edge** without six new stations. Two sliders: LE thickness scale and TE thickness scale (default 1 = unchanged).

## Decisions (locked)

| Choice | Decision |
|---|---|
| Model | Chordwise bias on existing thickness (option 1 / B / global) |
| UI | Two sliders: LE scale, TE scale |
| Span | Global (same at every station) |
| Impl | Weight thickness `b` by LE/TE blend of chord `x` after NACA |

## Goal

1. **Fields on `BladeParams`**

```text
le_thick_scale: float = 1.0   # ~0.5–1.5; 1 = no LE bias
te_thick_scale: float = 1.0   # ~0.5–1.5; 1 = no TE bias
```

2. **Blend in `_section_loop`** (after `b = loop[:,1]*chord`, before features):

```text
w_le = 0.5 * (1 + cos(π * x))      # 1 at LE (x=0), 0 at TE (x=1)
w_te = 0.5 * (1 + cos(π * (1-x)))  # 0 at LE, 1 at TE
s    = le_thick_scale * w_le + te_thick_scale * w_te
b    = b * s
```

Clamp scales to `[0.5, 1.5]` when applying. Both `1.0` ⇒ `s ≡ 1` (exact noop).

3. Thread scales through loft / tip helpers / `open_tip_rmax` / placement (same as other section kwargs).

4. **`blade_from_flat` / `blade_to_flat`** — keys `le_thick_scale`, `te_thick_scale`; absent → 1.0.

5. **Cockpit** — under Airfoil, after Thickness tip: **LE thickness scale**, **TE thickness scale** (0.5–1.5, step 0.05). Help text. `edit_flat` / load / `EDITOR_VARS`.

6. **Optimize** — not a new NSGA variable this cycle.

## Tests (no Docker)

- Defaults `1.0`; both 1.0 leaves tip-section max `|b|` unchanged vs scales omitted.
- `le_thick_scale=1.5`, `te=1.0`: near-LE thickness up ≥20% vs baseline; near-TE within ~5%.
- `te_thick_scale=0.5`, `le=1.0`: near-TE thickness down; near-LE within ~5%.
- Flat round-trip.

## Files

| Path | Role |
|---|---|
| `fansim/geometry/blade.py` | fields + blend + thread |
| `fansim/optimize/search_space.py` | flat round-trip |
| `fansim/cockpit/app.py` | sliders + state |
| `fansim/cockpit/placement.py` | pass scales if it builds sections |
| `tests/test_le_te_thick.py` | blend / noop / round-trip |

## Non-goals

- Per-station LE/TE scales
- Replacing NACA
- NSGA / bio-feature reopen
- Claiming CFM/noise wins without CFD
