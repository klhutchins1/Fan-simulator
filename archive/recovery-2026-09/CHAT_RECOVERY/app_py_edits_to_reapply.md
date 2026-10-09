<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# app.py — edits captured from Claude Code transcripts

app.py grew to ~2377 lines under Cursor; my transcripts hold only a 990-line (Aug 30) full copy,
so recover the FULL app.py from Cursor's chat, then re-apply the edits below (newest last) that my
later sessions made on top of Cursor's version. Each block is an exact find/replace.

================================================================================
## EDIT 1  @ 2026-08-26T21:50:38

--- FIND ---
def scatter_figure(designs) -> dict:
--- REPLACE WITH ---
def scatter_figure(designs) -> go.Figure:

================================================================================
## EDIT 2  @ 2026-08-26T21:50:41

--- FIND ---
        title="Design space (★ = Pareto front)", height=560,
        template="plotly_white",
    )
    return fig.to_dict()
--- REPLACE WITH ---
        title="Design space (★ = Pareto front)", height=560,
        template="plotly_white",
    )
    return fig

================================================================================
## EDIT 3  @ 2026-08-26T21:50:45

--- FIND ---
    state.selected_trial = None
    state.info_lines = ["Select a design (click a point or use the dropdown)."]
    state.figure = scatter_figure(designs)
--- REPLACE WITH ---
    state.selected_trial = None
    state.info_lines = ["Select a design (click a point or use the dropdown)."]
    figure = scatter_figure(designs)

================================================================================
## EDIT 4  @ 2026-08-26T21:50:49

--- FIND ---
                        plotly_widgets.Figure(
                            figure=("figure",),
                            click=(on_plotly_click, "[$event]"),
                            style="width:100%;",
                        )
--- REPLACE WITH ---
                        plotly_widgets.Figure(
                            figure=figure,
                            click=(on_plotly_click, "[$event]"),
                            style="width:100%;",
                        )

================================================================================
## EDIT 5  @ 2026-08-26T21:53:37

--- FIND ---
        state.selected_trial = int(trial)
        state.info_lines = [
            f"Trial {d.trial}   {d.extra.get('n_blades')} blades"
            + ("   ★ Pareto" if d.is_pareto else ""),
            f"CFM free {o['cfm_free']:.1f}   CFM load {o['cfm_load']:.1f}"
            f"   efficiency {o['efficiency']:.1f}%",
            f"stagger r/m/t {p.get('stagger_root',0):.0f}/{p.get('stagger_mid',0):.0f}"
            f"/{p.get('stagger_tip',0):.0f}   camber {p.get('max_camber',0):.3f}",
            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
            f"/{p.get('sweep_tip',0):.1f}",
        ]
        if hasattr(ctrl, "view_update"):
            ctrl.view_update()
--- REPLACE WITH ---
        state.selected_trial = int(trial)
        state.info_lines = [
            f"Trial {d.trial}   {d.extra.get('n_blades')} blades"
            + ("   ★ Pareto" if d.is_pareto else ""),
            f"CFM free {o['cfm_free']:.1f}   CFM load {o['cfm_load']:.1f}"
            f"   efficiency {o['efficiency']:.1f}%",
            f"stagger r/m/t {p.get('stagger_root',0):.0f}/{p.get('stagger_mid',0):.0f}"
            f"/{p.get('stagger_tip',0):.0f}   camber {p.get('max_camber',0):.3f}",
            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
            f"/{p.get('sweep_tip',0):.1f}",
        ]
        try:
            ctrl.view_update()
        except Exception:
            pass

================================================================================
## EDIT 6  @ 2026-08-26T21:53:40

--- FIND ---
                        with v3.VCard(style="height:520px;"):
                            plotter_ui(plotter)
    return server
--- REPLACE WITH ---
                        with v3.VCard(style="height:520px;"):
                            view = plotter_ui(plotter)
    ctrl.view_update = view.update
    return server

================================================================================
## EDIT 7  @ 2026-08-26T21:55:43

--- FIND ---
    def select(trial: int | None):
        if trial is None:
            return
        d = by_trial.get(int(trial))
        if d is None:
            return
--- REPLACE WITH ---
    def select(trial: int | None):
        print(f"[cockpit] select({trial!r})", flush=True)
        if trial is None:
            return
        d = by_trial.get(int(trial))
        if d is None:
            return

================================================================================
## EDIT 8  @ 2026-08-26T21:55:48

--- FIND ---
                            v3.VSelect(
                                label="Design",
                                v_model=("selected_trial",),
                                items=("trial_items",),
                                density="compact", variant="outlined",
                                hide_details=True,
                            )
--- REPLACE WITH ---
                            v3.VSelect(
                                label="Design",
                                v_model=("selected_trial",),
                                items=("trial_items",),
                                density="compact", variant="outlined",
                                hide_details=True,
                                update_modelValue=(select, "[$event]"),
                            )

================================================================================
## EDIT 9  @ 2026-08-26T22:04:23

--- FIND ---
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
import pyvista as pv
from pyvista.trame.ui import plotter_ui
from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import html
from trame.widgets import plotly as plotly_widgets
from trame.widgets import vuetify3 as v3

from fansim.cockpit.data import feasible_designs, load_designs
--- REPLACE WITH ---
from __future__ import annotations

import tempfile
from pathlib import Path

import plotly.graph_objects as go
import pyvista as pv
from pyvista.trame.ui import plotter_ui
from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import html
from trame.widgets import plotly as plotly_widgets
from trame.widgets import vuetify3 as v3

from fansim.cockpit.data import feasible_designs, load_designs
from fansim.geometry import build_impeller, export_stl
from fansim.geometry.features import Features
from fansim.manufacturability import check_printability
from fansim.optimize.search_space import blade_from_flat

================================================================================
## EDIT 10  @ 2026-08-26T22:04:39

--- FIND ---
    state.selected_trial = None
    state.info_lines = ["Select a design (click a point or use the dropdown)."]
    figure = scatter_figure(designs)

    def select(trial: int | None):
--- REPLACE WITH ---
    state.selected_trial = None
    state.info_lines = ["Select a design (click a point or use the dropdown)."]
    state.preview_msg = "Select a design, then edit and press Preview geometry."
    figure = scatter_figure(designs)

    preview_stl = Path(tempfile.gettempdir()) / "fansim_cockpit_preview.stl"

    def _init_editor(p: dict, feat: Features | None = None):
        """Load the parameter-editor sliders from a design's params + features."""
        feat = feat or Features()
        state.e_n_blades = int(p.get("n_blades", 7))
        state.e_stagger_root = float(p.get("stagger_root", 50.0))
        state.e_stagger_mid = float(p.get("stagger_mid", 40.0))
        state.e_stagger_tip = float(p.get("stagger_tip", 30.0))
        state.e_chord_root = float(p.get("chord_root", 20.0))
        state.e_chord_mid = float(p.get("chord_mid", 22.0))
        state.e_chord_tip = float(p.get("chord_tip", 18.0))
        state.e_camber = float(p.get("max_camber", 0.02))
        state.e_sweep_mid = float(p.get("sweep_mid", 2.0))
        state.e_sweep_tip = float(p.get("sweep_tip", 6.0))
        state.e_tub_amp = feat.tubercle_amp
        state.e_tub_waves = feat.tubercle_waves
        state.e_ser_amp = feat.serration_amp
        state.e_ser_waves = feat.serration_waves
        state.e_dim_amp = feat.dimple_amp
        state.e_dim_rows = feat.dimple_rows
        state.e_dim_cols = feat.dimple_cols

    _init_editor({})

    def build_edit_params():
        flat = dict(
            n_blades=int(state.e_n_blades),
            stagger_root=state.e_stagger_root, stagger_mid=state.e_stagger_mid,
            stagger_tip=state.e_stagger_tip, chord_root=state.e_chord_root,
            chord_mid=state.e_chord_mid, chord_tip=state.e_chord_tip,
            sweep_mid=state.e_sweep_mid, sweep_tip=state.e_sweep_tip,
            max_camber=state.e_camber,
        )
        feat = Features(
            tubercle_amp=state.e_tub_amp, tubercle_waves=int(state.e_tub_waves),
            serration_amp=state.e_ser_amp, serration_waves=int(state.e_ser_waves),
            dimple_amp=state.e_dim_amp, dimple_rows=int(state.e_dim_rows),
            dimple_cols=int(state.e_dim_cols),
        )
        return blade_from_flat(flat, feat)

    def do_preview():
        params = build_edit_params()
        printable = check_printability(params)
        if not printable.printable:
            state.preview_msg = f"⚠ Not printable: {printable.reason}"
            return
        state.preview_msg = "Building preview geometry…"
        try:
            export_stl(build_impeller(params), preview_stl)
        except Exception as exc:  # loft / boolean failure on an extreme edit
            state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__}"
            return
        plotter.clear_actors()
        plotter.add_mesh(pv.read(str(preview_stl)), color="darkorange",
                         smooth_shading=True)
        plotter.reset_camera()
        feats = "features ON" if params.features.active else "smooth"
        state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                             f"camber {state.e_camber:.3f}, {feats} — geometry only, "
                             f"not yet evaluated. Use 'Assess' to run CFD.")
        try:
            ctrl.view_update()
        except Exception:
            pass

    def select(trial: int | None):

================================================================================
## EDIT 11  @ 2026-08-26T22:04:46

--- FIND ---
            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
            f"/{p.get('sweep_tip',0):.1f}",
        ]
        try:
            ctrl.view_update()
        except Exception:
            pass
--- REPLACE WITH ---
            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
            f"/{p.get('sweep_tip',0):.1f}",
        ]
        _init_editor(p)  # load the editor sliders from the selected design
        state.preview_msg = "Edit the sliders below, then press Preview geometry."
        try:
            ctrl.view_update()
        except Exception:
            pass

================================================================================
## EDIT 12  @ 2026-08-26T22:05:10

--- FIND ---
                            html.Div(
                                "{{ line }}",
                                v_for="line in info_lines",
                                classes="text-body-2 mt-2",
                            )
                        with v3.VCard(style="height:520px;"):
                            view = plotter_ui(plotter)
    ctrl.view_update = view.update
    return server
--- REPLACE WITH ---
                            html.Div(
                                "{{ line }}",
                                v_for="line in info_lines",
                                classes="text-body-2 mt-2",
                            )
                        with v3.VCard(classes="mb-2 pa-3"):
                            html.Div("Modify design", classes="text-subtitle-2 mb-1")
                            with v3.VExpansionPanels(variant="accordion", multiple=True):
                                with v3.VExpansionPanel(title="Geometry"):
                                    with v3.VExpansionPanelText():
                                        _slider("Blades", "e_n_blades", 5, 11, 1)
                                        _slider("Camber (curve)", "e_camber", 0.0, 0.06, 0.005)
                                        _slider("Stagger root", "e_stagger_root", 15, 70, 1)
                                        _slider("Stagger mid", "e_stagger_mid", 15, 70, 1)
                                        _slider("Stagger tip", "e_stagger_tip", 15, 70, 1)
                                        _slider("Chord root", "e_chord_root", 10, 28, 0.5)
                                        _slider("Chord mid", "e_chord_mid", 10, 28, 0.5)
                                        _slider("Chord tip", "e_chord_tip", 10, 28, 0.5)
                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)
                                with v3.VExpansionPanel(title="Features (bio-inspired)"):
                                    with v3.VExpansionPanelText():
                                        _slider("Tubercle amp", "e_tub_amp", 0.0, 0.10, 0.01)
                                        _slider("Tubercle waves", "e_tub_waves", 0, 8, 1)
                                        _slider("Serration amp", "e_ser_amp", 0.0, 0.06, 0.005)
                                        _slider("Serration teeth", "e_ser_waves", 0, 12, 1)
                                        _slider("Dimple depth", "e_dim_amp", 0.0, 0.35, 0.05)
                                        _slider("Dimple rows", "e_dim_rows", 0, 6, 1)
                                        _slider("Dimple cols", "e_dim_cols", 0, 6, 1)
                            with v3.VRow(no_gutters=True, classes="mt-2"):
                                v3.VBtn("Preview geometry", color="primary", size="small",
                                        click=do_preview, classes="mr-2")
                                v3.VBtn("Reset", size="small", variant="tonal",
                                        click=(select, "[selected_trial]"))
                            html.Div("{{ preview_msg }}", classes="text-caption mt-2")
                        with v3.VCard(style="height:460px;"):
                            view = plotter_ui(plotter)
    ctrl.view_update = view.update
    return server

================================================================================
## EDIT 13  @ 2026-08-26T22:05:20

--- FIND ---
pv.OFF_SCREEN = True


def scatter_figure(designs) -> go.Figure:
--- REPLACE WITH ---
pv.OFF_SCREEN = True


def _slider(label: str, model: str, mn: float, mx: float, step: float):
    """Compact labelled slider bound to a state variable (used in the editor panel)."""
    v3.VSlider(
        v_model=(model,), min=mn, max=mx, step=step, label=label,
        thumb_label=True, density="compact", hide_details=True, classes="mb-1",
    )


def scatter_figure(designs) -> go.Figure:

================================================================================
## EDIT 14  @ 2026-08-26T22:14:17

--- FIND ---
from __future__ import annotations

import tempfile
from pathlib import Path

import plotly.graph_objects as go
import pyvista as pv
from pyvista.trame.ui import plotter_ui
from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import html
from trame.widgets import plotly as plotly_widgets
from trame.widgets import vuetify3 as v3

from fansim.cockpit.data import feasible_designs, load_designs
from fansim.geometry import build_impeller, export_stl
from fansim.geometry.features import Features
from fansim.manufacturability import check_printability
from fansim.optimize.search_space import blade_from_flat
--- REPLACE WITH ---
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import plotly.graph_objects as go
import pyvista as pv
from pyvista.trame.ui import plotter_ui
from trame.app import asynchronous, get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import html
from trame.widgets import plotly as plotly_widgets
from trame.widgets import vuetify3 as v3

from fansim.cockpit.data import Design, feasible_designs, load_designs
from fansim.geometry import build_impeller, export_stl
from fansim.geometry.features import Features
from fansim.manufacturability import check_printability
from fansim.optimize.objectives import evaluate_candidate
from fansim.optimize.search_space import blade_from_flat

================================================================================
## EDIT 15  @ 2026-08-26T22:14:31

--- FIND ---
def scatter_figure(designs) -> go.Figure:
    xs = [d.objectives["cfm_free"] for d in designs]
    ys = [d.objectives["cfm_load"] for d in designs]
    cs = [d.objectives["efficiency"] for d in designs]
    trials = [d.trial for d in designs]
    sizes = [22 if d.is_pareto else 13 for d in designs]
    symbols = ["star" if d.is_pareto else "circle" for d in designs]
    fig = go.Figure(
        go.Scatter(
            x=xs, y=ys, mode="markers",
            marker=dict(size=sizes, symbol=symbols, color=cs, colorscale="Viridis",
                        showscale=True, colorbar=dict(title="eff %"),
                        line=dict(width=1, color="rgba(0,0,0,0.4)")),
            customdata=trials,
            hovertemplate="trial %{customdata}<br>free %{x:.1f} CFM"
                          "<br>load %{y:.1f} CFM<extra></extra>",
        )
    )
    fig.update_layout(
        margin=dict(l=50, r=10, t=30, b=45),
        xaxis_title="CFM at free delivery", yaxis_title="CFM at load",
        title="Design space (★ = Pareto front)", height=560,
        template="plotly_white",
    )
    return fig
--- REPLACE WITH ---
def scatter_figure(study_designs, user_designs=()) -> go.Figure:
    def trace(designs, name, symbol_pareto, symbol_plain, line):
        return go.Scatter(
            x=[d.objectives["cfm_free"] for d in designs],
            y=[d.objectives["cfm_load"] for d in designs],
            mode="markers", name=name,
            marker=dict(
                size=[22 if d.is_pareto else 14 for d in designs],
                symbol=[symbol_pareto if d.is_pareto else symbol_plain for d in designs],
                color=[d.objectives["efficiency"] for d in designs],
                colorscale="Viridis", showscale=True, colorbar=dict(title="eff %"),
                cmin=0, cmax=22, line=line,
            ),
            customdata=[d.trial for d in designs],
            hovertemplate="#%{customdata}<br>free %{x:.1f} CFM"
                          "<br>load %{y:.1f} CFM<extra>" + name + "</extra>",
        )

    fig = go.Figure()
    fig.add_trace(trace(study_designs, "study", "star", "circle",
                        dict(width=1, color="rgba(0,0,0,0.4)")))
    if user_designs:
        fig.add_trace(trace(list(user_designs), "your runs", "diamond", "diamond",
                            dict(width=2, color="crimson")))
    fig.update_layout(
        margin=dict(l=50, r=10, t=30, b=45),
        xaxis_title="CFM at free delivery", yaxis_title="CFM at load",
        title="Design space (★ Pareto, ◆ your runs)", height=560,
        template="plotly_white", showlegend=False,
    )
    return fig

================================================================================
## EDIT 16  @ 2026-08-26T22:14:42

--- FIND ---
    designs = feasible_designs(load_designs(run_dir, study_name))
    by_trial = {d.trial: d for d in designs}
    if not designs:
        raise SystemExit(f"No feasible designs found in {run_dir}")

    server = get_server(client_type="vue3")
    state, ctrl = server.state, server.controller
--- REPLACE WITH ---
    run_dir = Path(run_dir)
    study_designs = feasible_designs(load_designs(run_dir, study_name))
    user_designs: list[Design] = []
    by_trial = {d.trial: d for d in study_designs}
    if not study_designs:
        raise SystemExit(f"No feasible designs found in {run_dir}")
    assess_dir = run_dir / "cockpit_assess"
    next_id = [9000]  # ids for user-assessed designs (distinct from study trials)

    server = get_server(client_type="vue3")
    state, ctrl = server.state, server.controller

================================================================================
## EDIT 17  @ 2026-08-26T22:14:52

--- FIND ---
    state.trial_items = [
        {"title": f"trial {d.trial}"
                  + ("  ★" if d.is_pareto else ""), "value": d.trial}
        for d in sorted(designs, key=lambda d: -d.objectives["cfm_load"])
    ]
    state.selected_trial = None
    state.info_lines = ["Select a design (click a point or use the dropdown)."]
    state.preview_msg = "Select a design, then edit and press Preview geometry."
    figure = scatter_figure(designs)

    preview_stl = Path(tempfile.gettempdir()) / "fansim_cockpit_preview.stl"
--- REPLACE WITH ---
    def _label(d):
        tag = "  ★" if d.is_pareto else ("  ◆" if d.trial >= 9000 else "")
        return {"title": f"#{d.trial}{tag}", "value": d.trial}

    def refresh_items():
        alld = sorted(study_designs + user_designs,
                      key=lambda d: -d.objectives["cfm_load"])
        state.trial_items = [_label(d) for d in alld]

    state.selected_trial = None
    state.info_lines = ["Select a design (click a point or use the dropdown)."]
    state.preview_msg = "Select a design, then edit and press Preview geometry."
    state.assess_msg = ""
    state.assess_busy = False
    state.sweep_param = "max_camber"
    state.sweep_steps = 3
    refresh_items()

    preview_stl = Path(tempfile.gettempdir()) / "fansim_cockpit_preview.stl"

    def refresh_figure():
        fig = scatter_figure(study_designs, user_designs)
        if hasattr(ctrl, "figure_update"):
            ctrl.figure_update(fig)

================================================================================
## EDIT 18  @ 2026-08-26T22:15:11

--- FIND ---
    def build_edit_params():
        flat = dict(
            n_blades=int(state.e_n_blades),
            stagger_root=state.e_stagger_root, stagger_mid=state.e_stagger_mid,
            stagger_tip=state.e_stagger_tip, chord_root=state.e_chord_root,
            chord_mid=state.e_chord_mid, chord_tip=state.e_chord_tip,
            sweep_mid=state.e_sweep_mid, sweep_tip=state.e_sweep_tip,
            max_camber=state.e_camber,
        )
        feat = Features(
            tubercle_amp=state.e_tub_amp, tubercle_waves=int(state.e_tub_waves),
            serration_amp=state.e_ser_amp, serration_waves=int(state.e_ser_waves),
            dimple_amp=state.e_dim_amp, dimple_rows=int(state.e_dim_rows),
            dimple_cols=int(state.e_dim_cols),
        )
        return blade_from_flat(flat, feat)
--- REPLACE WITH ---
    def edit_flat() -> dict:
        return dict(
            n_blades=int(state.e_n_blades),
            stagger_root=state.e_stagger_root, stagger_mid=state.e_stagger_mid,
            stagger_tip=state.e_stagger_tip, chord_root=state.e_chord_root,
            chord_mid=state.e_chord_mid, chord_tip=state.e_chord_tip,
            sweep_mid=state.e_sweep_mid, sweep_tip=state.e_sweep_tip,
            max_camber=state.e_camber,
        )

    def edit_features() -> Features:
        return Features(
            tubercle_amp=state.e_tub_amp, tubercle_waves=int(state.e_tub_waves),
            serration_amp=state.e_ser_amp, serration_waves=int(state.e_ser_waves),
            dimple_amp=state.e_dim_amp, dimple_rows=int(state.e_dim_rows),
            dimple_cols=int(state.e_dim_cols),
        )

    def build_edit_params():
        return blade_from_flat(edit_flat(), edit_features())

================================================================================
## EDIT 19  @ 2026-08-26T22:16:41

--- FIND ---
        state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                             f"camber {state.e_camber:.3f}, {feats} — geometry only, "
                             f"not yet evaluated. Use 'Assess' to run CFD.")
        try:
            ctrl.view_update()
        except Exception:
            pass

    def select(trial: int | None):
--- REPLACE WITH ---
        state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                             f"camber {state.e_camber:.3f}, {feats} — geometry only, "
                             f"not yet evaluated. Use 'Assess' to run CFD.")
        try:
            ctrl.view_update()
        except Exception:
            pass

    # --- Assess (run CFD) + Sweep (regression over one parameter) ---
    SWEEP_OPTIONS = [
        ("camber", "flat", "max_camber", 0.0, 0.06),
        ("blades", "flat", "n_blades", 5.0, 11.0),
        ("stagger tip", "flat", "stagger_tip", 20.0, 50.0),
        ("sweep tip", "flat", "sweep_tip", 0.0, 15.0),
        ("tubercle amp", "tub", "tubercle_amp", 0.0, 0.10),
        ("serration amp", "ser", "serration_amp", 0.0, 0.06),
        ("dimple depth", "dim", "dimple_amp", 0.0, 0.35),
    ]
    state.sweep_items = [o[0] for o in SWEEP_OPTIONS]

    def _feat_dict() -> dict:
        f = edit_features()
        return dict(tubercle_amp=f.tubercle_amp, tubercle_waves=f.tubercle_waves,
                    serration_amp=f.serration_amp, serration_waves=f.serration_waves,
                    dimple_amp=f.dimple_amp, dimple_rows=f.dimple_rows,
                    dimple_cols=f.dimple_cols)

    def _blocking_eval(params, workdir):
        return evaluate_candidate(params, workdir, procs=8, base_cell=0.006, iters=500)

    async def _assess(params, flat, label):
        tid = next_id[0]
        next_id[0] += 1
        workdir = assess_dir / f"design_{tid}"
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _blocking_eval, params, workdir)
        if not result.feasible:
            state.assess_msg = f"{label}: rejected — {result.reason}"
            state.flush()
            return None
        stl = workdir / "impeller.stl"
        d = Design(
            trial=tid, params=dict(flat),
            objectives={"cfm_free": result.cfm_free, "cfm_load": result.cfm_load,
                        "efficiency": result.efficiency},
            feasible=True, is_pareto=False,
            stl_path=stl if stl.exists() else None,
            extra={"n_blades": params.n_blades, "source": "user"},
        )
        user_designs.append(d)
        by_trial[tid] = d
        refresh_items()
        refresh_figure()
        state.flush()
        return d

    def on_assess():
        if state.assess_busy:
            return
        params, flat = build_edit_params(), edit_flat()

        async def task():
            state.assess_busy = True
            state.assess_msg = "Running CFD on your design… (~4 min)"
            state.flush()
            d = await _assess(params, flat, "Assess")
            if d:
                o = d.objectives
                state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
                                    f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
                                    f"  (added to plot)")
                state.selected_trial = d.trial
            state.assess_busy = False
            state.flush()

        asynchronous.create_task(task())

    def on_sweep():
        if state.assess_busy:
            return
        import numpy as np

        opt = next((o for o in SWEEP_OPTIONS if o[0] == state.sweep_param), SWEEP_OPTIONS[0])
        label, kind, field, mn, mx = opt
        base_flat, base_feat = edit_flat(), _feat_dict()
        steps = max(2, int(state.sweep_steps))
        raw = list(np.linspace(mn, mx, steps))
        values = sorted(set(int(round(v)) for v in raw)) if field == "n_blades" else raw

        async def task():
            state.assess_busy = True
            done = 0
            for i, val in enumerate(values):
                flat, feat = dict(base_flat), dict(base_feat)
                if kind == "flat":
                    flat[field] = int(val) if field == "n_blades" else float(val)
                else:
                    feat[field] = float(val)
                    if kind == "tub" and feat["tubercle_waves"] == 0:
                        feat["tubercle_waves"] = 6
                    if kind == "ser" and feat["serration_waves"] == 0:
                        feat["serration_waves"] = 8
                    if kind == "dim":
                        feat["dimple_rows"] = feat["dimple_rows"] or 5
                        feat["dimple_cols"] = feat["dimple_cols"] or 5
                params = blade_from_flat(flat, Features(**feat))
                state.assess_msg = f"Sweep {label} {i+1}/{len(values)} = {val:g}: running CFD…"
                state.flush()
                if not check_printability(params).printable:
                    continue
                if await _assess(params, flat, f"sweep {label}={val:g}"):
                    done += 1
            state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
            state.assess_busy = False
            state.flush()

        asynchronous.create_task(task())

    def select(trial: int | None):

================================================================================
## EDIT 20  @ 2026-08-26T22:16:49

--- FIND ---
                    with v3.VCol(cols=6, classes="pr-2"):
                        plotly_widgets.Figure(
                            figure=figure,
                            click=(on_plotly_click, "[$event]"),
                            style="width:100%;",
                        )
--- REPLACE WITH ---
                    with v3.VCol(cols=6, classes="pr-2"):
                        fig_widget = plotly_widgets.Figure(
                            figure=scatter_figure(study_designs, user_designs),
                            click=(on_plotly_click, "[$event]"),
                            style="width:100%;",
                        )

================================================================================
## EDIT 21  @ 2026-08-26T22:17:01

--- FIND ---
                            with v3.VRow(no_gutters=True, classes="mt-2"):
                                v3.VBtn("Preview geometry", color="primary", size="small",
                                        click=do_preview, classes="mr-2")
                                v3.VBtn("Reset", size="small", variant="tonal",
                                        click=(select, "[selected_trial]"))
                            html.Div("{{ preview_msg }}", classes="text-caption mt-2")
                        with v3.VCard(style="height:460px;"):
                            view = plotter_ui(plotter)
    ctrl.view_update = view.update
    return server
--- REPLACE WITH ---
                            with v3.VRow(no_gutters=True, classes="mt-2"):
                                v3.VBtn("Preview geometry", color="primary", size="small",
                                        click=do_preview, classes="mr-2",
                                        disabled=("assess_busy",))
                                v3.VBtn("Reset", size="small", variant="tonal",
                                        click=(select, "[selected_trial]"))
                            html.Div("{{ preview_msg }}", classes="text-caption mt-2")
                        with v3.VCard(classes="mb-2 pa-3"):
                            html.Div("Assess & sweep (runs CFD)",
                                     classes="text-subtitle-2 mb-1")
                            v3.VBtn("Assess this design", color="success", size="small",
                                    block=True, click=on_assess,
                                    loading=("assess_busy",), disabled=("assess_busy",))
                            with v3.VRow(no_gutters=True, classes="mt-2 align-center"):
                                with v3.VCol(cols=6, classes="pr-1"):
                                    v3.VSelect(label="Sweep", v_model=("sweep_param",),
                                               items=("sweep_items",), density="compact",
                                               variant="outlined", hide_details=True)
                                with v3.VCol(cols=3, classes="px-1"):
                                    v3.VTextField(label="steps", v_model=("sweep_steps",),
                                                  type="number", density="compact",
                                                  variant="outlined", hide_details=True)
                                with v3.VCol(cols=3, classes="pl-1"):
                                    v3.VBtn("Run", size="small", color="success",
                                            variant="tonal", click=on_sweep,
                                            disabled=("assess_busy",))
                            html.Div("{{ assess_msg }}", classes="text-caption mt-2")
                        with v3.VCard(style="height:420px;"):
                            view = plotter_ui(plotter)
    ctrl.view_update = view.update
    ctrl.figure_update = fig_widget.update
    return server

================================================================================
## EDIT 22  @ 2026-08-26T22:49:19

--- FIND ---
                                v3.VBtn("Preview geometry", color="primary", size="small",
                                        click=do_preview, classes="mr-2",
                                        disabled=("assess_busy",))
--- REPLACE WITH ---
                                v3.VBtn("Preview geometry", color="primary", size="small",
                                        click=(do_preview,), classes="mr-2",
                                        disabled=("assess_busy",))

================================================================================
## EDIT 23  @ 2026-08-26T22:49:24

--- FIND ---
                            v3.VBtn("Assess this design", color="success", size="small",
                                    block=True, click=on_assess,
                                    loading=("assess_busy",), disabled=("assess_busy",))
--- REPLACE WITH ---
                            v3.VBtn("Assess this design", color="success", size="small",
                                    block=True, click=(on_assess,),
                                    loading=("assess_busy",), disabled=("assess_busy",))

================================================================================
## EDIT 24  @ 2026-08-26T22:49:28

--- FIND ---
                                    v3.VBtn("Run", size="small", color="success",
                                            variant="tonal", click=on_sweep,
                                            disabled=("assess_busy",))
--- REPLACE WITH ---
                                    v3.VBtn("Run", size="small", color="success",
                                            variant="tonal", click=(on_sweep,),
                                            disabled=("assess_busy",))

================================================================================
## EDIT 25  @ 2026-08-27T01:03:22

--- FIND ---
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
--- REPLACE WITH ---
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path


def _quiet_connection_reset(server) -> None:
    """Silence the benign Windows proactor ConnectionResetError spam on client disconnect.

    On Windows, when a browser tab closes/navigates away, asyncio's ProactorEventLoop tries
    to shut down an already-closed socket and logs a full traceback. It is harmless (the
    server keeps running); we swallow ONLY ConnectionResetError and pass everything else to
    the default handler so real errors still surface.
    """
    def _ready(**_):
        try:
            loop = asyncio.get_running_loop()

            def handler(loop, context):
                if isinstance(context.get("exception"), ConnectionResetError):
                    return
                loop.default_exception_handler(context)

            loop.set_exception_handler(handler)
        except Exception:
            pass

    server.controller.on_server_ready.add(_ready)

================================================================================
## EDIT 26  @ 2026-08-27T01:03:28

--- FIND ---
    server = get_server(client_type="vue3")
    state, ctrl = server.state, server.controller
--- REPLACE WITH ---
    server = get_server(client_type="vue3")
    state, ctrl = server.state, server.controller
    _quiet_connection_reset(server)

================================================================================
## EDIT 27  @ 2026-08-27T14:13:13

--- FIND ---
    state.preview_msg = "Select a design, then edit and press Preview geometry."
    state.assess_msg = ""
    state.assess_busy = False
--- REPLACE WITH ---
    state.preview_msg = "Select a design, then edit and press Preview geometry."
    state.preview_busy = False
    state.assess_msg = ""
    state.assess_busy = False

================================================================================
## EDIT 28  @ 2026-08-27T14:13:23

--- FIND ---
        state.e_n_blades = int(p.get("n_blades", 7))
        state.e_stagger_root = float(p.get("stagger_root", 50.0))
        state.e_stagger_mid = float(p.get("stagger_mid", 40.0))
        state.e_stagger_tip = float(p.get("stagger_tip", 30.0))
        state.e_chord_root = float(p.get("chord_root", 20.0))
        state.e_chord_mid = float(p.get("chord_mid", 22.0))
        state.e_chord_tip = float(p.get("chord_tip", 18.0))
        state.e_camber = float(p.get("max_camber", 0.02))
        state.e_sweep_mid = float(p.get("sweep_mid", 2.0))
        state.e_sweep_tip = float(p.get("sweep_tip", 6.0))
--- REPLACE WITH ---
        state.e_n_blades = int(p.get("n_blades", 7))
        state.e_stagger_root = float(p.get("stagger_root", 26.0))
        state.e_stagger_mid = float(p.get("stagger_mid", 26.0))
        state.e_stagger_tip = float(p.get("stagger_tip", 22.0))
        state.e_chord_root = float(p.get("chord_root", 34.0))
        state.e_chord_mid = float(p.get("chord_mid", 44.0))
        state.e_chord_tip = float(p.get("chord_tip", 38.0))
        state.e_camber = float(p.get("max_camber", 0.05))
        state.e_sweep_mid = float(p.get("sweep_mid", 3.0))
        state.e_sweep_tip = float(p.get("sweep_tip", 5.0))
        state.e_lean_mid = float(p.get("lean_mid", 14.0))  # circumferential WRAP (deg)
        state.e_lean_tip = float(p.get("lean_tip", 26.0))

================================================================================
## EDIT 29  @ 2026-08-27T14:13:34

--- FIND ---
            sweep_mid=state.e_sweep_mid, sweep_tip=state.e_sweep_tip,
            max_camber=state.e_camber,
        )

    def edit_features() -> Features:
        return Features(
            tubercle_amp=state.e_tub_amp, tubercle_waves=int(state.e_tub_waves),
            serration_amp=state.e_ser_amp, serration_waves=int(state.e_ser_waves),
            dimple_amp=state.e_dim_amp, dimple_rows=int(state.e_dim_rows),
            dimple_cols=int(state.e_dim_cols),
        )
--- REPLACE WITH ---
            sweep_mid=state.e_sweep_mid, sweep_tip=state.e_sweep_tip,
            max_camber=state.e_camber,
            lean_mid=state.e_lean_mid, lean_tip=state.e_lean_tip,
        )

    def edit_features() -> Features:
        # A feature needs BOTH amplitude and a count to be visible; if the user raises only the
        # amplitude slider, auto-fill a sensible count so it actually shows up.
        tw = int(state.e_tub_waves) or (6 if state.e_tub_amp > 0 else 0)
        sw = int(state.e_ser_waves) or (8 if state.e_ser_amp > 0 else 0)
        dr = int(state.e_dim_rows) or (5 if state.e_dim_amp > 0 else 0)
        dc = int(state.e_dim_cols) or (5 if state.e_dim_amp > 0 else 0)
        return Features(
            tubercle_amp=state.e_tub_amp, tubercle_waves=tw,
            serration_amp=state.e_ser_amp, serration_waves=sw,
            dimple_amp=state.e_dim_amp, dimple_rows=dr, dimple_cols=dc,
        )

================================================================================
## EDIT 30  @ 2026-08-27T14:13:52

--- FIND ---
    def do_preview():
        params = build_edit_params()
        printable = check_printability(params)
        if not printable.printable:
            state.preview_msg = f"⚠ Not printable: {printable.reason}"
            return
        state.preview_msg = "Building preview geometry…"
        try:
            export_stl(build_impeller(params), preview_stl)
        except Exception as exc:  # loft / boolean failure on an extreme edit
            state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__}"
            return
        plotter.clear_actors()
        plotter.add_mesh(pv.read(str(preview_stl)), color="darkorange",
                         smooth_shading=True)
        plotter.reset_camera()
        feats = "features ON" if params.features.active else "smooth"
        state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                             f"camber {state.e_camber:.3f}, {feats} — geometry only, "
                             f"not yet evaluated. Use 'Assess' to run CFD.")
        try:
            ctrl.view_update()
        except Exception:
            pass
