"""Fan-tab viz binder: 3-D render, geometry preview, and duct-airflow overlays (§13.9).

Owns the PyVista plotter state (``session.render_state``): drawing the current mesh with the
spec-highlight / envelope / velocity-glyph overlays (``_apply_render``), the async geometry
Preview, and loading the midplane airflow images + 3-D velocity arrows for a scored design.
Cross-domain: reads the editor flat and ``session.spec_status`` (assess) during Preview.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fansim.cfd.cockpit_viz import bake_cockpit_viz_heavy, load_case_mesh
from fansim.cfd.glyphs import (
    cfd_cloud_to_as_built,
    ensure_velocity_glyphs,
    make_glyph_arrows,
    peek_cached_velocity_glyphs,
)
from fansim.cfd.midplane import (
    axial_artifact_path,
    ensure_axial_uz_artifact,
    ensure_midplane_artifacts,
    ensure_streamlines_artifact,
    find_cached_midplane,
    streamline_artifact_path,
)
from fansim.cfd.orientation import AXIAL_CFD_ORIENTATION
from fansim.cfd.spanwise import ensure_spanwise_artifacts, find_cached_spanwise
from fansim.cockpit.airflow_panel import pick_airflow_uri, png_data_uri
from fansim.cockpit import fan_runtime
from fansim.cockpit.data import Design, scored_case_dir
from fansim.cockpit.errors import log_caught
from fansim.geometry.blade import validate_blade_params
from fansim.manufacturability import check_printability
from fansim.manufacturability.fdm_rules import preview_unprintable_note

_log = logging.getLogger(__name__)

_GLYPH_STRIDE = {"coarse": 4, "medium": 2, "fine": 1}
_GLYPH_MAX = {"coarse": 250, "medium": 500, "fine": 800}


def preview_built_camber(params) -> str:
    """Root/mid/tip camber of the *built* params, not live sliders (QA-26 / roadmap 27.5)."""
    st = sorted(params.stations, key=lambda s: s.r_frac)
    def nearest(frac: float):
        return min(st, key=lambda s: abs(float(s.r_frac) - frac))
    root, mid, tip = nearest(0.0), nearest(0.5), nearest(1.0)
    return f"{root.max_camber:.3f}/{mid.max_camber:.3f}/{tip.max_camber:.3f}"


def _has_speed_range(arrows) -> bool:
    """True when the glyphs carry a non-trivial |U| spread worth a colour bar."""
    try:
        import numpy as np

        u = np.asarray(arrows["U_mag"], dtype=float)
        return u.size > 0 and float(np.nanmax(u) - np.nanmin(u)) > 1e-6
    except Exception:  # noqa: BLE001 — missing array: fall back to a solid colour
        return False


def bind(session) -> None:
    state, ctrl = session.state, session.ctrl
    plotter = session.plotter
    spawn_busy_ticker = session.spawn_busy_ticker
    render_state = session.render_state
    preview_stl = session.preview_stl
    airflow_gen = session.airflow_gen
    airflow_lock = session.airflow_lock

    def _rebuild_glyph_arrows():
        cloud = render_state.get("glyph_cloud")
        if cloud is None:
            render_state["glyph_arrows"] = None
            return
        dens = getattr(state, "glyph_density", "medium") or "medium"
        if dens not in _GLYPH_STRIDE:
            dens = "medium"
        try:
            factor = float(state.glyph_scale) if state.glyph_scale not in (None, "") else 2.0
        except (TypeError, ValueError):
            factor = 2.0
        factor = max(0.2, min(factor, 20.0))
        try:
            render_state["glyph_arrows"] = make_glyph_arrows(
                cloud,
                stride=_GLYPH_STRIDE[dens],
                factor=factor,
                max_arrows=_GLYPH_MAX[dens],
            )
        except Exception:  # noqa: BLE001
            render_state["glyph_arrows"] = None

    def _clear_glyphs(msg: str = "Velocity arrows not available for this design"):
        render_state["glyph_cloud"] = None
        render_state["glyph_arrows"] = None
        state.glyph_caption = msg

    def _intake_extra():
        from fansim.cockpit.placement import intake_extra_mm

        return intake_extra_mm(
            enabled=bool(getattr(state, "intake_overbuild", False)),
            extra_mm=float(getattr(state, "intake_overbuild_mm", 10.0) or 0.0),
        )

    def _spec_limits():
        s = session.active_spec()
        return s.tip_dia_mm[1] / 2.0, s.depth_mm[1], _intake_extra()

    def _out_of_spec_mask(mesh):
        import numpy as np

        from fansim.cockpit.placement import out_of_spec_point_mask

        pts = mesh.points
        r = np.hypot(pts[:, 0], pts[:, 1])
        z = pts[:, 2]
        tip_r, nom_depth, extra = _spec_limits()
        hub_r = float(getattr(state, "e_hub_radius", tip_r * 0.4) or (tip_r * 0.4))
        return out_of_spec_point_mask(
            r, z, tip_r=tip_r, hub_r=hub_r, nom_depth=nom_depth, intake_extra=extra,
        )

    def _add_envelope(mesh):
        import numpy as np

        from fansim.cockpit.placement import frame_z_mid_from_points, intake_envelope_z_range

        pts = mesh.points
        r = np.hypot(pts[:, 0], pts[:, 1])
        z = pts[:, 2]
        tip_r, nom_depth, extra = _spec_limits()
        hub_r = float(getattr(state, "e_hub_radius", tip_r * 0.4) or (tip_r * 0.4))
        zmid = frame_z_mid_from_points(r, z, hub_r, nominal_depth=nom_depth)
        z_lo, z_hi = intake_envelope_z_range(zmid, nom_depth, extra)
        height = max(z_hi - z_lo, 1e-3)
        center_z = 0.5 * (z_lo + z_hi)
        cyl = fan_runtime.pv.Cylinder(
            center=(0, 0, center_z),
            direction=(0, 0, 1),
            radius=tip_r,
            height=height,
            resolution=64,
        )
        plotter.add_mesh(cyl, color="seagreen", opacity=0.10)
        try:
            plotter.add_mesh(cyl.extract_feature_edges(), color="seagreen", line_width=2)
        except Exception as exc:  # noqa: BLE001 - feature edges optional
            log_caught(_log, "frame cylinder edges", exc, level=logging.DEBUG)

    def _add_direction_cues(mesh):
        """Fixed cues for the real-fan sense so the view is never ambiguous:
        - AIRFLOW (blue): bold −Z arrows just outside the tip — air enters the open +Z intake
          and exits the −Z face past the motor cup (matches the schematic glyph flow).
        - ROTATION (orange): tangent arrows around a ring, CCW viewed from the +Z intake.
        """
        import numpy as np

        pv = fan_runtime.pv
        pts = mesh.points
        z = pts[:, 2]
        r = np.hypot(pts[:, 0], pts[:, 1])
        zmin, zmax = float(z.min()), float(z.max())
        span = max(zmax - zmin, 1.0)
        tip = float(np.percentile(r, 99.0))
        key = (round(tip, 2), round(zmin, 2), round(zmax, 2), round(span, 2))
        cached = render_state.get("cue_meshes")
        if cached is not None and render_state.get("cue_key") == key:
            for arr, color in cached:
                plotter.add_mesh(arr, color=color)
            return
        built: list = []
        # Airflow: a few bold −Z arrows just outside the tip (air exits the −Z exhaust).
        for ang in np.linspace(0.0, 2.0 * np.pi, 4, endpoint=False):
            x, y = (tip * 1.15) * np.cos(ang), (tip * 1.15) * np.sin(ang)
            try:
                arr = pv.Arrow(start=(x, y, zmax + 0.25 * span),
                               direction=(0, 0, -1), scale=1.4 * span)
                built.append((arr, "royalblue"))
            except Exception as exc:  # noqa: BLE001 - cue is optional
                log_caught(_log, "airflow cue", exc, level=logging.DEBUG)
                break
        # Rotation: tangent arrows around a ring OUTSIDE the blade tip, CCW viewed from the +Z
        # intake, so the cue never overlaps the blades.
        zc = 0.5 * (zmin + zmax)
        rr = tip * 1.30
        for k in range(10):
            a = 2.0 * np.pi * k / 10.0
            x, y = rr * np.cos(a), rr * np.sin(a)
            tang = (-np.sin(a), np.cos(a), 0.0)  # CCW looking from +Z toward −Z
            try:
                arr = pv.Arrow(start=(x, y, zc), direction=tang, scale=tip * 0.34)
                built.append((arr, "darkorange"))
            except Exception as exc:  # noqa: BLE001 - cue is optional
                log_caught(_log, "rotation cue", exc, level=logging.DEBUG)
                break
        render_state["cue_key"] = key
        render_state["cue_meshes"] = built
        for arr, color in built:
            plotter.add_mesh(arr, color=color)

    def _apply_render(reset: bool = False, *, overlays: bool = True):
        """(Re)draw the current model. ``overlays=False`` is impeller-only (fast first paint)."""
        plotter.clear_actors()
        p = render_state["path"]
        mesh = None
        if p:
            if render_state.get("mesh_path") == p and render_state.get("mesh") is not None:
                mesh = render_state["mesh"]
            else:
                try:
                    mesh = fan_runtime.pv.read(str(p))
                    render_state["mesh"] = mesh
                    render_state["mesh_path"] = p
                except Exception as exc:  # noqa: BLE001
                    log_caught(_log, f"read preview mesh {p}", exc)
                    mesh = None
                    render_state["mesh"] = None
                    render_state["mesh_path"] = None
        if mesh is not None:
            base = render_state["color"]
            drawn = mesh
            if state.highlight_spec:
                mask = _out_of_spec_mask(mesh)
                if mask.any():
                    drawn = mesh.copy()
                    drawn["spec"] = mask
                    plotter.add_mesh(
                        drawn,
                        scalars="spec",
                        cmap=[base, "red"],
                        clim=[0, 1],
                        show_scalar_bar=False,
                        smooth_shading=True,
                    )
                else:
                    plotter.add_mesh(mesh, color=base, smooth_shading=True)
            else:
                plotter.add_mesh(mesh, color=base, smooth_shading=True)
            if overlays and state.show_envelope:
                _add_envelope(mesh)
            if overlays and getattr(state, "show_dir_cues", True):
                _add_direction_cues(mesh)
        if overlays and state.show_glyphs and render_state.get("glyph_arrows") is not None:
            try:
                if not _has_speed_range(render_state["glyph_arrows"]):
                    # Schematic (no-CFD) arrows all have one speed: a |U| bar reading 3.00/3.00 told
                    # the user nothing (§23.22). Solid colour, no bar.
                    raise ValueError("no |U| range")
                plotter.add_mesh(
                    render_state["glyph_arrows"],
                    scalars="U_mag",
                    cmap="viridis",
                    show_scalar_bar=True,
                    scalar_bar_args={"title": "|U| m/s", "n_labels": 3},
                )
            except Exception:  # noqa: BLE001
                try:
                    plotter.add_mesh(
                        render_state["glyph_arrows"],
                        color="royalblue",
                        show_scalar_bar=False,
                    )
                except Exception as exc:  # noqa: BLE001
                    log_caught(_log, "glyph overlay", exc, level=logging.DEBUG)
        if reset:
            bounds = _frame_bounds(mesh)
            plotter.reset_camera(bounds=bounds)
            if bounds is not None:
                # reset_camera fits a bounding SPHERE, generous for this oblique view: the cue
                # ring used ~45 % of the viewer height. 1.5x keeps it inside with a margin.
                plotter.camera.zoom(1.5)

    def _frame_bounds(mesh):
        """Camera fit around the fan (+ the rotation-cue ring at 1.3·tip), not the whole scene.

        Fitting every actor included the schematic flow-arrow cloud, which reaches far past the
        tip, so the fan came up at ~1/4 of the viewer (QA UI-9).
        """
        if mesh is None:
            return None
        x0, x1, y0, y1, z0, z1 = (float(v) for v in mesh.bounds)
        cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        half = 0.5 * max(x1 - x0, y1 - y0) * 1.45
        return (cx - half, cx + half, cy - half, cy + half, z0, z1)

    def _draw(path, color: str, *, overlays: bool = True, reset: bool = True):
        render_state["path"] = str(path)
        render_state["color"] = color
        _apply_render(reset=reset, overlays=overlays)

    def _draw_impeller(path, color: str):
        """Results click: impeller + camera only, so the view is rotatable before arrows."""
        _draw(path, color, overlays=False, reset=True)

    def _schedule_viz_overlay(d) -> None:
        """After the impeller frame is on screen, attach cached arrows/cues (not a new CFD run)."""
        token = int(d.trial)
        state.viz_overlay_busy = True

        async def task():
            try:
                state.flush()
                await asyncio.sleep(0)
                if state.selected_trial != token:
                    return
                _prepare_glyphs_for_design(d)
                _apply_render(reset=False, overlays=True)
                try:
                    ctrl.view_update()
                except Exception as exc:  # noqa: BLE001
                    log_caught(_log, "view_update (viz overlay)", exc, level=logging.DEBUG)
            finally:
                if state.selected_trial == token:
                    state.viz_overlay_busy = False
                    try:
                        state.flush()
                    except Exception as exc:  # noqa: BLE001
                        log_caught(_log, "state.flush (viz overlay)", exc, level=logging.DEBUG)

        fan_runtime.asynchronous.create_task(task())

    @state.change(
        "highlight_spec", "show_envelope", "fan_model", "show_glyphs", "show_dir_cues",
        "intake_overbuild", "intake_overbuild_mm",
    )
    def _on_viz_toggle(**_):
        _apply_render(reset=False)
        try:
            ctrl.view_update()
        except Exception as exc:  # noqa: BLE001
            log_caught(_log, "view_update (viz toggle)", exc, level=logging.DEBUG)

    @state.change("glyph_mode")
    def _on_glyph_mode(glyph_mode=None, **_):
        on = str(glyph_mode or "on") == "on"
        if bool(state.show_glyphs) != on:
            state.show_glyphs = on
            state.flush()

    @state.change("glyph_density", "glyph_scale")
    def _on_glyph_params(**_):
        if render_state.get("glyph_cloud") is None:
            return
        _rebuild_glyph_arrows()
        _apply_render(reset=False)
        try:
            ctrl.view_update()
        except Exception as exc:  # noqa: BLE001
            log_caught(_log, "view_update (glyph params)", exc, level=logging.DEBUG)

    def _build_preview_stl(flat, feat, spec, cup: bool):
        from dataclasses import asdict

        from fansim.geometry.isolated import build_stl_isolated

        from fansim.resources import current_tier

        mount = None
        if cup and current_tier().cup_build_ok:
            if spec.motor_mount is not None:
                mount = asdict(spec.motor_mount)
        # Motor cup needs a real boolean solid (not the fast non-fused preview mesh).
        build_stl_isolated(
            flat, feat, preview_stl, timeout=300.0,
            preview=mount is None,
            motor_mount=mount,
            progress_path=_preview_progress_path(),
            fuse_guard=True,  # a person is waiting: refuse plainly rather than swap (25.5)
        )

    def _preview_progress_path():
        return preview_stl.with_name(preview_stl.name + ".progress.json")

    def _preview_stage_hint() -> str:
        """Ticker hint: the worker's build stage; drives the determinate Preview bar (§23.17)."""
        from fansim.geometry.isolated import progress_caption, read_progress

        pct, text = progress_caption(read_progress(_preview_progress_path()),
                                     int(getattr(state, "preview_pct", 0) or 0))
        state.preview_pct = pct
        return text

    def do_preview():
        if state.preview_busy or state.assess_busy:
            return
        try:
            params = session.build_edit_params()
            validate_blade_params(params)
            printable = check_printability(params)
            print_warn = "" if printable.printable else "\n" + preview_unprintable_note(printable.reason)
            flat, feat = session.edit_flat(), session.edit_features()
            # Settings from the click (24.4, Kimball 2026-10-15): the fits/weight verdict and the cup
            # build use the fan model / material / leeway / cup switch as they were when Preview was
            # pressed, not as they are when the build finishes.
            spec = session.active_spec()
            cup = bool(getattr(state, "preview_motor_cup", False))
        except ValueError as exc:
            state.preview_msg = f"⚠ {exc}"
            state.flush()
            return
        except Exception as exc:  # noqa: BLE001 - sync preamble; surface or the button looks dead
            state.preview_msg = f"⚠ Preview setup failed: {type(exc).__name__}: {exc}"
            state.flush()
            return

        # Busy must be True *before* create_task. Setting it inside the coroutine left a window
        # where a second Preview (or Randomize then Preview) queued a second isolated worker.
        # Both write the same preview_stl and both call _draw/view_update on one VTK plotter —
        # the 3-D view freezes with no browser console error.
        state.preview_busy = True
        state.flush()

        async def task():
            heavy = ""
            if params.features.active:
                heavy = "features are heavy — up to ~2 min"
            elif int(getattr(params, "tip_notch_count", 0) or 0) > 0:
                heavy = "tip TE notches — first build can take ~30–60 s"
            # Determinate from the first frame: the shared bar only sweeps while this is 0. Clear the
            # last run's progress file first, or the first tick reads its "4/4" and max() pins the
            # bar at 75 % (QA UI-4 r4).
            from fansim.cockpit.fan_core import refresh_memory_tier
            from fansim.geometry.isolated import progress_caption

            ticker = None
            try:
                _preview_progress_path().unlink(missing_ok=True)
                refresh_memory_tier(state)
                state.preview_pct, _ = progress_caption(None)
                ticker, _t0 = spawn_busy_ticker(
                    action="Preview",
                    msg_attr="preview_msg",
                    busy_attr="preview_busy",
                    note=heavy,
                    hint_fn=_preview_stage_hint,
                    interval=0.5,  # stages can be ~1-2 s long; a 1 s poll skipped them (QA r3)
                )
                state.flush()
                loop = asyncio.get_running_loop()
                try:
                    await loop.run_in_executor(None, _build_preview_stl, flat, feat, spec, cup)
                except TimeoutError:
                    state.preview_msg = (
                        "⚠ Geometry build timed out — previous mesh kept (so nothing looks "
                        "changed). Tip TE notches / bio-features are heavy; wait for Preview to "
                        "finish, or turn notches off briefly to tweak Sickle/Wrap, then re-enable."
                    )
                    return
                except Exception as exc:  # noqa: BLE001
                    state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__}: {exc}"
                    return
                def _readouts():
                    """STL load + spec + printability (~3 s): off the event loop (QA UI-4 r4 freeze)."""
                    _, status = session.spec_status(preview_stl, params, flat, spec=spec)
                    try:
                        from fansim.manufacturability.printability_score import grade_printability

                        return status, "\n🖨 " + grade_printability(params).summary
                    except Exception:  # noqa: BLE001
                        return status, ""

                status, print_line = await loop.run_in_executor(None, _readouts)
                _draw(preview_stl, "darkorange")
                feats = "features ON" if params.features.active else "smooth"
                tone_line = ""
                if params.blade_angles_deg is not None:
                    try:
                        import numpy as _np

                        from fansim.acoustics.tonal import peak_tone_reduction_db

                        drop = -peak_tone_reduction_db(_np.radians(_np.asarray(params.blade_angles_deg)))
                        odd = (
                            ""
                            if params.n_blades % 2
                            else "  (even blade count — odd counts spread the tone more)"
                        )
                        tone_line = (
                            f"\n🔉 Uneven spacing: predicted peak tone −{drop:.1f} dB, free of any flow cost{odd}"
                        )
                    except Exception:  # noqa: BLE001
                        tone_line = ""
                state.preview_msg = (
                    f"Preview (orange): {params.n_blades} blades, "
                    f"camber {preview_built_camber(params)}, {feats}.\n{status}{print_line}"
                    f"{tone_line}{print_warn}"
                )
                try:
                    ctrl.view_update()
                except Exception as exc:  # noqa: BLE001
                    log_caught(_log, "view_update (preview)", exc, level=logging.DEBUG)
            finally:
                if ticker is not None:
                    ticker.cancel()
                state.preview_busy = False
                state.preview_pct = 0
                state.flush()

        fan_runtime.asynchronous.create_task(task())

    _png_data_uri = png_data_uri  # shared with the archetype tabs (airflow_panel)

    def _apply_airflow_field():
        uris = {
            "U": state._airflow_u_uri,
            "p": state._airflow_p_uri,
            "uz": state._airflow_uz_uri,
            "stream": state._airflow_stream_uri,
            "span": state._airflow_span_uri,
            "b2b": state._airflow_b2b_uri,
        }
        uri, caption = pick_airflow_uri(uris, getattr(state, "airflow_field", "U") or "U")
        if uri:
            state.airflow_img_uri = uri
            state.airflow_caption = caption
        else:
            state.airflow_img_uri = ""
            if not state.airflow_busy:
                state.airflow_caption = "Airflow not available for this design"

    def _clear_airflow(msg: str = "Airflow not available for this design"):
        state.airflow_busy = False
        state.airflow_cancel = False
        state.airflow_progress = ""
        state._airflow_u_uri = ""
        state._airflow_p_uri = ""
        state._airflow_uz_uri = ""
        state._airflow_stream_uri = ""
        state._airflow_span_uri = ""
        state._airflow_b2b_uri = ""
        state.airflow_img_uri = ""
        state.airflow_caption = msg
        _clear_glyphs("Velocity arrows not available for this design")

    def _mark(done: bool | None) -> str:
        if done is True:
            return "✓"
        if done is False:
            return "…"
        return "—"

    def _set_airflow_progress(
        *,
        midplane: bool | None = None,
        arrows: bool | None = None,
        heavy: bool | None = None,
        note: str = "",
    ) -> None:
        """Update checklist caption (§22.5). ``None`` = not started, False = in flight, True = done."""
        parts = [
            f"midplane {_mark(midplane)}",
            f"arrows {_mark(arrows)}",
            f"stream/span {_mark(heavy)}",
        ]
        state.airflow_progress = " · ".join(parts)
        base = state.airflow_progress
        state.airflow_caption = f"{note} {base}".strip() if note else base

    def cancel_airflow():
        """Abort in-flight core / heavy airflow builds (§22.5)."""
        if not state.airflow_busy:
            return
        state.airflow_cancel = True
        airflow_gen[0] += 1
        state.airflow_busy = False
        state.airflow_progress = "midplane — · arrows — · stream/span —"
        state.airflow_caption = "⏹ Airflow build cancelled — impeller kept; pick a design or toggle a view to retry."
        try:
            state.flush()
            ctrl.view_update()
        except Exception as exc:  # noqa: BLE001
            log_caught(_log, "view_update (cancel airflow)", exc, level=logging.DEBUG)

    def _apply_glyph_artifact(gly) -> None:
        """Install a VelocityGlyphs result onto the plotter (CFD → as-built frame)."""
        if gly is not None and gly.available and gly.cloud is not None:
            render_state["glyph_cloud"] = cfd_cloud_to_as_built(
                gly.cloud, AXIAL_CFD_ORIENTATION
            )
            state.glyph_caption = gly.caption
            _rebuild_glyph_arrows()
        elif gly is not None:
            _clear_glyphs(gly.caption or "Velocity arrows not available for this design")

    def _apply_png_pack(art, uz, stream, span) -> None:
        """Push PNG URIs into state. ``None`` args leave that slot unchanged (§22.7 partial)."""
        if uz is not None:
            state._airflow_uz_uri = _png_data_uri(uz.png) if uz.available else ""
        if stream is not None:
            state._airflow_stream_uri = (
                _png_data_uri(stream.png) if stream.available else "")
        if span is not None:
            state._airflow_span_uri = (
                _png_data_uri(span.spanwise_png)
                if span.available and span.spanwise_png
                else "")
            state._airflow_b2b_uri = (
                _png_data_uri(span.b2b_png)
                if span.available and span.b2b_png
                else "")
        has_extra = bool(
            state._airflow_uz_uri or state._airflow_stream_uri
            or state._airflow_span_uri or state._airflow_b2b_uri
        )
        if art is not None and art.available:
            state._airflow_u_uri = _png_data_uri(art.u_png)
            state._airflow_p_uri = _png_data_uri(art.p_png)
            state.airflow_busy = False
            _apply_airflow_field()
        elif art is not None and not art.available and not has_extra:
            state.airflow_busy = False
            state._airflow_u_uri = ""
            state._airflow_p_uri = ""
            state.airflow_img_uri = ""
            state.airflow_caption = art.caption or "Airflow not available for this design"
        elif has_extra or (art is not None and art.available):
            state.airflow_busy = False
            _apply_airflow_field()
        elif art is None and (uz is not None or stream is not None or span is not None):
            state.airflow_busy = False
            _apply_airflow_field()

    def _apply_cached_pngs(case) -> bool:
        """Apply any on-disk PNGs. Returns True if default midplane (|U|) is ready."""
        mid = find_cached_midplane(case)
        uz_path = axial_artifact_path(case)
        stream_path = streamline_artifact_path(case)
        span = find_cached_spanwise(case)

        class _Png:
            def __init__(self, png, available=True):
                self.png = png
                self.available = available

        uz = _Png(uz_path, uz_path.is_file()) if uz_path.is_file() else None
        stream = _Png(stream_path, True) if stream_path.is_file() else None
        if mid is not None or uz is not None or stream is not None or span is not None:
            _apply_png_pack(mid, uz, stream, span)
        return mid is not None and mid.available

    def _core_warm(case) -> bool:
        """True when midplane PNG + glyph cache cover the default Design view.

        Glyphs attach in ``_schedule_viz_overlay`` after the impeller is already
        on screen; a warm pick still uses the disk/memory cache, not a new CFD run.
        """
        mid_ok = _apply_cached_pngs(case)
        gly = peek_cached_velocity_glyphs(case)
        return bool(mid_ok and gly is not None and gly.available)

    def _prepare_glyphs_for_design(d) -> bool:
        """Put this design's cached arrows on the plotter, or drop the previous design's."""
        from fansim.cockpit.data import scored_case_dir

        case = None
        if d is not None and getattr(d, "has_model", False) and not (d.extra or {}).get("cfd_stale"):
            case = scored_case_dir(d)
        gly = peek_cached_velocity_glyphs(case) if case is not None else None
        if gly is not None and gly.available:
            _apply_glyph_artifact(gly)
            return True
        _clear_glyphs(
            "Loading 3-D velocity arrows…" if case is not None
            else "Velocity arrows not available for this design"
        )
        return False

    def _schedule_heavy_field(case, token: int, field: str) -> None:
        """Build streamlines / spanwise / Uz on demand when the user selects that view (§22.7)."""
        field = (field or "U").lower()
        if field in ("u", "p"):
            return
        need_uz = field == "uz" and not state._airflow_uz_uri
        need_stream = field == "stream" and not state._airflow_stream_uri
        need_span = field in ("span", "b2b") and not (
            state._airflow_span_uri if field == "span" else state._airflow_b2b_uri
        )
        if not (need_uz or need_stream or need_span):
            return

        airflow_gen[0] += 1
        gen = airflow_gen[0]
        state.airflow_cancel = False
        state.airflow_busy = True
        mid_ok = bool(state._airflow_u_uri or state._airflow_p_uri)
        arrows_ok = render_state.get("glyph_arrows") is not None
        _set_airflow_progress(
            midplane=True if mid_ok else None,
            arrows=True if arrows_ok else None,
            heavy=False,
            note=f"Building {field}…",
        )

        def _load():
            with airflow_lock:
                if airflow_gen[0] != gen or state.airflow_cancel:
                    return None
                mesh = load_case_mesh(case)
                if airflow_gen[0] != gen or state.airflow_cancel:
                    return None
                uz = stream = span = None
                if need_uz:
                    uz = ensure_axial_uz_artifact(case, mesh=mesh)
                if need_stream:
                    stream = ensure_streamlines_artifact(case, mesh=mesh)
                if need_span:
                    span = ensure_spanwise_artifacts(case, mesh=mesh)
                return uz, stream, span

        async def task():
            try:
                loop = asyncio.get_running_loop()
                pack = await loop.run_in_executor(None, _load)
                if state.selected_trial != token or pack is None:
                    return
                uz, stream, span = pack
                _apply_png_pack(None, uz, stream, span)
                state.airflow_busy = False
                state.airflow_cancel = False
                _set_airflow_progress(
                    midplane=True if (state._airflow_u_uri or state._airflow_p_uri) else None,
                    arrows=True if render_state.get("glyph_arrows") is not None else None,
                    heavy=True,
                )
                _apply_airflow_field()
            except Exception:  # noqa: BLE001
                if state.selected_trial == token:
                    state.airflow_busy = False
                    state.airflow_caption = f"{field} view not available for this design"
            finally:
                if state.selected_trial == token and airflow_gen[0] == gen:
                    state.airflow_busy = False
                try:
                    state.flush()
                    ctrl.view_update()
                except Exception as exc:  # noqa: BLE001
                    log_caught(_log, "view_update (heavy field)", exc, level=logging.DEBUG)

        fan_runtime.asynchronous.create_task(task())

    def _schedule_airflow(d: Design):
        # The run behind the score: refreshed designs keep old fields in their own folder.
        case = scored_case_dir(d) if d.has_model else None
        if case is None or d.extra.get("cfd_stale"):
            _clear_airflow("Airflow not available for this design")
            _apply_render(reset=False)
            return

        token = int(d.trial)
        airflow_gen[0] += 1
        gen = airflow_gen[0]
        render_state["airflow_case"] = str(case)
        state.airflow_cancel = False

        # Instant path: midplane + glyphs warm (§22.1 / §22.7 / §22.9). Heavy on field toggle.
        if _core_warm(case):
            state.airflow_busy = False
            _set_airflow_progress(midplane=True, arrows=True, heavy=None)
            # Prefer the field caption when a PNG is already showing.
            _apply_airflow_field()
            if not state.airflow_img_uri:
                state.airflow_caption = (
                    "Core airflow ready (midplane ✓ · arrows ✓). "
                    "Streamlines / spanwise build when selected."
                )
            try:
                state.flush()
            except Exception as exc:  # noqa: BLE001
                log_caught(_log, "state.flush (airflow cache hit)", exc, level=logging.DEBUG)
            _schedule_heavy_field(case, token, getattr(state, "airflow_field", "U"))
            return

        state.airflow_busy = True
        # Keep existing midplane image if cached; only blank when nothing on disk.
        if find_cached_midplane(case) is None:
            state.airflow_img_uri = ""
            state._airflow_u_uri = ""
            state._airflow_p_uri = ""
        if not axial_artifact_path(case).is_file():
            state._airflow_uz_uri = ""
        if not streamline_artifact_path(case).is_file():
            state._airflow_stream_uri = ""
        if find_cached_spanwise(case) is None:
            state._airflow_span_uri = ""
            state._airflow_b2b_uri = ""
        mid_cached_now = _apply_cached_pngs(case)
        _set_airflow_progress(
            midplane=True if mid_cached_now else False,
            arrows=False,
            heavy=None,
            note="Loading core airflow…",
        )

        cached_gly = peek_cached_velocity_glyphs(case)
        if cached_gly is not None and cached_gly.available:
            _set_airflow_progress(
                midplane=True if mid_cached_now else False,
                arrows=True,
                heavy=None,
                note="Loading core airflow…",
            )
        # Impeller is already on the plotter from select(); skip a second STL rebuild here.
        # Stale arrows from the previous design were cleared in _prepare_glyphs_for_design.

        def _load_core_pack():
            """Midplane + glyphs only — streamlines/spanwise deferred (§22.7)."""
            with airflow_lock:
                if airflow_gen[0] != gen or state.airflow_cancel:
                    return None
                mesh = None
                mid_cached = find_cached_midplane(case)
                gly_cached = peek_cached_velocity_glyphs(case)
                need_mesh = mid_cached is None or gly_cached is None
                if need_mesh:
                    mesh = load_case_mesh(case)
                if airflow_gen[0] != gen or state.airflow_cancel:
                    return None
                mid = ensure_midplane_artifacts(case, mesh=mesh)
                if airflow_gen[0] != gen or state.airflow_cancel:
                    return None
                uz = ensure_axial_uz_artifact(case, mesh=mesh)
                if airflow_gen[0] != gen or state.airflow_cancel:
                    return None
                gly = ensure_velocity_glyphs(case, mesh=mesh)
                return mid, gly, uz

        async def task():
            try:
                loop = asyncio.get_running_loop()
                pack = await loop.run_in_executor(None, _load_core_pack)
                if state.selected_trial != token or pack is None:
                    return
                art, gly, uz = pack
                _apply_png_pack(art, uz, None, None)
                _apply_glyph_artifact(gly)
                _apply_render(reset=False)
                state.airflow_busy = False
                state.airflow_cancel = False
                _set_airflow_progress(
                    midplane=bool(art and art.available),
                    arrows=bool(gly and gly.available),
                    heavy=None,
                )
                _apply_airflow_field()
                if not state.airflow_img_uri and art and art.available:
                    state.airflow_caption = state.airflow_progress
                field = getattr(state, "airflow_field", "U") or "U"
                if str(field).lower() in ("stream", "span", "b2b"):
                    _schedule_heavy_field(case, token, field)
                else:
                    async def _idle_heavy():
                        await asyncio.sleep(0.5)
                        if state.selected_trial != token or state.airflow_cancel:
                            return
                        await loop.run_in_executor(
                            None, lambda: bake_cockpit_viz_heavy(case),
                        )
                        if state.selected_trial == token and not state.airflow_cancel:
                            _apply_cached_pngs(case)
                            _set_airflow_progress(
                                midplane=True,
                                arrows=True,
                                heavy=True,
                            )
                            try:
                                state.flush()
                            except Exception as exc:  # noqa: BLE001
                                log_caught(
                                    _log, "state.flush (idle heavy)", exc, level=logging.DEBUG,
                                )
                    fan_runtime.asynchronous.create_task(_idle_heavy())
            except Exception:  # noqa: BLE001
                if state.selected_trial == token:
                    state.airflow_busy = False
                    state.airflow_progress = ""
                    state._airflow_u_uri = ""
                    state._airflow_p_uri = ""
                    state.airflow_img_uri = ""
                    state.airflow_caption = "Airflow not available for this design"
                    _clear_glyphs()
                    _apply_render(reset=False)
            finally:
                if state.selected_trial == token and airflow_gen[0] == gen:
                    state.airflow_busy = False
                try:
                    state.flush()
                    ctrl.view_update()
                except Exception as exc:  # noqa: BLE001
                    log_caught(_log, "view_update (airflow)", exc, level=logging.DEBUG)

        fan_runtime.asynchronous.create_task(task())

    @state.change("airflow_field")
    def _on_airflow_field(airflow_field=None, **_):
        _apply_airflow_field()
        field = airflow_field or getattr(state, "airflow_field", "U")
        tid = state.selected_trial
        case_s = render_state.get("airflow_case")
        if tid is not None and case_s:
            case = Path(case_s)
            if case.is_dir():
                _schedule_heavy_field(case, int(tid), field)
        try:
            state.flush()
        except Exception as exc:  # noqa: BLE001
            log_caught(_log, "state.flush (airflow field)", exc, level=logging.DEBUG)

    session._rebuild_glyph_arrows = _rebuild_glyph_arrows
    session._clear_glyphs = _clear_glyphs
    session._apply_render = _apply_render
    session._prepare_glyphs_for_design = _prepare_glyphs_for_design
    session._draw = _draw
    session._draw_impeller = _draw_impeller
    session._schedule_viz_overlay = _schedule_viz_overlay
    session.do_preview = do_preview
    session._schedule_airflow = _schedule_airflow
    session._clear_airflow = _clear_airflow
    session._apply_airflow_field = _apply_airflow_field
    session._schedule_heavy_field = _schedule_heavy_field
    session.cancel_airflow = cancel_airflow
