<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

---
name: fan-sim-cockpit-issues
description: "Open cockpit UX bugs the user reported — fix next session, don't forget"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9facc2be-ff12-44e2-9ede-0cced25b4756
  modified: 2026-08-31T20:48:53.600Z
---

STATUS: all 4 items FIXED 2026-08-27 in fansim/cockpit/app.py (18 tests still pass). Detail +
automation caveat: `E:\Projects\programming_2\Fan-simulator\docs\known-issues.md`.

**FAN-MODEL MANAGER + HUB-FIT HELPER 2026-08-31 (user: manage fan models add/edit/delete; hub slider
should show/match the optimal size for the specific fan; confirm motor-fit is relative). build_server
constructs; backend CRUD unit-verified.
(1) MOTOR-FIT IS ALREADY RELATIVE (confirmed, no change needed): carve_motor_mount / mount_min_hub_radius
= cavity_dia/2 + min_wall, per the SELECTED fan's motor — so ANY hub larger than that motor (+margin)
carves the cup regardless of motor size (5 or 55 mm); smaller-than-motor warns 'won't fit'. Made it
VISIBLE: new _hub_fit_readout() under the Hub-radius slider shows 'Motor hub X mm -> needs radius >= Y
mm. Current Z ✓ fits / ✗ TOO SMALL', live as sliders move (folded into _recompute_stale); + a 'Snap to
fit' VBtn (snap_hub_to_fit sets e_hub_radius = need+0.05). That's the user's 'match optimal hub size for
the fan'.
(2) FAN-MODEL MANAGER (add/edit/delete USER models; BUILT-INS read-only refs). fan_spec.py: _BUILTIN_
MODELS frozenset snapshot (a12x25/delta/generic_120), is_builtin(), save_user_fan_model(key,spec)->writes
config/fan_models/<key>.yaml + registers (refuses built-in names), delete_user_fan_model()(refuses
built-ins). Cockpit 'Manage fan models' nested panel (under Fan model & leeway): Load-selected-into-form,
name + max tip dia / max depth / hub dia min-max / motor cavity dia+depth + min hub H fields, 💾 Save
(dataclasses.replace on the selected base -> inherits voltage/power/material; cavity 0 = generic no
motor), 🗑 Delete (disabled=model_is_builtin). DESIGN ANSWER to user's 'modify only if new?': built-ins
are canonical references (real Noctua/Delta) = read-only so a measured spec can't be corrupted; to vary
one, Save under a NEW name -> a USER YAML you fully edit/delete (their 'delete+recreate', but the ref
stays). Load_fan_models_dir already imports user YAMLs at startup (reload_models refreshes).
(2b) FIT-TO-FRAME 2026-08-31 (user: 'nothing there reduces blade LENGTH to fit the housing; how did we
not add this?'). The 'Tip radius / length' slider always changed length, but only FLAGGED over-frame at
preview/export with no guidance/one-click fix (frame twin of the hub snap). Added _tip_fit_readout()
under the Tip-radius slider ('Frame <= X mm dia -> tip radius <= Y mm. Current Z ✓ fits / ✗ over by N
mm') live via _recompute_stale, + a 'Fit to frame' VBtn (snap_tip_to_frame sets e_tip_radius =
max_tip_dia/2 - 0.05, ONLY shrinks). Per-fan-model (a12x25 110mm, generic_120 119mm). Verified: 118mm
design -> 109.9mm for a12x25, unchanged for generic_120. NOT auto-applied on export (shrinking changes
aero) — deliberate button; export still warns over-frame. Could add auto-fit-on-export like the hub grow.
BUG FIX (user hit it): first version snapped tip_radius = max_dia/2 (NOMINAL), but the BUILT tip dia
BULGES past 2*tip_radius (wrapped/chord-wide tip section extends radially — measured 0.5mm on the user's
9-blade, 4.2mm on a wide-chord test), so it landed 0.5mm OVER. FIX: new module-level _blade_max_dia(params)
= max hypot(x,y) over the section points (FAST, no CAD solid, features off), and snap_tip_to_frame now
ITERATES tip_radius down against that real dia until built <= max_dia-0.15; _tip_fit_readout shows the
BUILT dia (matches preview's spec_status) not nominal. Verified: wrapped design 114.2mm@tr55 -> tr52.6 ->
109.7mm fits. This bulge is also why 'tip radius <= 55' guidance was optimistic — readout now honest.
(2c) FIT-DEPTH 2026-08-31 (user hit 'depth 25.7 > max 25.0' after fixing dia). Depth has NO single knob
(driven by sweep+LE-curve+stagger+thickness+wrap), so snap_depth_to_frame flattens only the AXIAL-RAKE
params (sweep_mid/tip, le_sweep_mid/tip = e_sweep_mid/tip, e_le_mid/tip) — the cheapest depth levers
(shift Z, not core aero) — scaling them toward 0 (steps 1.0..0.0, keep the largest that fits) until built
depth (_blade_z_extent, fast) <= max_depth-0.1. _depth_fit_readout shows built depth vs max, live via
_recompute_stale. UI: readout + 'Fit depth' VBtn in the '3-D shape' panel. If flat rake still overflows,
the rest is structural (stagger/thickness/wrap) — readout says reduce those or add Extra-depth leeway.
Verified: 28.9mm -> rake x0.55 -> 23.4mm fits. So the cockpit now has THREE frame fitters: hub 'Snap to
fit' (motor), tip 'Fit to frame' (dia, iterates real bulged dia), depth 'Fit depth' (rake flatten).
DEPTH FIT UPGRADED (user hit it again — rake flatten left it at 26mm): depth is dominated by
chord×sin(stagger) (~23mm structural for a 40mm chord @ 35°), so flattening sweep/LE ALONE can't fit a
structurally-deep blade (verified: low-sweep design 28.0mm -> rake x0 -> 27.95mm, only 0.1mm helped!).
snap_depth_to_frame now 2-STAGE: (1) flatten rake; (2) if still over, REDUCE STAGGER (all 3, min factor
that fits, 3% steps) — the direct 'flatten the blade' lever — and appends '(also lowered pitch/stagger;
re-Assess)' to the readout. Verified: 28.0mm -> stagger x0.85 (mid 40->34) -> 24.35mm fits. HONEST
BIG-PICTURE: the old designs were optimized WITHOUT the real 25mm-depth / 110mm frame, so they're deep by
construction; force-fitting costs real aero (pitch reduction hurts per design-rules stagger_mid=win). The
clean path is a fresh optimization WITH the real a12x25 envelope (110mm tip, 25mm depth, 37.25mm hub) —
worth suggesting to the user next.
(3) FIXED a latent crash: _model_readout formatted s.ref_cfm/.0f which is None for generic_120 (added
2026-08-31) -> guarded (shows '(no published reference — exploratory)'); also tags [built-in ref] /
[user model]. NOT browser-tested (user low on tokens; build_server + backend CRUD verified, UI mirrors
existing working panels). USER RESTART cockpit.**

**BLADE TIP CURVATURE + SWEEP PROGRESS/CANCEL 2026-08-30 (user: blade tips are blunt straight edges
between LE and TE, want them curved; + add sweep progress + cancel). BOTH BROWSER-VERIFIED (:8099).
(1) TIP ROUND: fansim/geometry/blade.py apply_tip_shape(params, tip_round, start_frac=0.80, n=4) —
tapers the chord over the outer span following a QUARTER-ELLIPSE (scale=(1-tr)+tr*sqrt(1-u^2), floored
0.12 so the tip wire isn't degenerate) so LE+TE converge into a rounded tip. Works because sections are
centred on mid-chord (_section_points_3d a=(x-0.5)*chord) -> shrinking chord pulls BOTH edges in
symmetrically. Inserts outer-span stations; build_blade_solid bumps n_span->max(30) when >3 stations so
the arc is smooth. Wired in search_space.blade_from_flat AFTER winglet (rounded tip keeps winglet curl).
Cockpit: e_tip_round(0-1)/e_tip_start(0.5-0.92) sliders in the renamed 'Tip — round & winglet' panel,
edit_flat tip_round/tip_round_start, _init_editor defaults, EDITOR_VARS, CONTROL_DESC, randomize_geometry
(50% chance). tests/test_hub.py +2 (tapers chord <0.5x + watertight; zero=noop). VERIFIED: tip_round 0.65
-> orange preview shows clearly rounded/tapered tips. CAVEAT surfaced to user: rounding thins the tip
(chord shrinks, thickness is a % of chord) -> can drop below min printable wall; raise Thickness tip or
lower Tip round. (2) PREVIEW-ON-NONPRINTABLE FIX (needed for #1): do_preview USED TO early-return on
'not printable' -> a thin rounded tip rendered NOTHING. Now it RENDERS the geometry + appends a warning
('⚠ Not printable as-is: thinnest 0.66<0.80mm. Preview shown anyway — thicken tip / lower Tip round;
gated at Assess/Export'). A preview is for LOOKING; Assess/Export still gate. (3) SWEEP PROGRESS+CANCEL:
state.sweep_active/sweep_cancel/sweep_progress; on_sweep sets them + checks sweep_cancel each iter (for/
else so a normal finish still prints 'done'); cancel_sweep() sets sweep_cancel + '⏹ Cancelling — stops
after current design'. UI: VProgressLinear(sweep_progress) + red '⏹ Cancel' VBtn, v_if=sweep_active,
under the Run row. VERIFIED: Run -> green progress bar + Cancel appear + 'Sweep stagger mid 1/3=15:
running CFD… (~4min/step)'; Cancel -> 'Cancelling — stopping after the current design finishes…' + btn
disabled. NOTE: cancel is COOPERATIVE — the in-flight CFD subprocess isn't interrupted (stops within one
~4-min step); a hard kill would need Popen+kill of the eval worker. build_server constructs clean.**

**PRINTABILITY GATE MADE RADIUS-AWARE 2026-08-30 (user: rounded tip flags 'thinnest 0.40mm < 0.80mm',
'everything mid-range', questioned if the error is CORRECT). DIAGNOSIS: honest — the old check
min_section_thickness_mm = min(thickness*chord over ALL stations) = airfoil MAX thickness at the
thinnest station (NOT the razor TE), and tip rounding shrinks the tip chord -> genuinely 0.40mm. BUT
the check applied a 2-perimeter (0.8mm) wall EVERYWHERE incl. the deliberately-tapered TIP EDGE, which
is wrong: real fan/prop blades have thin tips; a tip prints fine as a SINGLE wall down to one nozzle
width, and only BELOW one extrusion width (~0.40mm at a 0.4mm nozzle) is it truly unprintable (no
plastic path). FIX fansim/manufacturability/fdm_rules.py: RADIUS-AWARE — blade BODY (r_frac<=0.85)
needs 2 perimeters (0.8mm); TIP EDGE (r_frac>0.85) needs only 1 (0.40mm). min_section_thickness_mm
gained body_only= kwarg. Reports which bound failed ('blade body thinnest X < 0.80' vs 'tip edge X <
one extrusion width 0.40'). printability_score.grade_printability aligned: FDM-capability/needs_resin
judged on BODY thickness; a thin-but-printable tip only nudges difficulty (wall_sev>=0.25), not resin.
RESULT: tip_round 0.6 mid design -> now PRINTABLE on FDM (was gated+resin); only extreme rounding
(<0.40mm tip) gates. tests/test_optimize.py +1 (thin tip OK, tip<1-wall gated); 3 printability tests
pass; existing thin-BODY reject still works. This also makes the OPTIMIZER accept realistic thin-tipped
blades the old 0.8mm-everywhere rule wrongly rejected (search_space 'chord>=14 for tip>0.8mm' now stale
but harmless). USER RESTART to get it.**

**--RELOAD ORPHANED CFD -> WHOLE MACHINE JAMMED (root-caused + FIXED 2026-08-30). User: export does
nothing, preview/assess won't run, CFD starts 3 min late, staleness stuck. DIAGNOSIS (process scan):
NOT an app bug — the user ran the cockpit with --reload, and I EDITED fansim/ files repeatedly this
session; EACH edit made the --reload supervisor kill+relaunch the child cockpit, and the OLD _stop()
only proc.terminate()'d the CHILD — orphaning its in-flight eval-worker subprocess AND its OpenFOAM
DOCKER CONTAINER (daemon-owned, survives the killed worker). Found 4 orphaned eval-workers + 2 live
containers + nested duplicate cockpit instances saturating the CPU. Exports WERE completing (~75s
each under load) — user just didn't see them. LESSON (CRITICAL): NEVER edit fansim/ or validation/
while the user runs a --reload cockpit — every save restarts their server + (pre-fix) orphaned CFD.
FIX (3 parts): (1) scripts/cockpit.py supervisor: _spawn sets env FANSIM_CFD_SESSION='cockpit-<pid>';
_stop now taskkill /PID <child> /T /F (kills the WHOLE tree: workers+docker CLI children) THEN
_reap_containers() = docker kill by 'label=fansim_cfd_session=<session>'; also reap on crash-relaunch.
(2) fansim/cfd/runner.py: docker run now adds _label_args() = --label fansim_cfd=1 [+ fansim_cfd_
session=<env> when set]; env inherited by every subprocess so a container started deep in an eval
worker still carries the label. Scoped by session id so a restart reaps ONLY its own child's
containers, never a concurrent optimization's. (3) EXPORT MADE ASYNC (app.py export_stl_current):
the fused watertight build is ~1-3min for featured designs and was SYNCHRONOUS = froze the whole UI
('nothing happens'); now runs in run_in_executor with state.export_busy, '⏳ Building print-ready STL…'
msg + button loading/disabled, non-blocking. VERIFIED LIVE (:8097 --reload): touch a src file ->
'[reload] change ... restarting' -> procs 4 BEFORE == 4 AFTER (no accumulation), 0 orphaned workers;
docker reap round-trip (start labeled container -> ps --filter -> kill -> gone, others untouched);
async export -> '⏳ Building…' immediately then '✓ Saved (watertight · ✓ motor cup carved)', UI
responsive. build_server constructs clean. CLEANUP CMD for a future pile-up: docker ps -q | kill +
kill python procs matching 'cockpit|_eval_worker|_build_worker'. FURTHER (not done): a running SWEEP
still gates preview/assess (assess_busy) with weak feedback + no cancel button — the next UX hardening
if it bites; also export is in-process (build_impeller) not subprocess-isolated like preview/assess.**

**SWEEP OPTIONS EXPANDED 2026-08-30 (user: 'should we add other modules to assess & sweep?'). SWEEP_
OPTIONS in app.py grown 7->17, grouped like the editor, adding the design-rules HIGH-VALUE CFD levers:
chord mid, chord tip, stagger root, stagger MID (the win-win-win lever, now the default), camber
position, sweep mid, wrap tip (lean_tip), winglet sweep, tip radius, hub radius. Each is a ('label',
'flat', field, mn, mx) tuple; on_sweep already handles 'flat' fields (verified all 14 build via blade_
from_flat). DELIBERATELY OMITTED (told user why): LE-curve/skew/thickness/camber-pos minor... wait
camber-pos IS added; omitted = LE-curve, skew, thickness, hub-height/nose (minor aero/structural), and
UNEVEN SPACING (spacing_spread) — it's a TONAL-NOISE lever the flow/eff RANS sweep CAN'T see; the
Preview tonal readout shows it live/free instead. Cost note surfaced: each sweep step = ~4-min CFD, so
only flow/eff-moving params included. ALSO FIXED a latent bug: state.sweep_param defaulted to
'max_camber' (a FIELD name) but the VSelect/on_sweep compare against LABELS (o[0]='camber') -> dropdown
showed raw 'max_camber' + fell back to option[0]; now defaults to 'stagger mid' (a valid label).
BROWSER-VERIFIED (:8096): dropdown shows the grouped list, default reads 'stagger mid'. Low-risk
(data + default); no CFD sweep re-run (on_sweep path already tested; _assess unchanged).**

**PREVIEW GEOMETRY TIMED OUT -> FAST NON-FUSED PREVIEW 2026-08-30 (user: 'the geometry build keeps
timing out. I want it to finish not timeout, and waste time'). PROFILED the build (heavy 11-blade
featured, n_span=72): loft ONE blade 2.6s, .clean() 4.9s, export 3-15s -- but the BOOLEAN FUSE
hub.fuse(*blades) = 139s ALONE = the whole problem, blew the 120s preview timeout for nothing. FIX:
a preview only needs to LOOK right, not be watertight, so skip the fuse. New geometry/blade.py
build_impeller_preview(params)-> (trimesh.Trimesh, volume_mm3): tessellate ONE lofted blade + the hub
(cq.Solid.tessellate) then ROTATE-COPY the blade mesh N times + concatenate (trimesh) -- NO boolean
union. ~160s -> ~10s (16x). Volume returned = accurate SUM of the solids' own .Volume() (the meshes
overlap at the roots so the concatenated mesh's own volume is wrong for the weight check). Wired:
_build_worker.py preview mode (writes STL + <stl>.meta.json volume sidecar); isolated.py
build_stl_isolated(..., preview: bool=False, timeout default 120->300); cockpit _build_preview_stl
passes preview=True; spec_status reads the .meta.json volume (falls back to mesh volume). REAL fused
build_impeller UNCHANGED (Export/CFD still get the watertight solid). VERIFIED LIVE (:8095): randomized
features -> Preview FINISHED (~10-16s, no timeout) -> orange featured impeller rendered (visible
tubercles+dimples) + spec check '✓ fits Noctua NF-A12x25 (dia 119, depth 22, 62 g)' (weight from
sidecar) + printability grade. 2 new tests (preview fast+sidecar; preview bounds match fused within
1.5mm); 11 geometry/isolated tests pass. NOTE: EXPORT (export_stl_current/build_impeller) still does the
real fuse -> a featured export can be slow (~150s) but it's a deliberate save, not the live-preview
timeout the user hit; make it async later if it bites.**

**EXPORT STL — 2 BUGS FIXED + BROWSER-VERIFIED 2026-08-30 (user: 'nothing happens'/overwrites
fan_current.stl every time + 'the STL doesn't have the spacing area where it fits over the noctua
hub'). export_stl_current() in fansim/cockpit/app.py rewritten. BUG 1 (naming): always wrote
design_<trial>.stl or fan_current.stl -> OVERWROTE every export. FIX: TIMESTAMPED name
design_<trial>_<YYYYmmdd-HHMMSS>.stl (fan_<stamp> if none selected); also writes a companion .md
print sheet. BUG 2 (no cavity): the motor cup only carves when hub_radius >= cavity/2+min_wall =
mount_min_hub_radius(a12x25)=52/2+1.2=27.2 mm; aero-optimized hubs are ~21.5 mm so carve_motor_mount
returned fits=False and left the hub SOLID (no cup) -> exported fan couldn't slip over the 50 mm
Noctua motor. FIX: on export, if hub < 27.2 mm, WIDEN state.e_hub_radius to need+0.05, rebuild, then
carve; UPDATE the Hub-radius slider so it's visible+reversible; message says 'Hub widened 21.5->27.2
mm to fit the 52 mm motor — press Preview; CFM/eff now approximate, re-Assess for exact'. VERIFIED
LIVE (:8093, opt_guided): click Export -> exports/fan_<stamp>.stl watertight, print sheet reads
'✓ Motor cup carved: cup cavity 52 mm x 12 mm deep + 20 mm center bore', hub 27.2 mm, and the UI shows
the full saved-path + widen message (no more 'nothing happens'). NOTE: the cup is INTERNAL (carved into
the rear -Z face) so it's hidden in the 3-D preview — verify it in a slicer's underside view or the .md.
The widened hub (27.2 mm radius = 54.4 mm dia) is within a12x25 hub_dia_mm=(30,60). Prop-tab export
(build_prop) unaffected (has its own shaft bore, no motor cup). 23 prop+acoustics tests still pass.
TOGGLE ADDED 2026-08-30 (user asked): state.export_fit_hub (default ON) + a VSwitch under the Export
row 'Fit hub to motor on export (widen a too-small hub so the cup carves)'. export_stl_current gates
the auto-widen on it; OFF keeps the aero hub (cup won't carve on a small hub, message appends 'turn on
Fit hub to motor on export to widen it and carve the cup'). BOTH paths browser-verified (:8094): ON ->
hub 21.5->27.2 + cup carved; OFF -> hub 21.5, 'NOT MOUNTABLE as-is', hint shown.**

**CRASH-ON-FEATURE-PREVIEW FIXED (2026-08-27). User: 'site crashed when adding things' -> confirmed
'Preview after a feature'. Root cause: the OCP featured-geometry build (heavy high-res lofts;
serration_max didn't finish in 115s under CPU load) crashed NATIVELY (OCP/VTK teardown segfault,
exit 139 -- reproduced: any process importing OCP + exiting normally segfaults; that's why scripts
use os._exit(0)) OR hung, bypassing do_preview's try/except and killing the whole trame server. FIX:
run the preview build in an ISOLATED SUBPROCESS with a timeout. New fansim/geometry/_build_worker.py
(python -m worker <job.json>: blade_from_flat+build_impeller+export_stl, os._exit(0)) +
fansim/geometry/isolated.py build_stl_isolated(flat,features,out,timeout=120) -> raises
TimeoutError/RuntimeError instead of crashing. cockpit _build_preview_stl now calls it; do_preview
catches Timeout/Exception -> shows msg, app SURVIVES. 3 tests (test_isolated_build.py). ALSO: featured
previews are SLOW esp. while an optimization saturates CPU -> may hit 120s timeout (now a graceful
msg, not a crash). USER MUST RESTART their cockpit (same cmd) to get the fix.**

**FEATURES DON'T LOAD ON SELECT — FIXED (2026-08-27). User: clicking a result with bio features
didn't populate the feature sliders (couldn't see what settings gave a result). TWO bugs in
fansim/cockpit/app.py: (1) _init_editor(p) read feature sliders from the `feat` arg (default
Features()=0), IGNORING the design's params -> now reads from p (p.get('tubercle_amp',...) etc.), so
feature-enabled optimizer runs + assessed designs show their settings. (2) on_assess stored
params=dict(flat)=GEOMETRY ONLY, dropping features -> now {**edit_flat(), **_feat_dict()} so assessed
featured designs round-trip. Verified logic (featured p -> loads; smooth -> zeros). NOTE: opt_v3 (the
run I loaded) was optimized WITHOUT --features, so ITS results have NO features (clicking them
correctly shows 0) -- the fix matters for feature-enabled runs + assessed designs. USER RESTART
cockpit to get it.**
Fixes: (1) editor slider ranges updated to new geometry + preview renders wrapped model;
(2) edit_features() auto-fills count when amp>0 so features activate; (3) added Wrap mid/tip
(lean) sliders + threaded lean through edit_flat/blade_from_flat; (4) do_preview() now ASYNC
with "Generating…" indicator + button loading. Caveat: Vuetify sliders don't sync v_model from
SYNTHETIC drags (browser automation) — work for a real mouse; verified logic in Python + wrap
sliders/preview render in-browser.

Original report (2026-08-26):

1. **Cockpit "Preview geometry" barely changes the model.** Check VSlider v_model two-way
   binding + `do_preview()` re-reads state + `ctrl.view_update()` fires (fansim/cockpit/app.py).
2. **Bio-inspired feature sliders don't show in preview.** Root cause likely: `Features.active`
   needs BOTH amplitude AND count(waves/rows/cols) > 0 — moving only the amp slider does nothing.
   Fix: auto-set a count when amp>0, or clearer UI. Also verify sliders update state.
3. **Cockpit editor is MISSING `lean_deg` (wrap) sliders entirely** — the editor predates the
   geometry rewrite; `edit_flat()`/`build_edit_params()` don't set lean, so previews use lean=0
   and don't match the optimizer's wrapped geometry. Add lean_mid/lean_tip sliders + thread them.

4. **No "processing" indicator while geometry builds** (Preview freezes ~7-35s, user can't tell
   it's working). FIX: make `do_preview()` ASYNC like on_assess (set preview_busy+msg+flush BEFORE
   the build, run build in executor, then update); bind Preview button `loading=("preview_busy",)`.
   Synchronous flush won't show during a blocking build.

Also clarified for user: pytest (~15s) = software correctness checks (NOT fan sims); the SLOW
processes (hours) = OpenFOAM CFD, ~5-6 min PER design (mesh + 2 solves), x24 designs = 2-3h.
GPU (4070 Ti) idle by design — current OpenFOAM RANS is CPU-appropriate; GPU's job is FluidX3D
LBM for the NOISE tier + fast screening (unbuilt).

**ASSESSED DESIGNS VANISHED ON RESTART — FIXED + persistence added (2026-08-28). User: designs they
created+Assessed in the UI are gone from graph/dropdown. ROOT CAUSE: user_designs was IN-MEMORY ONLY
(app.py user_designs=[]) + stored PER-RUN (run_dir/cockpit_assess/design_9xxx); repeated cockpit
restarts (for the other fixes) + loading a different run (opt_v3) cleared/hid them. On disk the STL +
OpenFOAM case survive BUT NO design.json/params were ever written -> OLD assessed designs
(runs/opt_run1 + opt_v2 /cockpit_assess/design_900x) are UNRECOVERABLE (design vector lost; verified
_load_assessed_designs returns 0 for them). FIX: _assess now writes design.json (trial/params/
objectives/extra) per assessed design; _load_assessed_designs() reloads them on cockpit startup into
user_designs+by_trial (next_id continues past reloaded). FUTURE assessed designs SURVIVE restarts
(per-run: shown when you load the run you assessed under). Verified new design reloads. RESTART cockpit.**

**LEEWAY UI POLISH + REJECT HINTS (2026-08-28). (1) 'Fan model & leeway' is now a collapsible
VExpansionPanel; Leeway is a NESTED collapsible sub-panel (sliders hidden by default). (2) _reject_hint
(reason) gives actionable guidance on assess rejection + shows in assess_msg (Div white-space:pre-line):
power rejection -> '~N% over: shaft power grows with blade LOADING (blade count x chord, camber,
stagger, tip); try 1 fewer blade / ~10% less chord / less camber, or add over-voltage leeway';
depth/tip/hub/weight -> their drivers + leeway. User Q: why do some assess as 0.77 vs 0.69W over the
0.67W budget? ANSWER: shaft power = torque x omega; at fixed 2000 RPM torque = blade loading, which
grows with solidity(blade count x chord)+camber+stagger+tip radius. A12x25 motor is very low power
(0.67W shaft) so high-flow designs exceed it easily; 0.69W is only 3% over (tiny tweak or over-voltage
leeway passes). Power gate is POST-CFD (needs torque) so it rejects after the ~4min run. USER RESTART.**

**SPEC CHECK AT PREVIEW (2026-08-28). User: why generate an out-of-spec design then only find out at
Assess? FIX: spec_status(stl,params) reads the BUILT preview STL bounds + volume (trimesh) and runs
check_build (envelope/hub/depth/weight) vs active_spec() with NO CFD; do_preview shows it in
preview_msg (white-space:pre-line): '✓ fits Noctua NF-A12x25 (dia 116, depth 23, 39g)' /
'⚠ OVER-SPEC (allowed via leeway): ...' / '⚠ Out of spec — Assess will reject: depth 25.0 > max 25.0.
[hint]'. So the user sees the verdict at GENERATION, before spending an Assess. (Note: even Assess
rejected these fast ~10-15s at the geometry-build gate, BEFORE the ~4min CFD -- but now no Assess
needed. Only POWER needs CFD and it DERATES not rejects.) Verified logic on real STLs. RESTART cockpit.**

**PER-SLIDER TOOLTIPS + MIN/MAX IMAGES (2026-08-28, user: docs should be HOVER TOOLTIPS per control
WITH images showing the min/max extremes). scripts/generate_control_images.py renders each control at
min vs max side-by-side as SHADED SOLIDS (pyvista off_screen; FULL impeller for spatial controls
blades/wrap/sweep/hub/chord/spacing, ZOOMED single blade via build_blade_solid for subtle airfoil
ones camber/thickness/camber_pos/LE-curve/features) -> docs/control_images/e_*.png (23 imgs).
IMPORTANT: first tried matplotlib WIREFRAME line-plots -> user said 'not clear what I'm looking at' ->
switched to shaded pyvista renders (recognizable fan). Cockpit: _slider now wraps VSlider in a
VTooltip (v3.Template v_slot_activator='{ props }' + VSlider v_bind='props') showing base64 img
(_load_control_images -> _IMG_URI) + CONTROL_DESC[model] text. REMOVED the old 'What these controls
do' expansion panel (tooltips replace it). Verified parse + v3.Template/VTooltip exist + 23 imgs load.
RISK: tooltip-wrapped slider drag behavior unverified in-browser (cockpit fragile to launch here);
if the slider feels off, fall back to an info-icon activator. Regenerate imgs w/ the script if geometry
changes. USER RESTART cockpit to verify.**

**DEPTH-DRIVER ATTRIBUTION (2026-08-28, user: out-of-spec depth warning doesn't say WHICH slider is
the culprit). FIX: _depth_drivers(flat) computes, per depth-driving slider, how many mm reducing it
would cut the blade Z-extent -- ranked, biggest first. FAST: uses _blade_z_extent() from the section
points (_section_points_3d, NO CAD-kernel solid), features OFF (barely affect depth). spec_status(...,
flat) appends 'Top depth drivers here: Sweep tip (~3 mm), Root chord (~2 mm), Tip chord (~2 mm)' when
depth is over (fail OR over-spec via leeway). Verified on the user's design (stagger 44/39/31, sweep
2.7/8.9, depth 27.7): top = Sweep tip ~2.8mm > Root chord ~1.9 > Tip chord ~1.5 -> reducing Sweep tip
(~3mm) fixes the 2.7mm overage. Generalizes to tip-dia/weight later. USER RESTART cockpit.**

**ASSESS/CFD CRASHED THE COCKPIT — ISOLATED (2026-08-28). User: cockpit crashed during Assess/run
CFD. ROOT CAUSE (same crash class as the earlier preview crash): on_assess ran evaluate_candidate
(OCP impeller build + OpenFOAM) directly in a run_in_executor WORKER THREAD of the live-VTK trame
process. Preview was already isolated into a subprocess (build_stl_isolated) precisely because an
in-process/off-main-thread OCP build can segfault natively (exit 139) and bypass try/except -> dead
server; Assess never got that treatment. Reproduced that CFD itself is FINE (Docker up, evaluate_
candidate feasible in a CLEAN process) — the clean-process repro can't trigger the thread+live-VTK
segfault, which is why it 'worked' in isolation. FIX: new fansim/optimize/_eval_worker.py (python -m,
runs evaluate_candidate from a JSON job -> writes ObjectiveResult asdict -> os._exit(0)) +
fansim/optimize/isolated_eval.py evaluate_candidate_isolated(flat, features, workdir, spec, procs,
base_cell, iters, timeout=1200) mirroring build_stl_isolated (subprocess.run, TimeoutError/RuntimeError
on timeout/non-zero-exit). Cockpit _blocking_eval now calls it (passes flat + params.features; blade_
from_flat ignores feature keys in the merged flat). ALSO hardened both async task()s (on_assess,
on_sweep) with try/except/finally: any eval error now shows in assess_msg ('Assess failed: ...') and
assess_busy ALWAYS resets (previously an exception left the UI stuck on 'Running CFD…' forever, read
as a crash); sweep continues past a single failing design. Verified: isolated round-trip returns a
real ObjectiveResult (57.5 CFM feasible), cockpit imports clean, 14 isolated/cockpit/objectives/spec
tests pass. NOTE: asked user for cockpit.log to CONFIRM native-crash vs python-exception, but the fix
covers BOTH. USER MUST RESTART cockpit. Isolation adds ~subprocess startup overhead per Assess (fine
vs a ~4min CFD).**

**ASSESSED DESIGNS PER-RUN -> CROSS-RUN + STALENESS WARN (2026-08-28). User: '9005 and other runs
not showing up' after relaunch. ROOT CAUSE: assessed designs load ONLY from the OPEN --run's
cockpit_assess (build_server: assess_dir = run_dir/'cockpit_assess'); user assessed 9005 under
opt_v2/opt_run1 but relaunched pointing elsewhere (default --run=runs/opt_run1) -> their designs
hidden (files SAFE on disk). FIX: _load_assessed_designs now takes an ITERABLE of assess dirs;
build_server globs runs/*/cockpit_assess (runs_root=run_dir.parent) and loads ALL of them so a user
design shows regardless of which run is open. Trial-id collisions across runs (9005 exists in BOTH
opt_v2 & opt_run1) re-keyed to a fresh >=9000 id (orig kept in extra['orig_trial']); each design
tags extra['source_run'] and the dropdown label shows it ('#9011  ◆ opt_v2'). New assessments still
write to the open run's dir + stamp source_run=run_dir.name. Verified: 17 user designs load from a
single --run opt_run1 launch, unique ids 9000-9016.
SECOND ASK — features round-trip: CONFIRMED ALREADY CORRECT. on_assess stores {**edit_flat(),
**_feat_dict()} (7 feature keys) + build_edit_params()=blade_from_flat(edit_flat(),edit_features())
bakes features into the assessed geometry; _init_editor reads feature keys back on select. The 9005s
were just SMOOTH (no features). Preview does NOT persist — only Assess creates a saved design, so
feature edits that were only Previewed are lost on selecting another design.
STALENESS (user chose 'Warn + require Assess', NOT auto-CFD): added state.edited_stale/stale_msg +
EDITOR_VARS (all 28 e_ sliders) + sel_sig baseline. _editor_sig() (rounded geom+feat), _set_baseline()
(called in select() after _init_editor, and after a successful Assess), _recompute_stale() registered
via state.change(*EDITOR_VARS). VAlert(warning, v_if=edited_stale) above the Assess button warns
'⚠ Edited since assessment — shown CFM/eff are for the un-edited design. Press Assess…'. USER RESTART.**

**PLOT CLICK SYNCS THE DROPDOWN — FIXED + BROWSER-VERIFIED 2026-08-28. Two parts: (1) SYNC: on_plotly_
click set state.selected_trial without state.flush() -> value not pushed to the VSelect. Added
state.flush(). VERIFIED in a real browser (test cockpit on :8081): emitting plotly_click -> dropdown
displayed '#15'/'#8', model+info loaded. (2) THE REAL USER ISSUE = MARKERS TOO SMALL TO CLICK: plotly
only fires plotly_click on a PRECISE marker hit; size 14/22 markers are fiddly (I missed them repeatedly
with a mouse too). FIX: scatter_figure marker size 14->20 (plain) / 22->30 (pareto) = bigger click
targets. So the sync was fine once flushed; the user's clicks were just missing the dots. DEBUG METHOD
worth remembering: drove the cockpit via Browser MCP on a SEPARATE port (8081, own instance, didn't touch
user's), grep'd '[cockpit] select(' in the log to confirm firing, read the VSelect .v-field__input text
for the dropdown value.**

**^ REOPENED then TRUE ROOT CAUSE FOUND + VERIFIED 2026-08-28: the flush + bigger markers were NOT the
fix — user still couldn't select by clicking. REAL BUG: the plotly click binding was
`click=(on_plotly_click, "[$event]")` sending the ENTIRE plotly event to the server. A real plotly_click
event's points[0] carries NON-SERIALIZABLE fields (data, fullData, xaxis/yaxis objects w/ functions,
DOM bbox) -> trame fails to marshal it -> the message is SILENTLY DROPPED, server never gets the click
(select never fires). That's the 'Unrecognized object: [object Function]' console error. My earlier
gd.emit('plotly_click',{points:[{customdata:N}]}) 'worked' ONLY because it passed a tiny CLEAN object —
a false positive that misled me. FIX: send ONLY the trial id, not the event:
`click=(on_plotly_click, "[$event?.points?.[0]?.customdata]")` + on_plotly_click(trial) sets
state.selected_trial+flush. VERIFIED END-TO-END: dispatched a REAL click through plotly's drag layer
(.nsewdrag) at a marker's l2p pixel (native DOM click on the point PATH does NOT work — plotly hit-tests
on the drag layer) -> server logged select(13) -> VSelect showed '#13'. LESSON: never trust gd.emit as a
proxy for a real plotly click through trame; the serialization of $event is the whole problem. The flush
+ bigger markers stay (both are real improvements) but the customdata-only binding is THE fix. USER RESTART.**

**RANDOMIZE GEOMETRY + FEATURES BUTTONS — DONE + BROWSER-VERIFIED 2026-08-28 (user wanted a geometry
randomizer too, not just features). randomize_geometry() rolls all geometry sliders (blades 5-11,
stagger/chord/sweep/wrap/LE/hub_radius/tip_radius/thickness within OPEN-ish ranges + hub_profile
cylinder/cone/dome + nose) leaving features alone; randomize_features() (earlier) rolls the bio-feature
layer leaving geometry alone. '🎲 Randomize geometry' VBtn atop the Geometry panel, '🎲 Randomize
features' atop Features. Both flush + set a preview_msg; may land out-of-spec (Preview shows it).
VERIFIED in-browser: clicking Randomize geometry moved all sliders to random positions. USER RESTART.**

**RANDOMIZE FEATURES BUTTON — DONE 2026-08-28 (user: a randomize-features button for 'crazy stuff' to
optimize off). randomize_features() in cockpit app.py rolls a random bio-feature combo (each of tub/ser/
dim ~60% on, >=1 always on) on the CURRENT geometry (geometry untouched -> stays buildable): tub_amp
0.02-0.10/waves 3-8, ser_amp 0.015-0.06/teeth 4-12, dim_amp 0.10-0.35/rows&cols 2-6. Sets the e_* feature
sliders + flush + a '🎲 Randomized (…)' preview_msg. '🎲 Randomize features' VBtn at top of the Features
panel. Editor-change watcher recomputes staleness. Builds clean. USER RESTART cockpit.**

**COCKPIT --reload DEV MODE — DONE + VERIFIED 2026-08-28 (user: 'why the strange server-restart
constraint, build it into the tool'). The cockpit is a trame server that builds its UI from Python at
startup, so code edits need a process reload (not artificial — Python holds code in memory). FIX:
scripts/cockpit.py --reload runs the server as a CHILD subprocess under a pure-Python supervisor (no
new dep) that polls mtimes of fansim/ + validation/ *.py every 1s and terminates+relaunches the child
on any change (also relaunches if it dies); browser auto-reconnects. Verified: touched a source file ->
'[reload] change (...) — restarting server' -> fresh server up. Without --reload = single run
(production). SO: future cockpit code changes no longer need a manual USER RESTART if they launch with
--reload. NOTE for cleanup: killing just the child leaves the SUPERVISOR, which relaunches it — kill BOTH
(all 'cockpit.py*<port>' python procs).**

**FULL COCKPIT END-TO-END VERIFICATION — DONE 2026-08-29 (user: 'make everything work reliably').
Drove the whole cockpit in a real browser (8090, opt_run1). ALL WORKING, ZERO server tracebacks across
every interaction: page renders + all panels present; PLOT CLICK -> select + dropdown sync ('#2 ★', the
previously-broken bug CONFIRMED FIXED — the old 'Unrecognized object:[object Function]' console errors
are GONE); design select loads info; Geometry panel has every control (blades/stagger/chord/sweep/wrap/
LE-curve/hub-radius/tip-radius/hub-height/hub-profile/hub-nose/thickness/camber-pos/spacing, 29 sliders);
RANDOMIZE GEOMETRY works (msg + staleness warning fire); RANDOMIZE FEATURES works ('Randomized features
(tub)'); STALENESS warning works; PREVIEW GEOMETRY verified 4 things at once — isolated subprocess build
+ render + spec-check ('depth 26.9 > 25') + depth-driver attribution (correctly named the new HUB NOSE
driver) + printability grade ('Difficulty 46/100'); constraint-viz toggles (highlight/envelope) fire
clean. Console clean except one benign 405. NON-BUGS found: (1) 3D pane shows BLACK in the AUTOMATED
browser only — known pyvista/trame headless quirk; server-side render SUCCEEDS (preview_msg is set AFTER
_draw, no errors; the 3D rendered fine earlier this session on 8081); works for real users. (2) Slow
startup ~30s for opt_run1 (globs all cockpit_assess) — my earlier 'refused' panics were just premature
waits, NOT a bug; also 808x ports get poisoned by TIME_WAIT from rapid kill/relaunch -> use a fresh port.
Record-measurement + --reload were verified in earlier sessions. VERDICT: the app works reliably; no code
bugs found. Assess/Sweep full CFD not re-run (heavy; isolated-eval path tested earlier).**

**EXPORT STL BUTTON + WHAT-HELPS TOOL (2026-08-29, user asks). (1) Cockpit '💾 Export STL' btn next to
Preview/Reset -> export_stl_current() saves the CURRENT editor design as a print-ready STL (motor-mount
cup carved via active_spec().motor_mount) to exports/design_<trial>.stl + state.export_msg shows path +
watertight/mountable. NOTE: saves to a local folder (cockpit is local; file IS on the user's disk),
NOT a browser-download-to-Downloads (trame download is fiddly). Verified: 1.3MB watertight mountable STL.
(2) scripts/what_helps.py: Spearman corr of every geometry param vs airflow/eff/noise across ALL
catalogued designs (compute-free, answers 'what helps most' from existing data). Findings: max_camber
HURTS airflow (-0.59), stagger_root/tip_radius HELP; lean_tip(wrap) best for eff (+0.52); tip_radius
biggest NOISE driver (+0.85). The optimizer IS the auto-batch-runner; this makes its signal legible.
(3) DECLUTTER (user: 'delete some when a ton cluster on the graph', chose BOTH). VIEW FILTER: cockpit
'Declutter (hide near-duplicate designs)' VSwitch above the plot -> _thin() keeps one design per ~2.5-CFM
(free,load) bucket (pareto>eff), NON-destructive (plot only, dropdown/disk untouched), @state.change
re-renders. DEDUP TOOL: scripts/dedup_designs.py clusters catalog designs, keeps best per cluster, hides
the rest. SAFE: dry-run default; --apply writes a REVERSIBLE exclusion list catalog/removed.json (build_
catalog skips those ids); --restore un-hides; --delete-files optionally rm their (case-pruned, small)
dirs. VERIFIED round-trip: apply hid 39/73 -> 34 catalog, 610 STLs UNTOUCHED on disk, restore -> 73 back.
catalog.py gained load_removed/save_removed + REMOVED_LIST; build_catalog references it at call time
(testable). test_catalog exclusion test. All 3 user asks done + tested.**

See [[fan-sim-status]] and [[fan-sim-adversarial-review]].
