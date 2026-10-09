# Hub-first cockpit and catalog

**Date:** 2026-09-01  
**Status:** draft for review  
**Approach:** A — hub workspace + recipe library

## Problem

The cockpit treats every optimizer trial as one cloud of CFM points. That mixes
envelopes: a 118 mm unconstrained rotor and an NF-A12x25-legal impeller are not
the same machine. The hub model is buried; the 3D view sits under ~40 sliders;
run folders are named `opt_run1` with no English meaning. “Show only what fits”
as a filter is backwards: non-fitting geometries are still *recipes* you may
want to place onto the selected hub.

The Fan Showdown was the impetus, not the product boundary. The propeller tab
stays as a later expansion. Physical airflow/noise measurement waits until a
Noctua hub is on hand again. Printability (already proven once in PLA+) is the
near-term physical check.

## Goal

Selecting a **fan hub** is the first act. Everything you design, compare, and
export is for that hub. Other sizes live in a **library** so they can be placed
onto the current hub. Results graphs never rank machines that do not share that
hub.

## Non-goals (this spec)

- Outlet guide vanes / unswirl geometry
- Literature feature presets (tubercles, serrations, forked TE)
- Tip-gap / no-slip shroud CFD study
- A new `--mountable` optimizer campaign at hub 19.8–24 mm

Those remain agreed follow-ons after this cockpit/data change ships.

## Users and modes

One operator (you). Two jobs:

1. **Build** a blade for the selected hub — 3D is the primary surface.
2. **Compare** blades that already belong to that hub — the graph is allowed.

A third surface, **Library**, is how you find a recipe from any past run and
place it on the current hub.

## Information architecture

```
[ Fan | Propeller ]

Fan:
  Hub picker  (always visible: name, cup, frame tip×depth, motor)

  [ Design | Results | Library ]

  Design   — 3D (main) + editors + Fit toolbar. No ranking graph.
  Results  — scatter + list of designs already on THIS hub with live CFD.
  Library  — all recipes, any size, human-named runs. Place onto current hub.
```

Changing the hub switches the workspace. It does not overlay foreign CFM on the
Results plot.

### Why not “filter the current graph”

A 2-foot fan and a 120 mm fan differ in Reynolds number, blade-pass frequency,
and motor. Shared CFM axes are a lie. The library still *shows* the 2-foot
recipe so it is not stranded; placing it creates a **new** A12x25-sized draft
whose old CFM is stale.

## Data model

Keep folder ids (`opt_run1`, …) on disk. Add names people can read.

### Run labels

New file `config/run_labels.yaml`:

```yaml
opt_run1: "First unconstrained 120 mm search"
opt_v2: "Second unconstrained search"
opt_v3: "Third unconstrained search"
opt_guided: "Guided search (design-rules bounds)"
opt_noise: "Search with noise objective"
opt_noise2: "Noise objective, second pass"
opt_extended: "Search with hub/thickness DOFs"
opt_extended2: "Extended search, second pass"
opt_mountable: "Hub sized for old 52 mm motor estimate"
opt_realframe: "Tip constrained to 110 mm A12x25 frame"
opt_overnight: "Overnight unconstrained search"
opt_loadcap: "Solidity-floor (load spreading) search"
opt_val: "Validation search"
```

Unknown folders fall back to the folder name. The library and Results show the
label; the id stays in a caption for traceability.

### Catalog fields (additive)

Each catalog row gains:

| Field | Meaning |
|---|---|
| `hub_models` | JSON list of fan-spec keys this geometry **fits** (`a12x25`, `generic_120`, …). Empty if it fits none. A separate `placed_on` key is set when the user explicitly places onto a hub that it did not originally fit. |
| `fit_status` | `fits` \| `over_spec` \| `unplaced` |
| `placed_on` | Hub key this row was explicitly placed onto, or empty |
| `cfd_stale` | True after Fit/Scale until Assess completes |
| `parent_id` | Library design this was placed from, or empty |
| `place_op` | `fit_envelope` \| `scale_to_hub` \| empty |

Rebuild (`scripts/catalog.py build`) classifies existing rows:

- If stored params’ built tip diameter, hub radius, and depth satisfy a known
  `FanSpec` (including `a12x25` motor cup ≥ 19.825 mm), append that key to
  `hub_models` and set `fit_status=fits`.
- A design may fit more than one spec; record every match. Results for hub
  *H* include rows where `H` is in `hub_models`, or `placed_on == H`.
- Rows that fit nothing stay `unplaced` (`hub_models=[]`) and appear only in
  Library until placed.

Do not delete historical rows. Do not rewrite `runs/` folder names.

### New objects vs in-place edit

Fit envelope and Scale **always create a new design** in the current hub
workspace (`source=placed`, new trial id in `cockpit_assess`). The library
original is unchanged. That matches “I printed a too-big PLA+ fan and learned
the cup was wrong” without destroying the evidence.

## Placement operations

Hub toolbar (Design view), not per-slider buttons:

1. **Fit envelope** — keep chords, stagger, blade count, lean. Change only
   what this hub requires, in order:
   1. Hub radius → motor cup + wall (`mount_min_hub_radius`)
   2. Tip length → built diameter ≤ frame max (existing iterative bulge logic)
   3. Depth → flatten sweep/LE first, then stagger if still over
   4. Hub height → at least `min_hub_height_mm`

2. **Scale to this hub** — linear scale `s = target_tip / source_tip` (target
   is the hub’s max impeller radius minus the known bulge margin). Multiply
   lengths (hub radius, tip radius, chords, sweep, skew, LE sweep, hub height,
   hub nose, winglet sweep mm). Do **not** scale angles, thickness fractions,
   camber fractions, blade count, or feature wave counts. Then run Fit
   envelope so the motor cup still fits if scale shrank the hub too far.