--- REPLACE WITH ---
    def _build_preview_stl(params):
        """Blocking geometry build (runs off the event loop)."""
        export_stl(build_impeller(params), preview_stl)

    def do_preview():
        # Async so the "Generating…" indicator shows while the (7-35 s) geometry build runs;
        # a synchronous build would freeze the UI with no feedback until it finished.
        if state.preview_busy or state.assess_busy:
            return
        params = build_edit_params()
        printable = check_printability(params)
        if not printable.printable:
            state.preview_msg = f"⚠ Not printable: {printable.reason}"
            return

        async def task():
            state.preview_busy = True
            state.preview_msg = "⏳ Generating geometry… (a few seconds)"
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, _build_preview_stl, params)
            except Exception as exc:  # loft / boolean failure on an extreme edit
                state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__}"
                state.preview_busy = False
                state.flush()
                return
            plotter.clear_actors()
            plotter.add_mesh(pv.read(str(preview_stl)), color="darkorange",
                             smooth_shading=True)
            plotter.reset_camera()
            feats = "features ON" if params.features.active else "smooth"
            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                                 f"camber {state.e_camber:.3f}, {feats} — geometry only, "
                                 f"not yet evaluated. Use 'Assess' to run CFD.")
            state.preview_busy = False
            try:
                ctrl.view_update()
            except Exception:
                pass
            state.flush()

        asynchronous.create_task(task())

================================================================================
## EDIT 31  @ 2026-08-27T14:14:11

--- FIND ---
                                        _slider("Stagger root", "e_stagger_root", 15, 70, 1)
                                        _slider("Stagger mid", "e_stagger_mid", 15, 70, 1)
                                        _slider("Stagger tip", "e_stagger_tip", 15, 70, 1)
                                        _slider("Chord root", "e_chord_root", 10, 28, 0.5)
                                        _slider("Chord mid", "e_chord_mid", 10, 28, 0.5)
                                        _slider("Chord tip", "e_chord_tip", 10, 28, 0.5)
                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)
--- REPLACE WITH ---
                                        _slider("Stagger root", "e_stagger_root", 15, 55, 1)
                                        _slider("Stagger mid", "e_stagger_mid", 15, 55, 1)
                                        _slider("Stagger tip", "e_stagger_tip", 15, 55, 1)
                                        _slider("Chord root", "e_chord_root", 14, 42, 0.5)
                                        _slider("Chord mid", "e_chord_mid", 14, 42, 0.5)
                                        _slider("Chord tip", "e_chord_tip", 14, 42, 0.5)
                                        _slider("Wrap mid (deg)", "e_lean_mid", 0, 30, 1)
                                        _slider("Wrap tip (deg)", "e_lean_tip", 0, 45, 1)
                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)

================================================================================
## EDIT 32  @ 2026-08-27T14:14:17

--- FIND ---
                                v3.VBtn("Preview geometry", color="primary", size="small",
                                        click=(do_preview,), classes="mr-2",
                                        disabled=("assess_busy",))
--- REPLACE WITH ---
                                v3.VBtn("Preview geometry", color="primary", size="small",
                                        click=(do_preview,), classes="mr-2",
                                        loading=("preview_busy",),
                                        disabled=("preview_busy || assess_busy",))

================================================================================
## EDIT 33  @ 2026-08-28T02:00:18

--- FIND ---
        state.e_lean_mid = float(p.get("lean_mid", 14.0))  # circumferential WRAP (deg)
        state.e_lean_tip = float(p.get("lean_tip", 26.0))
        state.e_tub_amp = feat.tubercle_amp
--- REPLACE WITH ---
        state.e_lean_mid = float(p.get("lean_mid", 14.0))  # circumferential WRAP (deg)
        state.e_lean_tip = float(p.get("lean_tip", 26.0))
        state.e_le_mid = float(p.get("le_sweep_mid", 0.0))  # leading-edge curve (mm)
        state.e_le_tip = float(p.get("le_sweep_tip", 0.0))
        state.e_tub_amp = feat.tubercle_amp

================================================================================
## EDIT 34  @ 2026-08-28T02:00:22

--- FIND ---
            max_camber=state.e_camber,
            lean_mid=state.e_lean_mid, lean_tip=state.e_lean_tip,
        )
--- REPLACE WITH ---
            max_camber=state.e_camber,
            lean_mid=state.e_lean_mid, lean_tip=state.e_lean_tip,
            le_sweep_mid=state.e_le_mid, le_sweep_tip=state.e_le_tip,
        )

================================================================================
## EDIT 35  @ 2026-08-28T02:00:29

--- FIND ---
                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)
--- REPLACE WITH ---
                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)
                                        _slider("LE curve mid (mm)", "e_le_mid", -8, 8, 0.5)
                                        _slider("LE curve tip (mm)", "e_le_tip", -8, 8, 0.5)

================================================================================
## EDIT 36  @ 2026-08-28T02:00:59

--- FIND ---
def _slider(label: str, model: str, mn: float, mx: float, step: float):
    """Compact labelled slider bound to a state variable (used in the editor panel)."""
    v3.VSlider(
        v_model=(model,), min=mn, max=mx, step=step, label=label,
        thumb_label=True, density="compact", hide_details=True, classes="mb-1",
    )
--- REPLACE WITH ---
def _slider(label: str, model: str, mn: float, mx: float, step: float):
    """Compact labelled slider bound to a state variable (used in the editor panel)."""
    v3.VSlider(
        v_model=(model,), min=mn, max=mx, step=step, label=label,
        thumb_label=True, density="compact", hide_details=True, classes="mb-1",
    )


# Plain-English "map" of what each control does + its performance effect (shown in a help panel).
CONTROL_HELP = [
    ("Blades", "How many blades. More = more airflow & pressure, but louder and less efficient."),
    ("Camber (curve)", "How curved each blade section is. More camber turns the air harder "
                       "(more pressure) but too much hurts efficiency."),
    ("Stagger root/mid/tip", "Blade pitch angle at hub / mid / tip. Higher = more axial (flow-through); "
                             "lower = blades overlap more (pressure)."),
    ("Chord root/mid/tip", "Blade width at hub / mid / tip. Wider = more blade area / solidity "
                           "(pressure), but heavier and lower efficiency."),
    ("Wrap mid/tip (deg)", "Circumferential lean — wraps the blades around the axis so they overlap "
                           "like a real fan (0 = a flat radial paddle)."),
    ("Sweep mid/tip", "Axial position of the WHOLE section (forward/back rake of the blade)."),
    ("LE curve mid/tip (mm)", "Rakes only the LEADING edge forward/back, curving the leading-edge "
                              "line without moving the trailing edge. 0 = the flat default LE."),
    ("Tubercle amp/waves", "Bumpy leading edge (humpback-whale flipper) — delays stall."),
    ("Serration amp/teeth", "Sawtooth trailing edge (owl wing) — reduces edge noise."),
    ("Dimple depth/rows/cols", "Golf-ball-style surface dimples — texture the blade surface."),
]

================================================================================
## EDIT 37  @ 2026-08-28T02:01:05

--- FIND ---
                                with v3.VExpansionPanel(title="Geometry"):
                                    with v3.VExpansionPanelText():
                                        _slider("Blades", "e_n_blades", 5, 11, 1)
--- REPLACE WITH ---
                                with v3.VExpansionPanel(title="ℹ What these controls do"):
                                    with v3.VExpansionPanelText():
                                        for _term, _desc in CONTROL_HELP:
                                            with v3.VRow(no_gutters=True, classes="mb-1"):
                                                with v3.VCol(cols=5):
                                                    html.Span(_term,
                                                              classes="text-caption font-weight-bold")
                                                with v3.VCol(cols=7):
                                                    html.Span(_desc, classes="text-caption")
                                with v3.VExpansionPanel(title="Geometry"):
                                    with v3.VExpansionPanelText():
                                        _slider("Blades", "e_n_blades", 5, 11, 1)

================================================================================
## EDIT 38  @ 2026-08-28T04:03:06

--- FIND ---
    def _build_preview_stl(params):
        """Blocking geometry build (runs off the event loop)."""
        export_stl(build_impeller(params), preview_stl)
--- REPLACE WITH ---
    def _build_preview_stl(flat, feat):
        """Blocking geometry build in an ISOLATED subprocess (a native OCP crash or a runaway
        featured build can't take down the cockpit server — it surfaces as a caught error)."""
        from fansim.geometry.isolated import build_stl_isolated
        build_stl_isolated(flat, feat, preview_stl, timeout=120.0)

================================================================================
## EDIT 39  @ 2026-08-28T04:03:15

--- FIND ---
        params = build_edit_params()
        printable = check_printability(params)
        if not printable.printable:
            state.preview_msg = f"⚠ Not printable: {printable.reason}"
            return

        async def task():
            state.preview_busy = True
            state.preview_msg = "⏳ Generating geometry… (a few seconds)"
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, _build_preview_stl, params)
            except Exception as exc:  # loft / boolean failure on an extreme edit
                state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__}"
                state.preview_busy = False
                state.flush()
                return
--- REPLACE WITH ---
        params = build_edit_params()
        printable = check_printability(params)
        if not printable.printable:
            state.preview_msg = f"⚠ Not printable: {printable.reason}"
            return
        flat, feat = edit_flat(), edit_features()  # serializable inputs for the isolated build

        async def task():
            state.preview_busy = True
            heavy = " (features are heavy — up to ~2 min)" if params.features.active else ""
            state.preview_msg = f"⏳ Generating geometry…{heavy}"
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, _build_preview_stl, flat, feat)
            except TimeoutError:
                state.preview_msg = ("⚠ Geometry build timed out — featured blades are heavy; "
                                     "try a lower serration/dimple count (the app is fine).")
                state.preview_busy = False
                state.flush()
                return
            except Exception as exc:  # loft/boolean failure or isolated native crash — app survives
                state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__} (the app is fine)"
                state.preview_busy = False
                state.flush()
                return

================================================================================
## EDIT 40  @ 2026-08-28T04:19:28

--- FIND ---
    def on_assess():
        if state.assess_busy:
            return
        params, flat = build_edit_params(), edit_flat()
--- REPLACE WITH ---
    def on_assess():
        if state.assess_busy:
            return
        # store features alongside geometry so an assessed design's settings reload when reselected
        params, flat = build_edit_params(), {**edit_flat(), **_feat_dict()}

================================================================================
## EDIT 41  @ 2026-08-28T04:19:36

--- FIND ---
        state.e_tub_amp = feat.tubercle_amp
        state.e_tub_waves = feat.tubercle_waves
        state.e_ser_amp = feat.serration_amp
        state.e_ser_waves = feat.serration_waves
        state.e_dim_amp = feat.dimple_amp
        state.e_dim_rows = feat.dimple_rows
        state.e_dim_cols = feat.dimple_cols
--- REPLACE WITH ---
        # Load feature sliders from the design's params (feature-enabled runs + assessed designs
        # store them there), falling back to the passed Features. This is why selecting a featured
        # result now shows its bio-feature settings instead of resetting them to zero.
        state.e_tub_amp = float(p.get("tubercle_amp", feat.tubercle_amp))
        state.e_tub_waves = int(p.get("tubercle_waves", feat.tubercle_waves))
        state.e_ser_amp = float(p.get("serration_amp", feat.serration_amp))
        state.e_ser_waves = int(p.get("serration_waves", feat.serration_waves))
        state.e_dim_amp = float(p.get("dimple_amp", feat.dimple_amp))
        state.e_dim_rows = int(p.get("dimple_rows", feat.dimple_rows))
        state.e_dim_cols = int(p.get("dimple_cols", feat.dimple_cols))

================================================================================
## EDIT 42  @ 2026-08-28T05:31:22

--- FIND ---
        state.e_le_mid = float(p.get("le_sweep_mid", 0.0))  # leading-edge curve (mm)
        state.e_le_tip = float(p.get("le_sweep_tip", 0.0))
--- REPLACE WITH ---
        state.e_le_mid = float(p.get("le_sweep_mid", 0.0))  # leading-edge curve (mm)
        state.e_le_tip = float(p.get("le_sweep_tip", 0.0))
        state.e_hub_radius = float(p.get("hub_radius", 21.5))       # hub radius (mm)
        state.e_thick_root = float(p.get("thickness_root", 0.10))   # blade thickness (frac chord)
        state.e_thick_mid = float(p.get("thickness_mid", 0.08))
        state.e_thick_tip = float(p.get("thickness_tip", 0.06))
        state.e_camber_pos = float(p.get("camber_pos", 0.4))        # max-camber chordwise position
        state.e_spacing = float(p.get("spacing_spread", 0.0))       # uneven-spacing spread (0=even)

================================================================================
## EDIT 43  @ 2026-08-28T05:31:27

--- FIND ---
            max_camber=state.e_camber,
            lean_mid=state.e_lean_mid, lean_tip=state.e_lean_tip,
            le_sweep_mid=state.e_le_mid, le_sweep_tip=state.e_le_tip,
        )
--- REPLACE WITH ---
            max_camber=state.e_camber, camber_pos=state.e_camber_pos,
            lean_mid=state.e_lean_mid, lean_tip=state.e_lean_tip,
            le_sweep_mid=state.e_le_mid, le_sweep_tip=state.e_le_tip,
            hub_radius=state.e_hub_radius,
            thickness_root=state.e_thick_root, thickness_mid=state.e_thick_mid,
            thickness_tip=state.e_thick_tip,
            spacing_spread=state.e_spacing, spacing_seed=0,
        )

================================================================================
## EDIT 44  @ 2026-08-28T05:31:39

--- FIND ---
                                        _slider("LE curve mid (mm)", "e_le_mid", -8, 8, 0.5)
                                        _slider("LE curve tip (mm)", "e_le_tip", -8, 8, 0.5)
--- REPLACE WITH ---
                                        _slider("LE curve mid (mm)", "e_le_mid", -8, 8, 0.5)
                                        _slider("LE curve tip (mm)", "e_le_tip", -8, 8, 0.5)
                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
                                        _slider("Camber position", "e_camber_pos", 0.2, 0.6, 0.05)
                                        _slider("Thickness root", "e_thick_root", 0.03, 0.15, 0.01)
                                        _slider("Thickness mid", "e_thick_mid", 0.03, 0.15, 0.01)
                                        _slider("Thickness tip", "e_thick_tip", 0.03, 0.15, 0.01)
                                        _slider("Uneven spacing", "e_spacing", 0.0, 0.6, 0.05)

================================================================================
## EDIT 45  @ 2026-08-28T05:31:48

--- FIND ---
    ("LE curve mid/tip (mm)", "Rakes only the LEADING edge forward/back, curving the leading-edge "
                              "line without moving the trailing edge. 0 = the flat default LE."),
--- REPLACE WITH ---
    ("LE curve mid/tip (mm)", "Rakes only the LEADING edge forward/back, curving the leading-edge "
                              "line without moving the trailing edge. 0 = the flat default LE."),
    ("Hub radius (mm)", "Size of the central hub. Bigger hub = smaller flow annulus (less airflow) "
                        "but more room for the motor; must fit the fan model's hub-diameter limits."),
    ("Camber position", "Where the max camber sits along the chord (0.2=near LE, 0.6=aft). Shifts "
                        "the loading fore/aft."),
    ("Thickness root/mid/tip", "Blade thickness (fraction of chord) at hub/mid/tip. Thicker = stronger "
                               "/ more printable but heavier and less efficient; thin tips can drop "
                               "below the min printable wall."),
    ("Uneven spacing", "Spreads the blades to UNEVEN (but still balanced) angles to smear the "
                       "blade-pass tone. 0 = evenly spaced. Higher = more tone-spreading."),

================================================================================
## EDIT 46  @ 2026-08-28T14:20:41

--- FIND ---
def build_server(run_dir: str | Path, study_name: str | None = None):
    run_dir = Path(run_dir)
    study_designs = feasible_designs(load_designs(run_dir, study_name))
    user_designs: list[Design] = []
    by_trial = {d.trial: d for d in study_designs}
    if not study_designs:
        raise SystemExit(f"No feasible designs found in {run_dir}")
    assess_dir = run_dir / "cockpit_assess"
    next_id = [9000]  # ids for user-assessed designs (distinct from study trials)
--- REPLACE WITH ---
def build_server(run_dir: str | Path, study_name: str | None = None):
    run_dir = Path(run_dir)
    study_designs = feasible_designs(load_designs(run_dir, study_name))
    if not study_designs:
        raise SystemExit(f"No feasible designs found in {run_dir}")
    assess_dir = run_dir / "cockpit_assess"
    # Reload previously assessed designs from disk so they SURVIVE a cockpit restart (they used to
    # live only in memory and vanished on restart).
    user_designs: list[Design] = _load_assessed_designs(assess_dir)
    by_trial = {d.trial: d for d in study_designs}
    by_trial.update({d.trial: d for d in user_designs})
    next_id = [max([9000] + [d.trial + 1 for d in user_designs])]  # continue past reloaded ids

================================================================================
## EDIT 47  @ 2026-08-28T14:20:52

--- FIND ---
import asyncio
import tempfile
from pathlib import Path
--- REPLACE WITH ---
import asyncio
import json
import tempfile
from pathlib import Path

================================================================================
## EDIT 48  @ 2026-08-28T14:20:59

--- FIND ---
def build_server(run_dir: str | Path, study_name: str | None = None):
--- REPLACE WITH ---
def _load_assessed_designs(assess_dir: Path) -> list[Design]:
    """Reload designs the user assessed in earlier cockpit sessions (persisted as design.json)."""
    out: list[Design] = []
    if not assess_dir.exists():
        return out
    for jf in sorted(assess_dir.glob("design_*/design.json")):
        try:
            d = json.loads(jf.read_text())
            stl = jf.parent / "impeller.stl"
            out.append(Design(
                trial=int(d["trial"]), params=d.get("params", {}),
                objectives=d["objectives"], feasible=d.get("feasible", True), is_pareto=False,
                stl_path=stl if stl.exists() else None,
                reason=d.get("reason", ""), extra=d.get("extra", {})))
        except Exception:  # noqa: BLE001 - skip a corrupt/partial assess dir
            continue
    return out


def build_server(run_dir: str | Path, study_name: str | None = None):

================================================================================
## EDIT 49  @ 2026-08-28T14:21:12

--- FIND ---
            feasible=True, is_pareto=False,
            stl_path=stl if stl.exists() else None,
            extra={"n_blades": params.n_blades, "source": "user"},
        )
        user_designs.append(d)
        by_trial[tid] = d
--- REPLACE WITH ---
            feasible=True, is_pareto=False,
            stl_path=stl if stl.exists() else None,
            extra={"n_blades": params.n_blades, "source": "user"},
        )
        # persist so the design survives a cockpit restart (reloaded by _load_assessed_designs)
        try:
            (workdir / "design.json").write_text(json.dumps(
                {"trial": d.trial, "params": d.params, "objectives": d.objectives,
                 "feasible": True, "reason": d.reason, "extra": d.extra}, indent=2))
        except Exception:  # noqa: BLE001 - persistence is best-effort; keep the in-memory design
            pass
        user_designs.append(d)
        by_trial[tid] = d

================================================================================
## EDIT 50  @ 2026-08-28T14:38:22

--- FIND ---
import asyncio
import json
import tempfile
from pathlib import Path
--- REPLACE WITH ---
import asyncio
import dataclasses
import json
import tempfile
from pathlib import Path

================================================================================
## EDIT 51  @ 2026-08-28T14:38:27

--- FIND ---
from fansim.cockpit.data import Design, feasible_designs, load_designs
from fansim.geometry import build_impeller, export_stl
--- REPLACE WITH ---
from fansim.cockpit.data import Design, feasible_designs, load_designs
from fansim.fan_spec import fan_spec_names, get_fan_spec, load_fan_models_dir
from fansim.geometry import build_impeller, export_stl

================================================================================
## EDIT 52  @ 2026-08-28T14:38:33

--- FIND ---
    def _blocking_eval(params, workdir):
        return evaluate_candidate(params, workdir, procs=8, base_cell=0.006, iters=500)
--- REPLACE WITH ---
    def active_spec():
        """The selected fan model with the current leeway margins applied (nominal untouched)."""
        return dataclasses.replace(
            get_fan_spec(state.fan_model),
            leeway_tip_dia_mm=float(state.lee_tip), leeway_depth_mm=float(state.lee_depth),
            leeway_weight_g=float(state.lee_weight), over_voltage_v=float(state.lee_overvolt))

    def _blocking_eval(params, workdir):
        return evaluate_candidate(params, workdir, procs=8, base_cell=0.006, iters=500,
                                  spec=active_spec())

================================================================================
## EDIT 53  @ 2026-08-28T14:38:39

--- FIND ---
            feasible=True, is_pareto=False,
            stl_path=stl if stl.exists() else None,
            extra={"n_blades": params.n_blades, "source": "user"},
        )
--- REPLACE WITH ---
            feasible=True, is_pareto=False,
            stl_path=stl if stl.exists() else None,
            extra={"n_blades": params.n_blades, "source": "user",
                   "over_spec": list(result.over_spec), "fan_model": state.fan_model},
        )

================================================================================
## EDIT 54  @ 2026-08-28T14:38:47

--- FIND ---
            d = await _assess(params, flat, "Assess")
            if d:
                o = d.objectives
                state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
                                    f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
                                    f"  (added to plot)")
                state.selected_trial = d.trial
--- REPLACE WITH ---
            d = await _assess(params, flat, "Assess")
            if d:
                o = d.objectives
                over = d.extra.get("over_spec") or []
                tag = ("  ⚠ OVER-SPEC: " + "; ".join(over)) if over else ""
                state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
                                    f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
                                    f"  (added to plot){tag}")
                state.selected_trial = d.trial

================================================================================
## EDIT 55  @ 2026-08-28T14:39:15

--- FIND ---
    state.assess_msg = ""
    state.assess_busy = False
--- REPLACE WITH ---
    state.assess_msg = ""
    state.assess_busy = False
    # fan-model constraints + leeway (applied when you Assess). Nominal is never changed; leeway lets
    # a design exceed it (flagged over-spec). Import new models by dropping YAML in config/fan_models/.
    state.fan_model = "a12x25"
    state.fan_models = fan_spec_names()
    state.lee_tip = 0.0
    state.lee_depth = 0.0
    state.lee_overvolt = 0.0
    state.lee_weight = 0.0

    def _model_readout():
        s = get_fan_spec(state.fan_model)
        state.model_info = (f"{s.name}: tip ≤{s.tip_dia_mm[1]:.0f} mm, depth ≤{s.depth_mm[1]:.0f} mm, "
                            f"hub {s.hub_dia_mm[0]:.0f}-{s.hub_dia_mm[1]:.0f} mm, "
                            f"{s.max_shaft_power_w:.2f} W shaft ({s.voltage_v:.0f} V×{s.max_current_a:.2f} A), "
                            f"≤{s.max_weight_g:.0f} g. Published {s.ref_cfm:.0f} CFM / "
                            f"{s.ref_static_pa:.0f} Pa / {s.ref_noise_dba:.0f} dBA.")
    _model_readout()

    def reload_models():
        load_fan_models_dir()
        state.fan_models = fan_spec_names()
        _model_readout()
        state.flush()

    @state.change("fan_model")
    def _on_model(**_):
        _model_readout()

================================================================================
## EDIT 56  @ 2026-08-28T14:39:36

--- FIND ---
                        with v3.VCard(classes="mb-2 pa-3"):
                            html.Div("Assess & sweep (runs CFD)",
                                     classes="text-subtitle-2 mb-1")
                            v3.VBtn("Assess this design", color="success", size="small",
                                    block=True, click=(on_assess,),
                                    loading=("assess_busy",), disabled=("assess_busy",))
--- REPLACE WITH ---
                        with v3.VCard(classes="mb-2 pa-3"):
                            html.Div("Fan model & leeway", classes="text-subtitle-2 mb-1")
                            with v3.VRow(no_gutters=True, classes="align-center"):
                                with v3.VCol(cols=8, classes="pr-1"):
                                    v3.VSelect(label="Fan model", v_model=("fan_model",),
                                               items=("fan_models",), density="compact",
                                               hide_details=True)
                                with v3.VCol(cols=4):
                                    v3.VBtn("Reload", size="x-small", variant="tonal",
                                            click=(reload_models,))
                            html.Div("{{ model_info }}", classes="text-caption my-1")
                            html.Div("Leeway — allow exceeding nominal (flagged over-spec):",
                                     classes="text-caption mt-1")
                            _slider("Tip past frame (mm)", "lee_tip", 0, 10, 0.5)
                            _slider("Extra depth Z (mm)", "lee_depth", 0, 12, 0.5)
                            _slider("Over-voltage (V)", "lee_overvolt", 0, 12, 0.5)
                            _slider("Extra weight (g)", "lee_weight", 0, 40, 1)
                        with v3.VCard(classes="mb-2 pa-3"):
                            html.Div("Assess & sweep (runs CFD)",
                                     classes="text-subtitle-2 mb-1")
                            v3.VBtn("Assess this design", color="success", size="small",
                                    block=True, click=(on_assess,),
                                    loading=("assess_busy",), disabled=("assess_busy",))

================================================================================
## EDIT 57  @ 2026-08-28T14:39:57

--- FIND ---
            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
            f"/{p.get('sweep_tip',0):.1f}",
        ]
--- REPLACE WITH ---
            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
            f"/{p.get('sweep_tip',0):.1f}",
        ]
        if d.extra.get("over_spec"):
            state.info_lines.append("⚠ OVER-SPEC: " + "; ".join(d.extra["over_spec"]))

================================================================================
## EDIT 58  @ 2026-08-28T15:09:57

--- FIND ---
def _load_assessed_designs(assess_dir: Path) -> list[Design]:
--- REPLACE WITH ---
def _reject_hint(reason: str) -> str:
    """Turn a gate rejection into an actionable hint about which sliders drive it."""
    import re
    r = reason.lower()
    if "shaft" in r:  # over motor power
        m = re.search(r"needs ([\d.]+) w .*? ([\d.]+) w", r)
        pct = ""
        if m:
            need, cap = float(m.group(1)), float(m.group(2))
            pct = f" (~{100 * (need - cap) / cap:.0f}% over)"
        return (f"↳ shaft power grows with blade LOADING{pct}: solidity (blade count × chord), "
                "camber, stagger, and tip size. Try 1 fewer blade, ~10% less chord, or less camber "
                "— or add Over-voltage leeway to raise the budget.")
    if "depth" in r:
        return ("↳ depth = how far blades reach in Z. Driven by sweep, LE curve, stagger, thickness "
                "and wrap. Reduce those (esp. Sweep tip / LE curve tip) — or add Extra-depth leeway.")
    if "tip dia" in r:
        return "↳ tip diameter too big: reduce Chord tip / stagger — or add Tip-past-frame leeway."
    if "hub" in r:
        return "↳ hub diameter out of range: adjust the Hub radius slider."
    if "weight" in r:
        return ("↳ too heavy: thinner blades (Thickness sliders), smaller chord/hub, or fewer blades "
                "— or add Extra-weight leeway.")
    return ""


def _load_assessed_designs(assess_dir: Path) -> list[Design]:

================================================================================
## EDIT 59  @ 2026-08-28T15:10:02

--- FIND ---
        if not result.feasible:
            state.assess_msg = f"{label}: rejected — {result.reason}"
            state.flush()
            return None
--- REPLACE WITH ---
        if not result.feasible:
            hint = _reject_hint(result.reason)
            state.assess_msg = f"{label}: rejected — {result.reason}" + (f"\n{hint}" if hint else "")
            state.flush()
            return None

================================================================================
## EDIT 60  @ 2026-08-28T15:10:11

--- FIND ---
                            html.Div("{{ assess_msg }}", classes="text-caption mt-2")
--- REPLACE WITH ---
                            html.Div("{{ assess_msg }}", classes="text-caption mt-2",
                                     style="white-space: pre-line")

================================================================================
## EDIT 61  @ 2026-08-28T15:10:37

--- FIND ---
                        with v3.VCard(classes="mb-2 pa-3"):
                            html.Div("Fan model & leeway", classes="text-subtitle-2 mb-1")
                            with v3.VRow(no_gutters=True, classes="align-center"):
                                with v3.VCol(cols=8, classes="pr-1"):
                                    v3.VSelect(label="Fan model", v_model=("fan_model",),
                                               items=("fan_models",), density="compact",
                                               hide_details=True)
                                with v3.VCol(cols=4):
                                    v3.VBtn("Reload", size="x-small", variant="tonal",
                                            click=(reload_models,))
                            html.Div("{{ model_info }}", classes="text-caption my-1")
                            html.Div("Leeway — allow exceeding nominal (flagged over-spec):",
                                     classes="text-caption mt-1")
                            _slider("Tip past frame (mm)", "lee_tip", 0, 10, 0.5)
                            _slider("Extra depth Z (mm)", "lee_depth", 0, 12, 0.5)
                            _slider("Over-voltage (V)", "lee_overvolt", 0, 12, 0.5)
                            _slider("Extra weight (g)", "lee_weight", 0, 40, 1)
--- REPLACE WITH ---
                        with v3.VExpansionPanels(classes="mb-2"):
                            with v3.VExpansionPanel(title="Fan model & leeway"):
                                with v3.VExpansionPanelText():
                                    with v3.VRow(no_gutters=True, classes="align-center"):
                                        with v3.VCol(cols=8, classes="pr-1"):
                                            v3.VSelect(label="Fan model", v_model=("fan_model",),
                                                       items=("fan_models",), density="compact",
                                                       hide_details=True)
                                        with v3.VCol(cols=4):
                                            v3.VBtn("Reload", size="x-small", variant="tonal",
                                                    click=(reload_models,))
                                    html.Div("{{ model_info }}", classes="text-caption my-1")
                                    with v3.VExpansionPanels(classes="mt-1"):
                                        with v3.VExpansionPanel(
                                                title="Leeway (allow exceeding nominal → over-spec)"):
                                            with v3.VExpansionPanelText():
                                                _slider("Tip past frame (mm)", "lee_tip", 0, 10, 0.5)
                                                _slider("Extra depth Z (mm)", "lee_depth", 0, 12, 0.5)
                                                _slider("Over-voltage (V)", "lee_overvolt", 0, 12, 0.5)
                                                _slider("Extra weight (g)", "lee_weight", 0, 40, 1)

================================================================================
## EDIT 62  @ 2026-08-28T15:18:14

--- FIND ---
            extra={"n_blades": params.n_blades, "source": "user",
                   "over_spec": list(result.over_spec), "fan_model": state.fan_model},
        )
--- REPLACE WITH ---
            extra={"n_blades": params.n_blades, "source": "user",
                   "over_spec": list(result.over_spec), "fan_model": state.fan_model,
                   "actual_rpm": round(result.actual_rpm)},
        )

================================================================================
## EDIT 63  @ 2026-08-28T15:18:21

--- FIND ---
                o = d.objectives
                over = d.extra.get("over_spec") or []
                tag = ("  ⚠ OVER-SPEC: " + "; ".join(over)) if over else ""
                state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
                                    f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
                                    f"  (added to plot){tag}")
--- REPLACE WITH ---
                o = d.objectives
                over = d.extra.get("over_spec") or []
                tag = ("  ⚠ OVER-SPEC: " + "; ".join(over)) if over else ""
                spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
                rpm = d.extra.get("actual_rpm", 0)
                rpm_tag = (f"  ⚙ motor-limited: {rpm:.0f} RPM ({100*rpm/spec.rpm:.0f}%)"
                           if rpm and rpm < spec.rpm * 0.995 else "")
                state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
                                    f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
                                    f"  (added to plot){rpm_tag}{tag}")

================================================================================
## EDIT 64  @ 2026-08-28T15:18:33

--- FIND ---
    import re
    r = reason.lower()
    if "shaft" in r:  # over motor power
        m = re.search(r"needs ([\d.]+) w .*? ([\d.]+) w", r)
        pct = ""
        if m:
            need, cap = float(m.group(1)), float(m.group(2))
            pct = f" (~{100 * (need - cap) / cap:.0f}% over)"
        return (f"↳ shaft power grows with blade LOADING{pct}: solidity (blade count × chord), "
                "camber, stagger, and tip size. Try 1 fewer blade, ~10% less chord, or less camber "
                "— or add Over-voltage leeway to raise the budget.")
    if "depth" in r:
--- REPLACE WITH ---
    r = reason.lower()
    # (over-power no longer rejects -- it derates RPM; only the hard geometry limits reject)
    if "depth" in r:

================================================================================
## EDIT 65  @ 2026-08-28T15:18:38

--- FIND ---
        if d.extra.get("over_spec"):
            state.info_lines.append("⚠ OVER-SPEC: " + "; ".join(d.extra["over_spec"]))
--- REPLACE WITH ---
        rpm = d.extra.get("actual_rpm", 0)
        spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
        if rpm and rpm < spec.rpm * 0.995:
            state.info_lines.append(f"⚙ motor-limited: runs at {rpm:.0f} RPM "
                                    f"({100*rpm/spec.rpm:.0f}% of {spec.rpm:.0f}) — flow already derated")
        if d.extra.get("over_spec"):
            state.info_lines.append("⚠ OVER-SPEC: " + "; ".join(d.extra["over_spec"]))

================================================================================
## EDIT 66  @ 2026-08-28T15:42:12

--- FIND ---
from fansim.fan_spec import fan_spec_names, get_fan_spec, load_fan_models_dir
--- REPLACE WITH ---
from fansim.fan_spec import (
    check_build,
    estimate_weight_g,
    fan_spec_names,
    get_fan_spec,
    load_fan_models_dir,
    over_spec_flags,
)

================================================================================
## EDIT 67  @ 2026-08-28T15:42:32

--- FIND ---
    def _blocking_eval(params, workdir):
        return evaluate_candidate(params, workdir, procs=8, base_cell=0.006, iters=500,
                                  spec=active_spec())
--- REPLACE WITH ---
    def spec_status(stl_path, params):
        """Check the BUILT geometry against the active fan model (envelope/hub/depth/weight) with NO
        CFD -- lets us flag an out-of-spec design at Preview instead of after an Assess."""
        spec = active_spec()
        try:
            import trimesh
            m = trimesh.load(str(stl_path))
            (xmin, ymin, zmin), (xmax, ymax, zmax) = m.bounds
            dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
            depth = zmax - zmin
            weight = estimate_weight_g(abs(float(m.volume)), spec.material)
        except Exception:  # noqa: BLE001 - if we can't measure it, don't block
            return True, ""
        ok, reason = check_build(spec, dia, 2.0 * params.hub_radius, depth, weight)
        if not ok:
            return False, f"⚠ Out of spec — Assess will reject: {reason}. {_reject_hint(reason)}"
        over = over_spec_flags(spec, dia, depth, weight)
        if over:
            return True, "⚠ OVER-SPEC (allowed via leeway): " + "; ".join(over)
        return True, f"✓ fits {spec.name} (dia {dia:.0f} mm, depth {depth:.0f} mm, {weight:.0f} g)"

    def _blocking_eval(params, workdir):
        return evaluate_candidate(params, workdir, procs=8, base_cell=0.006, iters=500,
                                  spec=active_spec())

================================================================================
## EDIT 68  @ 2026-08-28T15:42:45

--- FIND ---
            feats = "features ON" if params.features.active else "smooth"
            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                                 f"camber {state.e_camber:.3f}, {feats} — geometry only, "
                                 f"not yet evaluated. Use 'Assess' to run CFD.")
            state.preview_busy = False
--- REPLACE WITH ---
            feats = "features ON" if params.features.active else "smooth"
            _, status = spec_status(preview_stl, params)   # spec check now, before any CFD
            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                                 f"camber {state.e_camber:.3f}, {feats}.\n{status}")
            state.preview_busy = False

================================================================================
## EDIT 69  @ 2026-08-28T15:43:05

--- FIND ---
                            html.Div("{{ preview_msg }}", classes="text-caption mt-2")
--- REPLACE WITH ---
                            html.Div("{{ preview_msg }}", classes="text-caption mt-2",
                                     style="white-space: pre-line")

================================================================================
## EDIT 70  @ 2026-08-28T16:02:50

