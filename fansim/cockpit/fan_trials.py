"""Fan-tab trials binder: select a design, record measurements, load the stock reference (§13.9).

Selecting a trial draws it, fills the info panel + editor, and schedules its airflow overlay.
Also records real-world measurements against a design and loads the parametric stock reference.
Cross-domain: draws via ``session._draw`` / ``_apply_render`` and seeds the editor through
``session``.
"""

from __future__ import annotations

import asyncio
import logging

from fansim.cockpit import fan_runtime
from fansim.cockpit.errors import log_caught
from fansim.cockpit.score_caption import score_caption, shape_note
from fansim.fan_spec import get_fan_spec, published_scatter_point
from fansim.geometry.features import Features
from fansim.optimize.presets import assess_load
from fansim.optimize.search_space import stock_blade_flat
from validation.ingest import MeasuredPoint
from validation.store import (
    calibration_from_store,
    make_design_id,
    record_measurement,
    sim_vs_real,
)

_log = logging.getLogger(__name__)

# R1.4 (Kimball 2026-10-21): same wording in Expert and the README Known limits list.
STOCK_RECIPE_GAP = (
    "Stock is rebuilt from a parametric recipe and reads about 5 % less airflow than the "
    "real A12x25 shape (55.7 vs 58.3 CFM in the same test). Designs are compared with this "
    "Stock, so comparisons are like for like."
)


