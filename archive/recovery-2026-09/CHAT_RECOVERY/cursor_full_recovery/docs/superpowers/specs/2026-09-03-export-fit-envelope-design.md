# Fit envelope on export (opt-in)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** A second export switch, same pattern as “Fit hub to motor on export.” When on, run existing `fit_envelope` on the editor flat **before** the STL build. Default **off**. Message lists what changed and that Assess numbers are stale. Not Scale-to-hub. Not a new fitter.  
**Roadmap:** §3.4. Hub-grow toggle stays. Fit envelope button stays.

## Plain language

Export already widens a too-small hub so the motor cup carves. It does **not** shrink an oversize tip or flatten an oversize depth. You have to click **Fit envelope** first or the STL will not fit the frame. An opt-in switch does that Fit on the way out, with the same “this is not the assessed geometry” warning hub-grow already prints.

## Problem

```text
export_fit_hub  # hub radius + hub height only
# tip / depth / sweep still whatever the sliders say
```

`fit_envelope` already does hub min, tip leftover, depth (sweep then stagger), hub height. Export does not call it.

## Goal

1. State: `export_fit_frame: bool = False` next to `export_fit_hub`.
2. Switch label: **Fit envelope on export** — shrink tip/depth to the selected frame (changes aero; re-Assess).
3. When on, **before** `build_edit_params()`:

```text
res = fit_envelope(edit_flat(), spec)
_apply_editor_flat(res.flat)
edited_stale = True
```

Then the existing hub-grow block still runs (no-op if Fit already raised the hub).

4. Export message: if `res.changes`, append the same `preview_changes` text plus the existing “CFM/eff were for the original geometry — re-Assess” line (reuse the hub-grow caveat; don’t invent a second one).
5. Default off. No CLI. Prop tab unchanged.
6. Helper so tests don’t boot Trame:

```text
prepare_export_flat(flat, spec, fit_frame: bool) -> (flat, changes)
# fit_frame False -> deepcopy, []
# fit_frame True  -> fit_envelope(...).flat / .changes
```

`export_stl_current` uses that helper, then hub-grow as today.

## Non-goals

- Default-on
- Scale to this hub on export
- Auto-fit on Preview or Assess
- Changing `fit_envelope` math
- Optimizer / catalog
- Prop export

## Tests (no Docker, no Trame)

- `fit_frame=False`: flat unchanged, no changes
- Oversize tip (`tip_radius` 59 on A12x25): `fit_frame=True` shrinks tip; `blade_max_dia` leaves the 0.5 mm leftover (same as Fit envelope)
- A12x25-legal flat: `fit_frame=True` may still no-op (empty or tiny changes); does not grow the tip
- `app.py` contains the switch label string (same style as other cockpit copy tests)

## Files

| Path | Responsibility |
|---|---|
| `fansim/cockpit/placement.py` | `prepare_export_flat` |
| `fansim/cockpit/app.py` | switch, call helper, stale + message |
| `tests/test_placement.py` | helper cases |
| `docs/roadmap.md` | §3.4 done |

Do not add Python dependencies. Do not commit `catalog/catalog.db`.