Before apply: a confirmation list (“hub 16.5 → 19.8 mm; tip 59 → 53.2 mm;
depth 28 → 25 mm; CFD will be stale”). Cancel leaves the original.

After apply: 3D shows the new solid; metrics show “stale — Assess to score on
this hub.” Export is allowed (printability still gates). Assess writes live
CFD onto the **new** row only.

Printability after scale: if a tip wall drops below the FDM minimum, the
preview says so and Assess/Export keep the existing manufacturability gate.

## Cockpit layout

`fansim/cockpit/app.py` is a 2,100-line god file. This change splits:

- `fansim/cockpit/placement.py` — Fit envelope + Scale (pure functions, unit-tested)
- `fansim/cockpit/labels.py` — run label lookup
- `fansim/cockpit/app.py` — Trame server, state, layout

Fan tab structure:

- **Top bar:** hub `<VSelect>` + one-line spec readout + Fit envelope / Scale
  (disabled until a design is loaded).
- **Sub-tabs:** Design | Results | Library.
- **Design:** left = 3D (≥ half the row, ≥ 520 px tall). Right = accordion
  editors (planform, pitch, airfoil, 3-D shape, tip, hub, spacing, features).
  Per-slider Snap/Fit buttons are removed; the hub toolbar replaces them.
- **Results:** current scatter (CFM free vs load, efficiency color). Population
  = catalog rows for this `hub_model` with `cfd_stale` false. Stale drafts
  listed separately as “unscored on this hub.”
- **Library:** table or compact list: label, original envelope (tip dia, hub
  dia), CFM as “score in original envelope” (captioned, not mixed into
  Results). Actions: Open in Design (read-only geometry) or Place (Fit or
  Scale).
- **Propeller tab:** unchanged.

Efficiency colorbar uses the data range (or at least 0–45%), not a hard 0–22
cap.

Page title: “Fan-simulator Cockpit”, not the Trame default.

## CFD and constraints

Assess/Sweep already take `state.fan_model`. They must use the **selected hub**
only; leeway still exists under an advanced panel but defaults to zero.

`fits_only` as a user toggle goes away. Results are already hub-scoped.
Library is already “everything.”

Optimizer CLI (`--fan-model`, `--mountable`) is unchanged in this spec. Future
campaigns should pass the measured A12x25 cup (hub radius ≥ 19.8 mm) and real
frame; that is a follow-on run, not a cockpit rewrite.

## Error handling

- Place with no hub selected: refuse, message “Select a hub first.”
- Scale with source tip radius ≤ 0: refuse.
- Fit that still exceeds the frame after stagger flattening: keep the draft,
  `fit_status=over_spec`, list remaining overage. User can add leeway or edit.
- Catalog rebuild with missing params: `hub_models=[]`, Library only.
- Windows console: catalog CLI must not print `★` (use `*` or `[pareto]`).

## Testing

No Docker. Fast tests under `tests/`:

- `test_placement.py` — Fit envelope raises hub from 16.5 to ≥ 19.825 on
  `a12x25`; shrinks a 59 mm tip until built diameter ≤ 110 mm; Scale halves
  chords when tip radius halves and leaves stagger unchanged; parent row
  unchanged when a placed child is created.
- `test_catalog.py` — rebuild classifies a known-fitting param set with
  `a12x25` in `hub_models`; a 118 mm tip is absent from the a12x25 Results set.
- `test_labels.py` — `opt_realframe` maps to the YAML label; unknown id echoes
  the folder name.
- `test_mountable.py` — update the stale 52 mm / 27.2 mm assertion to the
  measured cup (37.25 mm → 19.825 mm). That is a bugfix required for honest
  classification, not a new feature.

## Files

| Path | Role |
|---|---|
| `config/run_labels.yaml` | Human names for existing runs |
| `fansim/cockpit/placement.py` | Fit envelope + Scale |
| `fansim/cockpit/labels.py` | Label lookup |
| `fansim/catalog.py` | New columns + classify-on-build |
| `fansim/cockpit/app.py` | Hub-first layout, sub-tabs |
| `fansim/fan_spec.py` | Classification helpers if needed |
| `scripts/catalog.py` | ASCII-safe list output |
| `docs/known-issues.md` | Point at this spec; drop stale GPU/idle claims that contradict README |

## Success criteria

- Opening the cockpit with hub `a12x25` shows Design 3D first, not a mixed
  scatter of 118 mm rotors.
- Results for `a12x25` do not include `opt_run1_t9038` (hub 16.5, tip 59)
  until it is placed.
- Placing that row with Fit envelope yields a new draft, stale CFD, hub
  ≥ 19.8 mm, built tip ≤ 110 mm (or explicit over-spec leftover).
- Library still lists it under “First unconstrained 120 mm search.”
- Propeller tab still exists.
- `uv run python -m pytest -q -m "not docker and not slow"` covers the new
  tests (CadQuery tests that heap-corrupt on this machine stay marked slow /
  isolated as they are today).

## Follow-ons (not this spec)

1. Re-run mountable + real-frame search: hub 19.8–24 mm, built tip under 110 mm.
2. Outlet guide vanes / unswirl as a solid in the 25 mm frame.
3. Named literature presets instead of raw feature sliders.
4. Tip-gap sweep at 0.6 / 1.0 / 1.5 mm with no-slip shroud.
5. When a Noctua is back: record FPM/noise against printed PLA+/PETG parts.