--- FIND ---
import asyncio
import dataclasses
import json
import tempfile
from pathlib import Path
--- REPLACE WITH ---
import asyncio
import base64
import dataclasses
import json
import tempfile
from pathlib import Path

================================================================================
## EDIT 71  @ 2026-08-28T16:12:03

--- FIND ---
def _slider(label: str, model: str, mn: float, mx: float, step: float):
    """Compact labelled slider bound to a state variable (used in the editor panel)."""
    v3.VSlider(
        v_model=(model,), min=mn, max=mx, step=step, label=label,
        thumb_label=True, density="compact", hide_details=True, classes="mb-1",
    )


# Plain-English "map" of what each control does + its performance effect (shown in a help panel).
CONTROL_HELP = [
    ("Blades", "How many blades. More = more airflow & pressure, but louder and less efficient."),
    ("Camber (curve)", "How curved each blade section is. More camber turns the air harder "
                       "(more pressure) but too much hurts efficiency."),
    ("Stagger root/mid/tip", "Blade pitch angle at hub / mid / tip. Higher = more axial (flow-through); "
                             "lower = blades overlap more (pressure)."),
    ("Chord root/mid/tip", "Blade width at hub / mid / tip. Wider = more blade area / solidity "
                           "(pressure), but heavier and lower efficiency."),
    ("Wrap mid/tip (deg)", "Circumferential lean — wraps the blades around the axis so they overlap "
                           "like a real fan (0 = a flat radial paddle)."),
    ("Sweep mid/tip", "Axial position of the WHOLE section (forward/back rake of the blade)."),
    ("LE curve mid/tip (mm)", "Rakes only the LEADING edge forward/back, curving the leading-edge "
                              "line without moving the trailing edge. 0 = the flat default LE."),
    ("Hub radius (mm)", "Size of the central hub. Bigger hub = smaller flow annulus (less airflow) "
                        "but more room for the motor; must fit the fan model's hub-diameter limits."),
    ("Camber position", "Where the max camber sits along the chord (0.2=near LE, 0.6=aft). Shifts "
                        "the loading fore/aft."),
    ("Thickness root/mid/tip", "Blade thickness (fraction of chord) at hub/mid/tip. Thicker = stronger "
                               "/ more printable but heavier and less efficient; thin tips can drop "
                               "below the min printable wall."),
    ("Uneven spacing", "Spreads the blades to UNEVEN (but still balanced) angles to smear the "
                       "blade-pass tone. 0 = evenly spaced. Higher = more tone-spreading."),
    ("Tubercle amp/waves", "Bumpy leading edge (humpback-whale flipper) — delays stall."),
    ("Serration amp/teeth", "Sawtooth trailing edge (owl wing) — reduces edge noise."),
    ("Dimple depth/rows/cols", "Golf-ball-style surface dimples — texture the blade surface."),
]
--- REPLACE WITH ---
# Per-slider plain-English descriptions + min/max illustration images (shown as hover tooltips).
_CTRL_IMG_DIR = Path(__file__).resolve().parents[2] / "docs" / "control_images"


def _load_control_images() -> dict:
    uris = {}
    if _CTRL_IMG_DIR.exists():
        for p in _CTRL_IMG_DIR.glob("e_*.png"):
            try:
                uris[p.stem] = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
            except Exception:  # noqa: BLE001
                pass
    return uris


_IMG_URI = _load_control_images()

CONTROL_DESC = {
    "e_n_blades": "How many blades. More = more airflow & pressure, but louder and less efficient.",
    "e_camber": "Blade curvature. More camber turns the air harder (pressure); too much hurts efficiency.",
    "e_stagger_root": "Blade PITCH angle at the hub. Higher = more axial (flow); lower = blades overlap (pressure).",
    "e_stagger_mid": "Blade PITCH angle at mid-span.",
    "e_stagger_tip": "Blade PITCH angle at the tip.",
    "e_chord_root": "Blade width at the hub. Wider = more area/solidity (pressure) but heavier, less efficient.",
    "e_chord_mid": "Blade width at mid-span.",
    "e_chord_tip": "Blade width at the tip.",
    "e_lean_mid": "Circumferential WRAP at mid-span — wraps blades so they overlap like a real fan.",
    "e_lean_tip": "Circumferential WRAP at the tip (0 = a flat radial paddle).",
    "e_sweep_mid": "Axial position of the WHOLE mid section (forward/back rake).",
    "e_sweep_tip": "Axial position of the WHOLE tip section.",
    "e_le_mid": "Rakes only the LEADING edge at mid-span — curves the LE line, trailing edge unchanged.",
    "e_le_tip": "Rakes only the LEADING edge at the tip.",
    "e_hub_radius": "Hub size. Smaller hub = bigger flow annulus (more airflow/efficiency); must fit the model's hub limits.",
    "e_camber_pos": "Where max camber sits along the chord (0.2 = near LE, 0.6 = aft). Shifts loading fore/aft.",
    "e_thick_root": "Blade thickness at the hub. Thinner = lighter/more efficient; too thin drops below the min printable wall.",
    "e_thick_mid": "Blade thickness at mid-span.",
    "e_thick_tip": "Blade thickness at the tip.",
    "e_spacing": "Uneven-but-balanced blade spacing to spread the blade-pass tone. 0 = evenly spaced.",
    "e_tub_amp": "Tubercle amplitude — bumpy leading edge (whale-fin), delays stall.",
    "e_tub_waves": "Number of tubercle bumps along the span.",
    "e_ser_amp": "Serration depth — sawtooth trailing edge (owl-wing), cuts edge noise.",
    "e_ser_waves": "Number of serration teeth.",
    "e_dim_amp": "Dimple depth — golf-ball-style surface texture.",
    "e_dim_rows": "Dimples along the chord.",
    "e_dim_cols": "Dimples along the span.",
}


def _slider(label: str, model: str, mn: float, mx: float, step: float):
    """A labelled slider with a HOVER TOOLTIP: what it does + a min/max illustration."""
    desc, uri = CONTROL_DESC.get(model, ""), _IMG_URI.get(model)
    if not desc and not uri:
        v3.VSlider(v_model=(model,), min=mn, max=mx, step=step, label=label, thumb_label=True,
                   density="compact", hide_details=True, classes="mb-1")
        return
    with v3.VTooltip(location="end", open_delay=150, max_width=380):
        with v3.Template(v_slot_activator="{ props }"):
            v3.VSlider("__activator__", v_bind="props", v_model=(model,), min=mn, max=mx, step=step,
                       label=label, thumb_label=True, density="compact", hide_details=True,
                       classes="mb-1")
        if uri:
            html.Img(src=uri, style="width:360px;max-width:100%;display:block;"
                                    "margin-bottom:4px;border-radius:4px;")
        html.Div(desc, classes="text-caption")

================================================================================
## EDIT 72  @ 2026-08-28T16:12:10

--- FIND ---
        with v3.Template(v_slot_activator="{ props }"):
            v3.VSlider("__activator__", v_bind="props", v_model=(model,), min=mn, max=mx, step=step,
                       label=label, thumb_label=True, density="compact", hide_details=True,
                       classes="mb-1")
--- REPLACE WITH ---
        with v3.Template(v_slot_activator="{ props }"):
            v3.VSlider(v_bind="props", v_model=(model,), min=mn, max=mx, step=step,
                       label=label, thumb_label=True, density="compact", hide_details=True,
                       classes="mb-1")

================================================================================
## EDIT 73  @ 2026-08-28T16:12:25

--- FIND ---
                            html.Div("Modify design", classes="text-subtitle-2 mb-1")
                            with v3.VExpansionPanels(variant="accordion", multiple=True):
                                with v3.VExpansionPanel(title="ℹ What these controls do"):
                                    with v3.VExpansionPanelText():
                                        for _term, _desc in CONTROL_HELP:
                                            with v3.VRow(no_gutters=True, classes="mb-1"):
                                                with v3.VCol(cols=5):
                                                    html.Span(_term,
                                                              classes="text-caption font-weight-bold")
                                                with v3.VCol(cols=7):
                                                    html.Span(_desc, classes="text-caption")
                                with v3.VExpansionPanel(title="Geometry"):
--- REPLACE WITH ---
                            html.Div("Modify design — hover any slider for a min/max picture + what it does",
                                     classes="text-caption mb-1")
                            with v3.VExpansionPanels(variant="accordion", multiple=True):
                                with v3.VExpansionPanel(title="Geometry"):

================================================================================
## EDIT 74  @ 2026-08-28T16:52:37

--- FIND ---
def _load_assessed_designs(assess_dir: Path) -> list[Design]:
--- REPLACE WITH ---
def _blade_z_extent(params) -> float:
    """Axial (Z) extent of the blade from its section points -- FAST (no CAD-kernel solid)."""
    from fansim.geometry.blade import _interp_stations, _section_points_3d
    it = _interp_stations(params, params.n_span)
    r0 = params.hub_radius - params.root_embed
    zs = []
    for i in range(params.n_span):
        rf = float(it["r_frac"][i]); r = r0 + (params.tip_radius - r0) * rf
        pts = _section_points_3d(
            r=r, r_frac=rf, chord=float(it["chord"][i]), stagger_deg=float(it["stagger_deg"][i]),
            thickness=float(it["thickness"][i]), max_camber=float(it["max_camber"][i]),
            camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]),
            skew=float(it["skew"][i]), le_sweep=float(it["le_sweep"][i]),
            lean_deg=float(it["lean_deg"][i]), n_chord=params.n_chord, features=None.__class__() if False else params.features)
        zs += [v.z for v in pts]
    return max(zs) - min(zs)


def _depth_drivers(flat: dict, top: int = 3) -> list[tuple[str, float]]:
    """For THIS design, how much each slider would cut the blade's Z-depth -- ranked. Features off
    (they barely affect depth) so it's fast. Returns [(label, mm_saved), ...] biggest first."""
    from fansim.geometry.features import Features
    from fansim.optimize.search_space import blade_from_flat
    base = _blade_z_extent(blade_from_flat(flat, Features()))
    tests = [("Sweep tip", "sweep_tip", -4.0), ("Sweep mid", "sweep_mid", -4.0),
             ("Mid stagger/pitch", "stagger_mid", -6.0), ("Tip stagger/pitch", "stagger_tip", -6.0),
             ("Root stagger/pitch", "stagger_root", -6.0), ("Mid chord", "chord_mid", -6.0),
             ("Tip chord", "chord_tip", -6.0), ("Root chord", "chord_root", -6.0),
             ("LE curve tip", "le_sweep_tip", 0.0), ("LE curve mid", "le_sweep_mid", 0.0),
             ("Wrap tip", "lean_tip", -10.0), ("Wrap mid", "lean_mid", -10.0)]
    out = []
    for label, key, delta in tests:
        f = dict(flat)
        f[key] = 0.0 if delta == 0.0 else f.get(key, 0.0) + delta
        try:
            saved = base - _blade_z_extent(blade_from_flat(f, Features()))
        except Exception:  # noqa: BLE001
            continue
        if saved > 0.3:
            out.append((label, saved))
    f = dict(flat)
    for k in ("thickness_root", "thickness_mid", "thickness_tip"):
        f[k] = max(0.03, f.get(k, 0.08) - 0.02)
    try:
        saved = base - _blade_z_extent(blade_from_flat(f, Features()))
        if saved > 0.3:
            out.append(("Thinner blades", saved))
    except Exception:  # noqa: BLE001
        pass
    out.sort(key=lambda t: -t[1])
    return out[:top]


def _load_assessed_designs(assess_dir: Path) -> list[Design]:

================================================================================
## EDIT 75  @ 2026-08-28T16:52:42

--- FIND ---
            lean_deg=float(it["lean_deg"][i]), n_chord=params.n_chord, features=None.__class__() if False else params.features)
--- REPLACE WITH ---
            lean_deg=float(it["lean_deg"][i]), n_chord=params.n_chord, features=params.features)

================================================================================
## EDIT 76  @ 2026-08-28T16:53:10

--- FIND ---
    def spec_status(stl_path, params):
        """Check the BUILT geometry against the active fan model (envelope/hub/depth/weight) with NO
        CFD -- lets us flag an out-of-spec design at Preview instead of after an Assess."""
        spec = active_spec()
        try:
            import trimesh
            m = trimesh.load(str(stl_path))
            (xmin, ymin, zmin), (xmax, ymax, zmax) = m.bounds
            dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
            depth = zmax - zmin
            weight = estimate_weight_g(abs(float(m.volume)), spec.material)
        except Exception:  # noqa: BLE001 - if we can't measure it, don't block
            return True, ""
        ok, reason = check_build(spec, dia, 2.0 * params.hub_radius, depth, weight)
        if not ok:
            return False, f"⚠ Out of spec — Assess will reject: {reason}. {_reject_hint(reason)}"
        over = over_spec_flags(spec, dia, depth, weight)
        if over:
            return True, "⚠ OVER-SPEC (allowed via leeway): " + "; ".join(over)
        return True, f"✓ fits {spec.name} (dia {dia:.0f} mm, depth {depth:.0f} mm, {weight:.0f} g)"
--- REPLACE WITH ---
    def _depth_driver_msg(flat):
        """Name the top depth-driving sliders FOR THIS design, with mm each would save."""
        try:
            drivers = _depth_drivers(flat)
        except Exception:  # noqa: BLE001
            return ""
        if not drivers:
            return ""
        return "  Top depth drivers here: " + ", ".join(f"{lab} (~{mm:.0f} mm)" for lab, mm in drivers)

    def spec_status(stl_path, params, flat=None):
        """Check the BUILT geometry against the active fan model (envelope/hub/depth/weight) with NO
        CFD -- lets us flag an out-of-spec design at Preview instead of after an Assess. On a depth
        issue, names the specific sliders driving it for THIS design."""
        spec = active_spec()
        try:
            import trimesh
            m = trimesh.load(str(stl_path))
            (xmin, ymin, zmin), (xmax, ymax, zmax) = m.bounds
            dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
            depth = zmax - zmin
            weight = estimate_weight_g(abs(float(m.volume)), spec.material)
        except Exception:  # noqa: BLE001 - if we can't measure it, don't block
            return True, ""
        ok, reason = check_build(spec, dia, 2.0 * params.hub_radius, depth, weight)
        depth_msg = _depth_driver_msg(flat) if (flat and "depth" in reason.lower()) else ""
        if not ok:
            return False, f"⚠ Out of spec — Assess will reject: {reason}. {_reject_hint(reason)}{depth_msg}"
        over = over_spec_flags(spec, dia, depth, weight)
        if over:
            dm = _depth_driver_msg(flat) if (flat and any("depth" in o for o in over)) else ""
            return True, "⚠ OVER-SPEC (allowed via leeway): " + "; ".join(over) + dm
        return True, f"✓ fits {spec.name} (dia {dia:.0f} mm, depth {depth:.0f} mm, {weight:.0f} g)"

================================================================================
## EDIT 77  @ 2026-08-28T16:53:14

--- FIND ---
            _, status = spec_status(preview_stl, params)   # spec check now, before any CFD
--- REPLACE WITH ---
            _, status = spec_status(preview_stl, params, flat)   # spec check now, before any CFD

================================================================================
## EDIT 78  @ 2026-08-28T16:57:48

--- FIND ---
        state.e_hub_radius = float(p.get("hub_radius", 21.5))       # hub radius (mm)
--- REPLACE WITH ---
        state.e_hub_radius = float(p.get("hub_radius", 21.5))       # hub radius (mm)
        state.e_tip_radius = float(p.get("tip_radius", 56.5))       # tip radius = blade length (mm)

================================================================================
## EDIT 79  @ 2026-08-28T16:57:52

--- FIND ---
            hub_radius=state.e_hub_radius,
            thickness_root=state.e_thick_root, thickness_mid=state.e_thick_mid,
--- REPLACE WITH ---
            hub_radius=state.e_hub_radius, tip_radius=state.e_tip_radius,
            thickness_root=state.e_thick_root, thickness_mid=state.e_thick_mid,

================================================================================
## EDIT 80  @ 2026-08-28T16:57:56

--- FIND ---
                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
--- REPLACE WITH ---
                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
                                        _slider("Tip radius / length (mm)", "e_tip_radius", 45, 59, 0.5)

================================================================================
## EDIT 81  @ 2026-08-28T16:58:01

--- FIND ---
    "e_hub_radius": "Hub size. Smaller hub = bigger flow annulus (more airflow/efficiency); must fit the model's hub limits.",
--- REPLACE WITH ---
    "e_hub_radius": "Hub size. Smaller hub = bigger flow annulus (more airflow/efficiency); must fit the model's hub limits.",
    "e_tip_radius": "Blade LENGTH (outer radius). Shrink it to make an oversized blade fit the frame (tip diameter) or trim depth.",

================================================================================
## EDIT 82  @ 2026-08-28T16:58:07

--- FIND ---
             ("Wrap tip", "lean_tip", -10.0), ("Wrap mid", "lean_mid", -10.0)]
--- REPLACE WITH ---
             ("Wrap tip", "lean_tip", -10.0), ("Wrap mid", "lean_mid", -10.0),
             ("Tip radius / length", "tip_radius", -5.0)]

================================================================================
## EDIT 83  @ 2026-08-28T18:03:39

--- FIND ---
from fansim.optimize.objectives import evaluate_candidate
from fansim.optimize.search_space import blade_from_flat
--- REPLACE WITH ---
from fansim.optimize.objectives import evaluate_candidate
from fansim.optimize.isolated_eval import evaluate_candidate_isolated
from fansim.optimize.search_space import blade_from_flat

================================================================================
## EDIT 84  @ 2026-08-28T18:03:47

--- FIND ---
from fansim.optimize.objectives import evaluate_candidate
from fansim.optimize.isolated_eval import evaluate_candidate_isolated
--- REPLACE WITH ---
from fansim.optimize.isolated_eval import evaluate_candidate_isolated

================================================================================
## EDIT 85  @ 2026-08-28T18:03:53

--- FIND ---
    def _blocking_eval(params, workdir):
        return evaluate_candidate(params, workdir, procs=8, base_cell=0.006, iters=500,
                                  spec=active_spec())

    async def _assess(params, flat, label):
        tid = next_id[0]
        next_id[0] += 1
        workdir = assess_dir / f"design_{tid}"
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _blocking_eval, params, workdir)
--- REPLACE WITH ---
    def _blocking_eval(flat, features, workdir):
        # Isolated subprocess: an OCP native crash / OpenFOAM hang can't take the cockpit down.
        return evaluate_candidate_isolated(flat, features, workdir, spec=active_spec(),
                                           procs=8, base_cell=0.006, iters=500)

    async def _assess(params, flat, label):
        tid = next_id[0]
        next_id[0] += 1
        workdir = assess_dir / f"design_{tid}"
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _blocking_eval, flat, params.features, workdir)

================================================================================
## EDIT 86  @ 2026-08-28T18:04:08

--- FIND ---
        async def task():
            state.assess_busy = True
            state.assess_msg = "Running CFD on your design… (~4 min)"
            state.flush()
            d = await _assess(params, flat, "Assess")
            if d:
                o = d.objectives
                over = d.extra.get("over_spec") or []
                tag = ("  ⚠ OVER-SPEC: " + "; ".join(over)) if over else ""
                spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
                rpm = d.extra.get("actual_rpm", 0)
                rpm_tag = (f"  ⚙ motor-limited: {rpm:.0f} RPM ({100*rpm/spec.rpm:.0f}%)"
                           if rpm and rpm < spec.rpm * 0.995 else "")
                state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
                                    f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
                                    f"  (added to plot){rpm_tag}{tag}")
                state.selected_trial = d.trial
            state.assess_busy = False
            state.flush()

        asynchronous.create_task(task())
--- REPLACE WITH ---
        async def task():
            state.assess_busy = True
            state.assess_msg = "Running CFD on your design… (~4 min)"
            state.flush()
            try:
                d = await _assess(params, flat, "Assess")
                if d:
                    o = d.objectives
                    over = d.extra.get("over_spec") or []
                    tag = ("  ⚠ OVER-SPEC: " + "; ".join(over)) if over else ""
                    spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
                    rpm = d.extra.get("actual_rpm", 0)
                    rpm_tag = (f"  ⚙ motor-limited: {rpm:.0f} RPM ({100*rpm/spec.rpm:.0f}%)"
                               if rpm and rpm < spec.rpm * 0.995 else "")
                    state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
                                        f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
                                        f"  (added to plot){rpm_tag}{tag}")
                    state.selected_trial = d.trial
            except Exception as exc:  # noqa: BLE001 - surface eval errors; never a stuck/dead UI
                state.assess_msg = f"Assess failed: {type(exc).__name__}: {exc}"
            finally:
                state.assess_busy = False
                state.flush()

        asynchronous.create_task(task())

================================================================================
## EDIT 87  @ 2026-08-28T18:04:24

--- FIND ---
        async def task():
            state.assess_busy = True
            done = 0
            for i, val in enumerate(values):
                flat, feat = dict(base_flat), dict(base_feat)
                if kind == "flat":
                    flat[field] = int(val) if field == "n_blades" else float(val)
                else:
                    feat[field] = float(val)
                    if kind == "tub" and feat["tubercle_waves"] == 0:
                        feat["tubercle_waves"] = 6
                    if kind == "ser" and feat["serration_waves"] == 0:
                        feat["serration_waves"] = 8
                    if kind == "dim":
                        feat["dimple_rows"] = feat["dimple_rows"] or 5
                        feat["dimple_cols"] = feat["dimple_cols"] or 5
                params = blade_from_flat(flat, Features(**feat))
                state.assess_msg = f"Sweep {label} {i+1}/{len(values)} = {val:g}: running CFD…"
                state.flush()
                if not check_printability(params).printable:
                    continue
                if await _assess(params, flat, f"sweep {label}={val:g}"):
                    done += 1
            state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
            state.assess_busy = False
            state.flush()

        asynchronous.create_task(task())
--- REPLACE WITH ---
        async def task():
            state.assess_busy = True
            done = 0
            try:
                for i, val in enumerate(values):
                    flat, feat = dict(base_flat), dict(base_feat)
                    if kind == "flat":
                        flat[field] = int(val) if field == "n_blades" else float(val)
                    else:
                        feat[field] = float(val)
                        if kind == "tub" and feat["tubercle_waves"] == 0:
                            feat["tubercle_waves"] = 6
                        if kind == "ser" and feat["serration_waves"] == 0:
                            feat["serration_waves"] = 8
                        if kind == "dim":
                            feat["dimple_rows"] = feat["dimple_rows"] or 5
                            feat["dimple_cols"] = feat["dimple_cols"] or 5
                    params = blade_from_flat(flat, Features(**feat))
                    state.assess_msg = f"Sweep {label} {i+1}/{len(values)} = {val:g}: running CFD…"
                    state.flush()
                    if not check_printability(params).printable:
                        continue
                    try:  # one design failing shouldn't abort the whole sweep
                        if await _assess(params, flat, f"sweep {label}={val:g}"):
                            done += 1
                    except Exception as exc:  # noqa: BLE001
                        state.assess_msg = f"Sweep {label}={val:g} failed: {type(exc).__name__}: {exc}"
                        state.flush()
                state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
            finally:
                state.assess_busy = False
                state.flush()

        asynchronous.create_task(task())

================================================================================
## EDIT 88  @ 2026-08-28T18:55:28

--- FIND ---
def _load_assessed_designs(assess_dir: Path) -> list[Design]:
    """Reload designs the user assessed in earlier cockpit sessions (persisted as design.json)."""
    out: list[Design] = []
    if not assess_dir.exists():
        return out
    for jf in sorted(assess_dir.glob("design_*/design.json")):
        try:
            d = json.loads(jf.read_text())
            stl = jf.parent / "impeller.stl"
            out.append(Design(
                trial=int(d["trial"]), params=d.get("params", {}),
                objectives=d["objectives"], feasible=d.get("feasible", True), is_pareto=False,
                stl_path=stl if stl.exists() else None,
                reason=d.get("reason", ""), extra=d.get("extra", {})))
        except Exception:  # noqa: BLE001 - skip a corrupt/partial assess dir
            continue
    return out
--- REPLACE WITH ---
def _load_assessed_designs(assess_dirs) -> list[Design]:
    """Reload designs the user assessed in earlier cockpit sessions (persisted as design.json).

    Accepts a single dir or an iterable of cockpit_assess dirs so a design assessed under ANY run
    shows up regardless of which --run is currently open (user designs are the user's own work, not
    tied to one optimizer run). Trial ids that collide across runs are re-keyed to a fresh id (the
    original is kept in extra['orig_trial']); each design records its source run in extra['source_run'].
    """
    if isinstance(assess_dirs, (str, Path)):
        assess_dirs = [Path(assess_dirs)]
    out: list[Design] = []
    used: set[int] = set()

    def _fresh() -> int:
        i = 9000
        while i in used:
            i += 1
        used.add(i)
        return i

    for assess_dir in assess_dirs:
        assess_dir = Path(assess_dir)
        if not assess_dir.exists():
            continue
        run_name = assess_dir.parent.name
        for jf in sorted(assess_dir.glob("design_*/design.json")):
            try:
                d = json.loads(jf.read_text())
                stl = jf.parent / "impeller.stl"
                orig = int(d["trial"])
                if orig in used:
                    tid = _fresh()
                else:
                    tid = orig
                    used.add(tid)
                extra = dict(d.get("extra", {}))
                extra.setdefault("source_run", run_name)
                if tid != orig:
                    extra["orig_trial"] = orig
                out.append(Design(
                    trial=tid, params=d.get("params", {}),
                    objectives=d["objectives"], feasible=d.get("feasible", True), is_pareto=False,
                    stl_path=stl if stl.exists() else None,
                    reason=d.get("reason", ""), extra=extra))
            except Exception:  # noqa: BLE001 - skip a corrupt/partial assess dir
                continue
    return out

================================================================================
## EDIT 89  @ 2026-08-28T18:55:35

--- FIND ---
    assess_dir = run_dir / "cockpit_assess"
    # Reload previously assessed designs from disk so they SURVIVE a cockpit restart (they used to
    # live only in memory and vanished on restart).
    user_designs: list[Design] = _load_assessed_designs(assess_dir)
--- REPLACE WITH ---
    assess_dir = run_dir / "cockpit_assess"   # new assessments this session land here
    # Reload previously assessed designs from disk so they SURVIVE a cockpit restart (they used to
    # live only in memory and vanished on restart). Scan EVERY run's cockpit_assess, not just the
    # open --run, so a design you assessed under any run still shows (user designs aren't tied to one
    # optimizer run). Falls back to the single dir if the runs root can't be globbed.
    runs_root = run_dir.parent
    all_assess_dirs = sorted(runs_root.glob("*/cockpit_assess")) if runs_root.exists() else []
    if assess_dir not in all_assess_dirs:
        all_assess_dirs.append(assess_dir)
    user_designs: list[Design] = _load_assessed_designs(all_assess_dirs)

================================================================================
## EDIT 90  @ 2026-08-28T18:55:42

--- FIND ---
    def _label(d):
        tag = "  ★" if d.is_pareto else ("  ◆" if d.trial >= 9000 else "")
        return {"title": f"#{d.trial}{tag}", "value": d.trial}
--- REPLACE WITH ---
    def _label(d):
        if d.is_pareto:
            tag = "  ★"
        elif d.trial >= 9000:  # user-assessed; note which run it was assessed under
            run = d.extra.get("source_run", "")
            tag = f"  ◆ {run}" if run else "  ◆"
        else:
            tag = ""
        return {"title": f"#{d.trial}{tag}", "value": d.trial}

================================================================================
## EDIT 91  @ 2026-08-28T18:55:46

--- FIND ---
            extra={"n_blades": params.n_blades, "source": "user",
                   "over_spec": list(result.over_spec), "fan_model": state.fan_model,
                   "actual_rpm": round(result.actual_rpm)},
--- REPLACE WITH ---
            extra={"n_blades": params.n_blades, "source": "user",
                   "source_run": run_dir.name,
                   "over_spec": list(result.over_spec), "fan_model": state.fan_model,
                   "actual_rpm": round(result.actual_rpm)},

================================================================================
## EDIT 92  @ 2026-08-28T18:58:05

--- FIND ---
    state.assess_msg = ""
    state.assess_busy = False
--- REPLACE WITH ---
    state.assess_msg = ""
    state.assess_busy = False
    # staleness: True once the editor diverges from the selected design's assessed config, so the
    # shown CFM/eff no longer reflect the edits and a re-Assess is needed (esp. after feature edits).
    state.edited_stale = False
    state.stale_msg = ""

================================================================================
## EDIT 93  @ 2026-08-28T18:58:17

--- FIND ---
    def active_spec():
        """The selected fan model with the current leeway margins applied (nominal untouched)."""
--- REPLACE WITH ---
    # --- Edited-since-assessment tracking ---------------------------------------------------------
    # EDITOR_VARS is every slider that feeds the geometry/CFD, so a change to ANY of them can make a
    # prior assessment stale. sel_sig holds the signature of the selected design's assessed config.
    EDITOR_VARS = (
        "e_n_blades", "e_stagger_root", "e_stagger_mid", "e_stagger_tip",
        "e_chord_root", "e_chord_mid", "e_chord_tip", "e_sweep_mid", "e_sweep_tip",
        "e_camber", "e_camber_pos", "e_lean_mid", "e_lean_tip", "e_le_mid", "e_le_tip",
        "e_hub_radius", "e_tip_radius", "e_thick_root", "e_thick_mid", "e_thick_tip", "e_spacing",
        "e_tub_amp", "e_tub_waves", "e_ser_amp", "e_ser_waves", "e_dim_amp", "e_dim_rows", "e_dim_cols",
    )
    sel_sig = [None]  # signature of the currently-selected design's assessed geometry+features

    def _editor_sig() -> dict:
        """Normalized signature of the current editor state (geometry + features), rounded so tiny
        float noise doesn't read as an edit."""
        s = {**edit_flat(), **_feat_dict()}
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()}

    def _set_baseline():
        """Mark the current editor state as the assessed baseline (not stale)."""
        sel_sig[0] = _editor_sig()
        state.edited_stale = False
        state.stale_msg = ""

    def _recompute_stale(**_):
        if sel_sig[0] is None:
            return
        stale = _editor_sig() != sel_sig[0]
        state.edited_stale = stale
        state.stale_msg = ("⚠ Edited since assessment — the shown CFM/efficiency are for the "
                           "un-edited design. Press Assess to evaluate your changes." if stale else "")

    state.change(*EDITOR_VARS)(_recompute_stale)

    def active_spec():
        """The selected fan model with the current leeway margins applied (nominal untouched)."""

================================================================================
## EDIT 94  @ 2026-08-28T18:58:28

--- FIND ---
        _init_editor(p)  # load the editor sliders from the selected design
        state.preview_msg = "Edit the sliders below, then press Preview geometry."
--- REPLACE WITH ---
        _init_editor(p)  # load the editor sliders from the selected design
        _set_baseline()  # editor now matches the assessed design — not stale until edited
        state.preview_msg = "Edit the sliders below, then press Preview geometry."

================================================================================
## EDIT 95  @ 2026-08-28T18:58:31

--- FIND ---
                                        f"  (added to plot){rpm_tag}{tag}")
                    state.selected_trial = d.trial
--- REPLACE WITH ---
                                        f"  (added to plot){rpm_tag}{tag}")
                    state.selected_trial = d.trial
                    _set_baseline()  # the editor now matches the just-assessed design

================================================================================
## EDIT 96  @ 2026-08-28T18:58:47

--- FIND ---
                            html.Div("Assess & sweep (runs CFD)",
                                     classes="text-subtitle-2 mb-1")
                            v3.VBtn("Assess this design", color="success", size="small",
                                    block=True, click=(on_assess,),
                                    loading=("assess_busy",), disabled=("assess_busy",))
--- REPLACE WITH ---
                            html.Div("Assess & sweep (runs CFD)",
                                     classes="text-subtitle-2 mb-1")
                            v3.VAlert("{{ stale_msg }}", v_if="edited_stale", type="warning",
                                      density="compact", variant="tonal", classes="mb-2",
                                      style="white-space: pre-line")
                            v3.VBtn("Assess this design", color="success", size="small",
                                    block=True, click=(on_assess,),
                                    loading=("assess_busy",), disabled=("assess_busy",))

================================================================================
## EDIT 97  @ 2026-08-28T19:08:19

--- FIND ---
    # staleness: True once the editor diverges from the selected design's assessed config, so the
    # shown CFM/eff no longer reflect the edits and a re-Assess is needed (esp. after feature edits).
    state.edited_stale = False
    state.stale_msg = ""
--- REPLACE WITH ---
    # staleness: True once the editor diverges from the selected design's assessed config, so the
    # shown CFM/eff no longer reflect the edits and a re-Assess is needed (esp. after feature edits).
    state.edited_stale = False
    state.stale_msg = ""
    # 3D-view constraint aids: paint the geometry that pokes past the fan's nominal envelope red, and
    # optionally draw the outer-case envelope (max tip diameter x max depth) as a translucent shell.
    state.highlight_spec = True
    state.show_envelope = False

================================================================================
## EDIT 98  @ 2026-08-28T19:08:37

--- FIND ---
    def do_preview():
        # Async so the "Generating…" indicator shows while the (7-35 s) geometry build runs;
--- REPLACE WITH ---
    # --- 3D render with constraint aids -----------------------------------------------------------
    # render_state remembers the mesh + base color currently shown so the highlight/envelope toggles
    # can redraw the SAME model without a rebuild or a camera reset.
    render_state = {"path": None, "color": "lightsteelblue"}

    def _spec_limits():
        """Nominal outer-case limits of the active fan model: (max tip RADIUS mm, max DEPTH mm).
        Uses the nominal spec (not leeway) so red = 'past the real fan's envelope'."""
        s = active_spec()
        return s.tip_dia_mm[1] / 2.0, s.depth_mm[1]

    def _out_of_spec_mask(mesh):
        """Per-point 1.0 where the geometry exceeds the nominal tip radius or depth budget, else 0.0.
        Depth is measured as distance from the model's own z-midplane (no absolute case datum)."""
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
        cyl = pv.Cylinder(center=(0, 0, zmid), direction=(0, 0, 1),
                          radius=tip_r, height=depth_lim, resolution=64)
        plotter.add_mesh(cyl, color="seagreen", opacity=0.10)
        try:  # crisp rim/outline so the envelope reads as a box even at low opacity
            plotter.add_mesh(cyl.extract_feature_edges(), color="seagreen", line_width=2)
        except Exception:  # noqa: BLE001 - edges are cosmetic
            pass

    def _apply_render(reset: bool = False):
        """(Re)draw the current model with the active highlight/envelope options."""
        plotter.clear_actors()
        p = render_state["path"]
        if not p:
            return
        try:
            mesh = pv.read(str(p))
        except Exception:  # noqa: BLE001 - nothing to show
            return
        base = render_state["color"]
        if state.highlight_spec:
            mask = _out_of_spec_mask(mesh)
            if mask.any():  # 2-color map: base where in-spec, red where it breaks the envelope
                mesh["spec"] = mask
                plotter.add_mesh(mesh, scalars="spec", cmap=[base, "red"], clim=[0, 1],
                                 show_scalar_bar=False, smooth_shading=True)
            else:
                plotter.add_mesh(mesh, color=base, smooth_shading=True)
        else:
            plotter.add_mesh(mesh, color=base, smooth_shading=True)
        if state.show_envelope:
            _add_envelope(mesh)
        if reset:
            plotter.reset_camera()

    def _draw(path, color: str):
        render_state["path"] = str(path)
        render_state["color"] = color
        _apply_render(reset=True)

    @state.change("highlight_spec", "show_envelope", "fan_model")
    def _on_viz_toggle(**_):
        _apply_render(reset=False)  # keep the current camera when just toggling an aid
        try:
            ctrl.view_update()
        except Exception:  # noqa: BLE001
            pass

    def do_preview():
        # Async so the "Generating…" indicator shows while the (7-35 s) geometry build runs;

================================================================================
## EDIT 99  @ 2026-08-28T19:08:44

