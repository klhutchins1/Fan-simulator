# Tooltip audit: Fan Simulator cockpit (2026-10-31)

- **Asked by:** Kimball, Sat 2026-10-31 12:58 MDT. Do all settings have image tooltips? If not, make them, especially for Optimize. What does each Optimize setting do, and does it change the fan's shape?
- **Code:** master `3b92eea`, fresh clone `/workspace/fansim/repo-tt` from `handoff_in/master_3b92eea.bundle`.
  - No source edits and no commits. This note, the `docs/QA_REVIEW.md` rows and `handoff/2026-10-31_from-qa-tooltips/` are the only additions.
  - No CFD, Docker, OpenFOAM, Assess, Sweep or Optimize was run.
- **Live check:** the cockpit ran headless on `:8080` against an empty run dir, using Playwright with the box's Chrome.
  - Read-only: it switched mode, opened panels and hovered controls. It never clicked Preview, Assess, Optimize or Export.
  - Results are in `handoff/.../data/headless*.json` and `headless_*_design.png`.
- **Images are proposals.** They are not wired into the app. See UI-32 for the one-line loader change they need.

## 1. How tooltips work today

- **Loading images.** `fansim/cockpit/fan_copy.py:11-22` `_load_control_images()` globs **`docs/control_images/e_*.png` only**. It base64-encodes each file into `_IMG_URI[<state model name>]`.
- **Text.** Text comes from one of these maps:
  - `CONTROL_DESC` (`fan_copy.py:24`), for Design sliders;
  - `OPT_SEARCH_HELP` (`fan_copy.py:86`), for Optimize and the two Assess "honesty" switches;
  - `BLADE_DESC` (`blade_copy.py`), used once.
- **Helpers that draw tooltips.** `fansim/cockpit/fan_widgets.py`:
  - `slider()` (:19, tooltip at :56-70);
  - `help_switch()` (:79, :104-117);
  - `help_select()` (:120).
  - Each looks up the text by state model name, plus `_IMG_URI.get(model)`.
  - If either exists, the control is wrapped in `VTooltip(location="end", open_delay=150)`. The tooltip shows the image at 360 px wide, then the text. If neither exists, the control has no tooltip.
- **Controls with no tooltip.** A plain `v3.VSelect`, `VSwitch`, `VTextField`, `VBtn` or `VSlider` has no tooltip unless it is wrapped by hand.
  - `fan_tab_ui.py` has exactly 3 hand wraps, all text-only: Trials (:1022), PWM RPM min (:1083) and PWM RPM max (:1096).
- **Proxy tabs.** Prop, Mixed, Volute and CROR use `fan_widgets.slider` through local `_slider` wrappers (e.g. `prop_tab.py:939`).
  - Their model names are prefixed (`p_`, `mf_`, `volute_`, `cror_f_`, …), so the lookup never matches and **none of those sliders gets a tooltip**.

### 1a. The existing image generator, which Kimball remembered

- **Path:** `scripts/generate_control_images.py`. The 2026-09 roadmap (`docs/roadmap.md:537`) says to regenerate with `uv run python scripts/generate_control_images.py [model …]`.
- **How it works.**
  - It holds a `CONTROLS` list: `(model, label, flat key, min, max, 'fan'|'blade'[, base overrides])`.
  - For each row it builds the geometry twice, at min and at max, with `blade_from_flat` → `build_impeller` (whole fan) or `build_blade_solid` (one zoomed blade).
  - It renders the two side by side with pyvista off-screen: **460×250 PNG**, white background, `#3b82f6` smooth shading, isometric camera at zoom 1.3, captions "min = … / max = …".
  - It writes `docs/control_images/<model>.png`.
- **It runs on the box as-is.** It reproduced `e_n_blades.png` in about 110 s with the image visually identical.
- **Limits.**
  - It can only draw **rotor/blade geometry**: no frame, stator or casing, and no non-geometry settings.
  - Its hard-coded min/max values have drifted from the slider ranges (UI-35).
- **How I used it without editing it.** `scripts/run_repo_generator.py` (in the handoff) imports the module, swaps its `CONTROLS` and `OUT`, and calls its own `main()`, so the style is exactly the generator's:
  ```
  REPO=/workspace/fansim/repo-tt
  $REPO/.venv/bin/python run_repo_generator.py missing   # e_hub_profile*, opt_shroud, opt_sickle, opt_notched
  $REPO/.venv/bin/python run_repo_generator.py ranges    # 13 re-renders at the real slider ranges -> img/range_fix/
  ```
  - The proper fix is to add these rows to `CONTROLS` in the repo and run the generator. The rows are in that wrapper, ready to paste.
- **Fallbacks I had to write**, because the generator cannot draw these:
  - `scripts/render_stationary.py`: same pyvista settings, using the repo's own `build_frame_solid`, `build_stator_solid` and `build_casing_solid`. Covers `opt_stator` and `opt_stator_stack`.
    - The stepped-casing render was unreadable: a 1.2 mm lip on a long tube. `opt_stepped` is therefore a matplotlib section drawing.
  - `scripts/schematics.py`: matplotlib at the same 460×250 size and colours, for SEARCH/EVAL settings:
    - `opt_trials`, `opt_resume`, `opt_bem`, `opt_gp`, `opt_gp_boost`, `opt_gp_nn`, `opt_surrogate_guided`, `opt_search_rpm`, `opt_stepped`;
    - `assess_preset`, `assess_refine_op`, `assess_wall_ks`.
    - Their curves are illustrative shapes, not simulation output. The numbers in them come from code.
- **Size.** All images are 460×250 to match the existing tooltip assets, which the UI shows at 360 px. That is slightly bigger than the ~320×240 in the brief, chosen to match the existing style.

## 2. Counts

Raw data: `data/inventory.csv` / `inventory.json` (293 control instances), built by `scripts/scan_controls.py` + `scripts/build_inventory.py`.

| Scope | Image + text | Text only | No tooltip |
|---|---|---|---|
| All 229 controls bound to a setting (state model), all tabs, Expert | **53** | **19** | **157** |
| The same, visible in Simple mode | 53 | 3 | 92 |
| Fan tab only (120) | 53 | 18 | 49 |
| Prop/Mixed/Volute/CROR + shared blade panels (109) | 0 | 1 | 108 |
| Buttons, tabs and toggles without a setting (64) | 0 | 5 (top-level tabs) | 59 |

- All 53 image tooltips are Fan › Design › Geometry sliders and switches.
- **Optimize: 16 controls, 16 text-only, 0 images.** The whole panel is expert-only; this was confirmed headless.

## 3. Optimize settings: what each one does and whether it changes the fan's shape

All of these are under Fan › Design › Optimize, which is **Expert only**.

### First: Optimize does not use the Design sliders

`on_optimize_fan` (`fan_optimize.py:87-153`) builds the command with `optimization_argv` (`fansim/optimize/cli_argv.py:113-205`).

- It passes `fan_model`, the toggles below, and the shared Assess settings.
- It **never passes the current Design slider values**.
- `run_study` (`fansim/optimize/study.py:176`) asks Optuna for every shape from scratch with `suggest_params(..., space="guided")`, inside the fan model's frame envelope.
  - There is no `enqueue_trial` or seed from the edited design.
  - The sampler is NSGA-II with a fixed seed of 42 (`study.py:48`).
- So "Optimize" means **search for new fans that fit this frame**, not "polish my design". The UI does not say this; see UI-33.

Every trial's blade shape (blades, stagger, chord, sweep, wrap, camber, tip radius) is chosen by the optimizer. Kimball's settings do three different things:

- **GEOMETRY:** add a fixed part to every trial;
- **SEARCH:** change how candidates are picked or skipped;
- **EVAL:** change how each candidate is scored.

The last two never change a part directly, but they change **which shape wins**.

