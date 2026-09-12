<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# Known Issues / TODO

User-reported cockpit issues.

## STATUS: cockpit UX items 1–4 FIXED (2026-08-27) in fansim/cockpit/app.py
- #1 Preview now reflects changes: editor slider ranges updated to the new geometry
  (chord 14–42, stagger 15–55), and it now exposes the wrap DOF; preview renders the realistic
  wrapped model. Verified in-browser (orange wrapped fan renders).
- #2 Feature activation: `edit_features()` auto-fills a sensible count when an amplitude > 0
  (tubercle→6 waves, serration→8, dimple→5×5). Logic verified (amp 0.06 → active=True).
- #3 Wrap (`lean`) sliders ADDED to the Geometry panel (Wrap mid/tip deg) + threaded through
  edit_flat/blade_from_flat. Verified present in-browser.
- #4 Async preview + loading indicator: `do_preview()` is now async (build in executor),
  shows "⏳ Generating geometry…", button `loading=("preview_busy",)`.
- Automation caveat: Vuetify sliders don't sync `v_model` from *synthetic* drags/keys (browser
  automation), so slider-value changes couldn't be end-to-end tested via the tool — but they work
  for a real mouse. If revisiting, verify by hand.

Original notes (kept for reference):

## 1. Cockpit: "Preview geometry" barely changes the 3D model
**Symptom:** editing the sliders then clicking *Preview geometry* shows little visible change.
**Likely causes to check (in `fansim/cockpit/app.py`):**
- Confirm each VSlider's `v_model=("e_xxx",)` actually two-way-binds — move a slider, then log
  `state.e_camber` etc. server-side in `do_preview()` to verify the value changed.
- `do_preview()` rebuilds via `build_edit_params()` and replaces the mesh in orange. Verify it
  is actually re-reading state (not a captured/stale closure) and that `ctrl.view_update()` fires.
- Small slider deltas = small geometry change; test with a BIG change (blades 7→11, camber
  0→0.06) to confirm it responds at all, then judge sensitivity.
- After the geometry-engine rewrite (wrap/wide chords), the editor slider RANGES may no longer
  match the new realistic geometry — widen them (chord to 40, add lean sliders 0–45 which the
  editor is currently MISSING entirely — the cockpit editor has no `lean_deg` sliders yet!).

## 2. Cockpit: bio-inspired features don't appear in the preview
**Symptom:** moving tubercle/serration/dimple sliders adds nothing to the previewed model.
**Likely causes:**
- `Features.active` requires BOTH amplitude AND count > 0 (e.g. tubercle needs `tubercle_amp>0`
  AND `tubercle_waves>0`). If the user moves only "dimple depth" but rows/cols stay 0, nothing
  happens. FIX: either auto-set a sensible count when amplitude>0, or make the UI clearer.
- On the now-WIDER blades, a feature amp of 0.10*chord may be visually subtle — verify with a
  large amp + waves and a close-up render.
- Confirm `edit_features()` reads the feature slider state and `build_edit_params()` passes it to
  `blade_from_flat(flat, feat)` (it does in code — but verify the sliders update state).
- Feature geometry needs higher loft resolution; `required_span_sections` handles it, but confirm
  the preview isn't capped too low.

## 3. Editor is missing the new `lean_deg` (wrap) control
The geometry rewrite added `lean_deg` (circumferential wrap — the realism DOF). The cockpit
editor panel and `edit_flat()`/`build_edit_params()` were written BEFORE that and do NOT expose
or set lean. Add lean_mid/lean_tip sliders and thread them through, or previews won't reflect the
wrap that the optimizer now uses.

## 4. Cockpit: no "processing" indicator while geometry builds
**Symptom:** clicking *Preview geometry* freezes with no feedback for ~7–35 s while the impeller
is generated (featured/wrapped geometry is slower); the user can't tell if it's working or broken.
**Fix:** show a busy/loading state during generation. NOTE: `do_preview()` is currently
SYNCHRONOUS, so setting a `preview_busy` state + flush won't reach the client until after the
build finishes (same issue the Assess button had). Make `do_preview()` ASYNC like `on_assess`:
set `state.preview_busy=True` + `state.preview_msg="Generating geometry…"` + `state.flush()`,
run the build via `loop.run_in_executor(...)`, then update + set busy False. Bind the Preview
button `loading=("preview_busy",)` and disable it while busy. Apply the same pattern anywhere
geometry/CFD runs without feedback.

## General next-session TODO (from the adversarial review)
- Full P–Q validation of the real A12x25 STL + shut-off (22.9 Pa, near-stall) + cap the hub bore.
- Grid convergence (confirm 61.5 CFM is mesh-independent).
- Noise objective (Proudman/Curle proxy, then FW-H) — still unbuilt; GPU/FluidX3D still idle.