--- FIND ---
            plotter.clear_actors()
            plotter.add_mesh(pv.read(str(preview_stl)), color="darkorange",
                             smooth_shading=True)
            plotter.reset_camera()
            feats = "features ON" if params.features.active else "smooth"
--- REPLACE WITH ---
            _draw(preview_stl, "darkorange")  # renders with highlight/envelope aids
            feats = "features ON" if params.features.active else "smooth"

================================================================================
## EDIT 100  @ 2026-08-28T19:08:49

--- FIND ---
        plotter.clear_actors()
        if d.has_model:
            plotter.add_mesh(pv.read(str(d.stl_path)), color="lightsteelblue",
                             smooth_shading=True)
            plotter.reset_camera()
        o, p = d.objectives, d.params
--- REPLACE WITH ---
        if d.has_model:
            _draw(d.stl_path, "lightsteelblue")  # renders with highlight/envelope aids
        else:
            plotter.clear_actors()
        o, p = d.objectives, d.params

================================================================================
## EDIT 101  @ 2026-08-28T19:09:02

--- FIND ---
                        with v3.VCard(style="height:420px;"):
                            view = plotter_ui(plotter)
--- REPLACE WITH ---
                        with v3.VCard(classes="pa-2"):
                            with v3.VRow(no_gutters=True, classes="align-center"):
                                with v3.VCol(cols=7):
                                    v3.VSwitch(v_model=("highlight_spec",), density="compact",
                                               hide_details=True, color="error", inset=True,
                                               label="Highlight out-of-spec (red)")
                                with v3.VCol(cols=5):
                                    v3.VSwitch(v_model=("show_envelope",), density="compact",
                                               hide_details=True, color="success", inset=True,
                                               label="Case envelope")
                            html.Div("Red = geometry past the fan's nominal tip diameter or depth. "
                                     "Envelope = the max tip-dia × depth the blade must fit inside.",
                                     classes="text-caption text-medium-emphasis")
                        with v3.VCard(style="height:420px;"):
                            view = plotter_ui(plotter)

================================================================================
## EDIT 102  @ 2026-08-28T20:08:05

--- FIND ---
    "e_tip_radius": "Blade LENGTH (outer radius). Shrink it to make an oversized blade fit the frame (tip diameter) or trim depth.",
--- REPLACE WITH ---
    "e_tip_radius": "Blade LENGTH (outer radius). Shrink it to make an oversized blade fit the frame (tip diameter) or trim depth.",
    "e_hub_height": "Hub HEIGHT (mm). 0 = auto (just covers the blade roots — shortest). Raise it for a taller hub; it can't go below root coverage.",
    "e_hub_nose": "Nose height (mm) for the cone/dome hub profile. Adds a spinner on the intake side (increases depth — may go over-spec).",

================================================================================
## EDIT 103  @ 2026-08-28T20:08:10

--- FIND ---
        state.e_hub_radius = float(p.get("hub_radius", 21.5))       # hub radius (mm)
        state.e_tip_radius = float(p.get("tip_radius", 56.5))       # tip radius = blade length (mm)
--- REPLACE WITH ---
        state.e_hub_radius = float(p.get("hub_radius", 21.5))       # hub radius (mm)
        state.e_tip_radius = float(p.get("tip_radius", 56.5))       # tip radius = blade length (mm)
        state.e_hub_height = float(p.get("hub_height", 0.0))        # hub height (0 = auto/cover roots)
        state.e_hub_profile = str(p.get("hub_profile", "cylinder"))  # cylinder | cone | dome
        state.e_hub_nose = float(p.get("hub_nose", 0.0))            # nose height for cone/dome

================================================================================
## EDIT 104  @ 2026-08-28T20:08:18

--- FIND ---
            hub_radius=state.e_hub_radius, tip_radius=state.e_tip_radius,
            thickness_root=state.e_thick_root, thickness_mid=state.e_thick_mid,
            thickness_tip=state.e_thick_tip,
            spacing_spread=state.e_spacing, spacing_seed=0,
        )
--- REPLACE WITH ---
            hub_radius=state.e_hub_radius, tip_radius=state.e_tip_radius,
            hub_height=state.e_hub_height, hub_profile=state.e_hub_profile,
            hub_nose=state.e_hub_nose,
            thickness_root=state.e_thick_root, thickness_mid=state.e_thick_mid,
            thickness_tip=state.e_thick_tip,
            spacing_spread=state.e_spacing, spacing_seed=0,
        )

================================================================================
## EDIT 105  @ 2026-08-28T20:08:22

--- FIND ---
        "e_hub_radius", "e_tip_radius", "e_thick_root", "e_thick_mid", "e_thick_tip", "e_spacing",
--- REPLACE WITH ---
        "e_hub_radius", "e_tip_radius", "e_hub_height", "e_hub_profile", "e_hub_nose",
        "e_thick_root", "e_thick_mid", "e_thick_tip", "e_spacing",

================================================================================
## EDIT 106  @ 2026-08-28T20:08:36

--- FIND ---
    state.highlight_spec = True
    state.show_envelope = False
--- REPLACE WITH ---
    state.highlight_spec = True
    state.show_envelope = False
    state.hub_profiles = ["cylinder", "cone", "dome"]  # hub nose-shape options

================================================================================
## EDIT 107  @ 2026-08-28T20:08:41

--- FIND ---
                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
                                        _slider("Tip radius / length (mm)", "e_tip_radius", 45, 59, 0.5)
--- REPLACE WITH ---
                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
                                        _slider("Tip radius / length (mm)", "e_tip_radius", 45, 59, 0.5)
                                        _slider("Hub height (mm, 0=auto)", "e_hub_height", 0, 30, 0.5)
                                        v3.VSelect(label="Hub profile", v_model=("e_hub_profile",),
                                                   items=("hub_profiles",), density="compact",
                                                   variant="outlined", hide_details=True,
                                                   classes="mb-3")
                                        _slider("Hub nose (mm, cone/dome)", "e_hub_nose", 0, 15, 0.5)

================================================================================
## EDIT 108  @ 2026-08-28T20:09:15

--- FIND ---
    try:
        saved = base - _blade_z_extent(blade_from_flat(f, Features()))
        if saved > 0.3:
            out.append(("Thinner blades", saved))
    except Exception:  # noqa: BLE001
        pass
    out.sort(key=lambda t: -t[1])
    return out[:top]
--- REPLACE WITH ---
    try:
        saved = base - _blade_z_extent(blade_from_flat(f, Features()))
        if saved > 0.3:
            out.append(("Thinner blades", saved))
    except Exception:  # noqa: BLE001
        pass
    # Hub contributions to TOTAL depth (the hub, not just the blades, can be the binding element).
    nose = float(flat.get("hub_nose", 0.0))
    if nose > 0.3 and str(flat.get("hub_profile", "cylinder")).lower() != "cylinder":
        out.append(("Hub nose (set profile to cylinder / 0 nose)", nose))
    hh = float(flat.get("hub_height", 0.0))
    if hh > 0.0:  # explicit hub taller than the auto (root-covering) minimum adds depth
        try:
            from fansim.geometry.blade import _root_axial_span
            p = blade_from_flat(flat, Features())
            r_lo, r_hi = _root_axial_span(p)
            auto_h = (r_hi - r_lo) + 2.0 * p.hub_axial_margin
            if hh - auto_h > 0.3:
                out.append(("Hub height above auto (set Hub height to 0)", hh - auto_h))
        except Exception:  # noqa: BLE001
            pass
    out.sort(key=lambda t: -t[1])
    return out[:top]

================================================================================
## EDIT 109  @ 2026-08-28T22:01:46

--- FIND ---
            feats = "features ON" if params.features.active else "smooth"
            _, status = spec_status(preview_stl, params, flat)   # spec check now, before any CFD
            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                                 f"camber {state.e_camber:.3f}, {feats}.\n{status}")
--- REPLACE WITH ---
            feats = "features ON" if params.features.active else "smooth"
            _, status = spec_status(preview_stl, params, flat)   # spec check now, before any CFD
            try:
                from fansim.manufacturability.printability_score import grade_printability
                print_line = "\n🖨 " + grade_printability(params).summary
            except Exception:  # noqa: BLE001 - printability grade is informational
                print_line = ""
            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                                 f"camber {state.e_camber:.3f}, {feats}.\n{status}{print_line}")

================================================================================
## EDIT 110  @ 2026-08-28T22:25:41

--- FIND ---
    def on_plotly_click(event=None):
        pts = (event or {}).get("points") or []
        if pts and pts[0].get("customdata") is not None:
            state.selected_trial = int(pts[0]["customdata"])
--- REPLACE WITH ---
    def on_plotly_click(event=None):
        pts = (event or {}).get("points") or []
        if pts and pts[0].get("customdata") is not None:
            state.selected_trial = int(pts[0]["customdata"])
            state.flush()  # push the new selection back so the Design dropdown syncs to the clicked point

================================================================================
## EDIT 111  @ 2026-08-28T22:31:10

--- FIND ---
import asyncio
import base64
import dataclasses
import json
import tempfile
--- REPLACE WITH ---
import asyncio
import base64
import dataclasses
import json
import random
import tempfile

================================================================================
## EDIT 112  @ 2026-08-28T22:31:21

--- FIND ---
    def build_edit_params():
        return blade_from_flat(edit_flat(), edit_features())
--- REPLACE WITH ---
    def randomize_features():
        """Roll a random bio-feature combo on the CURRENT geometry — a creativity seed to preview,
        assess, or optimize from. Geometry is untouched, so the result stays buildable. At least one
        feature is always turned on (each with its count) so you actually get something 'crazy'."""
        on = {k: random.random() < 0.6 for k in ("tub", "ser", "dim")}
        if not any(on.values()):
            on[random.choice(("tub", "ser", "dim"))] = True
        state.e_tub_amp = round(random.uniform(0.02, 0.10), 3) if on["tub"] else 0.0
        state.e_tub_waves = random.randint(3, 8) if on["tub"] else 0
        state.e_ser_amp = round(random.uniform(0.015, 0.06), 3) if on["ser"] else 0.0
        state.e_ser_waves = random.randint(4, 12) if on["ser"] else 0
        state.e_dim_amp = round(random.uniform(0.10, 0.35), 2) if on["dim"] else 0.0
        state.e_dim_rows = random.randint(2, 6) if on["dim"] else 0
        state.e_dim_cols = random.randint(2, 6) if on["dim"] else 0
        active = ", ".join(k for k, v in on.items() if v)
        state.preview_msg = f"🎲 Randomized features ({active}). Press Preview geometry to see it."
        state.flush()

    def build_edit_params():
        return blade_from_flat(edit_flat(), edit_features())

================================================================================
## EDIT 113  @ 2026-08-28T22:31:26

--- FIND ---
                                with v3.VExpansionPanel(title="Features (bio-inspired)"):
                                    with v3.VExpansionPanelText():
                                        _slider("Tubercle amp", "e_tub_amp", 0.0, 0.10, 0.01)
--- REPLACE WITH ---
                                with v3.VExpansionPanel(title="Features (bio-inspired)"):
                                    with v3.VExpansionPanelText():
                                        v3.VBtn("🎲 Randomize features", size="x-small",
                                                variant="tonal", color="secondary", block=True,
                                                click=(randomize_features,), classes="mb-3")
                                        _slider("Tubercle amp", "e_tub_amp", 0.0, 0.10, 0.01)

================================================================================
## EDIT 114  @ 2026-08-28T22:55:12