| Setting (UI label) | Class | What it does in code | Changes the fan's shape? |
|---|---|---|---|
| **Trials** (`opt_trials`, default 8) | SEARCH | Number of CFD trials, clamped to 2..40 (`fan_optimize.py:94`) → `--trials`. | Not directly. More trials explore more shapes, so the best one found can differ. **Ignored when Surrogate-guided is on** (UI-31). |
| **Continue the last Optimize run** (`opt_resume`) | SEARCH | Appends trials to the latest `runs/cockpit_opt_*` study so the sampler keeps learning (`fan_optimize.py:96-108`). | No. It continues the search, so later trials are better informed. |
| **Tip ring / shroud** (`opt_shroud`) | GEOMETRY (rotor) | `--shroud`: every trial gets a 1.6 mm ring fused at the blade tips (`SHROUD_DEFAULT_MM`, `blade.py:203`). Its axial height is searched over 0.30–1.0 of the tip (`search_space.py:202-204`). The tip-radius cap shrinks by 1.6 mm so the fan still fits the frame (`study.py:43`, `search_space.py:176`). | **Yes.** It adds a ring and makes the blades shorter. Image `opt_shroud.png`. |
| **Stator vanes** (`opt_stator`) | GEOMETRY (stationary) | `--stator`: the 4-strut exit frame is replaced by a ring of fixed cambered vanes behind the rotor. Vane count is blades + 1..4 and stagger 35–65°, both searched (`search_space.py:518-524`, `cfd/stator.py:62`). | Not the rotor. It changes the **stationary part** in the CFD (and which rotor wins). Image `opt_stator.png`. |
| **Stator + frame stack** (`opt_stator_stack`) | GEOMETRY (stationary) | `--stator-stack`: vanes first, then the 4-strut frame downstream (`cfd/frame.py:27`). It overrides plain Stator (`fan_optimize.py:144`). | Same as Stator. Image `opt_stator_stack.png`. |
| **Sickle leading edge** (`opt_sickle`) | GEOMETRY (rotor) | `--sickle`: the leading edge is swept forward in the rotation plane. Tip `le_skew` is searched over 4–12 mm (`SICKLE_BOUNDS`, `search_space.py:495`), mid is 40 % of tip, hub 0 (`apply_sickle`, `blade.py:1358`; `study.py:181`). | **Yes**, a scimitar outline. Image `opt_sickle.png` (subtle at this size, like the existing Sickle slider images). |
| **Stepped inlet casing** (`opt_stepped`) | GEOMETRY (CFD casing) | `--stepped-inlet`: the CFD duct gets a 1.2 mm larger bore for the first 6 mm (`cfd/casing.py:15-16`). It is not on the blade, and **not in the exported STL**. | No, not the fan. It changes only the virtual test casing. Image `opt_stepped.png`. |
| **Notched tip trailing edge** (`opt_notched`) | GEOMETRY (rotor) | `--notched-tips`: three fixed 1.5 mm bites in the trailing edge over the outer 12 % (`apply_notched_tips`, `blade.py:1372`; `study.py:185`). | **Yes**, small cuts. Image `opt_notched.png`. |
| **BEM ranking screen** (`opt_bem`) | SEARCH | `--bem-prescreen 32`: a quick blade-element estimate. Trials predicted under 32 CFM skip CFD. | No stamp. It can prune shapes that BEM under-rates (BEM reads about 0.6× CFD), so it can change the winner. |
| **Catalog GP skip** (`opt_gp`) | SEARCH | `--surrogate-prescreen 40`: a Gaussian process trained on the catalog predicts free CFM. Trials with mean+uncertainty under 40 skip CFD. | No stamp. Same pruning effect. |
| **Boost + GP mean** (`opt_gp_boost`) | SEARCH | `--surrogate-boost`: boosted trees give the GP's mean. **Only added when GP skip or Surrogate-guided is on** (`cli_argv.py:164-173`). Otherwise it does nothing (UI-34). | No stamp. |
| **NN + GP mean** (`opt_gp_nn`) | SEARCH | `--surrogate-nn`: a small neural net gives the mean and beats Boost if both are on. Same condition as Boost. | No stamp. |
| **Surrogate-guided** (`opt_surrogate_guided`) | SEARCH (replaces the whole study) | `--surrogate-guided`: `run_optimization.py:160-192` takes a separate path: 24-point DoE → fit GP/boost/NN → NSGA-II on the model (64) → verify the top 4 → 2 rounds. The cockpit **never passes `--verify-cfd`**, so both the training labels and the "verify" step use `synthetic_label()`, a test formula (`surrogate_search.py:309-326, 458, 477`). | **Yes, wrongly.** The winner is decided by a formula that favours a wide tip chord, a high mid stagger, more blades and less camber, not by CFD. This path also **ignores** Trials, every Geometry stamp, Search RPM, Refine op and roughness. See UI-31 (HIGH). |
| **Search RPM in PWM band** (`opt_search_rpm`) | EVAL / SEARCH | `--search-rpm`: speed becomes an Optuna variable inside [RPM min, RPM max] (`pwm_table.suggest_rpm`, `study.py:192`). | Not directly. Each design is scored at the RPM the optimizer picks, so the best shape for a variable-speed fan can differ (e.g. lower pitch at a higher RPM). |
| **PWM RPM min / max** (`opt_rpm_min/max`, default 450/2000) | EVAL | The band for Search RPM, validated by `resolve_pwm_table` (`fan_optimize.py:111-127`). These fields only show when Search RPM is on. | Indirect, as above. |

### Shared with Assess (in "Assess & print", but they also change Optimize)

`fan_optimize.py:136-151` passes these to Optimize too:

| Setting | Class | What it does | Shape? |
|---|---|---|---|
| **Application (hose resistance)** (`assess_preset`, default `case`) | EVAL | `--preset`: the back-pressure each design is scored at. case 8 Pa, heatsink 20 Pa, radiator 35 Pa, legacy 1 Pa (`optimize/presets.py:18-33`). | Indirect but strong. Higher pressure favours steeper-pitch, more-blade, higher-solidity fans. Image `assess_preset.png`. **No tooltip today.** |
| **Print material** (`assess_material`, default PETG) | EVAL (constraint) | `--material`: root stress, bending, flutter, tip deflection and weight gates (`objectives.py:230-267, 358, 613`). | Indirect. A weaker material rejects or penalises thin and long-chord blades. No image (it is a gate, not a shape); **no tooltip today.** |
| **Third CFD at operating point** (`assess_refine_op`) | EVAL | `--refine-op`: a 3rd solve at the real operating pressure instead of a 2-point estimate (`objectives.py:590-591`). It takes about 50 % longer. | Indirect, through more honest load CFM. Image `assess_refine_op.png`. |
| **FDM wall roughness** (`assess_wall_ks`) | EVAL | `--wall-ks-mm 0.10` (`FDM_WALL_KS_MM`, `cfd/wall_roughness.py:11`): a rough wall model on the impeller and frame/stator. | Indirect. Image `assess_wall_ks.png`. |

- Loading a design from the picker **overwrites** these Assess/Optimize settings with that design's saved values (`fan_trials.py:103-105`), with no notice (UI-38).
- Not settable in the UI: `--space guided` and `--mountable` are always on. `--mountable` is a hub-fits-motor constraint (defaults at `cli_argv.py:121-122`; the cockpit never overrides them).

## 4. Other settings in plain words (by area)

- **Fan › Design › Geometry** (`fan_tab_ui.py:668-890`, both modes) is all **GEOMETRY**. Each slider writes `e_<key>`. `fan_editor` turns these into the flat dict → `blade_from_flat` (`search_space.py`) → `build_impeller`. Groups:
  - Blades and spacing (count, uneven angles).
  - Planform: chord root/mid/tip (blade width) and stagger root/mid/tip (pitch).
  - Section: family NACA/plate; camber root/mid/tip (scoop) and camber position.
  - Thickness: mode tapered/uniform, wall mm, t/c root/mid/tip, LE/TE thickness scale.
  - 3-D shape: wrap (lean), sweep, LE curve, sickle, skew, smooth span.
  - Tip: cylindrical trim, tip round and its start, TE notches and notch depth, winglet start/sweep/lean, shroud thickness/height.
  - Hub: radius, tip radius, hub height, blade-on-hub z, **hub profile**, hub nose.
  - Bio-features: tubercles, serrations, dimples.
  - 53 of these have image + text. `e_hub_profile` (`:856`, cylinder/cone/dome, `blade.py:145`) has neither, so I generated `e_hub_profile.png` and `e_hub_profile_dome.png`. "🎲 Randomize features" is a button.
- **Fan › Design › Assess & print** (`:892-1009`): see §3 for preset, material, refine and roughness.
  - Sweep param/steps/Run is EVAL (it runs Assess over one parameter). Out of scope to run; no tooltip.
- **Fan › Design › Fit & seed** (`:1119-1225`). All are GEOMETRY helpers that rewrite the Design sliders; none has a tooltip.
  - **Allow intake overbuild / Extra intake mm** (`intake_overbuild*`, 0–20 mm) lets blades and hub extend past the inlet face (+Z) when fitting (`fan_core.py:290-291`, `fan_viz.py:107`). The explanation is a caption below it, not a tooltip.
  - Seed-from-duty CFM/Pa/RPM/vortex fill stagger and camber magnitudes.
  - Fit envelope / Scale to hub resize the design.
- **Viewer** (highlight, envelope, direction cues, arrows/density/scale) is **DISPLAY**: it changes the 3-D view only. No tooltips; no images needed.
- **Export** (Fit hub to the motor, Fit tip + depth to the frame, Also export mirror, Show motor cup) is **GEOMETRY of the exported STL**: it carves the motor cup and grip pads and fits the envelope. No tooltips.
  - Images would help for "Fit hub to the motor" (cup carve) and "mirror" (CW/CCW). Not generated: the generator has no motor-cup path, so this is a follow-up.
- **Results** (Fits this fan only, Declutter, Show stock, airflow field toggle) is **DISPLAY**. No tooltips.
- **Library** (fan-model form, measurements, leeway sliders) is **DISPLAY/OTHER** (data entry and catalog filters). No tooltips.
  - The leeway sliders (`lee_*`, `:256-259`) go through `_slider` but have no `CONTROL_DESC` entry.
- **Fan header:** Fan model (hub) (`fan_model`, `:92`) is OTHER. It sets the frame envelope that Fit, Export and Optimize all use, which matters a lot for Optimize. **No tooltip.**
- **Action row** (Preview, Assess, Optimize, Cancel ×2, Randomize geometry, Reset; `:582-639`) has no tooltips. The labels carry time hints.
- **Prop / Mixed / Volute / CROR tabs** (Mixed, Volute and CROR are Expert-only, `app.py:190-221`): 108 of 109 controls have no tooltip; see UI-37. Their sliders are GEOMETRY of those machine types.
  - The generator cannot build them (it is fan-only), so no images were made for them. Their own `build_*` functions could be driven the same way as a follow-up.

## 5. Findings (new tracker rows UI-31 … UI-38)

