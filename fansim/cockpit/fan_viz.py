"""Fan-tab viz binder: 3-D render, geometry preview, and duct-airflow overlays (§13.9).

Owns the PyVista plotter state (``session.render_state``): drawing the current mesh with the
spec-highlight / envelope / velocity-glyph overlays (``_apply_render``), the async geometry
Preview, and loading the midplane airflow images + 3-D velocity arrows for a scored design.
Cross-domain: reads the editor flat and ``session.spec_status`` (assess) during Preview.
"""

from __future__ import annotations

import asyncio
import logging

from fansim.cfd.glyphs import ensure_velocity_glyphs, make_glyph_arrows
from fansim.cfd.midplane import ensure_midplane_artifacts
from fansim.cockpit import fan_runtime
from fansim.cockpit.data import Design
from fansim.cockpit.errors import log_caught
from fansim.manufacturability import check_printability
from fansim.manufacturability.fdm_rules import preview_unprintable_note

_log = logging.getLogger(__name__)

_GLYPH_STRIDE = {"coarse": 4, "medium": 2, "fine": 1}
_GLYPH_MAX = {"coarse": 250, "medium": 500, "fine": 800}


def bind(session) -> None:
    import base64
    from pathlib import Path

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

    def _spec_limits():
        s = session.active_spec()
        return s.tip_dia_mm[1] / 2.0, s.depth_mm[1]

    def _out_of_spec_mask(mesh):
        import numpy as np

        pts = mesh.points
        r = np.hypot(pts[:, 0], pts[:, 1])
        z = pts[:, 2]
        tip_r, depth_lim = _spec_limits()
        zmid = 0.5 * (float(z.min()) + float(z.max()))
        mask = (r > tip_r) | (np.abs(z - zmid) > depth_lim / 2.0)
        return mask.astype(float)

    def _add_envelope(mesh):
        zc = mesh.points[:, 2]
        zmid = 0.5 * (float(zc.min()) + float(zc.max()))
        tip_r, depth_lim = _spec_limits()
        cyl = fan_runtime.pv.Cylinder(
            center=(0, 0, zmid),
            direction=(0, 0, 1),
            radius=tip_r,
            height=depth_lim,
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
        - ROTATION (orange): tangent arrows around a ring, CCW viewed from the +Z intake (spin −1).
        """
        import numpy as np

        pv = fan_runtime.pv
        pts = mesh.points
        z = pts[:, 2]
        r = np.hypot(pts[:, 0], pts[:, 1])
        zmin, zmax = float(z.min()), float(z.max())
        span = max(zmax - zmin, 1.0)
        tip = float(np.percentile(r, 99.0))
        # Airflow: a few bold −Z arrows just outside the tip (air exits the −Z exhaust).
        for ang in np.linspace(0.0, 2.0 * np.pi, 4, endpoint=False):
            x, y = (tip * 1.18) * np.cos(ang), (tip * 1.18) * np.sin(ang)
            try:
                arr = pv.Arrow(start=(x, y, zmax + 0.25 * span),
                               direction=(0, 0, -1), scale=1.4 * span)
                plotter.add_mesh(arr, color="royalblue")
            except Exception as exc:  # noqa: BLE001 - cue is optional
                log_caught(_log, "airflow cue", exc, level=logging.DEBUG)
                break
        # Rotation: tangent arrows around a ring, CCW viewed from the +Z intake.
        zc = 0.5 * (zmin + zmax)
        rr = tip * 0.72
        for k in range(8):
            a = 2.0 * np.pi * k / 8.0
            x, y = rr * np.cos(a), rr * np.sin(a)
            tang = (-np.sin(a), np.cos(a), 0.0)  # CCW looking from +Z toward −Z
            try:
                arr = pv.Arrow(start=(x, y, zc), direction=tang, scale=tip * 0.30)
                plotter.add_mesh(arr, color="darkorange")
            except Exception as exc:  # noqa: BLE001 - cue is optional
                log_caught(_log, "rotation cue", exc, level=logging.DEBUG)
                break

    def _apply_render(reset: bool = False):
        """(Re)draw the current model with the active highlight/envelope/glyph options."""
        plotter.clear_actors()
        p = render_state["path"]
        mesh = None
        if p:
            try:
                mesh = fan_runtime.pv.read(str(p))
            except Exception as exc:  # noqa: BLE001
                log_caught(_log, f"read preview mesh {p}", exc)
                mesh = None
        if mesh is not None:
            base = render_state["color"]
            if state.highlight_spec:
                mask = _out_of_spec_mask(mesh)
                if mask.any():
                    mesh["spec"] = mask
                    plotter.add_mesh(
                        mesh,
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
            if state.show_envelope:
                _add_envelope(mesh)
            if getattr(state, "show_dir_cues", True):
                _add_direction_cues(mesh)
        if state.show_glyphs and render_state.get("glyph_arrows") is not None:
            try:
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
            plotter.reset_camera()

    def _draw(path, color: str):
        render_state["path"] = str(path)
        render_state["color"] = color
        _apply_render(reset=True)

    @state.change("highlight_spec", "show_envelope", "fan_model", "show_glyphs", "show_dir_cues")
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

    def _build_preview_stl(flat, feat):
        from dataclasses import asdict

        from fansim.geometry.isolated import build_stl_isolated

        mount = None
        if bool(getattr(state, "preview_motor_cup", False)):
            spec = session.active_spec()
            if spec.motor_mount is not None:
                mount = asdict(spec.motor_mount)
        # Motor cup needs a real boolean solid (not the fast non-fused preview mesh).
        build_stl_isolated(
            flat, feat, preview_stl, timeout=300.0,
            preview=mount is None,
            motor_mount=mount,
        )

    def do_preview():
        if state.preview_busy or state.assess_busy:
            return
        try:
            params = session.build_edit_params()
            printable = check_printability(params)
            print_warn = "" if printable.printable else "\n" + preview_unprintable_note(printable.reason)
            flat, feat = session.edit_flat(), session.edit_features()
        except Exception as exc:  # noqa: BLE001 - sync preamble; surface or the button looks dead
            state.preview_msg = f"⚠ Preview setup failed: {type(exc).__name__}: {exc}"
            state.flush()
            return

        async def task():
            state.preview_busy = True
            heavy = ""
            if params.features.active:
                heavy = "features are heavy — up to ~2 min"
            elif int(getattr(params, "tip_notch_count", 0) or 0) > 0:
                heavy = "tip TE notches — first build can take ~30–60 s"
            ticker, _t0 = spawn_busy_ticker(
                action="Preview",
                msg_attr="preview_msg",
                busy_attr="preview_busy",
                note=heavy,
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, _build_preview_stl, flat, feat)
            except TimeoutError:
                state.preview_msg = (
                    "⚠ Geometry build timed out — previous mesh kept (so nothing looks "
                    "changed). Tip TE notches / bio-features are heavy; wait for Preview to "
                    "finish, or turn notches off briefly to tweak Sickle/Wrap, then re-enable."
                )
                state.preview_busy = False
                ticker.cancel()
                state.flush()
                return
            except Exception as exc:  # noqa: BLE001
                state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__}: {exc}"
                state.preview_busy = False
                ticker.cancel()
                state.flush()
                return
            _draw(preview_stl, "darkorange")
            feats = "features ON" if params.features.active else "smooth"
            _, status = session.spec_status(preview_stl, params, flat)
            try:
                from fansim.manufacturability.printability_score import grade_printability

                print_line = "\n🖨 " + grade_printability(params).summary
            except Exception:  # noqa: BLE001
                print_line = ""
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
                f"camber {state.e_camber_root:.3f}/{state.e_camber_mid:.3f}/{state.e_camber_tip:.3f}, {feats}.\n{status}{print_line}"
                f"{tone_line}{print_warn}"
            )
            state.preview_busy = False
            ticker.cancel()
            try:
                ctrl.view_update()
            except Exception as exc:  # noqa: BLE001
                log_caught(_log, "view_update (preview)", exc, level=logging.DEBUG)
            state.flush()

        fan_runtime.asynchronous.create_task(task())

    def _png_data_uri(path) -> str:
        if path is None or not Path(path).is_file():
            return ""
        try:
            return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()
        except Exception:  # noqa: BLE001
            return ""

    def _apply_airflow_field():
        field = getattr(state, "airflow_field", "U") or "U"
        if field == "p" and state._airflow_p_uri:
            state.airflow_img_uri = state._airflow_p_uri
            state.airflow_caption = "pressure midplane — FRONT LEFT -> OUTLET RIGHT"
        elif state._airflow_u_uri:
            state.airflow_img_uri = state._airflow_u_uri
            state.airflow_caption = "Umag midplane — FRONT LEFT -> OUTLET RIGHT"
        elif state._airflow_p_uri:
            state.airflow_img_uri = state._airflow_p_uri
            state.airflow_caption = "pressure midplane — FRONT LEFT -> OUTLET RIGHT"
        else:
            state.airflow_img_uri = ""
            if not state.airflow_busy:
                state.airflow_caption = "Airflow not available for this design"

    def _clear_airflow(msg: str = "Airflow not available for this design"):
        state.airflow_busy = False
        state._airflow_u_uri = ""
        state._airflow_p_uri = ""
        state.airflow_img_uri = ""
        state.airflow_caption = msg
        _clear_glyphs("Velocity arrows not available for this design")

    def _schedule_airflow(d: Design):
        case = Path(d.stl_path).parent if d.has_model else None
        if case is None or d.extra.get("cfd_stale"):
            _clear_airflow("Airflow not available for this design")
            _apply_render(reset=False)
            return
        state.airflow_busy = True
        state.airflow_img_uri = ""
        state.airflow_caption = "Loading duct airflow midplane…"
        state._airflow_u_uri = ""
        state._airflow_p_uri = ""
        _clear_glyphs("Loading 3-D velocity arrows…")
        _apply_render(reset=False)
        token = int(d.trial)
        airflow_gen[0] += 1
        gen = airflow_gen[0]

        def _load_airflow_pack():
            with airflow_lock:
                if airflow_gen[0] != gen:
                    return None, None
                mid = ensure_midplane_artifacts(case)
                if airflow_gen[0] != gen:
                    return None, None
                gly = ensure_velocity_glyphs(case)
                return mid, gly

        async def task():
            try:
                loop = asyncio.get_running_loop()
                art, gly = await loop.run_in_executor(None, _load_airflow_pack)
                if state.selected_trial != token or art is None:
                    return
                if art.available:
                    state._airflow_u_uri = _png_data_uri(art.u_png)
                    state._airflow_p_uri = _png_data_uri(art.p_png)
                    state.airflow_busy = False
                    _apply_airflow_field()
                else:
                    state.airflow_busy = False
                    state._airflow_u_uri = ""
                    state._airflow_p_uri = ""
                    state.airflow_img_uri = ""
                    state.airflow_caption = art.caption or "Airflow not available for this design"
                if gly is not None and gly.available and gly.cloud is not None:
                    render_state["glyph_cloud"] = gly.cloud
                    state.glyph_caption = gly.caption
                    _rebuild_glyph_arrows()
                elif gly is not None:
                    _clear_glyphs(gly.caption or "Velocity arrows not available for this design")
                _apply_render(reset=False)
            except Exception:  # noqa: BLE001
                if state.selected_trial == token:
                    state.airflow_busy = False
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
        try:
            state.flush()
        except Exception as exc:  # noqa: BLE001
            log_caught(_log, "state.flush (airflow field)", exc, level=logging.DEBUG)

    session._rebuild_glyph_arrows = _rebuild_glyph_arrows
    session._clear_glyphs = _clear_glyphs
    session._apply_render = _apply_render
    session._draw = _draw
    session.do_preview = do_preview
    session._schedule_airflow = _schedule_airflow
    session._clear_airflow = _clear_airflow
    session._apply_airflow_field = _apply_airflow_field