--- FIND ---
            mode="markers", name=name,
            marker=dict(
                size=[22 if d.is_pareto else 14 for d in designs],
--- REPLACE WITH ---
            mode="markers", name=name,
            marker=dict(
                # bigger markers = easier click targets (plotly only fires a click on a precise hit)
                size=[30 if d.is_pareto else 20 for d in designs],

================================================================================
## EDIT 115  @ 2026-08-28T22:55:36

--- FIND ---
    def build_edit_params():
        return blade_from_flat(edit_flat(), edit_features())
--- REPLACE WITH ---
    def randomize_geometry():
        """Roll a random GEOMETRY (blades/angles/chords/sweep/wrap/hub) — a wild starting point to
        preview, assess, or optimize from. May land out-of-spec (Preview shows it); that's fine, it's
        a creativity seed. Leaves the feature layer alone (that has its own dice)."""
        import random as _r
        state.e_n_blades = _r.randint(5, 11)
        state.e_stagger_root = round(_r.uniform(18, 48), 1)
        state.e_stagger_mid = round(_r.uniform(18, 48), 1)
        state.e_stagger_tip = round(_r.uniform(16, 40), 1)
        state.e_chord_root = round(_r.uniform(16, 40), 1)
        state.e_chord_mid = round(_r.uniform(16, 42), 1)
        state.e_chord_tip = round(_r.uniform(16, 40), 1)
        state.e_sweep_mid = round(_r.uniform(-3, 8), 1)
        state.e_sweep_tip = round(_r.uniform(0, 12), 1)
        state.e_camber = round(_r.uniform(0.0, 0.06), 3)
        state.e_camber_pos = round(_r.uniform(0.3, 0.5), 2)
        state.e_lean_mid = round(_r.uniform(0, 25), 1)
        state.e_lean_tip = round(_r.uniform(0, 45), 1)
        state.e_le_mid = round(_r.uniform(-8, 8), 1)
        state.e_le_tip = round(_r.uniform(-8, 8), 1)
        state.e_hub_radius = round(_r.uniform(17, 28), 1)
        state.e_tip_radius = round(_r.uniform(48, 58), 1)
        state.e_thick_root = round(_r.uniform(0.06, 0.12), 3)
        state.e_thick_mid = round(_r.uniform(0.05, 0.10), 3)
        state.e_thick_tip = round(_r.uniform(0.04, 0.08), 3)
        state.e_hub_profile = _r.choice(["cylinder", "cylinder", "cone", "dome"])  # bias to plain
        state.e_hub_nose = round(_r.uniform(3, 12), 1) if state.e_hub_profile != "cylinder" else 0.0
        state.preview_msg = "🎲 Randomized geometry. Press Preview geometry to see it (may be out-of-spec)."
        state.flush()

    def build_edit_params():
        return blade_from_flat(edit_flat(), edit_features())

================================================================================
## EDIT 116  @ 2026-08-28T22:55:47

--- FIND ---
                                with v3.VExpansionPanel(title="Geometry"):
                                    with v3.VExpansionPanelText():
                                        _slider("Blades", "e_n_blades", 5, 11, 1)
--- REPLACE WITH ---
                                with v3.VExpansionPanel(title="Geometry"):
                                    with v3.VExpansionPanelText():
                                        v3.VBtn("🎲 Randomize geometry", size="x-small",
                                                variant="tonal", color="secondary", block=True,
                                                click=(randomize_geometry,), classes="mb-3")
                                        _slider("Blades", "e_n_blades", 5, 11, 1)

================================================================================
## EDIT 117  @ 2026-08-28T23:18:56

--- FIND ---
    def on_plotly_click(event=None):
        pts = (event or {}).get("points") or []
        if pts and pts[0].get("customdata") is not None:
            state.selected_trial = int(pts[0]["customdata"])
            state.flush()  # push the new selection back so the Design dropdown syncs to the clicked point
--- REPLACE WITH ---
    def on_plotly_click(trial=None):
        # We receive ONLY the clicked point's customdata (the trial id), not the whole plotly event:
        # the full $event contains non-serializable fields (functions/DOM refs) that fail to marshal to
        # the server, so the click never arrived. Extracting customdata client-side (see the binding)
        # sends a plain number that serializes cleanly.
        if trial is not None:
            state.selected_trial = int(trial)
            state.flush()  # push the new selection back so the Design dropdown syncs to the clicked point

================================================================================
## EDIT 118  @ 2026-08-28T23:19:01

--- FIND ---
                        fig_widget = plotly_widgets.Figure(
                            figure=scatter_figure(study_designs, user_designs),
                            click=(on_plotly_click, "[$event]"),
                            style="width:100%;",
                        )
--- REPLACE WITH ---
                        fig_widget = plotly_widgets.Figure(
                            figure=scatter_figure(study_designs, user_designs),
                            # send ONLY the clicked point's customdata (trial id) — the full $event has
                            # non-serializable fields that silently break the round-trip to the server.
                            click=(on_plotly_click, "[$event?.points?.[0]?.customdata]"),
                            style="width:100%;",
                        )

================================================================================
## EDIT 119  @ 2026-08-29T02:14:56

--- FIND ---
from fansim.optimize.isolated_eval import evaluate_candidate_isolated
from fansim.optimize.search_space import blade_from_flat
--- REPLACE WITH ---
from fansim.optimize.isolated_eval import evaluate_candidate_isolated
from fansim.optimize.search_space import blade_from_flat
from validation.ingest import MeasuredPoint
from validation.store import make_design_id, record_measurement, sim_vs_real

================================================================================
## EDIT 120  @ 2026-08-29T02:15:07

--- FIND ---
    state.highlight_spec = True
    state.show_envelope = False
    state.hub_profiles = ["cylinder", "cone", "dome"]  # hub nose-shape options
--- REPLACE WITH ---
    state.highlight_spec = True
    state.show_envelope = False
    state.hub_profiles = ["cylinder", "cone", "dome"]  # hub nose-shape options
    # physical-measurement recorder (fills validation/measurements/ — the sim-vs-real bridge)
    state.meas_cfm = None
    state.meas_static = None
    state.meas_noise = None
    state.meas_rpm = None
    state.meas_instrument = ""
    state.meas_notes = ""
    state.meas_msg = "Select a design, print + test it, then record what you measured."

================================================================================
## EDIT 121  @ 2026-08-29T02:15:40

--- FIND ---
    @state.change("selected_trial")
    def _on_dropdown(selected_trial=None, **_):
        select(selected_trial)
--- REPLACE WITH ---
    @state.change("selected_trial")
    def _on_dropdown(selected_trial=None, **_):
        select(selected_trial)

    def _mf(v):
        """Coerce a text-field value to float or None (blank fields come back as '' / None)."""
        try:
            return float(v) if v not in (None, "", "None") else None
        except (TypeError, ValueError):
            return None

    def save_measurement():
        """Save what the user physically measured for the selected design, tied to its sim numbers."""
        tid = state.selected_trial
        d = by_trial.get(int(tid)) if tid is not None else None
        if d is None:
            state.meas_msg = "⚠ Select a design first (click a point or use the dropdown)."
            state.flush(); return
        if _mf(state.meas_cfm) is None and _mf(state.meas_static) is None and _mf(state.meas_noise) is None:
            state.meas_msg = "⚠ Enter at least one measured value (CFM / static Pa / dB(A))."
            state.flush(); return
        run = d.extra.get("source_run") or run_dir.name
        design_id = make_design_id(run, d.trial)
        sim = {"cfm_free": d.objectives.get("cfm_free"), "cfm_load": d.objectives.get("cfm_load"),
               "efficiency": d.objectives.get("efficiency"), "actual_rpm": d.extra.get("actual_rpm")}
        rpm = _mf(state.meas_rpm) or d.extra.get("actual_rpm") or active_spec().rpm
        pt = MeasuredPoint(rpm=float(rpm), cfm=_mf(state.meas_cfm),
                           static_pressure_pa=_mf(state.meas_static), noise_dba=_mf(state.meas_noise),
                           source=state.meas_instrument or "")
        rec = record_measurement(design_id, pt, run=run, trial=d.trial,
                                 stl_path=str(d.stl_path) if d.has_model else "",
                                 material=active_spec().material, sim=sim,
                                 instrument=state.meas_instrument, notes=state.meas_notes)
        last = sim_vs_real(rec)[-1]
        parts = []
        if "cfm" in last:
            parts.append(f"CFM {last['cfm']['measured']:.1f} vs sim free {last['cfm']['sim']:.1f} "
                         f"(sim over-reads {last['cfm']['pct_error']:+.0f}%)")
        if "noise_dba" in last:
            parts.append(f"noise {last['noise_dba']['measured']:.1f} dBA "
                         f"(Δ{last['noise_dba']['delta_db']:+.1f} vs sim)")
        state.meas_msg = (f"✓ Saved to validation/measurements/ for {design_id} "
                          f"({len(rec.measured)} point(s)). " + "  ".join(parts))
        state.flush()

================================================================================
## EDIT 122  @ 2026-08-29T02:16:15

--- FIND ---
                            html.Div("{{ assess_msg }}", classes="text-caption mt-2",
                                     style="white-space: pre-line")
                        with v3.VCard(classes="pa-2"):
                            with v3.VRow(no_gutters=True, classes="align-center"):
                                with v3.VCol(cols=7):
                                    v3.VSwitch(v_model=("highlight_spec",), density="compact",
--- REPLACE WITH ---
                            html.Div("{{ assess_msg }}", classes="text-caption mt-2",
                                     style="white-space: pre-line")
                        with v3.VExpansionPanels(classes="mb-2"):
                            with v3.VExpansionPanel(title="Record measurement (physical)"):
                                with v3.VExpansionPanelText():
                                    html.Div("Printed + tested a design? Enter what you measured — it's "
                                             "saved to validation/measurements/ tied to this design's sim "
                                             "numbers, and compared. (Select the design first.)",
                                             classes="text-caption mb-2")
                                    with v3.VRow(no_gutters=True):
                                        with v3.VCol(cols=6, classes="pr-1"):
                                            v3.VTextField(label="Measured CFM", v_model=("meas_cfm",),
                                                          type="number", density="compact",
                                                          variant="outlined", hide_details=True,
                                                          classes="mb-2")
                                        with v3.VCol(cols=6, classes="pl-1"):
                                            v3.VTextField(label="Static Pa", v_model=("meas_static",),
                                                          type="number", density="compact",
                                                          variant="outlined", hide_details=True,
                                                          classes="mb-2")
                                    with v3.VRow(no_gutters=True):
                                        with v3.VCol(cols=6, classes="pr-1"):
                                            v3.VTextField(label="Noise dB(A)", v_model=("meas_noise",),
                                                          type="number", density="compact",
                                                          variant="outlined", hide_details=True,
                                                          classes="mb-2")
                                        with v3.VCol(cols=6, classes="pl-1"):
                                            v3.VTextField(label="RPM", v_model=("meas_rpm",),
                                                          type="number", density="compact",
                                                          variant="outlined", hide_details=True,
                                                          classes="mb-2")
                                    v3.VTextField(label="Instrument", v_model=("meas_instrument",),
                                                  density="compact", variant="outlined",
                                                  hide_details=True, classes="mb-2")
                                    v3.VTextField(label="Notes", v_model=("meas_notes",),
                                                  density="compact", variant="outlined",
                                                  hide_details=True, classes="mb-2")
                                    v3.VBtn("Save measurement", color="primary", size="small",
                                            block=True, click=(save_measurement,))
                                    html.Div("{{ meas_msg }}", classes="text-caption mt-2",
                                             style="white-space: pre-line")
                        with v3.VCard(classes="pa-2"):
                            with v3.VRow(no_gutters=True, classes="align-center"):
                                with v3.VCol(cols=7):
                                    v3.VSwitch(v_model=("highlight_spec",), density="compact",

================================================================================
## EDIT 123  @ 2026-08-29T16:27:30

--- FIND ---
from fansim.cockpit.data import Design, feasible_designs, load_designs
--- REPLACE WITH ---
from fansim.catalog import build_catalog, get_entry, load_catalog
from fansim.cockpit.data import Design, feasible_designs, load_designs

================================================================================
## EDIT 124  @ 2026-08-29T16:27:41

--- FIND ---
    state.meas_msg = "Select a design, print + test it, then record what you measured."
--- REPLACE WITH ---
    state.meas_msg = "Select a design, print + test it, then record what you measured."
    # unified catalog: every design across ALL runs, so the cockpit isn't limited to the loaded --run
    def _catalog_items():
        items = []
        for e in load_catalog():
            star = " ★" if e.is_pareto else ""
            meas = "  ✓meas" if e.has_measurement else ""
            free = f"{e.cfm_free:.0f}" if isinstance(e.cfm_free, (int, float)) else "?"
            items.append({"title": f"{e.design_id}  ·  {free} CFM{star}{meas}", "value": e.design_id})
        return items
    try:
        build_catalog()                     # refresh the index from all runs + measurements (cheap scan)
    except Exception:  # noqa: BLE001 - the catalog is a convenience; never block cockpit startup
        pass
    state.catalog_items = _catalog_items()
    state.catalog_sel = None
    state.catalog_info = f"{len(state.catalog_items)} designs across all runs. Pick one to load it here."

================================================================================
## EDIT 125  @ 2026-08-29T16:28:02

--- FIND ---
    state.change(*EDITOR_VARS)(_recompute_stale)

    def active_spec():
--- REPLACE WITH ---
    state.change(*EDITOR_VARS)(_recompute_stale)

    def load_catalog_design(design_id=None, **_):
        """Load ANY catalogued design (from any run) into the editor — breaks the single-run limit.
        Its params fill the sliders; press Preview to see it. Its sim numbers + any real measurement
        are shown so you can compare across runs without relaunching the cockpit."""
        if not design_id:
            return
        e = get_entry(design_id)
        if e is None:
            state.catalog_info = f"'{design_id}' not in the catalog (rebuild it if it's new)."
            state.flush()
            return
        _init_editor(e.params)          # params fill the editor sliders (features fall back to 0)
        _set_baseline()                 # editor now matches this design — not stale until edited
        parts = [f"Loaded {e.design_id}", f"{e.source}"]
        if isinstance(e.cfm_free, (int, float)):
            parts.append(f"sim {e.cfm_free:.0f}/{e.cfm_load or 0:.0f} CFM  eff {e.efficiency or 0:.0f}%")
        if e.has_measurement and e.measured_cfm is not None:
            parts.append(f"MEASURED {e.measured_cfm:.0f} CFM (sim {e.cfm_error_pct:+.0f}%)"
                         if e.cfm_error_pct is not None else f"MEASURED {e.measured_cfm:.0f} CFM")
        state.catalog_info = "  ·  ".join(parts)
        state.preview_msg = f"Loaded {e.design_id} from the catalog. Press Preview geometry to see it."
        state.flush()

    def active_spec():

================================================================================
## EDIT 126  @ 2026-08-29T16:28:20

--- FIND ---
                            html.Div(
                                "{{ line }}",
                                v_for="line in info_lines",
                                classes="text-body-2 mt-2",
                            )
                        with v3.VCard(classes="mb-2 pa-3"):
                            html.Div("Modify design — hover any slider for a min/max picture + what it does",
                                     classes="text-caption mb-1")
--- REPLACE WITH ---
                            html.Div(
                                "{{ line }}",
                                v_for="line in info_lines",
                                classes="text-body-2 mt-2",
                            )
                        with v3.VExpansionPanels(classes="mb-2"):
                            with v3.VExpansionPanel(title="Browse all designs (catalog)"):
                                with v3.VExpansionPanelText():
                                    v3.VSelect(label="Any design, any run", v_model=("catalog_sel",),
                                               items=("catalog_items",), density="compact",
                                               variant="outlined", hide_details=True,
                                               update_modelValue=(load_catalog_design, "[$event]"))
                                    html.Div("{{ catalog_info }}", classes="text-caption mt-2",
                                             style="white-space: pre-line")
                        with v3.VCard(classes="mb-2 pa-3"):
                            html.Div("Modify design — hover any slider for a min/max picture + what it does",
                                     classes="text-caption mb-1")

================================================================================
## EDIT 127  @ 2026-08-30T01:07:18

--- FIND ---
            try:
                from fansim.manufacturability.printability_score import grade_printability
                print_line = "\n🖨 " + grade_printability(params).summary
            except Exception:  # noqa: BLE001 - printability grade is informational
                print_line = ""
            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                                 f"camber {state.e_camber:.3f}, {feats}.\n{status}{print_line}")
--- REPLACE WITH ---
            try:
                from fansim.manufacturability.printability_score import grade_printability
                print_line = "\n🖨 " + grade_printability(params).summary
            except Exception:  # noqa: BLE001 - printability grade is informational
                print_line = ""
            # Uneven-spacing tonal readout (CFD-validated: cuts the peak tone ~5-6 dB at its best on odd
            # blade counts, for free). Predicted from the balanced-spacing pattern, no GPU needed.
            tone_line = ""
            if params.blade_angles_deg is not None:
                try:
                    import numpy as _np
                    from fansim.acoustics.tonal import peak_tone_reduction_db
                    drop = -peak_tone_reduction_db(_np.radians(_np.asarray(params.blade_angles_deg)))
                    odd = "" if params.n_blades % 2 else "  (even blade count — odd counts spread the tone more)"
                    tone_line = f"\n🔉 Uneven spacing: predicted peak tone −{drop:.1f} dB, free of any flow cost{odd}"
                except Exception:  # noqa: BLE001
                    tone_line = ""
            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                                 f"camber {state.e_camber:.3f}, {feats}.\n{status}{print_line}{tone_line}")

================================================================================
## EDIT 128  @ 2026-08-30T01:26:49

--- FIND ---
    def build_edit_params():
        return blade_from_flat(edit_flat(), edit_features())
--- REPLACE WITH ---
    def build_edit_params():
        return blade_from_flat(edit_flat(), edit_features())

    def export_stl_current():
        """Save the current design as a print-ready STL (motor-mount cup carved) into exports/."""
        from fansim.manufacturability.print_export import export_print_ready
        params = build_edit_params()
        spec = active_spec()
        exports = Path("exports")
        exports.mkdir(exist_ok=True)
        tid = state.selected_trial
        name = f"design_{tid}" if tid is not None else "fan_current"
        out = exports / f"{name}.stl"
        try:
            rep = export_print_ready(params, out, mount=spec.motor_mount)
        except Exception as exc:  # noqa: BLE001
            state.export_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
            state.flush()
            return
        wt = "watertight" if rep.ok else "⚠ NON-manifold"
        mnt = ("" if rep.mount_fits is None else
               ("· mountable" if rep.mount_fits else "· ⚠ hub too small to mount"))
        state.export_msg = f"✓ Saved {out.resolve()}  ({wt} {mnt})"
        state.flush()

================================================================================
## EDIT 129  @ 2026-08-30T01:26:55

--- FIND ---
                                v3.VBtn("Reset", size="small", variant="tonal",
                                        click=(select, "[selected_trial]"))
                            html.Div("{{ preview_msg }}", classes="text-caption mt-2",
                                     style="white-space: pre-line")
--- REPLACE WITH ---
                                v3.VBtn("Reset", size="small", variant="tonal",
                                        click=(select, "[selected_trial]"), classes="mr-2")
                                v3.VBtn("💾 Export STL", size="small", variant="tonal",
                                        color="primary", click=(export_stl_current,))
                            html.Div("{{ preview_msg }}", classes="text-caption mt-2",
                                     style="white-space: pre-line")
                            html.Div("{{ export_msg }}", classes="text-caption mt-1",
                                     style="white-space: pre-line")

================================================================================
## EDIT 130  @ 2026-08-30T01:27:00

--- FIND ---
    state.preview_msg = "Select a design, then edit and press Preview geometry."
--- REPLACE WITH ---
    state.preview_msg = "Select a design, then edit and press Preview geometry."
    state.export_msg = ""

================================================================================
## EDIT 131  @ 2026-08-30T01:33:30

--- FIND ---
    def refresh_figure():
        fig = scatter_figure(study_designs, user_designs)
        if hasattr(ctrl, "figure_update"):
            ctrl.figure_update(fig)
--- REPLACE WITH ---
    def _thin(designs, cell: float = 2.5):
        """Keep one design per ~cell-CFM bucket in (free, load) space — pareto first, then best eff.
        Non-destructive: only the PLOTTED set is thinned; nothing is removed from disk or the dropdown."""
        best = {}
        for d in designs:
            key = (round(d.objectives["cfm_free"] / cell), round(d.objectives["cfm_load"] / cell))
            cur = best.get(key)
            rank = (d.is_pareto, d.objectives.get("efficiency", 0))
            if cur is None or rank > (cur.is_pareto, cur.objectives.get("efficiency", 0)):
                best[key] = d
        return list(best.values())

    def refresh_figure():
        sd = _thin(study_designs) if state.declutter else study_designs
        ud = _thin(list(user_designs)) if state.declutter else user_designs
        fig = scatter_figure(sd, ud)
        if hasattr(ctrl, "figure_update"):
            ctrl.figure_update(fig)

    @state.change("declutter")
    def _on_declutter(**_):
        refresh_figure()

================================================================================
## EDIT 132  @ 2026-08-30T01:33:37

--- FIND ---
    state.hub_profiles = ["cylinder", "cone", "dome"]  # hub nose-shape options
--- REPLACE WITH ---
    state.hub_profiles = ["cylinder", "cone", "dome"]  # hub nose-shape options
    state.declutter = False   # thin near-duplicate points in the design-space plot (view only)

================================================================================
## EDIT 133  @ 2026-08-30T01:33:47

--- FIND ---
                with v3.VRow(no_gutters=True):
                    with v3.VCol(cols=6, classes="pr-2"):
                        fig_widget = plotly_widgets.Figure(
                            figure=scatter_figure(study_designs, user_designs),
--- REPLACE WITH ---
                with v3.VRow(no_gutters=True):
                    with v3.VCol(cols=6, classes="pr-2"):
                        v3.VSwitch(v_model=("declutter",), density="compact", hide_details=True,
                                   inset=True, color="primary", classes="ml-2",
                                   label="Declutter (hide near-duplicate designs)")
                        fig_widget = plotly_widgets.Figure(
                            figure=scatter_figure(study_designs, user_designs),

================================================================================
## EDIT 134  @ 2026-08-30T02:20:59

--- FIND ---
    "e_le_mid": "Rakes only the LEADING edge at mid-span — curves the LE line, trailing edge unchanged.",
    "e_le_tip": "Rakes only the LEADING edge at the tip.",
--- REPLACE WITH ---
    "e_le_mid": "Rakes only the LEADING edge at mid-span — curves the LE line, trailing edge unchanged.",
    "e_le_tip": "Rakes only the LEADING edge at the tip.",
    "e_skew_mid": "Skew (mm) — shifts the whole mid section sideways (tangentially). Fine balance/overlap tweak.",
    "e_skew_tip": "Skew (mm) — shifts the whole tip section sideways (tangentially).",

================================================================================
## EDIT 135  @ 2026-08-30T02:21:04

--- FIND ---
        state.e_le_mid = float(p.get("le_sweep_mid", 0.0))  # leading-edge curve (mm)
        state.e_le_tip = float(p.get("le_sweep_tip", 0.0))
--- REPLACE WITH ---
        state.e_le_mid = float(p.get("le_sweep_mid", 0.0))  # leading-edge curve (mm)
        state.e_le_tip = float(p.get("le_sweep_tip", 0.0))
        state.e_skew_mid = float(p.get("skew_mid", 0.0))    # tangential fine offset (mm)
        state.e_skew_tip = float(p.get("skew_tip", 0.0))

================================================================================
## EDIT 136  @ 2026-08-30T02:21:08

--- FIND ---
            le_sweep_mid=state.e_le_mid, le_sweep_tip=state.e_le_tip,
--- REPLACE WITH ---
            le_sweep_mid=state.e_le_mid, le_sweep_tip=state.e_le_tip,
            skew_mid=state.e_skew_mid, skew_tip=state.e_skew_tip,

================================================================================
## EDIT 137  @ 2026-08-30T02:21:13

--- FIND ---
        state.e_le_mid = round(_r.uniform(-8, 8), 1)
        state.e_le_tip = round(_r.uniform(-8, 8), 1)
--- REPLACE WITH ---
        state.e_le_mid = round(_r.uniform(-8, 8), 1)
        state.e_le_tip = round(_r.uniform(-8, 8), 1)
        state.e_skew_mid = round(_r.uniform(-4, 4), 1)
        state.e_skew_tip = round(_r.uniform(-4, 4), 1)

================================================================================
## EDIT 138  @ 2026-08-30T02:21:17

--- FIND ---
        "e_camber", "e_camber_pos", "e_lean_mid", "e_lean_tip", "e_le_mid", "e_le_tip",
--- REPLACE WITH ---
        "e_camber", "e_camber_pos", "e_lean_mid", "e_lean_tip", "e_le_mid", "e_le_tip",
        "e_skew_mid", "e_skew_tip",

================================================================================
## EDIT 139  @ 2026-08-30T02:21:23

--- FIND ---
                                        _slider("LE curve mid (mm)", "e_le_mid", -8, 8, 0.5)
                                        _slider("LE curve tip (mm)", "e_le_tip", -8, 8, 0.5)
--- REPLACE WITH ---
                                        _slider("LE curve mid (mm)", "e_le_mid", -8, 8, 0.5)
                                        _slider("LE curve tip (mm)", "e_le_tip", -8, 8, 0.5)
                                        _slider("Skew mid (mm)", "e_skew_mid", -6, 6, 0.5)
                                        _slider("Skew tip (mm)", "e_skew_tip", -6, 6, 0.5)

================================================================================
## EDIT 140  @ 2026-08-30T02:23:02

--- FIND ---
        parts = [f"Loaded {e.design_id}", f"{e.source}"]
        if isinstance(e.cfm_free, (int, float)):
            parts.append(f"sim {e.cfm_free:.0f}/{e.cfm_load or 0:.0f} CFM  eff {e.efficiency or 0:.0f}%")
        if e.has_measurement and e.measured_cfm is not None:
--- REPLACE WITH ---
        parts = [f"Loaded {e.design_id}", f"{e.source}"]
        if isinstance(e.cfm_free, (int, float)):
            parts.append(f"sim {e.cfm_free:.0f}/{e.cfm_load or 0:.0f} CFM  eff {e.efficiency or 0:.0f}%")
        try:  # mountability + print difficulty for the loaded design (cheap, no CFD)
            from fansim.fan_spec import mount_min_hub_radius
            from fansim.manufacturability.printability_score import grade_printability
            lp = blade_from_flat(e.params)
            need = mount_min_hub_radius(active_spec())
            parts.append("mountable" if (need is None or lp.hub_radius >= need) else "NOT mountable")
            parts.append(f"print {grade_printability(lp).difficulty:.0f}/100")
        except Exception:  # noqa: BLE001
            pass
        if e.has_measurement and e.measured_cfm is not None:

================================================================================
## EDIT 141  @ 2026-08-30T02:30:29

--- FIND ---
    "e_skew_mid": "Skew (mm) — shifts the whole mid section sideways (tangentially). Fine balance/overlap tweak.",
    "e_skew_tip": "Skew (mm) — shifts the whole tip section sideways (tangentially).",
--- REPLACE WITH ---
    "e_skew_mid": "Skew (mm) — shifts the whole mid section sideways (tangentially). Fine balance/overlap tweak.",
    "e_skew_tip": "Skew (mm) — shifts the whole tip section sideways (tangentially).",
    "e_winglet_span": "Where the WINGLET starts (fraction of span). Below this the blade is straight; beyond it the tip curls.",
    "e_winglet_sweep": "Winglet AXIAL bend (mm) — curls the tip forward/up out of the rotation plane (a real winglet). 0 = off.",
    "e_winglet_lean": "Winglet CIRCUMFERENTIAL curl (deg) — wraps the tip around the axis. 0 = off.",

================================================================================
## EDIT 142  @ 2026-08-30T02:30:35

--- FIND ---
        state.e_skew_mid = float(p.get("skew_mid", 0.0))    # tangential fine offset (mm)
        state.e_skew_tip = float(p.get("skew_tip", 0.0))
--- REPLACE WITH ---
        state.e_skew_mid = float(p.get("skew_mid", 0.0))    # tangential fine offset (mm)
        state.e_skew_tip = float(p.get("skew_tip", 0.0))
        state.e_winglet_span = float(p.get("winglet_span", 0.85))  # where the tip winglet begins
        state.e_winglet_sweep = float(p.get("winglet_sweep", 0.0))  # tip axial curl (mm), 0=off
        state.e_winglet_lean = float(p.get("winglet_lean", 0.0))   # tip circumferential curl (deg)

================================================================================
## EDIT 143  @ 2026-08-30T02:30:39

--- FIND ---
            skew_mid=state.e_skew_mid, skew_tip=state.e_skew_tip,
--- REPLACE WITH ---
            skew_mid=state.e_skew_mid, skew_tip=state.e_skew_tip,
            winglet_span=state.e_winglet_span, winglet_sweep=state.e_winglet_sweep,
            winglet_lean=state.e_winglet_lean,

================================================================================
## EDIT 144  @ 2026-08-30T02:30:45

--- FIND ---
        state.e_skew_mid = round(_r.uniform(-4, 4), 1)
        state.e_skew_tip = round(_r.uniform(-4, 4), 1)
--- REPLACE WITH ---
        state.e_skew_mid = round(_r.uniform(-4, 4), 1)
        state.e_skew_tip = round(_r.uniform(-4, 4), 1)
        wl = _r.random() < 0.4   # sometimes throw a winglet on for a wild tip
        state.e_winglet_span = round(_r.uniform(0.75, 0.9), 2)
        state.e_winglet_sweep = round(_r.uniform(4, 12), 1) if wl else 0.0
        state.e_winglet_lean = round(_r.uniform(0, 20), 1) if wl else 0.0

================================================================================
## EDIT 145  @ 2026-08-30T02:30:49

--- FIND ---
        "e_skew_mid", "e_skew_tip",
--- REPLACE WITH ---
        "e_skew_mid", "e_skew_tip", "e_winglet_span", "e_winglet_sweep", "e_winglet_lean",

================================================================================
## EDIT 146  @ 2026-08-30T02:30:55

--- FIND ---
                                        _slider("Skew mid (mm)", "e_skew_mid", -6, 6, 0.5)
                                        _slider("Skew tip (mm)", "e_skew_tip", -6, 6, 0.5)
--- REPLACE WITH ---
                                        _slider("Skew mid (mm)", "e_skew_mid", -6, 6, 0.5)
                                        _slider("Skew tip (mm)", "e_skew_tip", -6, 6, 0.5)
                                        _slider("Winglet start (span)", "e_winglet_span", 0.6, 0.95, 0.05)
                                        _slider("Winglet sweep (mm)", "e_winglet_sweep", 0, 15, 0.5)
                                        _slider("Winglet lean (deg)", "e_winglet_lean", 0, 30, 1)

================================================================================
## EDIT 147  @ 2026-08-30T18:47:30

--- FIND ---
from fansim.optimize.isolated_eval import evaluate_candidate_isolated
from fansim.optimize.search_space import blade_from_flat
from validation.ingest import MeasuredPoint
from validation.store import make_design_id, record_measurement, sim_vs_real
--- REPLACE WITH ---
from fansim.optimize.isolated_eval import evaluate_candidate_isolated
from fansim.optimize.search_space import blade_from_flat
from fansim.prop_spec import get_prop_spec, prop_spec_names
from fansim.propeller.bemt import analyze as bemt_analyze
from fansim.propeller.geometry import build_prop, prop_blade_params
from fansim.propeller.optimize import run_prop_study
from validation.ingest import MeasuredPoint
from validation.store import make_design_id, record_measurement, sim_vs_real

================================================================================
## EDIT 148  @ 2026-08-30T18:47:30

--- FIND ---
from fansim.optimize.isolated_eval import evaluate_candidate_isolated
from fansim.optimize.search_space import blade_from_flat
from validation.ingest import MeasuredPoint
from validation.store import make_design_id, record_measurement, sim_vs_real
--- REPLACE WITH ---
from fansim.optimize.isolated_eval import evaluate_candidate_isolated
from fansim.optimize.search_space import blade_from_flat
from fansim.prop_spec import get_prop_spec, prop_spec_names
from fansim.propeller.bemt import analyze as bemt_analyze
from fansim.propeller.geometry import build_prop, prop_blade_params
from fansim.propeller.optimize import run_prop_study
from validation.ingest import MeasuredPoint
from validation.store import make_design_id, record_measurement, sim_vs_real

================================================================================
## EDIT 149  @ 2026-08-30T18:47:36

--- FIND ---
    plotter = pv.Plotter()
    plotter.background_color = "white"
    plotter.add_axes()
--- REPLACE WITH ---
    plotter = pv.Plotter()
    plotter.background_color = "white"
    plotter.add_axes()

    prop_plotter = pv.Plotter()   # separate 3-D view for the Propeller tab
    prop_plotter.background_color = "white"
    prop_plotter.add_axes()

================================================================================
## EDIT 150  @ 2026-08-30T18:47:36

--- FIND ---
    plotter = pv.Plotter()
    plotter.background_color = "white"
    plotter.add_axes()
--- REPLACE WITH ---
    plotter = pv.Plotter()
    plotter.background_color = "white"
    plotter.add_axes()

    prop_plotter = pv.Plotter()   # separate 3-D view for the Propeller tab
    prop_plotter.background_color = "white"
    prop_plotter.add_axes()

================================================================================
## EDIT 151  @ 2026-08-30T18:48:17

--- FIND ---
    def on_plotly_click(trial=None):
        # We receive ONLY the clicked point's customdata (the trial id), not the whole plotly event:
        # the full $event contains non-serializable fields (functions/DOM refs) that fail to marshal to
        # the server, so the click never arrived. Extracting customdata client-side (see the binding)
        # sends a plain number that serializes cleanly.
        if trial is not None:
            state.selected_trial = int(trial)
            state.flush()  # push the new selection back so the Design dropdown syncs to the clicked point

    with SinglePageLayout(server) as layout:
--- REPLACE WITH ---
    def on_plotly_click(trial=None):
        # We receive ONLY the clicked point's customdata (the trial id), not the whole plotly event:
        # the full $event contains non-serializable fields (functions/DOM refs) that fail to marshal to
        # the server, so the click never arrived. Extracting customdata client-side (see the binding)
        # sends a plain number that serializes cleanly.
        if trial is not None:
            state.selected_trial = int(trial)
            state.flush()  # push the new selection back so the Design dropdown syncs to the clicked point

    # =========================================================================================
    # PROPELLER ARCHETYPE (separate tab). Drone props use pitch-driven twist + BEMT (instant, no
    # CFD): specify a size, tune the blade, analyze thrust/efficiency live, or auto-optimize the
    # whole front in ~1 s, then export a printable STL. Self-contained — no catalog/CFD/measurement
    # machinery (that's the fan's CFD workflow); this is design + fast physics.
    # =========================================================================================
    prop_preview_stl = Path(tempfile.gettempdir()) / "fansim_prop_preview.stl"
    prop_pareto_store: list[dict] = []   # full optimizer front (params kept here; table shows a digest)
    state.active_tab = "fan"
    state.prop_model = "fpv_5inch"
    state.prop_models = prop_spec_names()
    state.prop_info = "Pick a size, tune the blade, then Analyze (instant) or Optimize."
    state.prop_readout = ["Analyze a prop to see thrust, efficiency, and figure of merit."]
    state.prop_busy = False
    state.prop_msg = ""
    state.prop_export_msg = ""
    state.prop_trials = 400
    state.prop_maxpower = 700.0
    state.prop_pareto = []               # display rows for the optimizer front table

    def _init_prop_editor(spec):
        """Load the prop sliders from a spec's default blade (chord fractions + camber defaults)."""
        state.p_n_blades = int(spec.n_blades)
        state.p_pitch = float(spec.pitch_in)
        state.p_chord_root = 0.20
        state.p_chord_mid = 0.26
        state.p_chord_tip = 0.10
        state.p_camber = 0.04

    _init_prop_editor(get_prop_spec(state.prop_model))

    def _prop_model_readout():
        s = get_prop_spec(state.prop_model)
        tip_ms = s.tip_speed_ms(s.rpm_max)
        state.prop_info = (f"{s.name}: {s.diameter_in}×{s.pitch_in} in, {s.n_blades}-blade, "
                           f"{s.shaft.shaft_dia_mm:.0f} mm shaft, ≤{s.rpm_max:.0f} rpm "
                           f"(tip {tip_ms:.0f} m/s, Mach {s.tip_mach(s.rpm_max):.2f}). {s.material}.")

    _prop_model_readout()

    @state.change("prop_model")
    def _on_prop_model(**_):
        _init_prop_editor(get_prop_spec(state.prop_model))
        _prop_model_readout()

    def prop_editor_spec():
        """The selected prop envelope with the editor's blade-count + pitch applied."""
        return dataclasses.replace(get_prop_spec(state.prop_model),
                                   n_blades=int(state.p_n_blades), pitch_in=float(state.p_pitch))

    def prop_editor_params():
        return prop_blade_params(prop_editor_spec(),
                                 chord_frac=(float(state.p_chord_root), float(state.p_chord_mid),
                                             float(state.p_chord_tip)),
                                 camber=float(state.p_camber))

    def _draw_prop(path):
        prop_plotter.clear_actors()
        try:
            prop_plotter.add_mesh(pv.read(str(path)), color="cadetblue", smooth_shading=True)
            prop_plotter.reset_camera()
        except Exception:  # noqa: BLE001 - nothing to show
            pass
        try:
            ctrl.prop_view_update()
        except Exception:  # noqa: BLE001
            pass

    def _prop_perf_lines(spec, params):
        """BEMT readout for the current prop: static hover thrust/eff/FM + a forward-flight note."""
        perf = bemt_analyze(params, rpm=spec.rpm_max)
        lines = [
            f"⚙ {spec.n_blades}-blade  {spec.diameter_in}×{spec.pitch_in:.1f} in  @ {spec.rpm_max:.0f} rpm",
            f"Thrust {perf.thrust_g:.0f} g   ·   {perf.efficiency_g_per_w:.2f} g/W   ·   {perf.power_w:.0f} W",
            f"Figure of merit {perf.figure_of_merit:.2f}   (0.6–0.8 = a good real prop)",
        ]
        fwd = bemt_analyze(params, rpm=spec.rpm_max, v_forward=15.0)
        if fwd.prop_efficiency is not None:
            lines.append(f"At 15 m/s forward: prop efficiency {100*fwd.prop_efficiency:.0f}%")
        return lines

    def analyze_prop():
        """Instant BEMT readout, then an async 3-D preview build (geometry is the slow part)."""
        if state.prop_busy:
            return
        spec, params = prop_editor_spec(), prop_editor_params()
        try:
            state.prop_readout = _prop_perf_lines(spec, params)   # BEMT is instant — show it now
        except Exception as exc:  # noqa: BLE001
            state.prop_readout = [f"⚠ Analysis failed: {type(exc).__name__}: {exc}"]
            state.flush()
            return

        async def task():
            state.prop_busy = True
            state.prop_msg = "⏳ Building the 3-D prop…"
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, lambda: build_prop(
                    spec, prop_preview_stl,
                    chord_frac=(float(state.p_chord_root), float(state.p_chord_mid), float(state.p_chord_tip)),
                    camber=float(state.p_camber)))
                _draw_prop(prop_preview_stl)
                state.prop_msg = ""
            except Exception as exc:  # noqa: BLE001 - geometry failure shouldn't break the readout
                state.prop_msg = f"⚠ 3-D build failed: {type(exc).__name__} (numbers above are still valid)"
            finally:
                state.prop_busy = False
                state.flush()

        asynchronous.create_task(task())

    def optimize_prop():
        """Auto-design the blade front (thrust vs efficiency) with BEMT — fast enough to run live."""
        if state.prop_busy:
            return
        base = get_prop_spec(state.prop_model)   # optimizer searches n_blades + pitch itself
        cap = float(state.prop_maxpower) if state.prop_maxpower else None
        trials = max(50, int(state.prop_trials))

        async def task():
            state.prop_busy = True
            state.prop_msg = f"⏳ Optimizing {trials} blade designs (BEMT — a second or two)…"
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                _, pareto = await loop.run_in_executor(
                    None, lambda: run_prop_study(base, n_trials=trials, max_power_w=cap))
            except Exception as exc:  # noqa: BLE001
                state.prop_msg = f"⚠ Optimize failed: {type(exc).__name__}: {exc}"
                state.prop_busy = False
                state.flush()
                return
            prop_pareto_store.clear()
            prop_pareto_store.extend(pareto)
            rows = []
            for i, r in enumerate(pareto[:14]):
                p = r["params"]
                rows.append({
                    "idx": i, "thrust": f"{r['thrust_g']:.0f}", "eff": f"{r['eff_g_per_w']:.2f}",
                    "power": f"{r['power_w']:.0f}", "fm": f"{r['fm']:.2f}", "nb": r["n_blades"],
                    "pitch": f"{p['pitch_in']:.1f}",
                })
            state.prop_pareto = rows
            cap_txt = f" ≤{cap:.0f} W" if cap else ""
            state.prop_msg = (f"✓ {len(pareto)} designs on the thrust↔efficiency front{cap_txt}. "
                              f"Click a row to load it (top = most thrust, bottom = most efficient).")
            state.prop_busy = False
            state.flush()

        asynchronous.create_task(task())

    def load_prop_row(idx=None, **_):
        """Load an optimizer-front design into the prop sliders, then analyze it."""
        if idx is None or not (0 <= int(idx) < len(prop_pareto_store)):
            return
        p = prop_pareto_store[int(idx)]["params"]
        state.p_n_blades = int(p["n_blades"])
        state.p_pitch = float(p["pitch_in"])
        state.p_chord_root = float(p["chord_root"])
        state.p_chord_mid = float(p["chord_mid"])
        state.p_chord_tip = float(p["chord_tip"])
        state.p_camber = float(p["camber"])
        state.flush()
        analyze_prop()

    def export_prop_stl():
        """Save the current prop as a printable, shaft-bored STL into exports/."""
        spec = prop_editor_spec()
        exports = Path("exports")
        exports.mkdir(exist_ok=True)
        out = exports / f"prop_{state.prop_model}.stl"
        try:
            rep = build_prop(spec, out,
                             chord_frac=(float(state.p_chord_root), float(state.p_chord_mid),
                                         float(state.p_chord_tip)),
                             camber=float(state.p_camber))
        except Exception as exc:  # noqa: BLE001
            state.prop_export_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
            state.flush()
            return
        wt = "watertight" if rep.ok else "⚠ NON-manifold"
        state.prop_export_msg = f"✓ Saved {out.resolve()}  ({wt})"
        state.flush()

    with SinglePageLayout(server) as layout:

================================================================================
## EDIT 152  @ 2026-08-30T18:48:17

--- FIND ---
    def on_plotly_click(trial=None):
        # We receive ONLY the clicked point's customdata (the trial id), not the whole plotly event:
        # the full $event contains non-serializable fields (functions/DOM refs) that fail to marshal to
        # the server, so the click never arrived. Extracting customdata client-side (see the binding)
        # sends a plain number that serializes cleanly.
        if trial is not None:
            state.selected_trial = int(trial)
            state.flush()  # push the new selection back so the Design dropdown syncs to the clicked point

    with SinglePageLayout(server) as layout:
--- REPLACE WITH ---
    def on_plotly_click(trial=None):
        # We receive ONLY the clicked point's customdata (the trial id), not the whole plotly event:
        # the full $event contains non-serializable fields (functions/DOM refs) that fail to marshal to
        # the server, so the click never arrived. Extracting customdata client-side (see the binding)
        # sends a plain number that serializes cleanly.
        if trial is not None:
            state.selected_trial = int(trial)
            state.flush()  # push the new selection back so the Design dropdown syncs to the clicked point

    # =========================================================================================
    # PROPELLER ARCHETYPE (separate tab). Drone props use pitch-driven twist + BEMT (instant, no
    # CFD): specify a size, tune the blade, analyze thrust/efficiency live, or auto-optimize the
    # whole front in ~1 s, then export a printable STL. Self-contained — no catalog/CFD/measurement
    # machinery (that's the fan's CFD workflow); this is design + fast physics.
    # =========================================================================================
    prop_preview_stl = Path(tempfile.gettempdir()) / "fansim_prop_preview.stl"
    prop_pareto_store: list[dict] = []   # full optimizer front (params kept here; table shows a digest)
    state.active_tab = "fan"
    state.prop_model = "fpv_5inch"
    state.prop_models = prop_spec_names()
    state.prop_info = "Pick a size, tune the blade, then Analyze (instant) or Optimize."
    state.prop_readout = ["Analyze a prop to see thrust, efficiency, and figure of merit."]
    state.prop_busy = False
    state.prop_msg = ""
    state.prop_export_msg = ""
    state.prop_trials = 400
    state.prop_maxpower = 700.0
    state.prop_pareto = []               # display rows for the optimizer front table

    def _init_prop_editor(spec):
        """Load the prop sliders from a spec's default blade (chord fractions + camber defaults)."""
        state.p_n_blades = int(spec.n_blades)
        state.p_pitch = float(spec.pitch_in)
        state.p_chord_root = 0.20
        state.p_chord_mid = 0.26
        state.p_chord_tip = 0.10
        state.p_camber = 0.04

    _init_prop_editor(get_prop_spec(state.prop_model))

    def _prop_model_readout():
        s = get_prop_spec(state.prop_model)
        tip_ms = s.tip_speed_ms(s.rpm_max)
        state.prop_info = (f"{s.name}: {s.diameter_in}×{s.pitch_in} in, {s.n_blades}-blade, "
                           f"{s.shaft.shaft_dia_mm:.0f} mm shaft, ≤{s.rpm_max:.0f} rpm "
                           f"(tip {tip_ms:.0f} m/s, Mach {s.tip_mach(s.rpm_max):.2f}). {s.material}.")

    _prop_model_readout()

    @state.change("prop_model")
    def _on_prop_model(**_):
        _init_prop_editor(get_prop_spec(state.prop_model))
        _prop_model_readout()

    def prop_editor_spec():
        """The selected prop envelope with the editor's blade-count + pitch applied."""
        return dataclasses.replace(get_prop_spec(state.prop_model),
                                   n_blades=int(state.p_n_blades), pitch_in=float(state.p_pitch))

    def prop_editor_params():
        return prop_blade_params(prop_editor_spec(),
                                 chord_frac=(float(state.p_chord_root), float(state.p_chord_mid),
                                             float(state.p_chord_tip)),
                                 camber=float(state.p_camber))

    def _draw_prop(path):
        prop_plotter.clear_actors()
        try:
            prop_plotter.add_mesh(pv.read(str(path)), color="cadetblue", smooth_shading=True)
            prop_plotter.reset_camera()
        except Exception:  # noqa: BLE001 - nothing to show
            pass
        try:
            ctrl.prop_view_update()
        except Exception:  # noqa: BLE001
            pass

    def _prop_perf_lines(spec, params):
        """BEMT readout for the current prop: static hover thrust/eff/FM + a forward-flight note."""
        perf = bemt_analyze(params, rpm=spec.rpm_max)
        lines = [
            f"⚙ {spec.n_blades}-blade  {spec.diameter_in}×{spec.pitch_in:.1f} in  @ {spec.rpm_max:.0f} rpm",
            f"Thrust {perf.thrust_g:.0f} g   ·   {perf.efficiency_g_per_w:.2f} g/W   ·   {perf.power_w:.0f} W",
            f"Figure of merit {perf.figure_of_merit:.2f}   (0.6–0.8 = a good real prop)",
        ]
        fwd = bemt_analyze(params, rpm=spec.rpm_max, v_forward=15.0)
        if fwd.prop_efficiency is not None:
            lines.append(f"At 15 m/s forward: prop efficiency {100*fwd.prop_efficiency:.0f}%")
        return lines

    def analyze_prop():
        """Instant BEMT readout, then an async 3-D preview build (geometry is the slow part)."""
        if state.prop_busy:
            return
        spec, params = prop_editor_spec(), prop_editor_params()
        try:
            state.prop_readout = _prop_perf_lines(spec, params)   # BEMT is instant — show it now
        except Exception as exc:  # noqa: BLE001
            state.prop_readout = [f"⚠ Analysis failed: {type(exc).__name__}: {exc}"]
            state.flush()
            return

        async def task():
            state.prop_busy = True
            state.prop_msg = "⏳ Building the 3-D prop…"
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, lambda: build_prop(
                    spec, prop_preview_stl,
                    chord_frac=(float(state.p_chord_root), float(state.p_chord_mid), float(state.p_chord_tip)),
                    camber=float(state.p_camber)))
                _draw_prop(prop_preview_stl)
                state.prop_msg = ""
            except Exception as exc:  # noqa: BLE001 - geometry failure shouldn't break the readout
                state.prop_msg = f"⚠ 3-D build failed: {type(exc).__name__} (numbers above are still valid)"
            finally:
                state.prop_busy = False
                state.flush()

        asynchronous.create_task(task())

    def optimize_prop():
        """Auto-design the blade front (thrust vs efficiency) with BEMT — fast enough to run live."""
        if state.prop_busy:
            return
        base = get_prop_spec(state.prop_model)   # optimizer searches n_blades + pitch itself
        cap = float(state.prop_maxpower) if state.prop_maxpower else None
        trials = max(50, int(state.prop_trials))

        async def task():
            state.prop_busy = True
            state.prop_msg = f"⏳ Optimizing {trials} blade designs (BEMT — a second or two)…"
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                _, pareto = await loop.run_in_executor(
                    None, lambda: run_prop_study(base, n_trials=trials, max_power_w=cap))
            except Exception as exc:  # noqa: BLE001
                state.prop_msg = f"⚠ Optimize failed: {type(exc).__name__}: {exc}"
                state.prop_busy = False
                state.flush()
                return
            prop_pareto_store.clear()
            prop_pareto_store.extend(pareto)
            rows = []
            for i, r in enumerate(pareto[:14]):
                p = r["params"]
                rows.append({
                    "idx": i, "thrust": f"{r['thrust_g']:.0f}", "eff": f"{r['eff_g_per_w']:.2f}",
                    "power": f"{r['power_w']:.0f}", "fm": f"{r['fm']:.2f}", "nb": r["n_blades"],
                    "pitch": f"{p['pitch_in']:.1f}",
                })
            state.prop_pareto = rows
            cap_txt = f" ≤{cap:.0f} W" if cap else ""
            state.prop_msg = (f"✓ {len(pareto)} designs on the thrust↔efficiency front{cap_txt}. "
                              f"Click a row to load it (top = most thrust, bottom = most efficient).")
            state.prop_busy = False
            state.flush()

        asynchronous.create_task(task())

    def load_prop_row(idx=None, **_):
        """Load an optimizer-front design into the prop sliders, then analyze it."""
        if idx is None or not (0 <= int(idx) < len(prop_pareto_store)):
            return
        p = prop_pareto_store[int(idx)]["params"]
        state.p_n_blades = int(p["n_blades"])
        state.p_pitch = float(p["pitch_in"])
        state.p_chord_root = float(p["chord_root"])
        state.p_chord_mid = float(p["chord_mid"])
        state.p_chord_tip = float(p["chord_tip"])
        state.p_camber = float(p["camber"])
        state.flush()
        analyze_prop()

    def export_prop_stl():
        """Save the current prop as a printable, shaft-bored STL into exports/."""
        spec = prop_editor_spec()
        exports = Path("exports")
        exports.mkdir(exist_ok=True)
        out = exports / f"prop_{state.prop_model}.stl"
        try:
            rep = build_prop(spec, out,
                             chord_frac=(float(state.p_chord_root), float(state.p_chord_mid),
                                         float(state.p_chord_tip)),
                             camber=float(state.p_camber))
        except Exception as exc:  # noqa: BLE001
            state.prop_export_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
            state.flush()
            return
        wt = "watertight" if rep.ok else "⚠ NON-manifold"
        state.prop_export_msg = f"✓ Saved {out.resolve()}  ({wt})"
        state.flush()

    with SinglePageLayout(server) as layout:

================================================================================
## EDIT 153  @ 2026-08-30T18:49:52

--- FIND ---
        base = get_prop_spec(state.prop_model)   # optimizer searches n_blades + pitch itself
        cap = float(state.prop_maxpower) if state.prop_maxpower else None
        trials = max(50, int(state.prop_trials))
--- REPLACE WITH ---
        base = get_prop_spec(state.prop_model)   # optimizer searches n_blades + pitch itself
        try:
            cap = float(state.prop_maxpower)
        except (TypeError, ValueError):
            cap = None
        if not cap or cap <= 0:                  # blank or 0 = no power budget
            cap = None
        try:
            trials = max(50, int(float(state.prop_trials)))
        except (TypeError, ValueError):
            trials = 400

================================================================================
## EDIT 154  @ 2026-08-30T18:49:52

--- FIND ---
        base = get_prop_spec(state.prop_model)   # optimizer searches n_blades + pitch itself
        cap = float(state.prop_maxpower) if state.prop_maxpower else None
        trials = max(50, int(state.prop_trials))
--- REPLACE WITH ---
        base = get_prop_spec(state.prop_model)   # optimizer searches n_blades + pitch itself
        try:
            cap = float(state.prop_maxpower)
        except (TypeError, ValueError):
            cap = None
        if not cap or cap <= 0:                  # blank or 0 = no power budget
            cap = None
        try:
            trials = max(50, int(float(state.prop_trials)))
        except (TypeError, ValueError):
            trials = 400

================================================================================
## EDIT 155  @ 2026-08-30T18:49:59

--- FIND ---
        with layout.content:
            with v3.VContainer(fluid=True, classes="pa-2"):
                with v3.VRow(no_gutters=True):
                    with v3.VCol(cols=6, classes="pr-2"):
                        v3.VSwitch(v_model=("declutter",), density="compact", hide_details=True,
--- REPLACE WITH ---
        with layout.content:
            with v3.VContainer(fluid=True, classes="pa-2"):
                with v3.VTabs(v_model=("active_tab",), color="primary", classes="mb-3"):
                    v3.VTab("🌀  Fan — CFD design", value="fan")
                    v3.VTab("🚁  Propeller — instant BEMT design", value="propeller")
                # ---- FAN TAB (existing cockpit) ------------------------------------------------
                with v3.VRow(no_gutters=True, v_show="active_tab === 'fan'"):
                    with v3.VCol(cols=6, classes="pr-2"):
                        v3.VSwitch(v_model=("declutter",), density="compact", hide_details=True,

================================================================================
## EDIT 156  @ 2026-08-30T18:49:59

--- FIND ---
        with layout.content:
            with v3.VContainer(fluid=True, classes="pa-2"):
                with v3.VRow(no_gutters=True):
                    with v3.VCol(cols=6, classes="pr-2"):
                        v3.VSwitch(v_model=("declutter",), density="compact", hide_details=True,
--- REPLACE WITH ---
        with layout.content:
            with v3.VContainer(fluid=True, classes="pa-2"):
                with v3.VTabs(v_model=("active_tab",), color="primary", classes="mb-3"):
                    v3.VTab("🌀  Fan — CFD design", value="fan")
                    v3.VTab("🚁  Propeller — instant BEMT design", value="propeller")
                # ---- FAN TAB (existing cockpit) ------------------------------------------------
                with v3.VRow(no_gutters=True, v_show="active_tab === 'fan'"):
                    with v3.VCol(cols=6, classes="pr-2"):
                        v3.VSwitch(v_model=("declutter",), density="compact", hide_details=True,

================================================================================
## EDIT 157  @ 2026-08-30T18:50:20

--- FIND ---
                        with v3.VCard(style="height:420px;"):
                            view = plotter_ui(plotter)
    ctrl.view_update = view.update
    ctrl.figure_update = fig_widget.update
    return server
--- REPLACE WITH ---
                        with v3.VCard(style="height:420px;"):
                            view = plotter_ui(plotter)
                # ---- PROPELLER TAB -------------------------------------------------------------
                with html.Div(v_show="active_tab === 'propeller'"):
                    with v3.VRow(no_gutters=True):
                        # LEFT — pick a size, tune the blade, analyze / optimize / export
                        with v3.VCol(cols=5, classes="pr-2"):
                            with v3.VCard(classes="mb-2 pa-3"):
                                v3.VSelect(label="Propeller size", v_model=("prop_model",),
                                           items=("prop_models",), density="compact",
                                           variant="outlined", hide_details=True)
                                html.Div("{{ prop_info }}", classes="text-caption mt-2",
                                         style="white-space: pre-line")
                            with v3.VCard(classes="mb-2 pa-3"):
                                html.Div("Blade — pitch drives the twist automatically",
                                         classes="text-subtitle-2 mb-2")
                                _slider("Blades", "p_n_blades", 2, 4, 1)
                                _slider("Pitch (in)", "p_pitch", 1.5, 8.0, 0.1)
                                _slider("Chord root (×tip R)", "p_chord_root", 0.08, 0.30, 0.01)
                                _slider("Chord mid (×tip R)", "p_chord_mid", 0.10, 0.32, 0.01)
                                _slider("Chord tip (×tip R)", "p_chord_tip", 0.04, 0.18, 0.01)
                                _slider("Camber (curve)", "p_camber", 0.0, 0.06, 0.005)
                                with v3.VRow(no_gutters=True, classes="mt-2"):
                                    v3.VBtn("Analyze (BEMT)", color="primary", size="small",
                                            click=(analyze_prop,), classes="mr-2",
                                            loading=("prop_busy",), disabled=("prop_busy",))
                                    v3.VBtn("💾 Export STL", size="small", variant="tonal",
                                            color="primary", click=(export_prop_stl,))
                                html.Div("{{ prop_msg }}", classes="text-caption mt-2",
                                         style="white-space: pre-line")
                                html.Div("{{ prop_export_msg }}", classes="text-caption mt-1",
                                         style="white-space: pre-line")
                            with v3.VCard(classes="mb-2 pa-3"):
                                html.Div("Auto-optimize the blade (thrust ↔ efficiency, ~1 s)",
                                         classes="text-subtitle-2 mb-1")
                                with v3.VRow(no_gutters=True, classes="align-center"):
                                    with v3.VCol(cols=6, classes="pr-1"):
                                        v3.VTextField(label="Trials", v_model=("prop_trials",),
                                                      type="number", density="compact",
                                                      variant="outlined", hide_details=True)
                                    with v3.VCol(cols=6, classes="pl-1"):
                                        v3.VTextField(label="Max power W (0=any)",
                                                      v_model=("prop_maxpower",), type="number",
                                                      density="compact", variant="outlined",
                                                      hide_details=True)
                                v3.VBtn("Optimize", color="success", size="small", block=True,
                                        click=(optimize_prop,), classes="mt-2",
                                        loading=("prop_busy",), disabled=("prop_busy",))
                        # RIGHT — performance readout, 3-D prop, optimizer front
                        with v3.VCol(cols=7):
                            with v3.VCard(classes="mb-2 pa-3"):
                                html.Div("{{ line }}", v_for="line in prop_readout",
                                         classes="text-body-2")
                            with v3.VCard(style="height:360px;", classes="mb-2"):
                                prop_view = plotter_ui(prop_plotter)
                            with v3.VCard(classes="pa-2", v_if="prop_pareto.length"):
                                html.Div("Optimizer front — click a design to load it "
                                         "(top = most thrust, bottom = most efficient)",
                                         classes="text-subtitle-2 mb-1")
                                with v3.VList(density="compact", lines=False):
                                    with v3.VListItem(v_for="row in prop_pareto", key="row.idx",
                                                      click=(load_prop_row, "[row.idx]")):
                                        v3.VListItemTitle("{{ row.thrust }} g  ·  {{ row.eff }} g/W  "
                                                          "·  {{ row.power }} W  ·  FM {{ row.fm }}  "
                                                          "·  {{ row.nb }}-blade  {{ row.pitch }}\"")
    ctrl.view_update = view.update
    ctrl.figure_update = fig_widget.update
    ctrl.prop_view_update = prop_view.update
    return server

================================================================================
## EDIT 158  @ 2026-08-30T18:50:20

--- FIND ---
                        with v3.VCard(style="height:420px;"):
                            view = plotter_ui(plotter)
    ctrl.view_update = view.update
    ctrl.figure_update = fig_widget.update
    return server
--- REPLACE WITH ---
                        with v3.VCard(style="height:420px;"):
                            view = plotter_ui(plotter)
                # ---- PROPELLER TAB -------------------------------------------------------------
                with html.Div(v_show="active_tab === 'propeller'"):
                    with v3.VRow(no_gutters=True):
                        # LEFT — pick a size, tune the blade, analyze / optimize / export
                        with v3.VCol(cols=5, classes="pr-2"):
                            with v3.VCard(classes="mb-2 pa-3"):
                                v3.VSelect(label="Propeller size", v_model=("prop_model",),
                                           items=("prop_models",), density="compact",
                                           variant="outlined", hide_details=True)
                                html.Div("{{ prop_info }}", classes="text-caption mt-2",
                                         style="white-space: pre-line")
                            with v3.VCard(classes="mb-2 pa-3"):
                                html.Div("Blade — pitch drives the twist automatically",
                                         classes="text-subtitle-2 mb-2")
                                _slider("Blades", "p_n_blades", 2, 4, 1)
                                _slider("Pitch (in)", "p_pitch", 1.5, 8.0, 0.1)
                                _slider("Chord root (×tip R)", "p_chord_root", 0.08, 0.30, 0.01)
                                _slider("Chord mid (×tip R)", "p_chord_mid", 0.10, 0.32, 0.01)
                                _slider("Chord tip (×tip R)", "p_chord_tip", 0.04, 0.18, 0.01)
                                _slider("Camber (curve)", "p_camber", 0.0, 0.06, 0.005)
                                with v3.VRow(no_gutters=True, classes="mt-2"):
                                    v3.VBtn("Analyze (BEMT)", color="primary", size="small",
                                            click=(analyze_prop,), classes="mr-2",
                                            loading=("prop_busy",), disabled=("prop_busy",))
                                    v3.VBtn("💾 Export STL", size="small", variant="tonal",
                                            color="primary", click=(export_prop_stl,))
                                html.Div("{{ prop_msg }}", classes="text-caption mt-2",
                                         style="white-space: pre-line")
                                html.Div("{{ prop_export_msg }}", classes="text-caption mt-1",
                                         style="white-space: pre-line")
                            with v3.VCard(classes="mb-2 pa-3"):
                                html.Div("Auto-optimize the blade (thrust ↔ efficiency, ~1 s)",
                                         classes="text-subtitle-2 mb-1")
                                with v3.VRow(no_gutters=True, classes="align-center"):
                                    with v3.VCol(cols=6, classes="pr-1"):
                                        v3.VTextField(label="Trials", v_model=("prop_trials",),
                                                      type="number", density="compact",
                                                      variant="outlined", hide_details=True)
                                    with v3.VCol(cols=6, classes="pl-1"):
                                        v3.VTextField(label="Max power W (0=any)",
                                                      v_model=("prop_maxpower",), type="number",
                                                      density="compact", variant="outlined",
                                                      hide_details=True)
                                v3.VBtn("Optimize", color="success", size="small", block=True,
                                        click=(optimize_prop,), classes="mt-2",
                                        loading=("prop_busy",), disabled=("prop_busy",))
                        # RIGHT — performance readout, 3-D prop, optimizer front
                        with v3.VCol(cols=7):
                            with v3.VCard(classes="mb-2 pa-3"):
                                html.Div("{{ line }}", v_for="line in prop_readout",
                                         classes="text-body-2")
                            with v3.VCard(style="height:360px;", classes="mb-2"):
                                prop_view = plotter_ui(prop_plotter)
                            with v3.VCard(classes="pa-2", v_if="prop_pareto.length"):
                                html.Div("Optimizer front — click a design to load it "
                                         "(top = most thrust, bottom = most efficient)",
                                         classes="text-subtitle-2 mb-1")
                                with v3.VList(density="compact", lines=False):
                                    with v3.VListItem(v_for="row in prop_pareto", key="row.idx",
                                                      click=(load_prop_row, "[row.idx]")):
                                        v3.VListItemTitle("{{ row.thrust }} g  ·  {{ row.eff }} g/W  "
                                                          "·  {{ row.power }} W  ·  FM {{ row.fm }}  "
                                                          "·  {{ row.nb }}-blade  {{ row.pitch }}\"")
    ctrl.view_update = view.update
    ctrl.figure_update = fig_widget.update
    ctrl.prop_view_update = prop_view.update
    return server

================================================================================
## EDIT 159  @ 2026-08-30T18:51:35

--- FIND ---
                            with v3.VExpansionPanels(variant="accordion", multiple=True):
                                with v3.VExpansionPanel(title="Geometry"):
                                    with v3.VExpansionPanelText():
                                        v3.VBtn("🎲 Randomize geometry", size="x-small",
                                                variant="tonal", color="secondary", block=True,
                                                click=(randomize_geometry,), classes="mb-3")
                                        _slider("Blades", "e_n_blades", 5, 11, 1)
                                        _slider("Camber (curve)", "e_camber", 0.0, 0.06, 0.005)
                                        _slider("Stagger root", "e_stagger_root", 15, 55, 1)
                                        _slider("Stagger mid", "e_stagger_mid", 15, 55, 1)
                                        _slider("Stagger tip", "e_stagger_tip", 15, 55, 1)
                                        _slider("Chord root", "e_chord_root", 14, 42, 0.5)
                                        _slider("Chord mid", "e_chord_mid", 14, 42, 0.5)
                                        _slider("Chord tip", "e_chord_tip", 14, 42, 0.5)
                                        _slider("Wrap mid (deg)", "e_lean_mid", 0, 30, 1)
                                        _slider("Wrap tip (deg)", "e_lean_tip", 0, 45, 1)
                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)
                                        _slider("LE curve mid (mm)", "e_le_mid", -8, 8, 0.5)
                                        _slider("LE curve tip (mm)", "e_le_tip", -8, 8, 0.5)
                                        _slider("Skew mid (mm)", "e_skew_mid", -6, 6, 0.5)
                                        _slider("Skew tip (mm)", "e_skew_tip", -6, 6, 0.5)
                                        _slider("Winglet start (span)", "e_winglet_span", 0.6, 0.95, 0.05)
                                        _slider("Winglet sweep (mm)", "e_winglet_sweep", 0, 15, 0.5)
                                        _slider("Winglet lean (deg)", "e_winglet_lean", 0, 30, 1)
                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
                                        _slider("Tip radius / length (mm)", "e_tip_radius", 45, 59, 0.5)
                                        _slider("Hub height (mm, 0=auto)", "e_hub_height", 0, 30, 0.5)
                                        v3.VSelect(label="Hub profile", v_model=("e_hub_profile",),
                                                   items=("hub_profiles",), density="compact",
                                                   variant="outlined", hide_details=True,
                                                   classes="mb-3")
                                        _slider("Hub nose (mm, cone/dome)", "e_hub_nose", 0, 15, 0.5)
                                        _slider("Camber position", "e_camber_pos", 0.2, 0.6, 0.05)
                                        _slider("Thickness root", "e_thick_root", 0.03, 0.15, 0.01)
                                        _slider("Thickness mid", "e_thick_mid", 0.03, 0.15, 0.01)
                                        _slider("Thickness tip", "e_thick_tip", 0.03, 0.15, 0.01)
                                        _slider("Uneven spacing", "e_spacing", 0.0, 0.6, 0.05)
                                with v3.VExpansionPanel(title="Features (bio-inspired)"):
--- REPLACE WITH ---
                            v3.VBtn("🎲 Randomize geometry", size="x-small",
                                    variant="tonal", color="secondary", block=True,
                                    click=(randomize_geometry,), classes="mb-2")
                            with v3.VExpansionPanels(variant="accordion", multiple=True):
                                with v3.VExpansionPanel(title="Planform — blades & chord"):
                                    with v3.VExpansionPanelText():
                                        _slider("Blades", "e_n_blades", 5, 11, 1)
                                        _slider("Chord root", "e_chord_root", 14, 42, 0.5)
                                        _slider("Chord mid", "e_chord_mid", 14, 42, 0.5)
                                        _slider("Chord tip", "e_chord_tip", 14, 42, 0.5)
                                with v3.VExpansionPanel(title="Pitch / twist — stagger"):
                                    with v3.VExpansionPanelText():
                                        _slider("Stagger root", "e_stagger_root", 15, 55, 1)
                                        _slider("Stagger mid", "e_stagger_mid", 15, 55, 1)
                                        _slider("Stagger tip", "e_stagger_tip", 15, 55, 1)
                                with v3.VExpansionPanel(title="Airfoil — camber & thickness"):
                                    with v3.VExpansionPanelText():
                                        _slider("Camber (curve)", "e_camber", 0.0, 0.06, 0.005)
                                        _slider("Camber position", "e_camber_pos", 0.2, 0.6, 0.05)
                                        _slider("Thickness root", "e_thick_root", 0.03, 0.15, 0.01)
                                        _slider("Thickness mid", "e_thick_mid", 0.03, 0.15, 0.01)
                                        _slider("Thickness tip", "e_thick_tip", 0.03, 0.15, 0.01)
                                with v3.VExpansionPanel(title="3-D shape — wrap, sweep, rake"):
                                    with v3.VExpansionPanelText():
                                        _slider("Wrap mid (deg)", "e_lean_mid", 0, 30, 1)
                                        _slider("Wrap tip (deg)", "e_lean_tip", 0, 45, 1)
                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)
                                        _slider("LE curve mid (mm)", "e_le_mid", -8, 8, 0.5)
                                        _slider("LE curve tip (mm)", "e_le_tip", -8, 8, 0.5)
                                        _slider("Skew mid (mm)", "e_skew_mid", -6, 6, 0.5)
                                        _slider("Skew tip (mm)", "e_skew_tip", -6, 6, 0.5)
                                with v3.VExpansionPanel(title="Winglet — tip"):
                                    with v3.VExpansionPanelText():
                                        _slider("Winglet start (span)", "e_winglet_span", 0.6, 0.95, 0.05)
                                        _slider("Winglet sweep (mm)", "e_winglet_sweep", 0, 15, 0.5)
                                        _slider("Winglet lean (deg)", "e_winglet_lean", 0, 30, 1)
                                with v3.VExpansionPanel(title="Hub"):
                                    with v3.VExpansionPanelText():
                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
                                        _slider("Tip radius / length (mm)", "e_tip_radius", 45, 59, 0.5)
                                        _slider("Hub height (mm, 0=auto)", "e_hub_height", 0, 30, 0.5)
                                        v3.VSelect(label="Hub profile", v_model=("e_hub_profile",),
                                                   items=("hub_profiles",), density="compact",
                                                   variant="outlined", hide_details=True,
                                                   classes="mb-3")
                                        _slider("Hub nose (mm, cone/dome)", "e_hub_nose", 0, 15, 0.5)
                                with v3.VExpansionPanel(title="Spacing — tonal noise"):
                                    with v3.VExpansionPanelText():
                                        _slider("Uneven spacing", "e_spacing", 0.0, 0.6, 0.05)
                                with v3.VExpansionPanel(title="Features (bio-inspired)"):

================================================================================
## EDIT 160  @ 2026-08-30T18:51:35

--- FIND ---
                            with v3.VExpansionPanels(variant="accordion", multiple=True):
                                with v3.VExpansionPanel(title="Geometry"):
                                    with v3.VExpansionPanelText():
                                        v3.VBtn("🎲 Randomize geometry", size="x-small",
                                                variant="tonal", color="secondary", block=True,
                                                click=(randomize_geometry,), classes="mb-3")
                                        _slider("Blades", "e_n_blades", 5, 11, 1)
                                        _slider("Camber (curve)", "e_camber", 0.0, 0.06, 0.005)
                                        _slider("Stagger root", "e_stagger_root", 15, 55, 1)
                                        _slider("Stagger mid", "e_stagger_mid", 15, 55, 1)
                                        _slider("Stagger tip", "e_stagger_tip", 15, 55, 1)
                                        _slider("Chord root", "e_chord_root", 14, 42, 0.5)
                                        _slider("Chord mid", "e_chord_mid", 14, 42, 0.5)
                                        _slider("Chord tip", "e_chord_tip", 14, 42, 0.5)
                                        _slider("Wrap mid (deg)", "e_lean_mid", 0, 30, 1)
                                        _slider("Wrap tip (deg)", "e_lean_tip", 0, 45, 1)
                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)
                                        _slider("LE curve mid (mm)", "e_le_mid", -8, 8, 0.5)
                                        _slider("LE curve tip (mm)", "e_le_tip", -8, 8, 0.5)
                                        _slider("Skew mid (mm)", "e_skew_mid", -6, 6, 0.5)
                                        _slider("Skew tip (mm)", "e_skew_tip", -6, 6, 0.5)
                                        _slider("Winglet start (span)", "e_winglet_span", 0.6, 0.95, 0.05)
                                        _slider("Winglet sweep (mm)", "e_winglet_sweep", 0, 15, 0.5)
                                        _slider("Winglet lean (deg)", "e_winglet_lean", 0, 30, 1)
                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
                                        _slider("Tip radius / length (mm)", "e_tip_radius", 45, 59, 0.5)
                                        _slider("Hub height (mm, 0=auto)", "e_hub_height", 0, 30, 0.5)
                                        v3.VSelect(label="Hub profile", v_model=("e_hub_profile",),
                                                   items=("hub_profiles",), density="compact",
                                                   variant="outlined", hide_details=True,
                                                   classes="mb-3")
                                        _slider("Hub nose (mm, cone/dome)", "e_hub_nose", 0, 15, 0.5)
                                        _slider("Camber position", "e_camber_pos", 0.2, 0.6, 0.05)
                                        _slider("Thickness root", "e_thick_root", 0.03, 0.15, 0.01)
                                        _slider("Thickness mid", "e_thick_mid", 0.03, 0.15, 0.01)
                                        _slider("Thickness tip", "e_thick_tip", 0.03, 0.15, 0.01)
                                        _slider("Uneven spacing", "e_spacing", 0.0, 0.6, 0.05)
                                with v3.VExpansionPanel(title="Features (bio-inspired)"):
--- REPLACE WITH ---
                            v3.VBtn("🎲 Randomize geometry", size="x-small",
                                    variant="tonal", color="secondary", block=True,
                                    click=(randomize_geometry,), classes="mb-2")
                            with v3.VExpansionPanels(variant="accordion", multiple=True):
                                with v3.VExpansionPanel(title="Planform — blades & chord"):
                                    with v3.VExpansionPanelText():
                                        _slider("Blades", "e_n_blades", 5, 11, 1)
                                        _slider("Chord root", "e_chord_root", 14, 42, 0.5)
                                        _slider("Chord mid", "e_chord_mid", 14, 42, 0.5)
                                        _slider("Chord tip", "e_chord_tip", 14, 42, 0.5)
                                with v3.VExpansionPanel(title="Pitch / twist — stagger"):
                                    with v3.VExpansionPanelText():
                                        _slider("Stagger root", "e_stagger_root", 15, 55, 1)
                                        _slider("Stagger mid", "e_stagger_mid", 15, 55, 1)
                                        _slider("Stagger tip", "e_stagger_tip", 15, 55, 1)
                                with v3.VExpansionPanel(title="Airfoil — camber & thickness"):
                                    with v3.VExpansionPanelText():
                                        _slider("Camber (curve)", "e_camber", 0.0, 0.06, 0.005)
                                        _slider("Camber position", "e_camber_pos", 0.2, 0.6, 0.05)
                                        _slider("Thickness root", "e_thick_root", 0.03, 0.15, 0.01)
                                        _slider("Thickness mid", "e_thick_mid", 0.03, 0.15, 0.01)
                                        _slider("Thickness tip", "e_thick_tip", 0.03, 0.15, 0.01)
                                with v3.VExpansionPanel(title="3-D shape — wrap, sweep, rake"):
                                    with v3.VExpansionPanelText():
                                        _slider("Wrap mid (deg)", "e_lean_mid", 0, 30, 1)
                                        _slider("Wrap tip (deg)", "e_lean_tip", 0, 45, 1)
                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)
                                        _slider("LE curve mid (mm)", "e_le_mid", -8, 8, 0.5)
                                        _slider("LE curve tip (mm)", "e_le_tip", -8, 8, 0.5)
                                        _slider("Skew mid (mm)", "e_skew_mid", -6, 6, 0.5)
                                        _slider("Skew tip (mm)", "e_skew_tip", -6, 6, 0.5)
                                with v3.VExpansionPanel(title="Winglet — tip"):
                                    with v3.VExpansionPanelText():
                                        _slider("Winglet start (span)", "e_winglet_span", 0.6, 0.95, 0.05)
                                        _slider("Winglet sweep (mm)", "e_winglet_sweep", 0, 15, 0.5)
                                        _slider("Winglet lean (deg)", "e_winglet_lean", 0, 30, 1)
                                with v3.VExpansionPanel(title="Hub"):
                                    with v3.VExpansionPanelText():
                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
                                        _slider("Tip radius / length (mm)", "e_tip_radius", 45, 59, 0.5)
                                        _slider("Hub height (mm, 0=auto)", "e_hub_height", 0, 30, 0.5)
                                        v3.VSelect(label="Hub profile", v_model=("e_hub_profile",),
                                                   items=("hub_profiles",), density="compact",
                                                   variant="outlined", hide_details=True,
                                                   classes="mb-3")
                                        _slider("Hub nose (mm, cone/dome)", "e_hub_nose", 0, 15, 0.5)
                                with v3.VExpansionPanel(title="Spacing — tonal noise"):
                                    with v3.VExpansionPanelText():
                                        _slider("Uneven spacing", "e_spacing", 0.0, 0.6, 0.05)
                                with v3.VExpansionPanel(title="Features (bio-inspired)"):

================================================================================
## EDIT 161  @ 2026-08-30T21:57:19

--- FIND ---
    def export_stl_current():
        """Save the current design as a print-ready STL (motor-mount cup carved) into exports/."""
        from fansim.manufacturability.print_export import export_print_ready
        params = build_edit_params()
        spec = active_spec()
        exports = Path("exports")
        exports.mkdir(exist_ok=True)
        tid = state.selected_trial
        name = f"design_{tid}" if tid is not None else "fan_current"
        out = exports / f"{name}.stl"
        try:
            rep = export_print_ready(params, out, mount=spec.motor_mount)
        except Exception as exc:  # noqa: BLE001
            state.export_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
            state.flush()
            return
        wt = "watertight" if rep.ok else "⚠ NON-manifold"
        mnt = ("" if rep.mount_fits is None else
               ("· mountable" if rep.mount_fits else "· ⚠ hub too small to mount"))
        state.export_msg = f"✓ Saved {out.resolve()}  ({wt} {mnt})"
        state.flush()
--- REPLACE WITH ---
    def export_stl_current():
        """Save the current design as a print-ready STL with the motor-mount cup carved into the hub.

        Two things the earlier version got wrong (both fixed here):
        - Filenames are now TIMESTAMPED (design_<trial>_<YYYYmmdd-HHMMSS>.stl) so each export is its
          own file instead of overwriting fan_current.stl every time.
        - The motor cup can only be carved when the hub is wide enough to house the motor
          (hub_radius >= cavity/2 + wall). Aero-optimized hubs are too narrow, so the export used to
          come out as a SOLID hub with no cavity. Now, if the hub is too small, we widen it just enough
          to fit the real motor, update the Hub-radius slider to match, and say so — so the exported
          part actually slips over the fan's 50 mm motor hub. A companion .md print sheet is written too.
        """
        from datetime import datetime

        from fansim.fan_spec import mount_min_hub_radius
        from fansim.manufacturability.print_export import (
            balance_summary, export_print_ready, print_readme, recommend_print_settings,
        )
        spec = active_spec()
        # Widen the hub to the minimum mountable radius if it's too narrow, so the cup carves at all.
        need = mount_min_hub_radius(spec)
        grew_from = None
        if need is not None and float(state.e_hub_radius) < need:
            grew_from = float(state.e_hub_radius)
            state.e_hub_radius = round(need + 0.05, 2)   # just clears the fit test
        params = build_edit_params()                     # rebuilt with the (possibly widened) hub
        exports = Path("exports")
        exports.mkdir(exist_ok=True)
        tid = state.selected_trial
        base = f"design_{tid}" if tid is not None else "fan"
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = exports / f"{base}_{stamp}.stl"
        try:
            rep = export_print_ready(params, out, mount=spec.motor_mount)
        except Exception as exc:  # noqa: BLE001
            state.export_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
            state.flush()
            return
        try:  # companion print sheet (documents the cup dimensions, material, balance) — best-effort
            settings = recommend_print_settings(spec.material)
            bal = balance_summary(params, spec.rpm)
            (out.with_suffix(".md")).write_text(
                print_readme(out.stem, params, spec.material, rep, bal, settings, None),
                encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        wt = "watertight" if rep.ok else "⚠ NON-manifold"
        if rep.mount_fits is True:
            mnt = f" · ✓ motor cup carved ({rep.mount_msg})"
        elif rep.mount_fits is False:
            mnt = f" · ⚠ {rep.mount_msg}"
        else:
            mnt = " · (this fan model has no motor-mount defined)"
        grew = ""
        if grew_from is not None:
            grew = (f"\n↳ Hub widened {grew_from:.1f} → {state.e_hub_radius:.1f} mm to fit the "
                    f"{spec.motor_mount.cavity_dia_mm:.0f} mm motor — press Preview to see it. The CFM/eff "
                    f"shown were for the narrower hub, so they're now approximate; re-Assess for exact numbers.")
        state.export_msg = f"✓ Saved {out.resolve()}  ({wt}{mnt}){grew}"
        state.flush()

================================================================================
## EDIT 162  @ 2026-08-30T22:18:41

--- FIND ---
    state.preview_msg = "Select a design, then edit and press Preview geometry."
    state.export_msg = ""
--- REPLACE WITH ---
    state.preview_msg = "Select a design, then edit and press Preview geometry."
    state.export_msg = ""
    state.export_fit_hub = True   # on export, widen a too-small hub so the motor cup can be carved

================================================================================
## EDIT 163  @ 2026-08-30T22:18:48

--- FIND ---
        # Widen the hub to the minimum mountable radius if it's too narrow, so the cup carves at all.
        need = mount_min_hub_radius(spec)
        grew_from = None
        if need is not None and float(state.e_hub_radius) < need:
            grew_from = float(state.e_hub_radius)
            state.e_hub_radius = round(need + 0.05, 2)   # just clears the fit test
--- REPLACE WITH ---
        # Widen the hub to the minimum mountable radius if it's too narrow, so the cup carves at all.
        # Gated by the "Fit hub to motor on export" switch — off = keep the aero hub (cup won't carve
        # on a too-small hub, and the message says so) for users mounting the fan a different way.
        need = mount_min_hub_radius(spec)
        grew_from = None
        if state.export_fit_hub and need is not None and float(state.e_hub_radius) < need:
            grew_from = float(state.e_hub_radius)
            state.e_hub_radius = round(need + 0.05, 2)   # just clears the fit test

================================================================================
## EDIT 164  @ 2026-08-30T22:18:54

--- FIND ---
                                v3.VBtn("💾 Export STL", size="small", variant="tonal",
                                        color="primary", click=(export_stl_current,))
                            html.Div("{{ preview_msg }}", classes="text-caption mt-2",
                                     style="white-space: pre-line")
--- REPLACE WITH ---
                                v3.VBtn("💾 Export STL", size="small", variant="tonal",
                                        color="primary", click=(export_stl_current,))
                            v3.VSwitch(v_model=("export_fit_hub",), density="compact",
                                       hide_details=True, color="primary", inset=True, classes="mt-1",
                                       label="Fit hub to motor on export (widen a too-small hub so the "
                                             "cup carves)")
                            html.Div("{{ preview_msg }}", classes="text-caption mt-2",
                                     style="white-space: pre-line")

================================================================================
## EDIT 165  @ 2026-08-30T22:19:03

--- FIND ---
        if rep.mount_fits is True:
            mnt = f" · ✓ motor cup carved ({rep.mount_msg})"
        elif rep.mount_fits is False:
            mnt = f" · ⚠ {rep.mount_msg}"
        else:
            mnt = " · (this fan model has no motor-mount defined)"
--- REPLACE WITH ---
        if rep.mount_fits is True:
            mnt = f" · ✓ motor cup carved ({rep.mount_msg})"
        elif rep.mount_fits is False:
            mnt = f" · ⚠ {rep.mount_msg}"
            if not state.export_fit_hub:   # explain the solid hub + how to get the cup
                mnt += " — turn on 'Fit hub to motor on export' to widen it and carve the cup"
        else:
            mnt = " · (this fan model has no motor-mount defined)"

================================================================================
## EDIT 166  @ 2026-08-30T22:51:42

--- FIND ---
    def _build_preview_stl(flat, feat):
        """Blocking geometry build in an ISOLATED subprocess (a native OCP crash or a runaway
        featured build can't take down the cockpit server — it surfaces as a caught error)."""
        from fansim.geometry.isolated import build_stl_isolated
        build_stl_isolated(flat, feat, preview_stl, timeout=120.0)
--- REPLACE WITH ---
    def _build_preview_stl(flat, feat):
        """Blocking geometry build in an ISOLATED subprocess (a native OCP crash or a runaway
        featured build can't take down the cockpit server — it surfaces as a caught error).

        Uses the FAST non-fused preview mesh: the boolean fuse in the real build is ~140 s for a
        featured 11-blade design (blowing the old 120 s timeout for nothing), but a preview only needs
        to look right — the fast path is ~6 s. The generous timeout is just a safety net now."""
        from fansim.geometry.isolated import build_stl_isolated
        build_stl_isolated(flat, feat, preview_stl, timeout=300.0, preview=True)

================================================================================
## EDIT 167  @ 2026-08-30T22:51:50

--- FIND ---
        try:
            import trimesh
            m = trimesh.load(str(stl_path))
            (xmin, ymin, zmin), (xmax, ymax, zmax) = m.bounds
            dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
            depth = zmax - zmin
            weight = estimate_weight_g(abs(float(m.volume)), spec.material)
        except Exception:  # noqa: BLE001 - if we can't measure it, don't block
            return True, ""
--- REPLACE WITH ---
        try:
            import trimesh
            m = trimesh.load(str(stl_path))
            (xmin, ymin, zmin), (xmax, ymax, zmax) = m.bounds
            dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
            depth = zmax - zmin
            # The fast preview mesh is non-fused (blades overlap the hub), so its own volume is wrong;
            # prefer the accurate volume the preview worker wrote to a <stl>.meta.json sidecar.
            vol = abs(float(m.volume))
            meta = Path(str(stl_path) + ".meta.json")
            if meta.exists():
                try:
                    vol = float(json.loads(meta.read_text()).get("volume_mm3", vol))
                except Exception:  # noqa: BLE001 - fall back to the mesh volume
                    pass
            weight = estimate_weight_g(vol, spec.material)
        except Exception:  # noqa: BLE001 - if we can't measure it, don't block
            return True, ""

================================================================================
## EDIT 168  @ 2026-08-30T23:04:56

--- FIND ---
    SWEEP_OPTIONS = [
        ("camber", "flat", "max_camber", 0.0, 0.06),
        ("blades", "flat", "n_blades", 5.0, 11.0),
        ("stagger tip", "flat", "stagger_tip", 20.0, 50.0),
        ("sweep tip", "flat", "sweep_tip", 0.0, 15.0),
        ("tubercle amp", "tub", "tubercle_amp", 0.0, 0.10),
        ("serration amp", "ser", "serration_amp", 0.0, 0.06),
        ("dimple depth", "dim", "dimple_amp", 0.0, 0.35),
    ]
    state.sweep_items = [o[0] for o in SWEEP_OPTIONS]
--- REPLACE WITH ---
    # Each sweep step is a full ~4-min CFD run, so this lists the params that actually move the CFD
    # objectives (flow/eff) — the high-value levers from the design-rules study — grouped like the
    # editor. Deliberately omitted: LE-curve/skew/thickness/camber-pos (minor aero or structural) and
    # UNEVEN SPACING (a tonal-NOISE lever a flow/eff CFD sweep can't see — the Preview shows it live).
    SWEEP_OPTIONS = [
        # planform / solidity — biggest flow + pressure levers
        ("blades", "flat", "n_blades", 5.0, 11.0),
        ("chord mid", "flat", "chord_mid", 14.0, 42.0),
        ("chord tip", "flat", "chord_tip", 14.0, 42.0),
        # pitch / twist (stagger mid = the win-win-win lever from the design rules)
        ("stagger root", "flat", "stagger_root", 15.0, 55.0),
        ("stagger mid", "flat", "stagger_mid", 15.0, 55.0),
        ("stagger tip", "flat", "stagger_tip", 15.0, 55.0),
        # airfoil
        ("camber", "flat", "max_camber", 0.0, 0.06),
        ("camber position", "flat", "camber_pos", 0.2, 0.6),
        # 3-D shape
        ("sweep mid", "flat", "sweep_mid", -3.0, 8.0),
        ("sweep tip", "flat", "sweep_tip", 0.0, 15.0),
        ("wrap tip", "flat", "lean_tip", 0.0, 45.0),
        # winglet (mild CFD effect ~+4% flow; near the screening noise floor)
        ("winglet sweep", "flat", "winglet_sweep", 0.0, 15.0),
        # size / hub (blade length + flow annulus / mountability)
        ("tip radius (length)", "flat", "tip_radius", 45.0, 59.0),
        ("hub radius", "flat", "hub_radius", 15.0, 35.0),
        # bio-inspired features
        ("tubercle amp", "tub", "tubercle_amp", 0.0, 0.10),
        ("serration amp", "ser", "serration_amp", 0.0, 0.06),
        ("dimple depth", "dim", "dimple_amp", 0.0, 0.35),
    ]
    state.sweep_items = [o[0] for o in SWEEP_OPTIONS]

================================================================================
## EDIT 169  @ 2026-08-30T23:05:17

--- FIND ---
    state.sweep_param = "max_camber"
--- REPLACE WITH ---
    state.sweep_param = "stagger mid"   # a valid label (o[0]); the strongest flow/eff lever

================================================================================
## EDIT 170  @ 2026-08-30T23:29:59

--- FIND ---
    state.export_msg = ""
    state.export_fit_hub = True   # on export, widen a too-small hub so the motor cup can be carved
--- REPLACE WITH ---
    state.export_msg = ""
    state.export_busy = False     # export builds the FUSED (watertight) solid -> slow; runs async
    state.export_fit_hub = True   # on export, widen a too-small hub so the motor cup can be carved

================================================================================
## EDIT 171  @ 2026-08-30T23:30:39

--- FIND ---
    def export_stl_current():
        """Save the current design as a print-ready STL with the motor-mount cup carved into the hub.

        Two things the earlier version got wrong (both fixed here):
        - Filenames are now TIMESTAMPED (design_<trial>_<YYYYmmdd-HHMMSS>.stl) so each export is its
          own file instead of overwriting fan_current.stl every time.
        - The motor cup can only be carved when the hub is wide enough to house the motor
          (hub_radius >= cavity/2 + wall). Aero-optimized hubs are too narrow, so the export used to
          come out as a SOLID hub with no cavity. Now, if the hub is too small, we widen it just enough
          to fit the real motor, update the Hub-radius slider to match, and say so — so the exported
          part actually slips over the fan's 50 mm motor hub. A companion .md print sheet is written too.
        """
        from datetime import datetime

        from fansim.fan_spec import mount_min_hub_radius
        from fansim.manufacturability.print_export import (
            balance_summary, export_print_ready, print_readme, recommend_print_settings,
        )
        spec = active_spec()
        # Widen the hub to the minimum mountable radius if it's too narrow, so the cup carves at all.
        # Gated by the "Fit hub to motor on export" switch — off = keep the aero hub (cup won't carve
        # on a too-small hub, and the message says so) for users mounting the fan a different way.
        need = mount_min_hub_radius(spec)
        grew_from = None
        if state.export_fit_hub and need is not None and float(state.e_hub_radius) < need:
            grew_from = float(state.e_hub_radius)
            state.e_hub_radius = round(need + 0.05, 2)   # just clears the fit test
        params = build_edit_params()                     # rebuilt with the (possibly widened) hub
        exports = Path("exports")
        exports.mkdir(exist_ok=True)
        tid = state.selected_trial
        base = f"design_{tid}" if tid is not None else "fan"
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = exports / f"{base}_{stamp}.stl"
        try:
            rep = export_print_ready(params, out, mount=spec.motor_mount)
        except Exception as exc:  # noqa: BLE001
            state.export_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
            state.flush()
            return
        try:  # companion print sheet (documents the cup dimensions, material, balance) — best-effort
            settings = recommend_print_settings(spec.material)
            bal = balance_summary(params, spec.rpm)
            (out.with_suffix(".md")).write_text(
                print_readme(out.stem, params, spec.material, rep, bal, settings, None),
                encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        wt = "watertight" if rep.ok else "⚠ NON-manifold"
        if rep.mount_fits is True:
            mnt = f" · ✓ motor cup carved ({rep.mount_msg})"
        elif rep.mount_fits is False:
            mnt = f" · ⚠ {rep.mount_msg}"
            if not state.export_fit_hub:   # explain the solid hub + how to get the cup
                mnt += " — turn on 'Fit hub to motor on export' to widen it and carve the cup"
        else:
            mnt = " · (this fan model has no motor-mount defined)"
        grew = ""
        if grew_from is not None:
            grew = (f"\n↳ Hub widened {grew_from:.1f} → {state.e_hub_radius:.1f} mm to fit the "
                    f"{spec.motor_mount.cavity_dia_mm:.0f} mm motor — press Preview to see it. The CFM/eff "
                    f"shown were for the narrower hub, so they're now approximate; re-Assess for exact numbers.")
        state.export_msg = f"✓ Saved {out.resolve()}  ({wt}{mnt}){grew}"
        state.flush()
--- REPLACE WITH ---
    def _do_export(params, out, mount):
        """Blocking print-ready build (fused watertight solid + carved motor cup) + companion print
        sheet. Runs in an executor thread so the ~1-3 min featured build doesn't freeze the UI."""
        from fansim.manufacturability.print_export import (
            balance_summary, export_print_ready, print_readme, recommend_print_settings,
        )
        rep = export_print_ready(params, out, mount=mount)
        try:  # companion print sheet (documents the cup dimensions, material, balance) — best-effort
            spec = active_spec()
            settings = recommend_print_settings(spec.material)
            bal = balance_summary(params, spec.rpm)
            (out.with_suffix(".md")).write_text(
                print_readme(out.stem, params, spec.material, rep, bal, settings, None),
                encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        return rep

    def export_stl_current():
        """Save the current design as a print-ready STL with the motor-mount cup carved into the hub.

        The build (a FUSED watertight solid) is slow — ~1-3 min for a featured design — so it runs
        ASYNC in an executor: the button shows a spinner and the UI stays responsive (the old
        synchronous version froze the whole cockpit for the duration, which looked like 'nothing
        happened'). Filenames are TIMESTAMPED so each export is its own file. If the hub is too small
        to house the motor, it's widened just enough to carve the cup (unless 'Fit hub to motor' is off).
        """
        if state.export_busy or state.preview_busy or state.assess_busy:
            return
        from datetime import datetime

        from fansim.fan_spec import mount_min_hub_radius
        spec = active_spec()
        # Widen the hub to the minimum mountable radius if it's too narrow, so the cup carves at all.
        # Gated by the "Fit hub to motor on export" switch — off = keep the aero hub (cup won't carve
        # on a too-small hub, and the message says so) for users mounting the fan a different way.
        need = mount_min_hub_radius(spec)
        grew_from = None
        if state.export_fit_hub and need is not None and float(state.e_hub_radius) < need:
            grew_from = float(state.e_hub_radius)
            state.e_hub_radius = round(need + 0.05, 2)   # just clears the fit test
        params = build_edit_params()                     # rebuilt with the (possibly widened) hub
        exports = Path("exports")
        exports.mkdir(exist_ok=True)
        tid = state.selected_trial
        base = f"design_{tid}" if tid is not None else "fan"
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = exports / f"{base}_{stamp}.stl"

        async def task():
            state.export_busy = True
            heavy = " (features are heavy — up to ~3 min)" if params.features.active else ""
            state.export_msg = f"⏳ Building print-ready STL{heavy}…"
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                rep = await loop.run_in_executor(None, _do_export, params, out, spec.motor_mount)
            except Exception as exc:  # noqa: BLE001
                state.export_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
                state.export_busy = False
                state.flush()
                return
            wt = "watertight" if rep.ok else "⚠ NON-manifold"
            if rep.mount_fits is True:
                mnt = f" · ✓ motor cup carved ({rep.mount_msg})"
            elif rep.mount_fits is False:
                mnt = f" · ⚠ {rep.mount_msg}"
                if not state.export_fit_hub:   # explain the solid hub + how to get the cup
                    mnt += " — turn on 'Fit hub to motor on export' to widen it and carve the cup"
            else:
                mnt = " · (this fan model has no motor-mount defined)"
            grew = ""
            if grew_from is not None:
                grew = (f"\n↳ Hub widened {grew_from:.1f} → {state.e_hub_radius:.1f} mm to fit the "
                        f"{spec.motor_mount.cavity_dia_mm:.0f} mm motor — press Preview to see it. The "
                        f"CFM/eff shown were for the narrower hub, so they're now approximate; re-Assess "
                        f"for exact numbers.")
            state.export_msg = f"✓ Saved {out.resolve()}  ({wt}{mnt}){grew}"
            state.export_busy = False
            state.flush()

        asynchronous.create_task(task())

================================================================================
## EDIT 172  @ 2026-08-30T23:30:46

--- FIND ---
                                v3.VBtn("💾 Export STL", size="small", variant="tonal",
                                        color="primary", click=(export_stl_current,))
                            v3.VSwitch(v_model=("export_fit_hub",), density="compact",
--- REPLACE WITH ---
                                v3.VBtn("💾 Export STL", size="small", variant="tonal",
                                        color="primary", click=(export_stl_current,),
                                        loading=("export_busy",),
                                        disabled=("export_busy || preview_busy || assess_busy",))
                            v3.VSwitch(v_model=("export_fit_hub",), density="compact",

================================================================================
## EDIT 173  @ 2026-08-31T02:46:56

--- FIND ---
    state.sweep_param = "stagger mid"   # a valid label (o[0]); the strongest flow/eff lever
    state.sweep_steps = 3
--- REPLACE WITH ---
    state.sweep_param = "stagger mid"   # a valid label (o[0]); the strongest flow/eff lever
    state.sweep_steps = 3
    state.sweep_active = False           # a sweep is running -> show progress bar + Cancel
    state.sweep_cancel = False           # user asked to stop -> the loop halts after the current design
    state.sweep_progress = 0             # 0-100 for the progress bar

================================================================================
## EDIT 174  @ 2026-08-31T02:47:14

--- FIND ---
        async def task():
            state.assess_busy = True
            done = 0
            try:
                for i, val in enumerate(values):
                    flat, feat = dict(base_flat), dict(base_feat)
                    if kind == "flat":
                        flat[field] = int(val) if field == "n_blades" else float(val)
                    else:
                        feat[field] = float(val)
                        if kind == "tub" and feat["tubercle_waves"] == 0:
                            feat["tubercle_waves"] = 6
                        if kind == "ser" and feat["serration_waves"] == 0:
                            feat["serration_waves"] = 8
                        if kind == "dim":
                            feat["dimple_rows"] = feat["dimple_rows"] or 5
                            feat["dimple_cols"] = feat["dimple_cols"] or 5
                    params = blade_from_flat(flat, Features(**feat))
                    state.assess_msg = f"Sweep {label} {i+1}/{len(values)} = {val:g}: running CFD…"
                    state.flush()
                    if not check_printability(params).printable:
                        continue
                    try:  # one design failing shouldn't abort the whole sweep
                        if await _assess(params, flat, f"sweep {label}={val:g}"):
                            done += 1
                    except Exception as exc:  # noqa: BLE001
                        state.assess_msg = f"Sweep {label}={val:g} failed: {type(exc).__name__}: {exc}"
                        state.flush()
                state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
            finally:
                state.assess_busy = False
                state.flush()

        asynchronous.create_task(task())
--- REPLACE WITH ---
        async def task():
            state.assess_busy = True
            state.sweep_active = True
            state.sweep_cancel = False
            state.sweep_progress = 0
            done = 0
            n = len(values)
            try:
                for i, val in enumerate(values):
                    if state.sweep_cancel:   # user hit Cancel — stop before starting the next design
                        state.assess_msg = f"Sweep of {label} cancelled: {done}/{n} done ({done} ◆ added)."
                        break
                    flat, feat = dict(base_flat), dict(base_feat)
                    if kind == "flat":
                        flat[field] = int(val) if field == "n_blades" else float(val)
                    else:
                        feat[field] = float(val)
                        if kind == "tub" and feat["tubercle_waves"] == 0:
                            feat["tubercle_waves"] = 6
                        if kind == "ser" and feat["serration_waves"] == 0:
                            feat["serration_waves"] = 8
                        if kind == "dim":
                            feat["dimple_rows"] = feat["dimple_rows"] or 5
                            feat["dimple_cols"] = feat["dimple_cols"] or 5
                    params = blade_from_flat(flat, Features(**feat))
                    state.assess_msg = (f"Sweep {label} {i+1}/{n} = {val:g}: running CFD… "
                                        f"(~4 min/step; {done} added so far)")
                    state.sweep_progress = int(100 * i / n)
                    state.flush()
                    if not check_printability(params).printable:
                        continue
                    try:  # one design failing shouldn't abort the whole sweep
                        if await _assess(params, flat, f"sweep {label}={val:g}"):
                            done += 1
                    except Exception as exc:  # noqa: BLE001
                        state.assess_msg = f"Sweep {label}={val:g} failed: {type(exc).__name__}: {exc}"
                        state.flush()
                else:
                    state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
                state.sweep_progress = 100
            finally:
                state.assess_busy = False
                state.sweep_active = False
                state.sweep_cancel = False
                state.flush()

        asynchronous.create_task(task())

    def cancel_sweep():
        """Ask a running sweep to stop. The IN-FLIGHT CFD design still finishes (it's a subprocess we
        don't interrupt mid-solve), then the loop halts before the next one — so this stops within one
        ~4-min step, without killing the cockpit."""
        if state.sweep_active:
            state.sweep_cancel = True
            state.assess_msg = "⏹ Cancelling — stopping after the current design finishes…"
            state.flush()

================================================================================
## EDIT 175  @ 2026-08-31T02:47:32

--- FIND ---
                                    v3.VBtn("Run", size="small", color="success",
                                            variant="tonal", click=(on_sweep,),
                                            disabled=("assess_busy",))
                            html.Div("{{ assess_msg }}", classes="text-caption mt-2",
                                     style="white-space: pre-line")
--- REPLACE WITH ---
                                    v3.VBtn("Run", size="small", color="success",
                                            variant="tonal", click=(on_sweep,),
                                            disabled=("assess_busy",))
                            # live sweep progress + cancel (a sweep is many ~4-min CFD steps)
                            with v3.VRow(v_if="sweep_active", no_gutters=True,
                                         classes="mt-2 align-center"):
                                with v3.VCol(cols=9, classes="pr-2"):
                                    v3.VProgressLinear(model_value=("sweep_progress",), height=8,
                                                       color="success", rounded=True)
                                with v3.VCol(cols=3):
                                    v3.VBtn("⏹ Cancel", size="x-small", color="error",
                                            variant="tonal", block=True, click=(cancel_sweep,),
                                            disabled=("sweep_cancel",))
                            html.Div("{{ assess_msg }}", classes="text-caption mt-2",
                                     style="white-space: pre-line")

================================================================================
## EDIT 176  @ 2026-08-31T02:49:08

--- FIND ---
            winglet_span=state.e_winglet_span, winglet_sweep=state.e_winglet_sweep,
            winglet_lean=state.e_winglet_lean,
            hub_radius=state.e_hub_radius, tip_radius=state.e_tip_radius,
--- REPLACE WITH ---
            winglet_span=state.e_winglet_span, winglet_sweep=state.e_winglet_sweep,
            winglet_lean=state.e_winglet_lean,
            tip_round=state.e_tip_round, tip_round_start=state.e_tip_start,
            hub_radius=state.e_hub_radius, tip_radius=state.e_tip_radius,

================================================================================
## EDIT 177  @ 2026-08-31T02:49:14

--- FIND ---
        state.e_winglet_span = float(p.get("winglet_span", 0.85))  # where the tip winglet begins
        state.e_winglet_sweep = float(p.get("winglet_sweep", 0.0))  # tip axial curl (mm), 0=off
        state.e_winglet_lean = float(p.get("winglet_lean", 0.0))   # tip circumferential curl (deg)
--- REPLACE WITH ---
        state.e_winglet_span = float(p.get("winglet_span", 0.85))  # where the tip winglet begins
        state.e_winglet_sweep = float(p.get("winglet_sweep", 0.0))  # tip axial curl (mm), 0=off
        state.e_winglet_lean = float(p.get("winglet_lean", 0.0))   # tip circumferential curl (deg)
        state.e_tip_round = float(p.get("tip_round", 0.0))         # round the tip (0=square edge)
        state.e_tip_start = float(p.get("tip_round_start", 0.80))  # where tip rounding begins (span)

================================================================================
## EDIT 178  @ 2026-08-31T02:49:21

--- FIND ---
                                with v3.VExpansionPanel(title="Winglet — tip"):
                                    with v3.VExpansionPanelText():
                                        _slider("Winglet start (span)", "e_winglet_span", 0.6, 0.95, 0.05)
                                        _slider("Winglet sweep (mm)", "e_winglet_sweep", 0, 15, 0.5)
                                        _slider("Winglet lean (deg)", "e_winglet_lean", 0, 30, 1)
--- REPLACE WITH ---
                                with v3.VExpansionPanel(title="Tip — round & winglet"):
                                    with v3.VExpansionPanelText():
                                        _slider("Tip round", "e_tip_round", 0.0, 1.0, 0.05)
                                        _slider("Tip round start (span)", "e_tip_start", 0.5, 0.92, 0.02)
                                        _slider("Winglet start (span)", "e_winglet_span", 0.6, 0.95, 0.05)
                                        _slider("Winglet sweep (mm)", "e_winglet_sweep", 0, 15, 0.5)
                                        _slider("Winglet lean (deg)", "e_winglet_lean", 0, 30, 1)

================================================================================
## EDIT 179  @ 2026-08-31T02:49:27

--- FIND ---
    "e_winglet_span": "Where the WINGLET starts (fraction of span). Below this the blade is straight; beyond it the tip curls.",
--- REPLACE WITH ---
    "e_tip_round": "Rounds the blade TIP — tapers the chord over the outer span so the leading & trailing edges curve together, instead of a blunt straight tip edge. 0 = square.",
    "e_tip_start": "Where the tip rounding begins (fraction of span). Lower = a longer, gentler rounded tip; higher = a small rounded cap near the very tip.",
    "e_winglet_span": "Where the WINGLET starts (fraction of span). Below this the blade is straight; beyond it the tip curls.",

================================================================================
## EDIT 180  @ 2026-08-31T02:49:32

--- FIND ---
        "e_skew_mid", "e_skew_tip", "e_winglet_span", "e_winglet_sweep", "e_winglet_lean",
        "e_hub_radius", "e_tip_radius", "e_hub_height", "e_hub_profile", "e_hub_nose",
--- REPLACE WITH ---
        "e_skew_mid", "e_skew_tip", "e_winglet_span", "e_winglet_sweep", "e_winglet_lean",
        "e_tip_round", "e_tip_start",
        "e_hub_radius", "e_tip_radius", "e_hub_height", "e_hub_profile", "e_hub_nose",

================================================================================
## EDIT 181  @ 2026-08-31T02:49:38

--- FIND ---
        state.e_winglet_span = round(_r.uniform(0.75, 0.9), 2)
        state.e_winglet_sweep = round(_r.uniform(4, 12), 1) if wl else 0.0
        state.e_winglet_lean = round(_r.uniform(0, 20), 1) if wl else 0.0
--- REPLACE WITH ---
        state.e_winglet_span = round(_r.uniform(0.75, 0.9), 2)
        state.e_winglet_sweep = round(_r.uniform(4, 12), 1) if wl else 0.0
        state.e_winglet_lean = round(_r.uniform(0, 20), 1) if wl else 0.0
        tipr = _r.random() < 0.5   # sometimes round the tip for variety
        state.e_tip_round = round(_r.uniform(0.3, 0.9), 2) if tipr else 0.0
        state.e_tip_start = round(_r.uniform(0.7, 0.88), 2)

================================================================================
## EDIT 182  @ 2026-08-31T02:57:01

--- FIND ---
        params = build_edit_params()
        printable = check_printability(params)
        if not printable.printable:
            state.preview_msg = f"⚠ Not printable: {printable.reason}"
            return
        flat, feat = edit_flat(), edit_features()  # serializable inputs for the isolated build
--- REPLACE WITH ---
        params = build_edit_params()
        # A preview should SHOW the geometry even if it isn't printable (e.g. a rounded/thin tip) —
        # you're looking at the shape, not printing it. Warn instead of refusing to render; Assess and
        # Export still gate it. (The old code returned here, so a thin tip showed nothing at all.)
        printable = check_printability(params)
        print_warn = ("" if printable.printable else
                      f"\n⚠ Not printable as-is: {printable.reason}. Preview shown anyway — thicken the "
                      f"tip (Airfoil → Thickness tip) or lower Tip round; it'll be gated at Assess/Export.")
        flat, feat = edit_flat(), edit_features()  # serializable inputs for the isolated build

================================================================================
## EDIT 183  @ 2026-08-31T02:57:09

--- FIND ---
            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                                 f"camber {state.e_camber:.3f}, {feats}.\n{status}{print_line}{tone_line}")
--- REPLACE WITH ---
            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
                                 f"camber {state.e_camber:.3f}, {feats}.\n{status}{print_line}"
                                 f"{tone_line}{print_warn}")

================================================================================
## EDIT 184  @ 2026-08-31T14:20:33

--- FIND ---
        need = mount_min_hub_radius(spec)
        grew_from = None
        if state.export_fit_hub and need is not None and float(state.e_hub_radius) < need:
            grew_from = float(state.e_hub_radius)
            state.e_hub_radius = round(need + 0.05, 2)   # just clears the fit test
        params = build_edit_params()                     # rebuilt with the (possibly widened) hub
--- REPLACE WITH ---
        need = mount_min_hub_radius(spec)
        grew_from = None
        if state.export_fit_hub and need is not None and float(state.e_hub_radius) < need:
            grew_from = float(state.e_hub_radius)
            state.e_hub_radius = round(need + 0.05, 2)   # just clears the fit test
        # also grow the hub HEIGHT to the motor's requirement so the cup has a solid cap and the hub
        # is tall enough to clear the frame spokes (e_hub_height 0 = auto, usually shorter than needed).
        min_h = getattr(spec.motor_mount, "min_hub_height_mm", 0.0) if spec.motor_mount else 0.0
        grew_h_from = None
        if state.export_fit_hub and min_h and float(state.e_hub_height) < min_h:
            grew_h_from = float(state.e_hub_height)
            state.e_hub_height = float(min_h)
        params = build_edit_params()                     # rebuilt with the (possibly widened/taller) hub

================================================================================
## EDIT 185  @ 2026-08-31T14:20:45

--- FIND ---
            grew = ""
            if grew_from is not None:
                grew = (f"\n↳ Hub widened {grew_from:.1f} → {state.e_hub_radius:.1f} mm to fit the "
                        f"{spec.motor_mount.cavity_dia_mm:.0f} mm motor — press Preview to see it. The "
                        f"CFM/eff shown were for the narrower hub, so they're now approximate; re-Assess "
                        f"for exact numbers.")
--- REPLACE WITH ---
            grew = ""
            if grew_from is not None:
                grew += (f"\n↳ Hub widened {grew_from:.1f} → {state.e_hub_radius:.1f} mm to fit the "
                         f"{spec.motor_mount.cavity_dia_mm:.1f} mm motor hub.")
            if grew_h_from is not None:
                grew += (f"\n↳ Hub height set to {state.e_hub_height:.0f} mm so the cup has a cap and "
                         f"clears the frame spokes.")
            if grew:
                grew += (" Press Preview to see it; the CFM/eff shown were for the original hub, so "
                         "they're now approximate — re-Assess for exact numbers.")

================================================================================
## EDIT 186  @ 2026-08-31T15:10:04

--- FIND ---
from fansim.fan_spec import (
    check_build,
    estimate_weight_g,
    fan_spec_names,
    get_fan_spec,
    load_fan_models_dir,
    over_spec_flags,
)
--- REPLACE WITH ---
from fansim.fan_spec import (
    MotorMount,
    check_build,
    delete_user_fan_model,
    estimate_weight_g,
    fan_spec_names,
    get_fan_spec,
    is_builtin,
    load_fan_models_dir,
    mount_min_hub_radius,
    over_spec_flags,
    save_user_fan_model,
)

================================================================================
## EDIT 187  @ 2026-08-31T15:10:34

--- FIND ---
    def _model_readout():
        s = get_fan_spec(state.fan_model)
        state.model_info = (f"{s.name}: tip ≤{s.tip_dia_mm[1]:.0f} mm, depth ≤{s.depth_mm[1]:.0f} mm, "
                            f"hub {s.hub_dia_mm[0]:.0f}-{s.hub_dia_mm[1]:.0f} mm, "
                            f"{s.max_shaft_power_w:.2f} W shaft ({s.voltage_v:.0f} V×{s.max_current_a:.2f} A), "
                            f"≤{s.max_weight_g:.0f} g. Published {s.ref_cfm:.0f} CFM / "
                            f"{s.ref_static_pa:.0f} Pa / {s.ref_noise_dba:.0f} dBA.")
    _model_readout()

    def reload_models():
        load_fan_models_dir()
        state.fan_models = fan_spec_names()
        _model_readout()
        state.flush()

    @state.change("fan_model")
    def _on_model(**_):
        _model_readout()
--- REPLACE WITH ---
    def _model_readout():
        s = get_fan_spec(state.fan_model)
        refs = (f" Published {s.ref_cfm:.0f} CFM / {s.ref_static_pa:.0f} Pa / {s.ref_noise_dba:.0f} dBA."
                if s.ref_cfm is not None else " (no published reference — exploratory model).")
        tag = " [built-in ref, read-only]" if is_builtin(state.fan_model) else " [user model]"
        wt = f"≤{s.max_weight_g:.0f} g." if s.max_weight_g else ""
        state.model_info = (f"{s.name}{tag}: tip ≤{s.tip_dia_mm[1]:.0f} mm, depth ≤{s.depth_mm[1]:.0f} mm, "
                            f"hub {s.hub_dia_mm[0]:.0f}-{s.hub_dia_mm[1]:.0f} mm, "
                            f"{s.max_shaft_power_w:.2f} W shaft ({s.voltage_v:.0f} V×{s.max_current_a:.2f} A), "
                            f"{wt}{refs}")

    def _hub_fit_readout():
        """Live 'does the hub fit THIS fan's motor?' readout + the minimum hub that would fit."""
        s = get_fan_spec(state.fan_model)
        need = mount_min_hub_radius(s)
        if need is None:
            state.hub_fit_info = f"{s.name}: no motor mount defined — hub size unconstrained."
            return
        cur = float(state.e_hub_radius)
        cav = s.motor_mount.cavity_dia_mm
        state.hub_fit_info = (f"Motor hub {cav:.1f} mm → this hub needs radius ≥ {need:.1f} mm. "
                              + (f"Current {cur:.1f} mm ✓ fits — cup will carve." if cur >= need
                                 else f"Current {cur:.1f} mm ✗ TOO SMALL, won't fit (Snap, or turn up Hub radius)."))

    def snap_hub_to_fit():
        """Set the hub radius to the smallest that fits the selected fan's motor (with wall margin)."""
        s = get_fan_spec(state.fan_model)
        need = mount_min_hub_radius(s)
        if need is not None:
            state.e_hub_radius = round(need + 0.05, 2)
            _hub_fit_readout()
            state.flush()

    state.hub_fit_info = ""
    _model_readout(); _hub_fit_readout()

    def reload_models():
        load_fan_models_dir()
        state.fan_models = fan_spec_names()
        _model_readout(); _hub_fit_readout()
        state.flush()

    # ---- fan-model MANAGER: create / edit / delete USER models (built-ins are read-only refs) -----
    state.fm_key = ""
    state.fm_tip_max = 110.0
    state.fm_hub_min = 30.0
    state.fm_hub_max = 60.0
    state.fm_depth_max = 25.0
    state.fm_rpm = 2000.0
    state.fm_cav_dia = 37.25      # motor cavity dia the printed hub slips over (0 = no motor mount)
    state.fm_cav_depth = 13.0
    state.fm_hub_h = 15.0
    state.fm_msg = ""
    state.model_is_builtin = is_builtin(state.fan_model)

    def load_model_into_form(**_):
        """Prefill the form from the selected model (so 'edit' = tweak the fields, then Save)."""
        s = get_fan_spec(state.fan_model)
        state.fm_key = "" if is_builtin(state.fan_model) else state.fan_model
        state.fm_tip_max = float(s.tip_dia_mm[1]); state.fm_hub_min = float(s.hub_dia_mm[0])
        state.fm_hub_max = float(s.hub_dia_mm[1]); state.fm_depth_max = float(s.depth_mm[1])
        state.fm_rpm = float(s.rpm)
        m = s.motor_mount
        state.fm_cav_dia = float(m.cavity_dia_mm) if m else 0.0
        state.fm_cav_depth = float(m.cavity_depth_mm) if m else 0.0
        state.fm_hub_h = float(getattr(m, "min_hub_height_mm", 0.0)) if m else 0.0
        state.fm_msg = ("Loaded a built-in — Save under a NEW name to make an editable copy."
                        if is_builtin(state.fan_model) else f"Loaded user model '{state.fan_model}' — edit + Save.")
        state.flush()

    def save_model():
        key = (state.fm_key or "").strip().lower().replace(" ", "_")
        if not key:
            state.fm_msg = "⚠ Enter a model name first."; state.flush(); return
        base = get_fan_spec(state.fan_model)   # inherit unshown fields (voltage, power, material…)
        mount = None
        if float(state.fm_cav_dia) > 0:
            mount = MotorMount(cavity_dia_mm=float(state.fm_cav_dia), cavity_depth_mm=float(state.fm_cav_depth),
                               rear_bore_dia_mm=(base.motor_mount.rear_bore_dia_mm if base.motor_mount else 0.0),
                               shaft_dia_mm=(base.motor_mount.shaft_dia_mm if base.motor_mount else 0.0),
                               min_hub_height_mm=float(state.fm_hub_h))
        spec = dataclasses.replace(
            base, name=key.replace("_", " ").title(),
            tip_dia_mm=(base.tip_dia_mm[0], float(state.fm_tip_max)),
            hub_dia_mm=(float(state.fm_hub_min), float(state.fm_hub_max)),
            depth_mm=(base.depth_mm[0], float(state.fm_depth_max)),
            rpm=float(state.fm_rpm), motor_mount=mount,
            leeway_tip_dia_mm=0.0, leeway_depth_mm=0.0, leeway_weight_g=0.0, over_voltage_v=0.0)
        try:
            path = save_user_fan_model(key, spec)
        except Exception as exc:  # noqa: BLE001
            state.fm_msg = f"⚠ Save failed: {exc}"; state.flush(); return
        state.fan_models = fan_spec_names()
        state.fan_model = key
        state.fm_msg = f"✓ Saved user model '{key}' → {path}"
        state.flush()

    def delete_model():
        key = state.fan_model
        try:
            ok = delete_user_fan_model(key)
        except Exception as exc:  # noqa: BLE001 (built-in refuses)
            state.fm_msg = f"⚠ {exc}"; state.flush(); return
        state.fan_models = fan_spec_names()
        state.fan_model = "a12x25"
        state.fm_msg = f"{'✓ Deleted' if ok else '⚠ Not found:'} '{key}'."
        state.flush()

    @state.change("fan_model")
    def _on_model(**_):
        _model_readout(); _hub_fit_readout()
        state.model_is_builtin = is_builtin(state.fan_model)

================================================================================
## EDIT 188  @ 2026-08-31T15:10:49

--- FIND ---
    def _recompute_stale(**_):
        if sel_sig[0] is None:
            return
--- REPLACE WITH ---
    def _recompute_stale(**_):
        _hub_fit_readout()   # keep the 'does the hub fit the motor?' readout live as sliders move
        if sel_sig[0] is None:
            return

================================================================================
## EDIT 189  @ 2026-08-31T15:11:00

--- FIND ---
                                with v3.VExpansionPanel(title="Hub"):
                                    with v3.VExpansionPanelText():
                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
--- REPLACE WITH ---
                                with v3.VExpansionPanel(title="Hub"):
                                    with v3.VExpansionPanelText():
                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
                                        with v3.VRow(no_gutters=True, classes="align-center mb-1"):
                                            with v3.VCol(cols=8, classes="pr-1"):
                                                html.Div("{{ hub_fit_info }}", classes="text-caption")
                                            with v3.VCol(cols=4):
                                                v3.VBtn("Snap to fit", size="x-small", variant="tonal",
                                                        color="primary", block=True,
                                                        click=(snap_hub_to_fit,))

================================================================================
## EDIT 190  @ 2026-08-31T15:11:53

--- FIND ---
                                                _slider("Over-voltage (V)", "lee_overvolt", 0, 12, 0.5)
                                                _slider("Extra weight (g)", "lee_weight", 0, 40, 1)
                        with v3.VCard(classes="mb-2 pa-3"):
--- REPLACE WITH ---
                                                _slider("Over-voltage (V)", "lee_overvolt", 0, 12, 0.5)
                                                _slider("Extra weight (g)", "lee_weight", 0, 40, 1)
                                        with v3.VExpansionPanel(title="Manage fan models (add / edit / delete)"):
                                            with v3.VExpansionPanelText():
                                                html.Div("Built-in models are read-only references. Load one, "
                                                         "tweak, then Save under a NEW name to make your own "
                                                         "(editable + deletable).", classes="text-caption mb-2")
                                                v3.VBtn("Load selected model into form", size="x-small",
                                                        variant="tonal", block=True,
                                                        click=(load_model_into_form,), classes="mb-2")
                                                v3.VTextField(label="Model name (new name = create)",
                                                              v_model=("fm_key",), density="compact",
                                                              variant="outlined", hide_details=True, classes="mb-2")
                                                with v3.VRow(no_gutters=True):
                                                    with v3.VCol(cols=6, classes="pr-1"):
                                                        v3.VTextField(label="Max tip dia (mm)",
                                                                      v_model=("fm_tip_max",), type="number",
                                                                      density="compact", variant="outlined",
                                                                      hide_details=True, classes="mb-2")
                                                    with v3.VCol(cols=6, classes="pl-1"):
                                                        v3.VTextField(label="Max depth (mm)",
                                                                      v_model=("fm_depth_max",), type="number",
                                                                      density="compact", variant="outlined",
                                                                      hide_details=True, classes="mb-2")
                                                with v3.VRow(no_gutters=True):
                                                    with v3.VCol(cols=6, classes="pr-1"):
                                                        v3.VTextField(label="Hub dia min (mm)",
                                                                      v_model=("fm_hub_min",), type="number",
                                                                      density="compact", variant="outlined",
                                                                      hide_details=True, classes="mb-2")
                                                    with v3.VCol(cols=6, classes="pl-1"):
                                                        v3.VTextField(label="Hub dia max (mm)",
                                                                      v_model=("fm_hub_max",), type="number",
                                                                      density="compact", variant="outlined",
                                                                      hide_details=True, classes="mb-2")
                                                html.Div("Motor mount — 0 cavity = generic (no motor):",
                                                         classes="text-caption")
                                                with v3.VRow(no_gutters=True):
                                                    with v3.VCol(cols=4, classes="pr-1"):
                                                        v3.VTextField(label="Cavity dia", v_model=("fm_cav_dia",),
                                                                      type="number", density="compact",
                                                                      variant="outlined", hide_details=True,
                                                                      classes="mb-2")
                                                    with v3.VCol(cols=4, classes="px-1"):
                                                        v3.VTextField(label="Cavity depth",
                                                                      v_model=("fm_cav_depth",), type="number",
                                                                      density="compact", variant="outlined",
                                                                      hide_details=True, classes="mb-2")
                                                    with v3.VCol(cols=4, classes="pl-1"):
                                                        v3.VTextField(label="Min hub H", v_model=("fm_hub_h",),
                                                                      type="number", density="compact",
                                                                      variant="outlined", hide_details=True,
                                                                      classes="mb-2")
                                                with v3.VRow(no_gutters=True):
                                                    with v3.VCol(cols=6, classes="pr-1"):
                                                        v3.VBtn("💾 Save model", size="small", color="primary",
                                                                block=True, click=(save_model,))
                                                    with v3.VCol(cols=6, classes="pl-1"):
                                                        v3.VBtn("🗑 Delete", size="small", color="error",
                                                                variant="tonal", block=True,
                                                                click=(delete_model,),
                                                                disabled=("model_is_builtin",))
                                                html.Div("{{ fm_msg }}", classes="text-caption mt-2",
                                                         style="white-space: pre-line")
                        with v3.VCard(classes="mb-2 pa-3"):

================================================================================
## EDIT 191  @ 2026-08-31T15:13:15

--- FIND ---
        if need is None:
            state.hub_fit_info = f"{s.name}: no motor mount defined — hub size unconstrained."
            return
        cur = float(state.e_hub_radius)
        cav = s.motor_mount.cavity_dia_mm
        state.hub_fit_info = (f"Motor hub {cav:.1f} mm → this hub needs radius ≥ {need:.1f} mm. "
                              + (f"Current {cur:.1f} mm ✓ fits — cup will carve." if cur >= need
                                 else f"Current {cur:.1f} mm ✗ TOO SMALL, won't fit (Snap, or turn up Hub radius)."))
--- REPLACE WITH ---
        if need is None:
            state.hub_fit_info = f"{s.name}: no motor mount defined — hub size unconstrained."
            return
        cav = s.motor_mount.cavity_dia_mm
        cur = state.e_hub_radius
        if cur is None:   # before the editor is populated
            state.hub_fit_info = f"Motor hub {cav:.1f} mm → this hub needs radius ≥ {need:.1f} mm."
            return
        cur = float(cur)
        state.hub_fit_info = (f"Motor hub {cav:.1f} mm → this hub needs radius ≥ {need:.1f} mm. "
                              + (f"Current {cur:.1f} mm ✓ fits — cup will carve." if cur >= need
                                 else f"Current {cur:.1f} mm ✗ TOO SMALL, won't fit (Snap, or turn up Hub radius)."))

================================================================================
## EDIT 192  @ 2026-08-31T20:11:56

--- FIND ---
            state.e_hub_radius = round(need + 0.05, 2)
            _hub_fit_readout()
            state.flush()

    state.hub_fit_info = ""
    _model_readout(); _hub_fit_readout()
--- REPLACE WITH ---
            state.e_hub_radius = round(need + 0.05, 2)
            _hub_fit_readout()
            state.flush()

    def _tip_fit_readout():
        """Live 'does the blade fit inside the fan housing?' readout — the tip diameter (2×tip radius)
        vs the fan model's max frame diameter."""
        s = get_fan_spec(state.fan_model)
        max_dia = s.tip_dia_mm[1]
        max_r = max_dia / 2.0
        cur = state.e_tip_radius
        if cur is None:
            state.tip_fit_info = f"Frame ≤ {max_dia:.0f} mm dia → tip radius (length) ≤ {max_r:.1f} mm."
            return
        dia = 2.0 * float(cur)
        state.tip_fit_info = (f"Frame ≤ {max_dia:.0f} mm dia → tip radius ≤ {max_r:.1f} mm. "
                              + (f"Current {dia:.0f} mm ✓ fits the housing." if dia <= max_dia
                                 else f"Current {dia:.0f} mm ✗ over the frame by {dia-max_dia:.0f} mm "
                                      "— Fit to frame, or lower Tip radius."))

    def snap_tip_to_frame():
        """Shrink the blade length so its tip diameter fits inside the selected fan's frame (only
        shrinks — a design already inside the housing is left alone)."""
        s = get_fan_spec(state.fan_model)
        max_r = s.tip_dia_mm[1] / 2.0
        if state.e_tip_radius is not None and float(state.e_tip_radius) > max_r:
            state.e_tip_radius = round(max_r - 0.05, 2)   # a hair inside so the built dia clears
            _tip_fit_readout()
            state.flush()

    state.hub_fit_info = ""
    state.tip_fit_info = ""
    _model_readout(); _hub_fit_readout(); _tip_fit_readout()

================================================================================
## EDIT 193  @ 2026-08-31T20:12:04

--- FIND ---
    def reload_models():
        load_fan_models_dir()
        state.fan_models = fan_spec_names()
        _model_readout(); _hub_fit_readout()
        state.flush()
--- REPLACE WITH ---
    def reload_models():
        load_fan_models_dir()
        state.fan_models = fan_spec_names()
        _model_readout(); _hub_fit_readout(); _tip_fit_readout()
        state.flush()

================================================================================
## EDIT 194  @ 2026-08-31T20:12:08

--- FIND ---
    @state.change("fan_model")
    def _on_model(**_):
        _model_readout(); _hub_fit_readout()
        state.model_is_builtin = is_builtin(state.fan_model)
--- REPLACE WITH ---
    @state.change("fan_model")
    def _on_model(**_):
        _model_readout(); _hub_fit_readout(); _tip_fit_readout()
        state.model_is_builtin = is_builtin(state.fan_model)

================================================================================
## EDIT 195  @ 2026-08-31T20:12:13

--- FIND ---
    def _recompute_stale(**_):
        _hub_fit_readout()   # keep the 'does the hub fit the motor?' readout live as sliders move
        if sel_sig[0] is None:
            return
--- REPLACE WITH ---
    def _recompute_stale(**_):
        _hub_fit_readout()   # keep the fit readouts live as sliders move
        _tip_fit_readout()
        if sel_sig[0] is None:
            return

================================================================================
## EDIT 196  @ 2026-08-31T20:12:21

--- FIND ---
                                        _slider("Tip radius / length (mm)", "e_tip_radius", 45, 59, 0.5)
                                        _slider("Hub height (mm, 0=auto)", "e_hub_height", 0, 30, 0.5)
--- REPLACE WITH ---
                                        _slider("Tip radius / length (mm)", "e_tip_radius", 45, 59, 0.5)
                                        with v3.VRow(no_gutters=True, classes="align-center mb-1"):
                                            with v3.VCol(cols=8, classes="pr-1"):
                                                html.Div("{{ tip_fit_info }}", classes="text-caption")
                                            with v3.VCol(cols=4):
                                                v3.VBtn("Fit to frame", size="x-small", variant="tonal",
                                                        color="primary", block=True,
                                                        click=(snap_tip_to_frame,))
                                        _slider("Hub height (mm, 0=auto)", "e_hub_height", 0, 30, 0.5)

================================================================================
## EDIT 197  @ 2026-08-31T20:28:02

--- FIND ---
        zs += [v.z for v in pts]
    return max(zs) - min(zs)


def _depth_drivers(flat: dict, top: int = 3) -> list[tuple[str, float]]:
--- REPLACE WITH ---
        zs += [v.z for v in pts]
    return max(zs) - min(zs)


def _blade_max_dia(params) -> float:
    """Max blade DIAMETER (mm) from the section points -- FAST (no CAD solid). The BUILT tip diameter
    runs a bit past 2*tip_radius: the wrapped, chord-wide tip section bulges outward radially. This is
    the number the frame check must use, not the nominal 2*tip_radius (which reads ~0.5-2 mm small)."""
    import math

    from fansim.geometry.blade import _interp_stations, _section_points_3d
    from fansim.geometry.features import Features as _F
    it = _interp_stations(params, params.n_span)
    r0 = params.hub_radius - params.root_embed
    rmax = 0.0
    for i in range(params.n_span):
        rf = float(it["r_frac"][i]); r = r0 + (params.tip_radius - r0) * rf
        pts = _section_points_3d(
            r=r, r_frac=rf, chord=float(it["chord"][i]), stagger_deg=float(it["stagger_deg"][i]),
            thickness=float(it["thickness"][i]), max_camber=float(it["max_camber"][i]),
            camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]),
            skew=float(it["skew"][i]), le_sweep=float(it["le_sweep"][i]),
            lean_deg=float(it["lean_deg"][i]), n_chord=params.n_chord, features=_F())
        for v in pts:
            rr = math.hypot(v.x, v.y)
            if rr > rmax:
                rmax = rr
    return 2.0 * rmax


def _depth_drivers(flat: dict, top: int = 3) -> list[tuple[str, float]]:

================================================================================
## EDIT 198  @ 2026-08-31T20:28:20

--- FIND ---
    def _tip_fit_readout():
        """Live 'does the blade fit inside the fan housing?' readout — the tip diameter (2×tip radius)
        vs the fan model's max frame diameter."""
        s = get_fan_spec(state.fan_model)
        max_dia = s.tip_dia_mm[1]
        max_r = max_dia / 2.0
        cur = state.e_tip_radius
        if cur is None:
            state.tip_fit_info = f"Frame ≤ {max_dia:.0f} mm dia → tip radius (length) ≤ {max_r:.1f} mm."
            return
        dia = 2.0 * float(cur)
        state.tip_fit_info = (f"Frame ≤ {max_dia:.0f} mm dia → tip radius ≤ {max_r:.1f} mm. "
                              + (f"Current {dia:.0f} mm ✓ fits the housing." if dia <= max_dia
                                 else f"Current {dia:.0f} mm ✗ over the frame by {dia-max_dia:.0f} mm "
                                      "— Fit to frame, or lower Tip radius."))

    def snap_tip_to_frame():
        """Shrink the blade length so its tip diameter fits inside the selected fan's frame (only
        shrinks — a design already inside the housing is left alone)."""
        s = get_fan_spec(state.fan_model)
        max_r = s.tip_dia_mm[1] / 2.0
        if state.e_tip_radius is not None and float(state.e_tip_radius) > max_r:
            state.e_tip_radius = round(max_r - 0.05, 2)   # a hair inside so the built dia clears
            _tip_fit_readout()
            state.flush()
--- REPLACE WITH ---
    def _tip_fit_readout():
        """Live 'does the blade fit inside the fan housing?' readout — the ACTUAL built tip diameter
        (not the nominal 2×tip radius, which reads small) vs the fan model's max frame diameter."""
        s = get_fan_spec(state.fan_model)
        max_dia = s.tip_dia_mm[1]
        if state.e_tip_radius is None:
            state.tip_fit_info = f"Frame ≤ {max_dia:.0f} mm dia. 'Fit to frame' shrinks the blade to fit."
            return
        try:
            dia = _blade_max_dia(blade_from_flat(edit_flat(), Features()))
        except Exception:  # noqa: BLE001 - editor mid-populate; fall back to nominal
            dia = 2.0 * float(state.e_tip_radius)
        state.tip_fit_info = (f"Frame ≤ {max_dia:.0f} mm → built tip dia {dia:.1f} mm "
                              + ("✓ fits the housing." if dia <= max_dia
                                 else f"✗ over by {dia-max_dia:.1f} mm — click Fit to frame."))

    def snap_tip_to_frame():
        """Shrink the blade LENGTH until its BUILT tip diameter fits inside the selected fan's frame.
        Iterates against the real (section-point) diameter — the built tip bulges past 2×tip radius, so
        a naive radius = maxdia/2 lands ~0.5 mm over (the bug the user hit). Only shrinks."""
        s = get_fan_spec(state.fan_model)
        max_dia = s.tip_dia_mm[1]
        if state.e_tip_radius is None:
            return
        flat = edit_flat()
        tr = float(state.e_tip_radius)
        for _ in range(12):
            flat["tip_radius"] = tr
            try:
                dia = _blade_max_dia(blade_from_flat(flat, Features()))
            except Exception:  # noqa: BLE001
                break
            if dia <= max_dia - 0.15:      # land a hair inside so the built dia clears the frame
                break
            tr -= (dia - max_dia) / 2.0 + 0.15   # built dia ≈ 2*tr + bulge; drop tr by ~half the excess
            if tr < 20.0:                  # safety floor
                break
        state.e_tip_radius = round(tr, 2)
        _tip_fit_readout()
        state.flush()

================================================================================
## EDIT 199  @ 2026-08-31T20:37:12

--- FIND ---
        state.e_tip_radius = round(tr, 2)
        _tip_fit_readout()
        state.flush()

    state.hub_fit_info = ""
    state.tip_fit_info = ""
    _model_readout(); _hub_fit_readout(); _tip_fit_readout()
--- REPLACE WITH ---
        state.e_tip_radius = round(tr, 2)
        _tip_fit_readout()
        state.flush()

    def _depth_fit_readout():
        """Live 'does the blade fit the frame THICKNESS?' — built Z-depth vs the fan's max depth."""
        s = get_fan_spec(state.fan_model)
        max_d = s.depth_mm[1]
        if state.e_sweep_tip is None:
            state.depth_fit_info = f"Frame ≤ {max_d:.0f} mm deep. 'Fit depth' flattens the rake to fit."
            return
        try:
            d = _blade_z_extent(blade_from_flat(edit_flat(), Features()))
        except Exception:  # noqa: BLE001
            state.depth_fit_info = ""
            return
        state.depth_fit_info = (f"Frame ≤ {max_d:.0f} mm deep → blade {d:.1f} mm "
                                + ("✓ fits." if d <= max_d
                                   else f"✗ over by {d-max_d:.1f} mm — Fit depth (flattens sweep/LE), "
                                        "or add Extra-depth leeway."))

    def snap_depth_to_frame():
        """Reduce the blade's Z-depth to fit the frame by flattening the AXIAL-RAKE params (sweep + LE
        curve) — the cheapest depth levers, since they only shift the blade in Z, not its core aero.
        Scales them toward 0 until the built depth fits; if flat rake still overflows, the rest is
        structural (stagger/thickness/wrap) and it says so."""
        s = get_fan_spec(state.fan_model)
        max_d = s.depth_mm[1]
        if state.e_sweep_tip is None:
            return
        flat = edit_flat()
        rake = {"sweep_mid": "e_sweep_mid", "sweep_tip": "e_sweep_tip",
                "le_sweep_mid": "e_le_mid", "le_sweep_tip": "e_le_tip"}
        base = {k: float(flat.get(k, 0.0)) for k in rake}
        chosen = 0.0
        for f in (1.0, 0.85, 0.7, 0.55, 0.4, 0.25, 0.1, 0.0):   # keep as much rake as still fits
            for k in rake:
                flat[k] = base[k] * f
            try:
                d = _blade_z_extent(blade_from_flat(flat, Features()))
            except Exception:  # noqa: BLE001
                return
            if d <= max_d - 0.1:
                chosen = f
                break
        for k, sv in rake.items():
            setattr(state, sv, round(base[k] * chosen, 2))
        _depth_fit_readout()
        state.flush()

    state.hub_fit_info = ""
    state.tip_fit_info = ""
    state.depth_fit_info = ""
    _model_readout(); _hub_fit_readout(); _tip_fit_readout(); _depth_fit_readout()

================================================================================
## EDIT 200  @ 2026-08-31T20:37:37

--- FIND ---
                                        _slider("Skew mid (mm)", "e_skew_mid", -6, 6, 0.5)
                                        _slider("Skew tip (mm)", "e_skew_tip", -6, 6, 0.5)
--- REPLACE WITH ---
                                        _slider("Skew mid (mm)", "e_skew_mid", -6, 6, 0.5)
                                        _slider("Skew tip (mm)", "e_skew_tip", -6, 6, 0.5)
                                        with v3.VRow(no_gutters=True, classes="align-center mb-1"):
                                            with v3.VCol(cols=8, classes="pr-1"):
                                                html.Div("{{ depth_fit_info }}", classes="text-caption")
                                            with v3.VCol(cols=4):
                                                v3.VBtn("Fit depth", size="x-small", variant="tonal",
                                                        color="primary", block=True,
                                                        click=(snap_depth_to_frame,))

================================================================================
## EDIT 201  @ 2026-08-31T20:48:00

--- FIND ---
    def snap_depth_to_frame():
        """Reduce the blade's Z-depth to fit the frame by flattening the AXIAL-RAKE params (sweep + LE
        curve) — the cheapest depth levers, since they only shift the blade in Z, not its core aero.
        Scales them toward 0 until the built depth fits; if flat rake still overflows, the rest is
        structural (stagger/thickness/wrap) and it says so."""
        s = get_fan_spec(state.fan_model)
        max_d = s.depth_mm[1]
        if state.e_sweep_tip is None:
            return
        flat = edit_flat()
        rake = {"sweep_mid": "e_sweep_mid", "sweep_tip": "e_sweep_tip",
                "le_sweep_mid": "e_le_mid", "le_sweep_tip": "e_le_tip"}
        base = {k: float(flat.get(k, 0.0)) for k in rake}
        chosen = 0.0
        for f in (1.0, 0.85, 0.7, 0.55, 0.4, 0.25, 0.1, 0.0):   # keep as much rake as still fits
            for k in rake:
                flat[k] = base[k] * f
            try:
                d = _blade_z_extent(blade_from_flat(flat, Features()))
            except Exception:  # noqa: BLE001
                return
            if d <= max_d - 0.1:
                chosen = f
                break
        for k, sv in rake.items():
            setattr(state, sv, round(base[k] * chosen, 2))
        _depth_fit_readout()
        state.flush()
--- REPLACE WITH ---
    def snap_depth_to_frame():
        """Reduce the blade's Z-depth to fit the frame, cheapest-lever-first:
        (1) flatten the AXIAL RAKE (sweep + LE curve) — pure Z shift, no core-aero change;
        (2) if still over (depth is structural — chord×sin(stagger) dominates), gently REDUCE STAGGER
            (pitch) by the minimum factor that fits — this flattens the blade, at a real aero cost.
        Keeps as much of each as still fits, and the readout reports if it had to touch the pitch."""
        s = get_fan_spec(state.fan_model)
        max_d = s.depth_mm[1]
        if state.e_sweep_tip is None:
            return
        flat = edit_flat()

        def depth() -> float:
            return _blade_z_extent(blade_from_flat(flat, Features()))

        # stage 1 — flatten sweep + LE curve
        rake = {"sweep_mid": "e_sweep_mid", "sweep_tip": "e_sweep_tip",
                "le_sweep_mid": "e_le_mid", "le_sweep_tip": "e_le_tip"}
        base_rake = {k: float(flat.get(k, 0.0)) for k in rake}
        rf = 0.0
        for f in (1.0, 0.8, 0.6, 0.4, 0.2, 0.0):
            for k in rake:
                flat[k] = base_rake[k] * f
            try:
                if depth() <= max_d - 0.1:
                    rf = f
                    break
            except Exception:  # noqa: BLE001
                return

        # stage 2 — still too deep? reduce stagger (pitch) by the least amount that fits
        touched_pitch = False
        if depth() > max_d:
            stag = {"stagger_root": "e_stagger_root", "stagger_mid": "e_stagger_mid",
                    "stagger_tip": "e_stagger_tip"}
            base_stag = {k: float(flat.get(k, 0.0)) for k in stag}
            for g in (0.97, 0.94, 0.91, 0.88, 0.85, 0.82, 0.78, 0.74, 0.70):
                for k in stag:
                    flat[k] = base_stag[k] * g
                if depth() <= max_d - 0.1:
                    touched_pitch = True
                    break
            for k, sv in stag.items():
                setattr(state, sv, round(flat[k], 1))

        for k, sv in rake.items():
            setattr(state, sv, round(base_rake[k] * rf, 2))
        _depth_fit_readout()
        if touched_pitch:
            state.depth_fit_info += "  (flatten alone wasn't enough — also lowered the pitch/stagger; re-Assess.)"
        state.flush()

================================================================================
## EDIT 202  @ 2026-09-01T02:14:53

--- FIND ---
    def refresh_figure():
        sd = _thin(study_designs) if state.declutter else study_designs
        ud = _thin(list(user_designs)) if state.declutter else user_designs
        fig = scatter_figure(sd, ud)
        if hasattr(ctrl, "figure_update"):
            ctrl.figure_update(fig)

    @state.change("declutter")
    def _on_declutter(**_):
        refresh_figure()
--- REPLACE WITH ---
    _dims_cache: dict = {}

    def _design_dims(d):
        """(built tip dia, depth, hub radius) for a design — cached; model-independent geometry used
        to test whether it fits the selected fan's frame + motor. Fast (section points, no CAD)."""
        if d.trial not in _dims_cache:
            try:
                p = blade_from_flat(d.params)
                _dims_cache[d.trial] = (_blade_max_dia(p), _blade_z_extent(p), float(p.hub_radius))
            except Exception:  # noqa: BLE001
                _dims_cache[d.trial] = None
        return _dims_cache[d.trial]

    def _fits_model(d) -> bool:
        """True if the design physically fits the SELECTED fan: frame diameter + depth, and it mounts.
        This is what the oversized (larger = higher-airflow but un-buildable) designs fail."""
        dims = _design_dims(d)
        if dims is None:
            return True   # can't measure it -> don't hide it
        dia, depth, hub_r = dims
        s = active_spec()
        if dia > s.tip_dia_mm[1] + 0.3 or depth > s.depth_mm[1] + 0.3:
            return False
        need = mount_min_hub_radius(s)
        return not (need is not None and hub_r < need - 0.05)

    def refresh_figure():
        sd_all, ud_all = study_designs, list(user_designs)
        sd = [d for d in sd_all if _fits_model(d)] if state.fits_only else sd_all
        ud = [d for d in ud_all if _fits_model(d)] if state.fits_only else ud_all
        if state.fits_only:
            hidden = (len(sd_all) - len(sd)) + (len(ud_all) - len(ud))
            state.fits_msg = (f"{hidden} design(s) hidden that don't fit {active_spec().name} "
                              "(too big / won't mount)." if hidden else "All designs fit this fan.")
        else:
            state.fits_msg = ""
        if state.declutter:
            sd, ud = _thin(sd), _thin(list(ud))
        fig = scatter_figure(sd, ud)
        if hasattr(ctrl, "figure_update"):
            ctrl.figure_update(fig)

    @state.change("declutter", "fits_only")
    def _on_plot_filter(**_):
        refresh_figure()

================================================================================
## EDIT 203  @ 2026-09-01T02:14:59

--- FIND ---
    state.declutter = False   # thin near-duplicate points in the design-space plot (view only)
--- REPLACE WITH ---
    state.declutter = False   # thin near-duplicate points in the design-space plot (view only)
    state.fits_only = False   # hide designs that don't physically fit the selected fan (frame/motor)
    state.fits_msg = ""

================================================================================
## EDIT 204  @ 2026-09-01T02:15:04

--- FIND ---
    @state.change("fan_model")
    def _on_model(**_):
        _model_readout(); _hub_fit_readout(); _tip_fit_readout(); _depth_fit_readout()
        state.model_is_builtin = is_builtin(state.fan_model)
--- REPLACE WITH ---
    @state.change("fan_model")
    def _on_model(**_):
        _model_readout(); _hub_fit_readout(); _tip_fit_readout(); _depth_fit_readout()
        state.model_is_builtin = is_builtin(state.fan_model)
        if state.fits_only:      # 'fits this fan' filter is model-relative — re-filter the plot
            refresh_figure()

================================================================================
## EDIT 205  @ 2026-09-01T02:15:20

--- FIND ---
                    with v3.VCol(cols=6, classes="pr-2"):
                        v3.VSwitch(v_model=("declutter",), density="compact", hide_details=True,
                                   inset=True, color="primary", classes="ml-2",
                                   label="Declutter (hide near-duplicate designs)")
                        fig_widget = plotly_widgets.Figure(
--- REPLACE WITH ---
                    with v3.VCol(cols=6, classes="pr-2"):
                        with v3.VRow(no_gutters=True, classes="align-center"):
                            with v3.VCol(cols=6):
                                v3.VSwitch(v_model=("declutter",), density="compact", hide_details=True,
                                           inset=True, color="primary", classes="ml-2",
                                           label="Declutter (hide near-duplicates)")
                            with v3.VCol(cols=6):
                                v3.VSwitch(v_model=("fits_only",), density="compact", hide_details=True,
                                           inset=True, color="success", classes="ml-2",
                                           label="Only fits selected fan")
                        html.Div("{{ fits_msg }}", v_if="fits_msg", classes="text-caption ml-2 mb-1",
                                 style="color: var(--v-theme-success)")
                        fig_widget = plotly_widgets.Figure(

================================================================================
## EDIT 206  @ 2026-09-01T19:57:07

--- FIND ---
def scatter_figure(study_designs, user_designs=()) -> go.Figure:
--- REPLACE WITH ---
def prop_scatter_figure(pareto) -> go.Figure:
    """Propeller optimizer front: thrust vs efficiency, colored by power. customdata = the row index
    (into prop_pareto_store) so a click loads that design — the prop twin of the fan design-space plot."""
    fig = go.Figure()
    if pareto:
        fig.add_trace(go.Scatter(
            x=[r["thrust_g"] for r in pareto], y=[r["eff_g_per_w"] for r in pareto], mode="markers",
            marker=dict(size=14, color=[r["power_w"] for r in pareto], colorscale="Viridis",
                        showscale=True, colorbar=dict(title="W"),
                        line=dict(width=1, color="rgba(0,0,0,0.4)")),
            customdata=list(range(len(pareto))),
            hovertemplate="%{x:.0f} g<br>%{y:.2f} g/W<br>%{marker.color:.0f} W<extra></extra>"))
    fig.update_layout(margin=dict(l=55, r=10, t=32, b=42), xaxis_title="thrust (g)",
                      yaxis_title="efficiency (g/W)", title="Prop front — click a point to load it",
                      height=340, template="plotly_white", showlegend=False)
    return fig


def scatter_figure(study_designs, user_designs=()) -> go.Figure:

================================================================================
## EDIT 207  @ 2026-09-01T19:57:14

--- FIND ---
            state.prop_pareto = rows
            cap_txt = f" ≤{cap:.0f} W" if cap else ""
            state.prop_msg = (f"✓ {len(pareto)} designs on the thrust↔efficiency front{cap_txt}. "
                              f"Click a row to load it (top = most thrust, bottom = most efficient).")
--- REPLACE WITH ---
            state.prop_pareto = rows
            if hasattr(ctrl, "prop_fig_update"):    # push the thrust-vs-efficiency scatter
                ctrl.prop_fig_update(prop_scatter_figure(pareto))
            cap_txt = f" ≤{cap:.0f} W" if cap else ""
            state.prop_msg = (f"✓ {len(pareto)} designs on the thrust↔efficiency front{cap_txt}. "
                              f"Click a point (or row) to load it.")

================================================================================
## EDIT 208  @ 2026-09-01T19:57:29

--- FIND ---
                            with v3.VCard(classes="pa-2", v_if="prop_pareto.length"):
                                html.Div("Optimizer front — click a design to load it "
                                         "(top = most thrust, bottom = most efficient)",
                                         classes="text-subtitle-2 mb-1")
                                with v3.VList(density="compact", lines=False):
                                    with v3.VListItem(v_for="row in prop_pareto", key="row.idx",
                                                      click=(load_prop_row, "[row.idx]")):
                                        v3.VListItemTitle("{{ row.thrust }} g  ·  {{ row.eff }} g/W  "
                                                          "·  {{ row.power }} W  ·  FM {{ row.fm }}  "
                                                          "·  {{ row.nb }}-blade  {{ row.pitch }}\"")
    ctrl.view_update = view.update
    ctrl.figure_update = fig_widget.update
    ctrl.prop_view_update = prop_view.update
    return server
--- REPLACE WITH ---
                            with v3.VCard(classes="pa-2 mb-2", v_if="prop_pareto.length"):
                                prop_fig_widget = plotly_widgets.Figure(
                                    figure=prop_scatter_figure([]),
                                    click=(load_prop_row, "[$event?.points?.[0]?.customdata]"),
                                    style="width:100%;")
                            with v3.VCard(classes="pa-2", v_if="prop_pareto.length"):
                                html.Div("Optimizer front — click a point above or a row here "
                                         "(top = most thrust, bottom = most efficient)",
                                         classes="text-subtitle-2 mb-1")
                                with v3.VList(density="compact", lines=False):
                                    with v3.VListItem(v_for="row in prop_pareto", key="row.idx",
                                                      click=(load_prop_row, "[row.idx]")):
                                        v3.VListItemTitle("{{ row.thrust }} g  ·  {{ row.eff }} g/W  "
                                                          "·  {{ row.power }} W  ·  FM {{ row.fm }}  "
                                                          "·  {{ row.nb }}-blade  {{ row.pitch }}\"")
    ctrl.view_update = view.update
    ctrl.figure_update = fig_widget.update
    ctrl.prop_view_update = prop_view.update
    ctrl.prop_fig_update = prop_fig_widget.update
    return server

================================================================================
## EDIT 209  @ 2026-09-01T19:57:46

--- FIND ---
                            with v3.VCard(classes="pa-2 mb-2", v_if="prop_pareto.length"):
                                prop_fig_widget = plotly_widgets.Figure(
                                    figure=prop_scatter_figure([]),
                                    click=(load_prop_row, "[$event?.points?.[0]?.customdata]"),
                                    style="width:100%;")
--- REPLACE WITH ---
                            with v3.VCard(classes="pa-2 mb-2"):   # always mounted so prop_fig_update lands
                                prop_fig_widget = plotly_widgets.Figure(
                                    figure=prop_scatter_figure([]),
                                    click=(load_prop_row, "[$event?.points?.[0]?.customdata]"),
                                    style="width:100%;")

================================================================================
## EDIT 210  @ 2026-09-01T19:59:16

--- FIND ---
        rec = record_measurement(design_id, pt, run=run, trial=d.trial,
                                 stl_path=str(d.stl_path) if d.has_model else "",
                                 material=active_spec().material, sim=sim,
                                 instrument=state.meas_instrument, notes=state.meas_notes)
--- REPLACE WITH ---
        rec = record_measurement(design_id, pt, run=run, trial=d.trial,
                                 stl_path=str(d.stl_path) if d.has_model else "",
                                 material=(state.meas_material or active_spec().material),
                                 print_type=state.meas_print_type or "",
                                 weight_g=_mf(state.meas_weight), sim=sim,
                                 instrument=state.meas_instrument, notes=state.meas_notes)

================================================================================
## EDIT 211  @ 2026-09-01T19:59:21

--- FIND ---
    state.meas_rpm = None
    state.meas_instrument = ""
    state.meas_notes = ""
--- REPLACE WITH ---
    state.meas_rpm = None
    state.meas_material = ""       # what you actually printed it in (blank = use the fan model's material)
    state.meas_print_type = ""     # FDM / SLA-resin / SLS / …
    state.meas_weight = None       # measured printed weight (g)
    state.meas_print_types = ["FDM", "SLA / resin", "SLS", "other"]
    state.meas_instrument = ""
    state.meas_notes = ""

================================================================================
## EDIT 212  @ 2026-09-01T19:59:37

--- FIND ---
                                                v3.VTextField(label="Instrument", v_model=("meas_instrument",),
                                                              density="compact", variant="outlined",
                                                              hide_details=True, classes="mb-2")
--- REPLACE WITH ---
                                                with v3.VRow(no_gutters=True):
                                                    with v3.VCol(cols=5, classes="pr-1"):
                                                        v3.VTextField(label="Material (printed)",
                                                                      v_model=("meas_material",),
                                                                      density="compact", variant="outlined",
                                                                      hide_details=True, classes="mb-2")
                                                    with v3.VCol(cols=4, classes="px-1"):
                                                        v3.VSelect(label="Print type", v_model=("meas_print_type",),
                                                                   items=("meas_print_types",),
                                                                   density="compact", variant="outlined",
                                                                   hide_details=True, classes="mb-2")
                                                    with v3.VCol(cols=3, classes="pl-1"):
                                                        v3.VTextField(label="Weight g", v_model=("meas_weight",),
                                                                      type="number", density="compact",
                                                                      variant="outlined", hide_details=True,
                                                                      classes="mb-2")
                                                v3.VTextField(label="Instrument", v_model=("meas_instrument",),
                                                              density="compact", variant="outlined",
                                                              hide_details=True, classes="mb-2")

================================================================================
## EDIT 213  @ 2026-09-01T20:08:06

--- FIND ---
                                        v3.VSwitch(v_model=("declutter",), density="compact", hide_details=True,
                                                   inset=True, color="primary", classes="ml-2 mb-1",
                                                   label="Declutter (hide near-duplicates)")
                                        hub_all = [d for d in _hub_designs() if not d.extra.get("cfd_stale")]
                                        fig_widget = plotly_widgets.Figure(
                                            figure=scatter_figure([d for d in hub_all if d in study_designs],
                                                                  [d for d in hub_all if d in user_designs]),
                                            click=(on_plotly_click, "[$event?.points?.[0]?.customdata]"),
                                            style="width:100%;",
                                        )
                                        with v3.VCard(classes="mb-2 pa-3"):
                                            v3.VSelect(
                                                label="Design",
                                                v_model=("selected_trial",),
                                                items=("trial_items",),
                                                density="compact", variant="outlined",
                                                hide_details=True,
                                                update_modelValue=(select, "[$event]"),
                                            )
                                            html.Div(
                                                "{{ line }}",
                                                v_for="line in info_lines",
                                                classes="text-body-2 mt-2",
                                            )
--- REPLACE WITH ---
                                        v3.VSwitch(v_model=("declutter",), density="compact", hide_details=True,
                                                   inset=True, color="primary", classes="ml-2 mb-1",
                                                   label="Declutter (hide near-duplicates)")
                                        # design picker + info FIRST, then the graph in its own fixed-height
                                        # card — the plotly div doesn't reserve height on its own, so without
                                        # the card it collapses and the info card renders over the graph.
                                        with v3.VCard(classes="mb-2 pa-3"):
                                            v3.VSelect(
                                                label="Design",
                                                v_model=("selected_trial",),
                                                items=("trial_items",),
                                                density="compact", variant="outlined",
                                                hide_details=True,
                                                update_modelValue=(select, "[$event]"),
                                            )
                                            html.Div(
                                                "{{ line }}",
                                                v_for="line in info_lines",
                                                classes="text-body-2 mt-2",
                                            )
                                        hub_all = [d for d in _hub_designs() if not d.extra.get("cfd_stale")]
                                        with v3.VCard(style="height:580px;", classes="mb-2 pa-1"):
                                            fig_widget = plotly_widgets.Figure(
                                                figure=scatter_figure([d for d in hub_all if d in study_designs],
                                                                      [d for d in hub_all if d in user_designs]),
                                                click=(on_plotly_click, "[$event?.points?.[0]?.customdata]"),
                                                style="width:100%;",
                                            )

================================================================================
## EDIT 214  @ 2026-09-01T20:08:13

--- FIND ---
                            with v3.VCard(classes="pa-2 mb-2"):   # always mounted so prop_fig_update lands
                                prop_fig_widget = plotly_widgets.Figure(
                                    figure=prop_scatter_figure([]),
                                    click=(load_prop_row, "[$event?.points?.[0]?.customdata]"),
                                    style="width:100%;")
--- REPLACE WITH ---
                            with v3.VCard(style="height:360px;", classes="pa-1 mb-2"):   # reserve height so
                                # the plotly div doesn't collapse (always mounted so prop_fig_update lands)
                                prop_fig_widget = plotly_widgets.Figure(
                                    figure=prop_scatter_figure([]),
                                    click=(load_prop_row, "[$event?.points?.[0]?.customdata]"),
                                    style="width:100%;")

================================================================================
## EDIT 215  @ 2026-09-01T20:32:06

--- FIND ---
def prop_scatter_figure(pareto) -> go.Figure:
    """Propeller optimizer front: thrust vs efficiency, colored by power. customdata = the row index
    (into prop_pareto_store) so a click loads that design — the prop twin of the fan design-space plot."""
    fig = go.Figure()
    if pareto:
        fig.add_trace(go.Scatter(
            x=[r["thrust_g"] for r in pareto], y=[r["eff_g_per_w"] for r in pareto], mode="markers",
            marker=dict(size=14, color=[r["power_w"] for r in pareto], colorscale="Viridis",
                        showscale=True, colorbar=dict(title="W"),
                        line=dict(width=1, color="rgba(0,0,0,0.4)")),
            customdata=list(range(len(pareto))),
            hovertemplate="%{x:.0f} g<br>%{y:.2f} g/W<br>%{marker.color:.0f} W<extra></extra>"))
    fig.update_layout(margin=dict(l=55, r=10, t=32, b=42), xaxis_title="thrust (g)",
                      yaxis_title="efficiency (g/W)", title="Prop front — click a point to load it",
                      height=340, template="plotly_white", showlegend=False)
    return fig
--- REPLACE WITH ---
def prop_scatter_figure(pareto) -> go.Figure:
    """Propeller optimizer front: THRUST vs NOISE (the relative noise proxy), colored by efficiency —
    so you can pick a design that's punchy AND quiet. customdata = the row index (into
    prop_pareto_store) so a click loads that design. (Noise is a relative ranking score, not dB(A).)"""
    fig = go.Figure()
    if pareto and pareto[0].get("rel_dba") is not None:
        fig.add_trace(go.Scatter(
            x=[r["thrust_g"] for r in pareto], y=[r["rel_dba"] for r in pareto], mode="markers",
            marker=dict(size=14, color=[r["eff_g_per_w"] for r in pareto], colorscale="Viridis",
                        showscale=True, colorbar=dict(title="g/W"),
                        line=dict(width=1, color="rgba(0,0,0,0.4)")),
            customdata=list(range(len(pareto))),
            hovertemplate="%{x:.0f} g thrust<br>noise %{y:.0f} (rel)<br>%{marker.color:.2f} g/W<extra></extra>"))
    fig.update_layout(margin=dict(l=55, r=10, t=32, b=42), xaxis_title="thrust (g)",
                      yaxis_title="noise (relative — lower is quieter)",
                      title="Thrust vs noise — click a point (color = efficiency g/W)",
                      height=340, template="plotly_white", showlegend=False)
    return fig

================================================================================
## EDIT 216  @ 2026-09-01T20:32:14

--- FIND ---
from fansim.propeller.geometry import build_prop, prop_blade_params
from fansim.propeller.optimize import run_prop_study
--- REPLACE WITH ---
from fansim.propeller.geometry import build_prop, prop_blade_params
from fansim.propeller.noise import estimate_prop_noise
from fansim.propeller.optimize import run_prop_study

================================================================================
## EDIT 217  @ 2026-09-01T20:32:28

--- FIND ---
        fwd = bemt_analyze(params, rpm=spec.rpm_max, v_forward=15.0)
        if fwd.prop_efficiency is not None:
            lines.append(f"At 15 m/s forward: prop efficiency {100*fwd.prop_efficiency:.0f}%")
        return lines
--- REPLACE WITH ---
        nz = estimate_prop_noise(params, spec.rpm_max, perf)
        lines.append(f"🔉 Noise {nz['rel_dba']:.0f} (relative) · tip Mach {nz['tip_mach']:.2f} · "
                     f"BPF {nz['bpf_hz']:.0f} Hz  (relative rank, not calibrated dBA)")
        fwd = bemt_analyze(params, rpm=spec.rpm_max, v_forward=15.0)
        if fwd.prop_efficiency is not None:
            lines.append(f"At 15 m/s forward: prop efficiency {100*fwd.prop_efficiency:.0f}%")
        return lines

================================================================================
## EDIT 218  @ 2026-09-01T20:32:42

--- FIND ---
                rows.append({
                    "idx": i, "thrust": f"{r['thrust_g']:.0f}", "eff": f"{r['eff_g_per_w']:.2f}",
                    "power": f"{r['power_w']:.0f}", "fm": f"{r['fm']:.2f}", "nb": r["n_blades"],
                    "pitch": f"{p['pitch_in']:.1f}",
                })
--- REPLACE WITH ---
                rows.append({
                    "idx": i, "thrust": f"{r['thrust_g']:.0f}", "eff": f"{r['eff_g_per_w']:.2f}",
                    "power": f"{r['power_w']:.0f}", "fm": f"{r['fm']:.2f}", "nb": r["n_blades"],
                    "pitch": f"{p['pitch_in']:.1f}",
                    "noise": f"{r['rel_dba']:.0f}" if r.get("rel_dba") is not None else "—",
                })

================================================================================
## EDIT 219  @ 2026-09-01T20:32:48

--- FIND ---
                                        v3.VListItemTitle("{{ row.thrust }} g  ·  {{ row.eff }} g/W  "
                                                          "·  {{ row.power }} W  ·  FM {{ row.fm }}  "
                                                          "·  {{ row.nb }}-blade  {{ row.pitch }}\"")
--- REPLACE WITH ---
                                        v3.VListItemTitle("{{ row.thrust }} g  ·  {{ row.eff }} g/W  "
                                                          "·  🔉 {{ row.noise }}  ·  {{ row.power }} W  "
                                                          "·  {{ row.nb }}-blade  {{ row.pitch }}\"")

================================================================================
## EDIT 220  @ 2026-09-03T14:40:07

--- FIND ---
                                                    html.Div("0 thickness = off. First thickness step is 0.8 mm (two walls); 1.6 mm is four walls. Height 1.0 covers the full tip; below 1.0 the hoop starts at the trailing edge and BEM still treats it as an open tip. A full ring usually makes winglets worse — leave winglet at 0.",
--- REPLACE WITH ---
                                                    html.Div("0 thickness = off. First thickness step is 0.8 mm (two walls); 1.6 mm is four walls. Height 1.0 covers the full tip; below 1.0 the hoop starts at the trailing edge and BEM still treats it as an open tip. A full ring (height 1.0) disables the winglet automatically — once the tip is fully covered a winglet only adds blockage.",

================================================================================
## EDIT 221  @ 2026-09-03T15:21:40

--- FIND ---
    r = reason.lower()
    # (over-power no longer rejects -- it derates RPM; only the hard geometry limits reject)
    if "depth" in r:
--- REPLACE WITH ---
    r = reason.lower()
    # (over-power no longer rejects -- it derates RPM; only the hard geometry limits reject)
    if "tip gap" in r or "frame gap" in r:
        return ("↳ too close to the frame: a real fan needs ≥0.5 mm tip clearance, and CFD won't run "
                "without it. Click **Fit to frame** (now leaves that clearance) or lower Tip radius.")
    if "depth" in r:

================================================================================
## EDIT 222  @ 2026-09-03T15:21:47

--- FIND ---
        ok, reason = check_build(spec, dia, 2.0 * params.hub_radius, depth, weight)
        depth_msg = _depth_driver_msg(flat) if (flat and "depth" in reason.lower()) else ""
        if not ok:
            return False, f"⚠ Out of spec — Assess will reject: {reason}. {_reject_hint(reason)}{depth_msg}"
--- REPLACE WITH ---
        ok, reason = check_build(spec, dia, 2.0 * params.hub_radius, depth, weight)
        depth_msg = _depth_driver_msg(flat) if (flat and "depth" in reason.lower()) else ""
        if not ok:
            return False, f"⚠ Out of spec — Assess will reject: {reason}. {_reject_hint(reason)}{depth_msg}"
        # check_build allows the full frame; the CFD gate also needs the radial tip-gap clearance
        from fansim.cockpit.placement import frame_gap_note
        gap = frame_gap_note(dia, spec)
        if gap:
            return False, f"⚠ Out of spec — Assess will reject: {gap}. {_reject_hint(gap)}"

================================================================================
## EDIT 223  @ 2026-09-03T15:21:58

--- FIND ---
                else:
                    state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
                state.sweep_progress = 100
--- REPLACE WITH ---
                else:
                    if done == 0:
                        state.assess_msg = (
                            f"Sweep of {label} done: 0 ◆ added — every design was rejected before CFD "
                            "(not a crash). Usually the base design is out of spec or too close to the "
                            "frame: Preview shows the exact verdict, or click Fit to frame first.")
                    else:
                        state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
                state.sweep_progress = 100