def bind(session) -> None:
    state, ctrl = session.state, session.ctrl
    plotter = session.plotter
    run_dir = session.run_dir
    by_trial = session.by_trial
    spawn_busy_ticker = session.spawn_busy_ticker
    render_state = session.render_state

    def select(trial: int | None):
        _log.debug("select(%r)", trial)
        if trial is None:
            return
        d = by_trial.get(int(trial))
        if d is None:
            return
        state.library_parent_id = ""
        state.library_place_op = ""
        state.library_leftover = ""
        if d.has_model:
            session._draw_impeller(d.stl_path, "lightsteelblue")
        else:
            plotter.clear_actors()
            if not d.extra.get("is_reference") and not d.extra.get("is_outline"):
                state.preview_msg = (
                    "No impeller.stl for this design — press Preview to rebuild, or Assess to re-score."
                )
        o, p = d.objectives, d.params
        state.selected_trial = int(trial)
        if d.extra.get("is_outline"):
            state.info_lines = [
                "Outline copy — hub 26 mm plate, thinner front and back edges.",
                "Print this next to the Noctua. Line the two up on the leading edge.",
                "Use Load Stock / Reference for the older Stock blade.",
            ]
            session._init_editor(p)
            session._set_baseline()
            state.fan_subtab = "design"
            state.preview_msg = "Outline copy loaded. Press Preview geometry, then Export STL."
            try:
                state.flush()
                ctrl.view_update()
            except Exception as exc:  # noqa: BLE001
                log_caught(_log, "view_update (outline select)", exc, level=logging.DEBUG)
            return
        if d.extra.get("is_reference"):
            state.info_lines = [
                f"Published free {o['cfm_free']:.1f} CFM   ·   hose-est load {o['cfm_load']:.1f} CFM",
                STOCK_RECIPE_GAP,
            ]
            session._init_editor(p)
            session._set_baseline()
            state.preview_msg = "Reference stock loaded. Preview geometry, or Assess to run CFD."
            if not (state.preview_busy or state.assess_busy):
                _show_stock_preview(str(state.fan_model or "a12x25"), session.active_spec())
            try:
                ctrl.view_update()
            except Exception as exc:  # noqa: BLE001
                log_caught(_log, "view_update (reference select)", exc, level=logging.DEBUG)
            return
        state.info_lines = [
            f"Trial {d.trial}   {d.extra.get('n_blades')} blades" + ("   ★ Pareto" if d.is_pareto else ""),
            f"CFM free {o['cfm_free']:.1f}   CFM load {o['cfm_load']:.1f}"
            f"   efficiency {o['efficiency']:.1f}%",
            f"stagger r/m/t {p.get('stagger_root',0):.0f}/{p.get('stagger_mid',0):.0f}"
            f"/{p.get('stagger_tip',0):.0f}   camber {p.get('max_camber',0):.3f}",
            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
            f"/{p.get('sweep_tip',0):.1f}",
        ]
        rpm = d.extra.get("actual_rpm", 0)
        spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
        if rpm and rpm < spec.rpm * 0.995:
            state.info_lines.append(
                f"⚙ motor-limited: runs at {rpm:.0f} RPM "
                f"({100*rpm/spec.rpm:.0f}% of {spec.rpm:.0f}) — flow already derated"
            )
        if d.extra.get("over_spec"):
            state.info_lines.append("⚠ OVER-SPEC: " + "; ".join(d.extra["over_spec"]))
        cap = score_caption(d.extra)
        if cap:
            state.info_lines.append(cap)
        note = shape_note(p)
        if note:
            state.info_lines.append(note)
        if d.extra.get("preset"):
            state.assess_preset = d.extra["preset"]
        state.assess_refine_op = bool(d.extra.get("refine_op"))
        state.assess_wall_ks = float(d.extra.get("wall_ks_mm") or 0) > 0
        session._init_editor(p)
        session._set_baseline()
        if d.extra.get("cfd_stale"):
            parent_id = d.extra.get("parent_id") or ""
            op = d.extra.get("place_op") or ""
            if parent_id:  # placed onto a hub — geometry moved, CFD not yet re-run
                state.info_lines.append("⧗ CFD stale — press Assess to score this hub.")
                state.info_lines.append(f"↳ placed from {parent_id}" + (f" ({op})" if op else ""))
                state.preview_msg = "Placed onto this hub. CFD is stale until you press Assess."
            else:  # scored by an older solver generation — numbers not comparable
                state.info_lines.append(
                    "⧗ CFD stale — scored by an older solver; CFM/efficiency unreliable. "
                    "Press Assess to re-score.")
                state.preview_msg = (
                    "This design was scored by an older CFD solver (pre-2026-09-18 tail-mean + "
                    "adaptive-mesh fix). Its numbers are unreliable — press Assess to re-score.")
        elif d.has_model:
            state.preview_msg = "Edit the sliders below, then press Preview geometry."
        # else: missing-STL preview_msg already set above
        session._schedule_airflow(d)
        session._schedule_flow_report(d)
        session._schedule_viz_overlay(d)
        try:
            ctrl.view_update()
        except Exception as exc:  # noqa: BLE001
            log_caught(_log, "view_update (select)", exc, level=logging.DEBUG)

    @state.change("selected_trial")
    def _on_dropdown(selected_trial=None, **_):
        select(selected_trial)

    def _mf(v):
        try:
            return float(v) if v not in (None, "", "None") else None
        except (TypeError, ValueError):
            return None

    def save_measurement():
        tid = state.selected_trial
        d = by_trial.get(int(tid)) if tid is not None else None
        if d is None:
            state.meas_msg = "⚠ Select a design first (click a point or use the dropdown)."
            state.flush()
            return
        if _mf(state.meas_cfm) is None and _mf(state.meas_static) is None and _mf(state.meas_noise) is None:
            state.meas_msg = "⚠ Enter at least one measured value (CFM / static Pa / dB(A))."
            state.flush()
            return
        run = d.extra.get("source_run") or run_dir.name
        design_id = make_design_id(run, d.trial)
        sim = {
            "cfm_free": d.objectives.get("cfm_free"),
            "cfm_load": d.objectives.get("cfm_load"),
            "efficiency": d.objectives.get("efficiency"),
            "actual_rpm": d.extra.get("actual_rpm"),
        }
        rpm = _mf(state.meas_rpm) or d.extra.get("actual_rpm") or session.active_spec().rpm
        pt = MeasuredPoint(
            rpm=float(rpm),
            cfm=_mf(state.meas_cfm),
            static_pressure_pa=_mf(state.meas_static),
            noise_dba=_mf(state.meas_noise),
            source=state.meas_instrument or "",
        )
        rec = record_measurement(
            design_id,
            pt,
            run=run,
            trial=d.trial,
            stl_path=str(d.stl_path) if d.has_model else "",
            material=(state.meas_material or session.active_spec().material),
            print_type=state.meas_print_type or "",
            weight_g=_mf(state.meas_weight),
            sim=sim,
            instrument=state.meas_instrument,
            notes=state.meas_notes,
        )
        last = sim_vs_real(rec)[-1]
        parts = []
        if "cfm" in last:
            parts.append(
                f"CFM {last['cfm']['measured']:.1f} vs sim free {last['cfm']['sim']:.1f} "
                f"(sim over-reads {last['cfm']['pct_error']:+.0f}%)"
            )
        if "noise_dba" in last:
            parts.append(
                f"noise {last['noise_dba']['measured']:.1f} dBA "
                f"(Δ{last['noise_dba']['delta_db']:+.1f} vs sim)"
            )
        state.meas_msg = (
            f"✓ Saved to validation/measurements/ for {design_id} "
            f"({len(rec.measured)} point(s)). "
            + "  ".join(parts)
        )
        state.flush()

    def show_store_calibration():
        """Show aggregate sim→reality factors from validation/measurements/ in meas_msg."""
        cal = calibration_from_store()
        if cal.n_points == 0:
            state.meas_msg = (
                "Store calibration: no measured points yet "
                "(save a measurement first, or log CSV via scripts/rig_logger.py)."
            )
        else:
            def _fmt(v, kind="factor"):
                if v is None:
                    return "—"
                return f"{v:+.2f} dB" if kind == "offset" else f"{v:.3f}"

            state.meas_msg = (
                f"Store calibration ({cal.n_points} point(s)): "
                f"cfm×{_fmt(cal.cfm)}  "
                f"static×{_fmt(cal.static_pressure)}  "
                f"noise {_fmt(cal.noise_dba_offset, 'offset')}  "
                f"(reality = factor × sim; dB is additive offset)."
            )
        state.flush()

    def on_plotly_click(trial=None):
        if isinstance(trial, (list, tuple)):
            trial = trial[0] if trial else None
        if trial is None:
            return
        if trial == "stock":
            load_stock_reference()
            return
        try:
            state.selected_trial = int(trial)
        except (TypeError, ValueError):
            return
        state.flush()

    def _show_stock_preview(key: str, spec) -> None:
        """Draw the (cached) parametric Stock mesh + schematic arrows for the current editor flat.

        Shared by the startup Stock load and Reset / re-select of the Reference, which used to
        clear the 3-D view and leave empty axes (the Reference has no Assess mesh; §23.16).
        """
        from fansim.cockpit.stock_cache import (
            stock_cache_hit,
            stock_cache_paths,
            write_stock_cache_meta,
        )

        flat_s, feat_s = session.edit_flat(), session.edit_features()
        cache_stl, _cache_meta = stock_cache_paths(key)

        def _ensure_stock_preview():
            hit = stock_cache_hit(key, flat_s, preview=True)
            if hit is not None:
                return hit
            from fansim.geometry.isolated import build_stl_isolated

            cache_stl.parent.mkdir(parents=True, exist_ok=True)
            # Dense non-fused mesh for gold ✕ (full n_span — LE isn't a 10-section polyline).
            build_stl_isolated(
                flat_s, feat_s, cache_stl, timeout=300.0, preview=True, preview_dense=True)
            write_stock_cache_meta(key, flat_s, preview=True)
            return cache_stl

        async def task():
            state.preview_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="Stock preview",
                msg_attr="preview_msg",
                busy_attr="preview_busy",
                note="cached parametric mesh" if stock_cache_hit(key, flat_s, preview=True) else "building Stock cache once",
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                path = await loop.run_in_executor(None, _ensure_stock_preview)
                session._draw(path, "gold")
                from fansim.cfd.glyphs import schematic_axial_flow_cloud

                hub_r = float(flat_s.get("hub_radius") or 21.5)
                tip_r = float(flat_s.get("tip_radius") or (session.active_spec().tip_dia_mm[1] / 2.0 - 0.5))
                z_span = float(flat_s.get("hub_height") or 22.0)
                render_state["glyph_cloud"] = schematic_axial_flow_cloud(
                    hub_radius_mm=hub_r,
                    tip_radius_mm=tip_r,
                    z_span_mm=max(z_span, 20.0),
                )
                state.glyph_caption = (
                    "Schematic -Z annulus flow (stock has no CFD — Assess for real arrows; "
                    "hub/motor core is blocked)"
                )
                session._rebuild_glyph_arrows()
                session._apply_render(reset=False)
                cached = stock_cache_hit(key, flat_s, preview=True) is not None
                state.preview_msg = (
                    f"✓ Stock reference loaded ({spec.name})"
                    + (" — cached mesh." if cached else " — cached for next click.")
                    + " Gold = parametric Stock; published CFM is the ✕, not this mesh's CFD."
                )
            except Exception as exc:  # noqa: BLE001
                state.preview_msg = f"⚠ Stock preview failed: {exc}"
            finally:
                state.preview_busy = False
                ticker.cancel()
                try:
                    state.flush()
                    ctrl.view_update()
                except Exception as exc:  # noqa: BLE001
                    log_caught(_log, "view_update (stock preview)", exc, level=logging.DEBUG)

        fan_runtime.asynchronous.create_task(task())

    def load_stock_reference():
        if state.preview_busy or state.assess_busy:
            return
        key = str(state.fan_model or "a12x25")
        try:
            flat = stock_blade_flat(key)
        except KeyError:
            state.preview_msg = (
                f"⚠ No parametric stock geometry for '{key}'. "
                "Switch Fan model to a12x25 (Noctua) to load the reference blade."
            )
            state.flush()
            return
        except FileNotFoundError as exc:
            state.preview_msg = f"⚠ Stock geometry file missing: {exc}"
            state.flush()
            return

        from fansim.cockpit.placement import fit_envelope

        spec = session.active_spec()
        # Bake frame/mount fit so gold ✕ lands inside the housing (tip gap 0.5 mm).
        fitted = fit_envelope(flat, spec, features=Features())
        flat = fitted.flat
        load_pa, hose = assess_load(str(state.assess_preset or "case"))
        pub = published_scatter_point(spec, load_pa)
        session._init_editor(flat, Features())
        session._set_baseline()      # fresh Stock = unedited (was: compared against the previous design)
        state.selected_trial = None
        state.fan_subtab = "design"
        fit_note = ""
        if fitted.changes:
            bits = ", ".join(f"{c.field}→{c.after:g}" for c in fitted.changes[:4])
            fit_note = f" Frame-fit applied ({bits})."
        state.info_lines = [
            f"Stock reference — {spec.name} (parametric, not OEM CAD)",
            (
                f"Published free {pub['cfm_free']:.1f} CFM · hose-est load "
                f"{pub['cfm_load']:.1f} CFM ({hose})"
                if pub
                else "No published CFM on this fan model."
            ),
            "Sliders = Stock recipe (frame-fitted). Edit then Preview / Assess for CFD ◆."
            + fit_note,
            STOCK_RECIPE_GAP,
        ]
        state.preview_msg = "Loading stock 3-D preview…"
        state.stale_msg = (
            "Stock reference loaded — geometry is a parametric stand-in for the real fan. "
            "Edit freely; re-Assess after changes for CFD numbers."
        )
        session._clear_airflow("Stock reference — no CFD case (Assess to generate airflow viz).")
        state.glyph_caption = "Loading schematic flow arrows…"
        state.flush()

        _show_stock_preview(key, spec)

    session.select = select
    session.save_measurement = save_measurement
    session.show_store_calibration = show_store_calibration
    session.on_plotly_click = on_plotly_click
    session.load_stock_reference = load_stock_reference