| ID | Sev | Summary |
|---|---|---|
| UI-31 | HIGH | Surrogate-guided Optimize from the cockpit never runs CFD. Labels and "verify" come from `synthetic_label()`, a unit-test formula (`surrogate_search.py:309-326, 458, 477`), because the cockpit never passes `--verify-cfd`, and there is no toggle for it. The tooltip says "CFD when Docker verify is on". The path also silently ignores Trials, all 6 Geometry stamps, Search RPM/band, Refine op and roughness (`run_optimization.py:160-192`). |
| UI-32 | MED | Optimize (16 controls) and the Assess honesty switches have **no image tooltips**. The loader cannot show them even if images exist, because `fan_copy.py:14` globs only `e_*.png`, while `help_switch` already calls `_IMG_URI.get("opt_…")`. Fix: glob `*.png` (or `e_*`, `opt_*`, `assess_*`) and add the proposed images. 16 proposals are in the handoff. |
| UI-33 | MED | The UI does not say that Optimize ignores the current Design sliders. It searches the "guided" space for the fan model from scratch (`study.py:176`; no seed or `enqueue_trial`), and only fan model, stamps and Assess settings carry over. Kimball's question shows the gap. Suggest a caption: "Optimize searches new shapes for this frame; your sliders are not used." |
| UI-34 | MED | "Boost + GP mean" and "NN + GP mean" are silent no-ops unless Catalog GP skip **or** Surrogate-guided is on (`cli_argv.py:164-173`). They are not disabled, and the tooltip names only GP skip. |
| UI-35 | MED | 13 existing tooltip images label "min/max" values that differ from the slider's real range, because `generate_control_images.py` `CONTROLS` drifted. Worst: Skew mid/tip show ±6 on a ±20/±25 slider. Others: camber ×3 (0.12 vs 0.15), hub radius (30 vs 35), winglet sweep/lean, notch depth, wall mm, LE/TE thickness, shroud height. Full list: `data/range_check.json`. Re-renders at the slider range are in `img/range_fix/`. Counts whose min is 0 = off, and dynamic maxima (hub height, blade-on-hub, hub nose), were left alone. |
| UI-36 | MED | 49 Fan-tab settings have no tooltip at all. They include settings that change results: Fan model, Hub profile (no text or image), Application preset, Print material, Sweep, Intake overbuild, Seed-from-duty fields, the Export fit switches and the whole action row. Proposed images: `e_hub_profile*.png`, `assess_preset.png`. |
| UI-37 | LOW | The Prop, Mixed, Volute and CROR tabs and the shared blade panels have 0 tooltips on 108 controls. The shared `slider()` looks up `CONTROL_DESC` by the **prefixed** model name (`p_…`, `mf_…`, `cror_f_…`), which never matches. `BLADE_DESC` exists but is used only for Cylindrical tip (`blade_editor.py:150`). |
| UI-38 | LOW | Assess-panel settings silently drive Optimize, and loading a design overwrites them. Application and Print material don't say they also apply to Optimize (only the two switches do). Picking a design resets preset, refine op and roughness to that design's saved values (`fan_trials.py:103-105`) with no message. |

## 6. Proposed images (`handoff/2026-10-31_from-qa-tooltips/img/`, 460×250 PNG)

| File | Setting | Made with | Notes |
|---|---|---|---|
| `e_hub_profile.png`, `e_hub_profile_dome.png` | Hub profile | repo generator (wrapper) | cylinder→cone, cylinder→dome; hub nose 12 mm |
| `opt_shroud.png` | Tip ring / shroud | repo generator (wrapper) | 0 → 1.6 mm ring at 0.65 height |
| `opt_sickle.png` | Sickle LE | repo generator (wrapper) | `sickle_mm` 0 → 12 (top of search range) |
| `opt_notched.png` | Notched tip TE | repo generator (wrapper) | off → 3×1.5 mm; subtle at 360 px, like the existing `e_tip_notched` |
| `opt_stator.png`, `opt_stator_stack.png` | Stator / stack | `render_stationary.py` (same pyvista style) | blue = stationary part, grey = rotor for context |
| `opt_stepped.png` | Stepped inlet | `schematics.py` | section drawing; the 3-D tube view was unreadable |
| `opt_trials.png`, `opt_resume.png`, `opt_bem.png`, `opt_gp.png`, `opt_gp_boost.png`, `opt_gp_nn.png`, `opt_surrogate_guided.png`, `opt_search_rpm.png` | SEARCH | `schematics.py` | flow/schematic. PWM RPM min/max can reuse `opt_search_rpm.png`. |
| `assess_preset.png`, `assess_refine_op.png`, `assess_wall_ks.png` | EVAL | `schematics.py` | illustrative curves; values from code |
| `range_fix/e_*.png` (13) | existing Geometry sliders | repo generator (wrapper) | drop-in replacements at the real slider range (UI-35) |

- **No image needed (skipped):**
  - Viewer, Results and Library controls: display/data entry, and the effect is visible immediately.
  - Print material: a pass/fail gate with no visual.
  - Sweep: it runs Assess.
  - Seed/Fit buttons: they change sliders that already have images.
  - Proxy-tab sliders: the generator is fan-only (follow-up).
- **To adopt:**
  1. Copy the files into `docs/control_images/`.
  2. Change the glob at `fan_copy.py:14`.
  3. For VSelect/VSwitch/VTextField controls that are not helpers, swap to `help_select`/`help_switch` or wrap them by hand.
  4. Add the generator rows from `run_repo_generator.py` to `CONTROLS`, so the images can be regenerated.

## Appendix: full inventory

Generated from `data/inventory.json`. Status: IMG = image + text, TXT = text only, — = none. Mode is from `v_show` and was confirmed headless for Fan and the tabs.

