# Persistent 3D and readable Library browse

**Date:** 2026-09-01  
**Status:** draft for review  
**Approach:** A — 3D always left; tabs only swap the right panel  
**Amends:** `docs/superpowers/specs/2026-09-01-hub-first-cockpit-design.md` Library + Design layout

## Problem

Library hides the 3D view. Picking a recipe fills sliders but does not draw the
blade; the operator has to switch to Design and press Preview geometry. Library
also shows the same catalog twice (dropdown + list) with titles like
`opt_run1_t9038 · 92 CFM (original envelope)` that do not say what the machine
is.

## Goal

The impeller is always on screen while you browse. Clicking a Library recipe
Fits it onto the **current hub**, draws it immediately, and does not dump a new
Results row. Assess is what saves a draft. Scale remains a separate action for
recipes that should be shrunk, not just clamped.

## Non-goals (this spec)

- PNG / thumbnail card grid (no image pipeline yet)
- Pre-rendering screenshots for every catalog row
- Changing the Propeller tab
- OGV, literature presets, tip-gap study, new optimizer campaign
- Making toolbar Fit/Scale create catalog rows (they stay in-editor, as today)

## Users and modes

Same single operator. Browse a recipe → see it on this hub → keep clicking to
compare → Assess when you want it scored.

## Information architecture

```
Hub bar (always)

[ 3D view — always visible, ≥ half width, ≥ 520 px tall ]
[ Design | Results | Library ]   ← right column only
```

- **Design (right):** editor accordions, Assess, existing sliders. No second 3D.
- **Results (right):** scatter + this-hub list. Selecting a scored design draws
  its STL in the left 3D when a file exists; otherwise the fast preview.
- **Library (right):** one grouped list. No dropdown. No duplicate list.

Fan | Propeller top tabs stay. Hub picker stays above this split.

## Library list

Group headers use `run_label(run)` (English). The folder id (`opt_run1`) is a
caption on the group or row, not the primary title.

Each row, in this order:

1. Blade count: `9 blades`
2. Original size: `hub 33 mm · tip 118 mm` (from that recipe’s params, not the
   selected hub)
3. Original score: `92 CFM at original size` (never plotted as this-hub CFM)
4. Fit hint vs current hub: `fits this hub` | `too big — click Fits it` |
   `no geometry yet`

Use `nominal_fits_spec` (built tip + depth) for the fit hint. Missing hub/tip
params → `no geometry yet`; that row is not clickable for Fit.

Do not use the phrase “original envelope” in the UI.

## Click, Scale, Assess

**Click a Library row** (Fit):

1. Refuse if no hub is selected: message `Select a hub first.`
2. Run `fit_envelope` on a copy of the recipe params for `state.fan_model`.
3. Load the fitted flat into the editor (`_init_editor`). Do not append a
   `Design` / Results row.
4. Remember `library_parent_id`, `place_op=fit_envelope` on editor state so a
   later Assess can tag the saved draft.
5. Auto-run the existing fast preview build and draw it (orange preview path).
   Do not require “Preview geometry”.
6. Stay on the Library tab. Envelope overlay stays available.
7. If `fit_status == over_spec`, show `leftover` as a one-line caption under
   the list. Keep the draft in the editor anyway.

Clicking another row replaces the editor and 3D. Un-assessed Fits are discarded
(not stacked).

**Scale to this hub** (secondary / outline button, enabled when a row is
selected):

- Same as click, but `scale_to_hub` and `place_op=scale_to_hub`.
- Editor-only. No Results row until Assess.

**Assess:**

- Unchanged CFD path, except if `library_parent_id` is set, the saved user
  design gets `extra.parent_id`, `extra.place_op`, `extra.placed_on`, and
  starts with live CFD (`cfd_stale=false` after a successful Assess).
- After Assess, Results can show the new point because it belongs to this hub
  and is no longer stale.

Toolbar Fit / Scale on the hub bar remain in-editor edits of whatever is
already loaded (no catalog fork).

## 3D view

One plotter, left column, not inside a `v_show` that hides it on Library or
Results. Highlight-out-of-spec and case-envelope switches stay with the 3D
card (visible on every Fan sub-tab).

Library click uses the fast preview mesh (same as `do_preview` today). Results
selection prefers an existing STL when `has_model`.

## Error handling

- No hub selected: do not Fit; `Select a hub first.`
- Recipe with no usable params: row shows `no geometry yet`; click is a no-op
  with `This recipe has no blade numbers to Fit.`
- Preview build timeout or CadQuery failure: existing preview error string;
  sliders still hold the fitted numbers.
- Scale with source tip radius ≤ 0: existing `unplaced` leftover; do not draw
  a fake blade.

## Testing

Fast tests only (`tests/`, no Docker):

- `library_items_from_catalog` (or a dedicated formatter) returns grouped
  fields: English run label, blades, hub mm, tip mm, CFM caption containing
  `at original size`, and a fit hint. Oversized tip is not titled as if it
  already fits `a12x25`.
- A helper used by click (`fit_envelope` into a new dict) still does not
  mutate the parent params dict.
- Click path must not be implemented as `placed_child_record` + append
  `user_designs` (that is the old Place-creates-row behavior). Assert the
  editor-only helper returns a fitted flat and metadata without a new trial id.

## Files

| Path | Role |
|---|---|
| `fansim/cockpit/app.py` | Persistent 3D column; Library list; click → Fit + auto preview |
| `fansim/cockpit/library_view.py` | Row/group dicts from `CatalogEntry` + active `FanSpec` (keep formatting out of the Trame file) |
| `tests/test_library_view.py` | Row copy, fit hint, no parent mutation |
| `tests/test_cockpit_view.py` | Scatter + hub-scope tests unchanged; drop any assertion that Library items are a flat `title`/`value` dropdown pair if the shape changes |

## Success criteria

- On Library, the 3D view is visible without switching to Design.
- Clicking a recipe draws a fitted blade without pressing Preview geometry.
- There is one Library list, not a dropdown plus a list of the same ids.
- A row can be understood without knowing `opt_run1_t9038`.
- Clicking five recipes does not add five points to Results.
- Propeller tab unchanged.

## Spec coverage vs hub-first

Hub-first said Library actions were “Open in Design” or “Place (Fit or Scale)”
creating a new design immediately. This spec replaces that with: click Fits
the editor and draws; Assess creates the hub-scoped result. The library
original on disk is still never mutated.