| File:line | Area | Mode | Widget | Label | Model | Status | Image | Text tooltip (quoted) |
|---|---|---|---|---|---|---|---|---|
| app.py:163 | Header / tabs | Both | VBtnToggle |  | ui_mode | — |  |  |
| app.py:165 | Header / tabs | Both | VBtn | Simple |  | — |  |  |
| app.py:166 | Header / tabs | Both | VBtn | Expert |  | — |  |  |
| app.py:183 | Header / tabs | Both | VTab | Fan · CFD |  | TXT |  | “Fan — CFD-checked axial PC-fan blades (printable STL)” |
| app.py:190 | Header / tabs | Expert | VTab | Mixed · estimate |  | TXT |  | “Mixed-flow — drop-in impeller (rough estimate, not full Fan CFD)” |
| app.py:202 | Header / tabs | Expert | VTab | Volute · estimate |  | TXT |  | “Volute — radial blower (rough estimate, ranking only)” |
| app.py:214 | Header / tabs | Both | VTab | Prop · fast estimate |  | TXT |  | “Propeller — fast estimate (~1 s). Optional CFD check.” |
| app.py:221 | Header / tabs | Expert | VTab | CROR · estimate |  | TXT |  | “CROR — stacked rotors (fast estimate, not full CFD)” |
| blade_editor.py:121 | Prop+CROR shared shape panels | Both | slider | _lab("thick_mm", "Uniform wall") | f"{p}thick_mm" | — |  |  |
| blade_editor.py:127 | Prop+CROR shared shape panels | Both | slider | t/c root | f"{p}thickness_root" | — |  |  |
| blade_editor.py:128 | Prop+CROR shared shape panels | Both | slider | t/c mid | f"{p}thickness_mid" | — |  |  |
| blade_editor.py:129 | Prop+CROR shared shape panels | Both | slider | t/c tip | f"{p}thickness_tip" | — |  |  |
| blade_editor.py:130 | Prop+CROR shared shape panels | Both | slider | Camber root | f"{p}camber_root" | — |  |  |
| blade_editor.py:131 | Prop+CROR shared shape panels | Both | slider | Camber mid | f"{p}camber_mid" | — |  |  |
| blade_editor.py:132 | Prop+CROR shared shape panels | Both | slider | Camber tip | f"{p}camber_tip" | — |  |  |
| blade_editor.py:133 | Prop+CROR shared shape panels | Both | slider | Camber pos | f"{p}camber_pos" | — |  |  |
| blade_editor.py:136 | Prop+CROR shared shape panels | Both | slider | Sweep mid | f"{p}sweep_mid" | — |  |  |
| blade_editor.py:137 | Prop+CROR shared shape panels | Both | slider | Sweep tip | f"{p}sweep_tip" | — |  |  |
| blade_editor.py:138 | Prop+CROR shared shape panels | Both | slider | LE curve mid | f"{p}le_sweep_mid" | — |  |  |
| blade_editor.py:139 | Prop+CROR shared shape panels | Both | slider | LE curve tip | f"{p}le_sweep_tip" | — |  |  |
| blade_editor.py:140 | Prop+CROR shared shape panels | Both | slider | Sickle mid | f"{p}le_skew_mid" | — |  |  |
| blade_editor.py:141 | Prop+CROR shared shape panels | Both | slider | Sickle tip | f"{p}le_skew_tip" | — |  |  |
| blade_editor.py:142 | Prop+CROR shared shape panels | Both | slider | Wrap mid | f"{p}lean_mid" | — |  |  |
| blade_editor.py:143 | Prop+CROR shared shape panels | Both | slider | Wrap tip | f"{p}lean_tip" | — |  |  |
| blade_editor.py:147 | Prop+CROR shared shape panels | Both | help_switch | Cylindrical tip | f"{p}cylindrical_tip" | TXT |  | “Cut tip to a cylinder at tip radius so OD is constant.” |
| blade_editor.py:152 | Prop+CROR shared shape panels | Both | slider | Tip round | f"{p}tip_round" | — |  |  |
| blade_editor.py:153 | Prop+CROR shared shape panels | Both | slider | Tip round start | f"{p}tip_round_start" | — |  |  |
| cror_tab.py:597 | Cror tab | Expert | _slider | Hub R (mm) | cror_hub_r | — |  |  |
| cror_tab.py:598 | Cror tab | Expert | _slider | Tip R (mm) | cror_tip_r | — |  |  |
| cror_tab.py:599 | Cror tab | Expert | _slider | Axial gap (mm) | cror_gap | — |  |  |
| cror_tab.py:603 | Cror tab | Expert | _slider | Front blades | cror_f_n | — |  |  |
| cror_tab.py:604 | Cror tab | Expert | _slider | Chord root | cror_f_chord_root | — |  |  |
| cror_tab.py:606 | Cror tab | Expert | _slider | Chord mid | cror_f_chord_mid | — |  |  |
| cror_tab.py:608 | Cror tab | Expert | _slider | Chord tip | cror_f_chord_tip | — |  |  |
| cror_tab.py:610 | Cror tab | Expert | _slider | Stagger | cror_f_stagger | — |  |  |
| cror_tab.py:626 | Cror tab | Expert | _slider | Rear blades | cror_r_n | — |  |  |
| cror_tab.py:627 | Cror tab | Expert | _slider | Chord root | cror_r_chord_root | — |  |  |
| cror_tab.py:629 | Cror tab | Expert | _slider | Chord mid | cror_r_chord_mid | — |  |  |
| cror_tab.py:631 | Cror tab | Expert | _slider | Chord tip | cror_r_chord_tip | — |  |  |
| cror_tab.py:633 | Cror tab | Expert | _slider | Stagger | cror_r_stagger | — |  |  |
| cror_tab.py:647 | Cror tab | Expert | VBtn | Thin to depth |  | — |  |  |
| cror_tab.py:714 | Cror tab | Expert | VTextField | Trials | cror_trials | — |  |  |
| cror_tab.py:723 | Cror tab | Expert | VTextField | RPM | cror_rpm | — |  |  |
| cror_tab.py:732 | Cror tab | Expert | VTextField | Max depth mm | cror_max_depth | — |  |  |
| cror_tab.py:742 | Cror tab | Expert | VTextField | CFD refine top N | cror_cfd_top | — |  |  |
| cror_tab.py:751 | Cror tab | Expert | VBtn | CFD refine |  | — |  |  |
| cror_tab.py:766 | Cror tab | Expert | VSelect | Previous runs | cror_sel_idx | — |  |  |
| cror_tab.py:788 | Cror tab | Expert | VSelect | Previous runs | cror_sel_idx | — |  |  |
| cror_tab.py:840 | Cror tab | Expert | VBtnToggle |  | cror_airflow_field | — |  |  |
| cror_tab.py:847 | Cror tab | Expert | VBtn | \|U\| midplane |  | — |  |  |
| cror_tab.py:848 | Cror tab | Expert | VBtn | pressure midplane |  | — |  |  |
| cror_tab.py:849 | Cror tab | Expert | VBtn | axial Uz |  | — |  |  |
| cror_tab.py:850 | Cror tab | Expert | VBtn | streamlines |  | — |  |  |
| fan_tab_ui.py:92 | Fan header | Both | VSelect | Fan model (hub) | fan_model | — |  |  |
| fan_tab_ui.py:111 | Fan header | Both | VTab | Design |  | — |  |  |
| fan_tab_ui.py:112 | Fan header | Both | VTab | Results |  | — |  |  |
| fan_tab_ui.py:113 | Fan › Results | Both | VTab | Library |  | — |  |  |
| fan_tab_ui.py:116 | Fan › Results | Both | VSwitch | Fits this fan only | fits_only | — |  |  |
| fan_tab_ui.py:132 | Fan › Results | Both | VSwitch | Declutter (hide near-duplicates) | declutter | — |  |  |
| fan_tab_ui.py:141 | Fan › Results | Both | VSwitch | Show stock (published) | show_stock | — |  |  |
| fan_tab_ui.py:170 | Fan › Results | Both | VSelect | Design | selected_trial | — |  |  |
| fan_tab_ui.py:231 | Fan › Library | Both | VBtn | Scale to this hub |  | — |  |  |
| fan_tab_ui.py:256 | Fan › Library | Both | _slider | Tip past frame | lee_tip | — |  |  |
| fan_tab_ui.py:257 | Fan › Library | Both | _slider | Extra depth Z | lee_depth | — |  |  |
| fan_tab_ui.py:258 | Fan › Library | Both | _slider | Over-voltage | lee_overvolt | — |  |  |
| fan_tab_ui.py:259 | Fan › Library | Both | _slider | Extra weight | lee_weight | — |  |  |
| fan_tab_ui.py:268 | Fan › Library | Both | VBtn | Load selected model into form |  | — |  |  |
| fan_tab_ui.py:276 | Fan › Library | Both | VTextField | Model name (new name = create) | fm_key | — |  |  |
| fan_tab_ui.py:286 | Fan › Library | Both | VTextField | Max tip dia (mm) | fm_tip_max | — |  |  |
| fan_tab_ui.py:296 | Fan › Library | Both | VTextField | Max depth (mm) | fm_depth_max | — |  |  |
| fan_tab_ui.py:307 | Fan › Library | Both | VTextField | Hub dia min (mm) | fm_hub_min | — |  |  |
| fan_tab_ui.py:317 | Fan › Library | Both | VTextField | Hub dia max (mm) | fm_hub_max | — |  |  |
| fan_tab_ui.py:329 | Fan › Library | Both | VTextField | Cavity dia | fm_cav_dia | — |  |  |
| fan_tab_ui.py:339 | Fan › Library | Both | VTextField | Cavity depth | fm_cav_depth | — |  |  |
| fan_tab_ui.py:349 | Fan › Library | Both | VTextField | Min hub H | fm_hub_h | — |  |  |
| fan_tab_ui.py:360 | Fan › Library | Both | VBtn | 💾 Save model |  | — |  |  |
| fan_tab_ui.py:362 | Fan › Library | Both | VBtn | 🗑 Delete |  | — |  |  |
| fan_tab_ui.py:384 | Fan › Library | Both | VTextField | Measured CFM | meas_cfm | — |  |  |
| fan_tab_ui.py:394 | Fan › Library | Both | VTextField | Static Pa | meas_static | — |  |  |
| fan_tab_ui.py:405 | Fan › Library | Both | VTextField | Noise dB(A) | meas_noise | — |  |  |
| fan_tab_ui.py:415 | Fan › Library | Both | VTextField | RPM | meas_rpm | — |  |  |
| fan_tab_ui.py:426 | Fan › Library | Both | VTextField | Material (printed) | meas_material | — |  |  |
| fan_tab_ui.py:435 | Fan › Library | Both | VSelect | Print type | meas_print_type | — |  |  |
| fan_tab_ui.py:445 | Fan › Library | Both | VTextField | Weight g | meas_weight | — |  |  |
| fan_tab_ui.py:454 | Fan › Library | Both | VTextField | Instrument | meas_instrument | — |  |  |
| fan_tab_ui.py:462 | Fan › Library | Both | VTextField | Notes | meas_notes | — |  |  |
| fan_tab_ui.py:472 | Fan › Library | Both | VBtn | Save measurement |  | — |  |  |
| fan_tab_ui.py:480 | Fan › Library | Both | VBtn | Show store calibration |  | — |  |  |
| fan_tab_ui.py:516 | Fan › Design (top) | Both | VBtn | About |  | — |  |  |
| fan_tab_ui.py:522 | Fan › Design (top) | Both | VSelect | (edited_stale ? '✎ Edited copy (not saved) — based on:' : 'Design (unlocks Preview / Assess / Export)') | selected_trial | — |  |  |
| fan_tab_ui.py:582 | Fan action row | Both | VBtn(action) | Preview (sec) |  | — |  |  |
| fan_tab_ui.py:590 | Fan action row | Both | VBtn(action) | Assess (~15–30 min) |  | — |  |  |
| fan_tab_ui.py:600 | Fan action row | Both | VBtn(action) | Optimize (hours) |  | — |  |  |
| fan_tab_ui.py:610 | Fan action row | Both | VBtn(action) | ⏹ Cancel opt |  | — |  |  |
| fan_tab_ui.py:620 | Fan action row | Both | VBtn(action) | ⏹ Cancel Assess |  | — |  |  |
| fan_tab_ui.py:630 | Fan action row | Both | VBtn(action) | Randomize geometry |  | — |  |  |
| fan_tab_ui.py:639 | Fan › Design (top) | Both | VBtn | Reset |  | — |  |  |
| fan_tab_ui.py:639 | Fan action row | Both | VBtn | Reset |  | — |  |  |
| fan_tab_ui.py:677 | Fan › Design › Geometry | Both | _slider | Blades | e_n_blades | IMG | docs/control_images/e_n_blades.png | “How many blades. More = more airflow & pressure, but louder and less efficient.” |
| fan_tab_ui.py:678 | Fan › Design › Geometry | Both | _slider | Chord root | e_chord_root | IMG | docs/control_images/e_chord_root.png | “Blade WIDTH at the hub — leading edge to trailing edge (planform). Not wall thickness.” |
| fan_tab_ui.py:679 | Fan › Design › Geometry | Both | _slider | Chord mid | e_chord_mid | IMG | docs/control_images/e_chord_mid.png | “Blade WIDTH at mid-span (LE→TE). Not the thin wall through the blade.” |
| fan_tab_ui.py:680 | Fan › Design › Geometry | Both | _slider | Chord tip | e_chord_tip | IMG | docs/control_images/e_chord_tip.png | “Blade WIDTH at the tip (LE→TE). Raise this when the tip flattens (lower stagger) so the planform still covers the reference. Slider goes to 70 mm.” |
| fan_tab_ui.py:688 | Fan › Design › Geometry | Both | _slider | Stagger root | e_stagger_root | IMG | docs/control_images/e_stagger_root.png | “Blade PITCH angle at the hub. Higher = more axial (flow); lower = blades overlap (pressure).” |
| fan_tab_ui.py:689 | Fan › Design › Geometry | Both | _slider | Stagger mid | e_stagger_mid | IMG | docs/control_images/e_stagger_mid.png | “Blade PITCH angle at mid-span.” |
| fan_tab_ui.py:690 | Fan › Design › Geometry | Both | _slider | Stagger tip | e_stagger_tip | IMG | docs/control_images/e_stagger_tip.png | “Blade PITCH angle at the tip.” |
| fan_tab_ui.py:693 | Fan › Design › Geometry | Both | _help_select | Section family | e_section_family | IMG | docs/control_images/e_section_family.png | “NACA = cambered airfoil with sharp LE/TE. Rounded plate = constant wall, tunable LE/TE roundness + camber (bows the blade face — the slight tip→hub curve). Wrap/lean still set the spanwise vortex planform.” |
| fan_tab_ui.py:706 | Fan › Design › Geometry | Both | _slider | Camber root | e_camber_root | IMG | docs/control_images/e_camber_root.png | “Blade SCOOP at the hub — the face curves from leading edge to trailing edge (technical name: camber). Tip-on, a scooped blade looks U-shaped; zero camber is a flat paddle. This is what matches the white reference scoop. Wrap/sickle only move the planform outline.” |
| fan_tab_ui.py:707 | Fan › Design › Geometry | Both | _slider | Camber mid | e_camber_mid | IMG | docs/control_images/e_camber_mid.png | “Blade SCOOP at mid-span (camber). Raise this with tip camber until the tip-on overlay matches the reference. Works on NACA and Rounded plate.” |
| fan_tab_ui.py:708 | Fan › Design › Geometry | Both | _slider | Camber tip | e_camber_tip | IMG | docs/control_images/e_camber_tip.png | “Blade SCOOP at the tip (camber) — usually the biggest visual match to the reference tip-on U-curve. Stock tip is ~0.12; slider goes to 0.15. Press Preview after changing.” |
| fan_tab_ui.py:716 | Fan › Design › Geometry | Both | _slider | Camber position | e_camber_pos | IMG | docs/control_images/e_camber_pos.png | “Where max camber sits along the chord (0.2 = near LE, 0.6 = aft). Fraction of chord — not mm.” |
| fan_tab_ui.py:717 | Fan › Design › Geometry | Both | _help_select | Thickness span | e_thick_mode | IMG | docs/control_images/e_thick_mode.png | “Uniform wall = same mm through the blade at every station. Tapered = independent t/c. Does not set LE→TE width — that is Chord.” |
| fan_tab_ui.py:727 | Fan › Design › Geometry | Both | _slider | Wall thickness | e_thick_mm | IMG | docs/control_images/e_thick_mm.png | “Wall thickness through the blade (mm), held constant root→tip. This is the thin dimension — not chord/width. Typical printed fan ~1.8–2.8 mm. Use Rounded plate; set LE/TE roundness ~0.2 (full LE bullnose fights uniform wall).” |
| fan_tab_ui.py:732 | Fan › Design › Geometry | Both | _slider | Wall t/c root | e_thick_root | IMG | docs/control_images/e_thick_root.png | “Wall t/c at the hub (fraction of chord). Tapered mode only. Through-blade thickness, not LE→TE width.” |
| fan_tab_ui.py:737 | Fan › Design › Geometry | Both | _slider | Wall t/c mid | e_thick_mid | IMG | docs/control_images/e_thick_mid.png | “Wall t/c at mid-span. Tapered mode only.” |
| fan_tab_ui.py:742 | Fan › Design › Geometry | Both | _slider | Wall t/c tip | e_thick_tip | IMG | docs/control_images/e_thick_tip.png | “Wall t/c at the tip. Tapered mode only.” |
| fan_tab_ui.py:754 | Fan › Design › Geometry | Both | _slider | LE thick / roundness | e_le_thick | IMG | docs/control_images/e_le_thick.png | “LEADING-EDGE control. NACA: thickness scale (1 = stock; >1 fattens the nose). Plate: LE roundness 0–1 (1 = full bullnose bead — fights uniform wall; ~0.2 = sharp). If left at 1 with plate, LE follows TE roundness. Click Preview after changing.” |
| fan_tab_ui.py:758 | Fan › Design › Geometry | Both | _slider | TE thick / roundness | e_te_thick | IMG | docs/control_images/e_te_thick.png | “TRAILING-EDGE control. NACA: thickness scale (1 = stock; <1 thins aft; >1 fattens). Plate: TE roundness 0–1 (1 = full bullnose, ~0.2 = sharp printable TE).” |
| fan_tab_ui.py:772 | Fan › Design › Geometry | Both | _help_switch | Smooth span curves | e_smooth_span | IMG | docs/control_images/e_smooth_span.png | “Smooth span curves (PCHIP) — interpolate hub→mid→tip with a shape-preserving cubic so mid wrap/sweep/skew don't put a sharp kink in the blade. Off = linear (historical).” |
| fan_tab_ui.py:778 | Fan › Design › Geometry | Both | _slider | Wrap mid | e_lean_mid | IMG | docs/control_images/e_lean_mid.png | “Circumferential WRAP at mid-span — wraps blades so they overlap like a real fan.” |
| fan_tab_ui.py:779 | Fan › Design › Geometry | Both | _slider | Wrap tip | e_lean_tip | IMG | docs/control_images/e_lean_tip.png | “Circumferential WRAP at the tip (0 = a flat radial paddle).” |
| fan_tab_ui.py:780 | Fan › Design › Geometry | Both | _slider | Sweep mid | e_sweep_mid | IMG | docs/control_images/e_sweep_mid.png | “Axial rake of the WHOLE mid section (mm, + toward outlet / +Z). Wider range for matching reference STLs.” |
| fan_tab_ui.py:781 | Fan › Design › Geometry | Both | _slider | Sweep tip | e_sweep_tip | IMG | docs/control_images/e_sweep_tip.png | “Axial rake of the WHOLE tip section (mm, + toward outlet / +Z).” |
| fan_tab_ui.py:782 | Fan › Design › Geometry | Both | _slider | LE curve mid | e_le_mid | IMG | docs/control_images/e_le_mid.png | “Rakes only the LEADING edge at mid-span (mm) — curves the LE line, trailing edge unchanged.” |
| fan_tab_ui.py:783 | Fan › Design › Geometry | Both | _slider | LE curve tip | e_le_tip | IMG | docs/control_images/e_le_tip.png | “Rakes only the LEADING edge at the tip (mm).” |
| fan_tab_ui.py:784 | Fan › Design › Geometry | Both | _slider | Sickle mid | e_le_skew_mid | IMG | docs/control_images/e_le_skew_mid.png | “Sickle / LE skew at mid-span (mm) — shifts only the leading-edge region sideways in the rotation plane (scimitar). Trailing edge stays put. 0 = radial LE. Not live: press Preview. If Preview times out, the old mesh stays on screen so sickle looks like it did nothing.” |
| fan_tab_ui.py:785 | Fan › Design › Geometry | Both | _slider | Sickle tip | e_le_skew_tip | IMG | docs/control_images/e_le_skew_tip.png | “Sickle / LE skew at the tip (mm). Typical printed PC-fan tips sit around 4–12 mm. Same axis as Optimize → Sickle leading edge. Press Preview — a timed-out build keeps the previous orange mesh.” |
| fan_tab_ui.py:786 | Fan › Design › Geometry | Both | _slider | Skew mid | e_skew_mid | IMG | docs/control_images/e_skew_mid.png | “Skew (mm) — shifts the whole mid section sideways (tangentially). Fine balance/overlap tweak.” |
| fan_tab_ui.py:787 | Fan › Design › Geometry | Both | _slider | Skew tip | e_skew_tip | IMG | docs/control_images/e_skew_tip.png | “Skew (mm) — shifts the whole tip section sideways (tangentially). Wide range for matching reference planforms.” |
| fan_tab_ui.py:791 | Fan › Design › Geometry | Both | _help_switch | Cylindrical tip (match cover) | e_cylindrical_tip | IMG | docs/control_images/e_cylindrical_tip.png | “Cuts each blade tip to a cylinder at Tip radius so the outer tip face matches the fan-cover circle (constant OD). Off = legacy tips with LE/TE corners that bulge past Tip radius. Tip Round still petals the planform before the cut.” |
| fan_tab_ui.py:796 | Fan › Design › Geometry | Both | _slider | Tip round | e_tip_round | IMG | docs/control_images/e_tip_round.png | “Rounds the blade TIP — tapers the chord over the outer span so the leading & trailing edges curve together, instead of a blunt straight tip edge. 0 = square.” |
| fan_tab_ui.py:797 | Fan › Design › Geometry | Both | _slider | Tip round start | e_tip_start | IMG | docs/control_images/e_tip_start.png | “Where the tip rounding begins (fraction of span). Lower = a longer, gentler rounded tip; higher = a small rounded cap near the very tip.” |
| fan_tab_ui.py:798 | Fan › Design › Geometry | Both | _help_switch | Tip TE notches (3 boxy bites) | e_tip_notched | IMG | docs/control_images/e_tip_notched.png | “Three boxy / skewed-rectangle bites cut into the outer trailing edge (close-ref A12x25 tip TE steps). Not spanwise owl serrations and not LE tubercles. Slows Preview — wait for it to finish after changing Sickle/Wrap.” |
| fan_tab_ui.py:803 | Fan › Design › Geometry | Both | _slider | Tip notch depth | e_tip_notch_depth | IMG | docs/control_images/e_tip_notch_depth.png | “How deep each tip TE notch cuts toward mid-chord (mm). Stock ≈ 1.5 mm. Deeper = more staircase on the TE.” |
| fan_tab_ui.py:818 | Fan › Design › Geometry | Both | _slider | Winglet start | e_winglet_span | IMG | docs/control_images/e_winglet_span.png | “Where the WINGLET starts (fraction of span). Below this the blade is straight; beyond it the tip curls.” |
| fan_tab_ui.py:819 | Fan › Design › Geometry | Both | _slider | Winglet sweep | e_winglet_sweep | IMG | docs/control_images/e_winglet_sweep.png | “Winglet AXIAL bend (mm) — curls the tip forward/up out of the rotation plane (a real winglet). 0 = off.” |
| fan_tab_ui.py:820 | Fan › Design › Geometry | Both | _slider | Winglet lean | e_winglet_lean | IMG | docs/control_images/e_winglet_lean.png | “Winglet CIRCUMFERENTIAL curl (deg) — wraps the tip around the axis. 0 = off.” |
| fan_tab_ui.py:821 | Fan › Design › Geometry | Both | _slider | Shroud thickness | e_shroud_thick | IMG | docs/control_images/e_shroud_thick.png | “Radial wall of a ring fused at the blade tips (mm). 0 = open tip. Grows the outer diameter by twice this amount.” |
| fan_tab_ui.py:822 | Fan › Design › Geometry | Both | _slider | Shroud height | e_shroud_height | IMG | docs/control_images/e_shroud_height.png | “How much of the tip chord the ring covers. 1 = full span. Below 1 the hoop starts at the trailing edge. BEM still treats a partial ring as an open tip.” |
| fan_tab_ui.py:838 | Fan › Design › Geometry | Both | _slider | Hub radius | e_hub_radius | IMG | docs/control_images/e_hub_radius.png | “Hub size (mm). Smaller hub = bigger flow annulus (more airflow/efficiency); must fit the model's hub limits.” |
| fan_tab_ui.py:840 | Fan › Design › Geometry | Both | _slider | Tip radius / length | e_tip_radius | IMG | docs/control_images/e_tip_radius.png | “Blade LENGTH / outer radius (mm). Shrink it to make an oversized blade fit the frame (tip diameter) or trim depth.” |
| fan_tab_ui.py:842 | Fan › Design › Geometry | Both | _slider | Hub height (0=auto) | e_hub_height | IMG | docs/control_images/e_hub_height.png | “Hub HEIGHT (mm). 0 = auto (just covers the blade roots — shortest). Raise it for a taller hub; it can't go below root coverage. Needs slack above the root span before Blade on hub can shift.” |
| fan_tab_ui.py:846 | Fan › Design › Geometry | Both | _slider | Blade on hub | e_blade_hub_z | IMG | docs/control_images/e_blade_hub_z.png | “Where the blade roots sit on the hub (mm). 0 = centered. Positive = blades higher toward the intake (+Z), with more hub below — matches the real A12x25 which sits toward the top face. Negative = blades lower / toward the outlet. Clamped so roots stay inside the hub.” |
| fan_tab_ui.py:856 | Fan › Design › Geometry | Both | VSelect | Hub profile | e_hub_profile | — |  |  |
| fan_tab_ui.py:865 | Fan › Design › Geometry | Both | _slider | Hub nose (cone/dome) | e_hub_nose | IMG | docs/control_images/e_hub_nose.png | “Nose height (mm) for the cone/dome hub profile. Adds a spinner on the intake side (increases depth — may go over-spec).” |
| fan_tab_ui.py:871 | Fan › Design › Geometry | Both | _slider | Uneven spacing | e_spacing | IMG | docs/control_images/e_spacing.png | “Uneven-but-balanced blade spacing to spread the blade-pass tone. 0 = evenly spaced.” |
| fan_tab_ui.py:874 | Fan › Design › Geometry | Both | VBtn | 🎲 Randomize features |  | — |  |  |
| fan_tab_ui.py:884 | Fan › Design › Geometry | Both | _slider | Tubercle amp | e_tub_amp | IMG | docs/control_images/e_tub_amp.png | “Tubercle amplitude — bumpy leading edge (whale-fin), delays stall.” |
| fan_tab_ui.py:885 | Fan › Design › Geometry | Both | _slider | Tubercle waves | e_tub_waves | IMG | docs/control_images/e_tub_waves.png | “Number of tubercle bumps along the span.” |
| fan_tab_ui.py:886 | Fan › Design › Geometry | Both | _slider | Serration amp | e_ser_amp | IMG | docs/control_images/e_ser_amp.png | “Serration depth — sawtooth trailing edge (owl-wing), cuts edge noise.” |
| fan_tab_ui.py:887 | Fan › Design › Geometry | Both | _slider | Serration teeth | e_ser_waves | IMG | docs/control_images/e_ser_waves.png | “Number of serration teeth.” |
| fan_tab_ui.py:888 | Fan › Design › Geometry | Both | _slider | Dimple depth | e_dim_amp | IMG | docs/control_images/e_dim_amp.png | “Dimple depth — golf-ball-style surface texture.” |
| fan_tab_ui.py:889 | Fan › Design › Geometry | Both | _slider | Dimple rows | e_dim_rows | IMG | docs/control_images/e_dim_rows.png | “Dimples along the chord.” |
| fan_tab_ui.py:890 | Fan › Design › Geometry | Both | _slider | Dimple cols | e_dim_cols | IMG | docs/control_images/e_dim_cols.png | “Dimples along the span.” |
| fan_tab_ui.py:901 | Fan › Design › Assess & print | Both | VSelect | Application (hose resistance) | assess_preset | — |  |  |
| fan_tab_ui.py:916 | Fan › Design › Assess & print | Both | VSelect | Print material (stress gate + vibration warning) | assess_material | — |  |  |
| fan_tab_ui.py:931 | Fan › Design › Assess & print | Both | VBtn | Score multi-point BEM (ranking only) |  | — |  |  |
| fan_tab_ui.py:951 | Fan › Design › Assess & print | Both | _help_switch | Third CFD at operating point (~50% longer) | assess_refine_op | TXT |  | “Runs a third CFD at the real hose operating pressure instead of estimating load CFM from two points. Used by Assess and by Optimize. When to use: more honest load CFM. Cost: ~50% longer per design. Risk: still RANS, not a lab measurement.” |
| fan_tab_ui.py:956 | Fan › Design › Assess & print | Both | _help_switch | FDM wall roughness (ks≈0.1 mm) | assess_wall_ks | TXT |  | “Models FDM print roughness (~0.1 mm sand grain) on impeller + frame/stator; casing stays smooth. Used by Assess and Optimize. When to use: printed-part honesty. Cost: same solve time. Risk: slightly lower predicted CFM vs smooth walls.” |
| fan_tab_ui.py:963 | Fan › Design › Assess & print | Both | VSelect | Sweep | sweep_param | — |  |  |
| fan_tab_ui.py:972 | Fan › Design › Assess & print | Both | VTextField | steps | sweep_steps | — |  |  |
| fan_tab_ui.py:981 | Fan › Design › Assess & print | Both | VBtn | Run |  | — |  |  |
| fan_tab_ui.py:1000 | Fan › Design › Assess & print | Both | VBtn | ⏹ Cancel |  | — |  |  |
| fan_tab_ui.py:1024 | Fan › Design › Optimize | Expert | VTextField | Trials | opt_trials | TXT |  | “How many CFD designs to try. Each trial is a full mesh+solve (often tens of minutes). Start small (8). More trials ≈ better Pareto coverage, linear wall-clock cost.” |
| fan_tab_ui.py:1035 | Fan › Design › Optimize | Expert | _help_switch | Continue the last Optimize run | opt_resume | TXT |  | “Add new trials to the most recent runs/cockpit_opt_* run instead of starting a new one. The optimizer only learns from trials in the same run, so separate small runs each restart with random warm-up designs; continuing lets the trials add up. Risk: mixes settings if you changed hose/flags since the last batch. With no earlier Optimize run it continues the opened run.” |
| fan_tab_ui.py:1043 | Fan › Design › Optimize | Expert | _help_switch | Tip ring / shroud | opt_shroud | TXT |  | “Also search designs with a plastic tip ring fused at the blade tips (kills tip leak). When to use: ducted / sealed-tip ideas. Cost: same CFD budget, slightly different geometry stamp. Risk: ring grows OD — tip radius is capped so it still fits the frame.” |
| fan_tab_ui.py:1044 | Fan › Design › Optimize | Expert | _help_switch | Stator vanes | opt_stator | TXT |  | “Replace the usual four-bar exit frame with a row of fixed guide vanes (straightens swirl). When to use: chasing pressure / efficiency after the rotor. Cost: same CFD count. Risk: can cut free CFM; mutually exclusive with stator+frame stack.” |
| fan_tab_ui.py:1045 | Fan › Design › Optimize | Expert | _help_switch | Stator + frame stack | opt_stator_stack | TXT |  | “Guide vanes first, then the four-bar frame a few mm downstream. When to use: mountable hardware that still needs OGVs. Cost: same CFD count. Risk: more blockage than stator alone; turns off plain stator.” |
| fan_tab_ui.py:1046 | Fan › Design › Optimize | Expert | _help_switch | Sickle leading edge | opt_sickle | TXT |  | “Forward-sweeps the leading edge in the rotation plane (scimitar / sickle shape). When to use: exploring tip loading / tone ideas. Cost: same CFD count. Risk: another geometry family — compare fairly against un-sickled runs.” |
| fan_tab_ui.py:1047 | Fan › Design › Optimize | Expert | _help_switch | Stepped inlet casing | opt_stepped | TXT |  | “Adds a concentric step on the circular inlet casing (not on the blade). When to use: inlet-conditioning experiments. Cost: same CFD count. Risk: casing-only change.” |
| fan_tab_ui.py:1048 | Fan › Design › Optimize | Expert | _help_switch | Notched tip trailing edge | opt_notched | TXT |  | “Cuts three small bites into the trailing edge near the tip. When to use: tip-tone experiments. Cost: same CFD count. Risk: fixed recipe (not a free search variable); do not expect proven dB cuts.” |
| fan_tab_ui.py:1054 | Fan › Design › Optimize | Expert | _help_switch | BEM ranking screen — skip CFD below ~32 CFM | opt_bem | TXT |  | “RANKING-ONLY blade-element screen: skip CFD if predicted hose CFM is below ~32. Not absolute CFM — ignores thickness/lean/wrap/LE-TE/plate; typically under-ranks CFD (~0.6×). When to use: large campaigns to burn fewer CFD hours. Never quote BEM beside CFD as equal.” |
| fan_tab_ui.py:1058 | Fan › Design › Optimize | Expert | _help_switch | Catalog GP skip below ~40 CFM free | opt_gp | TXT |  | “Catalog Gaussian-process guess of free-delivery CFM: skip CFD when mean+uncertainty is below ~40 CFM. When to use: with a populated catalog. Cost: faster after a few scored points. Risk: weak early on; uncertain predictions still run CFD.” |
| fan_tab_ui.py:1062 | Fan › Design › Optimize | Expert | _help_switch | Boost + GP mean | opt_gp_boost | TXT |  | “With Catalog GP skip on: use a boosted-tree mean + GP uncertainty. When to use: richer catalog. Cost: tiny CPU overhead. Risk: needs scikit-learn or falls back to GP-only.” |
| fan_tab_ui.py:1066 | Fan › Design › Optimize | Expert | _help_switch | NN + GP mean | opt_gp_nn | TXT |  | “With Catalog GP skip on: use a small neural net for the CFM mean + GP uncertainty (wins over Boost if both on). When to use: experimental surrogate. Cost: tiny. Risk: needs PyTorch or falls back to GP-only.” |
| fan_tab_ui.py:1070 | Fan › Design › Optimize | Expert | _help_switch | Surrogate-guided (DoE→NSGA on GP→verify top-k) | opt_surrogate_guided | TXT |  | “Pro loop: space-filling DoE → fit GP/boost/NN → NSGA-II on the surrogate → verify top-k (stub by default; CFD when Docker verify is on) → refit. Uses ensemble/GP spread as the acquisition signal. When to use: explore many designs cheaply before spending CFD. Cost: CPU for DoE+NSGA; CFD only on top-k if verify is enabled. Risk: surrogate can mis-rank early; verify is the honesty gate.” |
| fan_tab_ui.py:1078 | Fan › Design › Optimize | Expert | _help_switch | Search RPM in PWM band | opt_search_rpm | TXT |  | “Treat RPM as a searchable dial inside the fan’s PWM band (not fixed nameplate speed). When to use: PWM / thermal fans. Cost: wider search → more trials to cover well. Risk: compares apples-to-oranges vs fixed-RPM campaigns.” |
| fan_tab_ui.py:1085 | Fan › Design › Optimize | Expert | VTextField | PWM RPM min | opt_rpm_min | TXT |  | “Lowest RPM Optuna may pick when Search RPM is on (PWM band floor).” |
| fan_tab_ui.py:1098 | Fan › Design › Optimize | Expert | VTextField | PWM RPM max | opt_rpm_max | TXT |  | “Highest RPM Optuna may pick when Search RPM is on (PWM band ceiling).” |
| fan_tab_ui.py:1121 | Fan › Design › Fit & seed | Both | VSwitch | Allow intake overbuild (+Z) | intake_overbuild | — |  |  |
| fan_tab_ui.py:1130 | Fan › Design › Fit & seed | Both | VSlider | Extra intake (mm) | intake_overbuild_mm | — |  |  |
| fan_tab_ui.py:1158 | Fan › Design › Fit & seed | Both | VBtn | Fit envelope |  | — |  |  |
| fan_tab_ui.py:1168 | Fan › Design › Fit & seed | Both | VBtn | Scale to this hub |  | — |  |  |
| fan_tab_ui.py:1183 | Fan › Design › Fit & seed | Both | VTextField | Target CFM | seed_duty_cfm | — |  |  |
| fan_tab_ui.py:1192 | Fan › Design › Fit & seed | Both | VTextField | ΔP (Pa) | seed_duty_pa | — |  |  |
| fan_tab_ui.py:1201 | Fan › Design › Fit & seed | Both | VTextField | RPM | seed_duty_rpm | — |  |  |
| fan_tab_ui.py:1209 | Fan › Design › Fit & seed | Both | VSelect | Vortex | seed_duty_vortex | — |  |  |
| fan_tab_ui.py:1218 | Fan › Design › Fit & seed | Both | VBtn | Apply stagger/camber seed |  | — |  |  |
| fan_tab_ui.py:1239 | Fan › Viewer | Both | VSwitch | Highlight out-of-spec (red) | highlight_spec | — |  |  |
| fan_tab_ui.py:1248 | Fan › Viewer | Both | VSwitch | Case envelope | show_envelope | — |  |  |
| fan_tab_ui.py:1258 | Fan › Viewer | Both | VSwitch | Rotation (CCW) + airflow (−Z) cues | show_dir_cues | — |  |  |
| fan_tab_ui.py:1268 | Fan › Viewer | Both | VBtnToggle |  | glyph_mode | — |  |  |
| fan_tab_ui.py:1275 | Fan › Viewer | Both | VBtn | Arrows on |  | — |  |  |
| fan_tab_ui.py:1276 | Fan › Viewer | Both | VBtn | Arrows off |  | — |  |  |
| fan_tab_ui.py:1278 | Fan › Viewer | Both | VSelect | Arrow density | glyph_density | — |  |  |
| fan_tab_ui.py:1288 | Fan › Viewer | Both | VTextField | Scale | glyph_scale | — |  |  |
| fan_tab_ui.py:1343 | Fan › Export | Both | VBtn | Export STL |  | — |  |  |
| fan_tab_ui.py:1353 | Fan › Export | Both | VSwitch | Fit hub to the motor | export_fit_hub | — |  |  |
| fan_tab_ui.py:1358 | Fan › Export | Both | VSwitch | Fit tip + depth to the frame | export_fit_frame | — |  |  |
| fan_tab_ui.py:1364 | Fan › Export | Both | VSwitch | Also export the mirror-image fan (CW + CCW) | export_also_mirror | — |  |  |
| fan_tab_ui.py:1369 | Fan › Export | Both | VSwitch | Show the motor cup in Preview (slower) | preview_motor_cup | — |  |  |
| fan_tab_ui.py:1439 | Fan › Results › Airflow | Expert | VBtnToggle |  | airflow_field | — |  |  |
| fan_tab_ui.py:1446 | Fan › Results › Airflow | Expert | VBtn | \|U\| midplane |  | — |  |  |
| fan_tab_ui.py:1447 | Fan › Results › Airflow | Expert | VBtn | pressure midplane |  | — |  |  |
| fan_tab_ui.py:1448 | Fan › Results › Airflow | Expert | VBtn | axial Uz |  | — |  |  |
| fan_tab_ui.py:1449 | Fan › Results › Airflow | Expert | VBtn | streamlines |  | — |  |  |
| fan_tab_ui.py:1450 | Fan › Results › Airflow | Expert | VBtn | spanwise |  | — |  |  |
| fan_tab_ui.py:1451 | Fan › Results › Airflow | Expert | VBtn | b2b Cp |  | — |  |  |
| fan_tab_ui.py:1468 | Fan › Results › Airflow | Expert | VBtn | ⏹ Cancel viz |  | — |  |  |
| mixed_tab.py:672 | Mixed tab | Expert | _slider | Blades | mf_n_blades | — |  |  |
| mixed_tab.py:673 | Mixed tab | Expert | _slider | Eye hub R (mm) | mf_r_eye | — |  |  |
| mixed_tab.py:674 | Mixed tab | Expert | _slider | Back hub R (mm) | mf_r_back | — |  |  |
| mixed_tab.py:675 | Mixed tab | Expert | _slider | Tip R (mm) | mf_r_tip | — |  |  |
| mixed_tab.py:676 | Mixed tab | Expert | _slider | Z span (mm) | mf_z_span | — |  |  |
| mixed_tab.py:678 | Mixed tab | Expert | _slider | Chord root (mm) | mf_chord_root | — |  |  |
| mixed_tab.py:679 | Mixed tab | Expert | _slider | Chord mid (mm) | mf_chord | — |  |  |
| mixed_tab.py:680 | Mixed tab | Expert | _slider | Chord tip (mm) | mf_chord_tip | — |  |  |
| mixed_tab.py:681 | Mixed tab | Expert | _slider | Stagger root (°) | mf_stagger_root | — |  |  |
| mixed_tab.py:682 | Mixed tab | Expert | _slider | Stagger mid (°) | mf_stagger | — |  |  |
| mixed_tab.py:683 | Mixed tab | Expert | _slider | Stagger tip (°) | mf_stagger_tip | — |  |  |
| mixed_tab.py:685 | Mixed tab | Expert | _slider | Thickness t/c | mf_thickness | — |  |  |
| mixed_tab.py:686 | Mixed tab | Expert | _slider | Camber | mf_camber | — |  |  |
| mixed_tab.py:687 | Mixed tab | Expert | _slider | Camber pos | mf_camber_pos | — |  |  |
| mixed_tab.py:689 | Mixed tab | Expert | VSelect | Application | mf_assess_preset | — |  |  |
| mixed_tab.py:698 | Mixed tab | Expert | VSwitch | Third CFD at operating point | mf_refine_op | — |  |  |
| mixed_tab.py:772 | Mixed tab | Expert | VTextField | Trials | mf_trials | — |  |  |
| mixed_tab.py:781 | Mixed tab | Expert | VSwitch | Continue last | mf_resume | — |  |  |
| mixed_tab.py:792 | Mixed tab | Expert | VTextField | CFD refine top N | mf_cfd_top | — |  |  |
| mixed_tab.py:801 | Mixed tab | Expert | VBtn | CFD refine |  | — |  |  |
| mixed_tab.py:816 | Mixed tab | Expert | VSelect | Previous runs | mf_sel_trial | — |  |  |
| mixed_tab.py:838 | Mixed tab | Expert | VSelect | Previous runs | mf_sel_trial | — |  |  |
| mixed_tab.py:883 | Mixed tab | Expert | VBtnToggle |  | mf_airflow_field | — |  |  |
| mixed_tab.py:890 | Mixed tab | Expert | VBtn | \|U\| midplane |  | — |  |  |
| mixed_tab.py:891 | Mixed tab | Expert | VBtn | pressure midplane |  | — |  |  |
| mixed_tab.py:892 | Mixed tab | Expert | VBtn | axial Uz |  | — |  |  |
| mixed_tab.py:893 | Mixed tab | Expert | VBtn | streamlines |  | — |  |  |
| prop_tab.py:981 | Prop tab | Both | VSelect | Propeller size | prop_model | — |  |  |
| prop_tab.py:1090 | Prop tab | Both | _slider | Blades | p_n_blades | — |  |  |
| prop_tab.py:1091 | Prop tab | Both | _slider | Pitch (in) | p_pitch | — |  |  |
| prop_tab.py:1092 | Prop tab | Both | _slider | Chord root (×tip R) | p_chord_root | — |  |  |
| prop_tab.py:1093 | Prop tab | Both | _slider | Chord mid (×tip R) | p_chord_mid | — |  |  |
| prop_tab.py:1094 | Prop tab | Both | _slider | Chord tip (×tip R) | p_chord_tip | — |  |  |
| prop_tab.py:1095 | Prop tab | Both | VSelect | Wall mode | p_thick_mode | — |  |  |
| prop_tab.py:1108 | Prop tab | Both | _slider | label | model | — |  |  |
| prop_tab.py:1132 | Prop tab | Both | VTextField | Trials | prop_trials | — |  |  |
| prop_tab.py:1141 | Prop tab | Both | VTextField | Max power W (0=any) | prop_maxpower | — |  |  |
| prop_tab.py:1149 | Prop tab | Both | VSelect | Mission | prop_mission | — |  |  |
| prop_tab.py:1160 | Prop tab | Both | VTextField | Weight (N) | prop_weight_n | — |  |  |
| prop_tab.py:1169 | Prop tab | Both | VTextField | Rotors | prop_n_rotors | — |  |  |
| prop_tab.py:1178 | Prop tab | Both | VTextField | Battery (Wh) | prop_battery_wh | — |  |  |
| prop_tab.py:1188 | Prop tab | Both | VTextField | Cruise (m/s) | prop_cruise_mps | — |  |  |
| prop_tab.py:1197 | Prop tab | Both | VTextField | Min hover (min) | prop_min_minutes | — |  |  |
| prop_tab.py:1204 | Prop tab | Both | VSwitch | Continue last prop study | prop_resume | — |  |  |
| prop_tab.py:1225 | Prop tab | Both | VTextField | CFD top N | prop_cfd_top | — |  |  |
| prop_tab.py:1234 | Prop tab | Both | VTextField | BEMT floor g | prop_bemt_floor | — |  |  |
| prop_tab.py:1243 | Prop tab | Both | VSelect | CFD mesh | prop_cfd_mesh_preset | — |  |  |
| prop_tab.py:1252 | Prop tab | Both | VBtn | CFD refine |  | — |  |  |
| prop_tab.py:1264 | Prop tab | Both | VSelect | BEMT polar backend | prop_polar_backend | — |  |  |
| prop_tab.py:1273 | Prop tab | Both | VTextField | Polar V∞ (m/s, comma) | prop_polar_v | — |  |  |
| prop_tab.py:1285 | Prop tab | Both | VSelect | Previous runs | prop_sel_idx | — |  |  |
| prop_tab.py:1328 | Prop tab | Both | VSelect | Previous runs | prop_sel_idx | — |  |  |
| prop_tab.py:1376 | Prop tab | Both | VBtnToggle |  | prop_airflow_field | — |  |  |
| prop_tab.py:1383 | Prop tab | Both | VBtn | \|U\| midplane |  | — |  |  |
| prop_tab.py:1384 | Prop tab | Both | VBtn | pressure midplane |  | — |  |  |
| prop_tab.py:1385 | Prop tab | Both | VBtn | axial Uz |  | — |  |  |
| prop_tab.py:1386 | Prop tab | Both | VBtn | streamlines |  | — |  |  |
| tab_shell.py:24 | Fan sub-tabs / action row | Both | VTab | Design |  | — |  |  |
| tab_shell.py:25 | Fan sub-tabs / action row | Both | VTab | Results |  | — |  |  |
| tab_shell.py:26 | Fan sub-tabs / action row | Both | VTab | Library |  | — |  |  |
| tab_shell.py:46 | Fan sub-tabs / action row | Both | VBtn | label |  | — |  |  |
| volute_tab.py:594 | Volute tab | Expert | _slider | Blades | volute_n_blades | — |  |  |
| volute_tab.py:595 | Volute tab | Expert | _slider | Hub R (mm) | volute_r_hub | — |  |  |
| volute_tab.py:596 | Volute tab | Expert | _slider | Tip R (mm) | volute_r_tip | — |  |  |
| volute_tab.py:597 | Volute tab | Expert | _slider | Blade height (mm) | volute_blade_h | — |  |  |
| volute_tab.py:598 | Volute tab | Expert | _slider | Blade thick (mm) | volute_blade_thick | — |  |  |
| volute_tab.py:599 | Volute tab | Expert | _slider | Backplate (mm) | volute_backplate | — |  |  |
| volute_tab.py:603 | Volute tab | Expert | _slider | Spiral growth (mm) | volute_spiral | — |  |  |
| volute_tab.py:604 | Volute tab | Expert | _slider | Tip clearance (mm) | volute_clearance | — |  |  |
| volute_tab.py:605 | Volute tab | Expert | _slider | Wall (mm) | volute_wall | — |  |  |
| volute_tab.py:606 | Volute tab | Expert | _slider | Tongue angle (°) | volute_tongue_angle | — |  |  |
| volute_tab.py:607 | Volute tab | Expert | _slider | Tongue clear (mm) | volute_tongue_clear | — |  |  |
| volute_tab.py:608 | Volute tab | Expert | _slider | Tongue fillet (mm) | volute_tongue_fillet | — |  |  |
| volute_tab.py:611 | Volute tab | Expert | _slider | Outlet width (mm) | volute_out_w | — |  |  |
| volute_tab.py:612 | Volute tab | Expert | _slider | Outlet length (mm) | volute_out_l | — |  |  |
| volute_tab.py:613 | Volute tab | Expert | _slider | Outlet height (mm) | volute_out_h | — |  |  |
| volute_tab.py:617 | Volute tab | Expert | VTextField | RPM | volute_rpm | — |  |  |
| volute_tab.py:626 | Volute tab | Expert | VTextField | Load Pa@50CFM | volute_load_pa | — |  |  |
| volute_tab.py:696 | Volute tab | Expert | VTextField | Trials | volute_trials | — |  |  |
| volute_tab.py:705 | Volute tab | Expert | VCheckbox | Resume last Optimize front | volute_resume | — |  |  |
| volute_tab.py:714 | Volute tab | Expert | VSelect | Previous runs | volute_sel_trial | — |  |  |
| volute_tab.py:736 | Volute tab | Expert | VSelect | Previous runs | volute_sel_trial | — |  |  |
| volute_tab.py:788 | Volute tab | Expert | VBtnToggle |  | volute_airflow_field | — |  |  |
| volute_tab.py:795 | Volute tab | Expert | VBtn | \|U\| scroll |  | — |  |  |
| volute_tab.py:796 | Volute tab | Expert | VBtn | pressure scroll |  | — |  |  |
