"""Trame design cockpit shell: bootstrap server + plotters, then delegate per-tab setup/render.

The heavy UI and controllers live in per-tab modules (Fan / Mixed / Volute / Prop / CROR).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from fansim.cockpit.busy_ui import make_busy_bar, make_busy_expr, make_spawn_busy_ticker
from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.data import Design, feasible_designs, load_designs
from fansim.cockpit.experimental import EXPERIMENTAL_LABEL
from fansim.cockpit.trame_vtk_compat import patch_trame_vtk_protocol_defer

_RUNNING_TESTS = "pytest" in sys.modules

if _RUNNING_TESTS:
    asynchronous = None  # type: ignore[assignment]
    get_server = None  # type: ignore[assignment]
    DivLayout = None  # type: ignore[assignment]
    SinglePageLayout = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
    html = None  # type: ignore[assignment]
    pv = None  # type: ignore[assignment]
else:
    import pyvista as pv
    from trame.app import asynchronous, get_server
    from trame.ui.html import DivLayout
    from trame.ui.vuetify3 import SinglePageLayout
    from trame.widgets import html
    from trame.widgets import vuetify3 as v3

    pv.OFF_SCREEN = True
    patch_trame_vtk_protocol_defer()


def _quiet_connection_reset(server) -> None:
    """Silence benign Windows proactor ConnectionResetError spam on client disconnect."""

    def _ready(**_):
        try:
            loop = asyncio.get_running_loop()

            def handler(loop, context):
                if isinstance(context.get("exception"), ConnectionResetError):
                    return
                loop.default_exception_handler(context)

            loop.set_exception_handler(handler)
        except Exception as exc:  # noqa: BLE001 - optional loop hook
            import logging

            logging.getLogger(__name__).debug(
                "skip asyncio exception handler install: %s: %s", type(exc).__name__, exc
            )

    server.controller.on_server_ready.add(_ready)


def load_study_designs(run_dir: str | Path, study_name: str | None = None) -> list[Design]:
    """Load feasible Optuna designs for a run, or [] if missing/empty/corrupt (§11.3)."""
    try:
        return feasible_designs(load_designs(run_dir, study_name))
    except Exception:  # noqa: BLE001
        return []


EXPORTS_URL_PREFIX = "fansim_exports"


def build_server(run_dir: str | Path, study_name: str | None = None):
    """Create the cockpit Trame server for the given run folder."""
    run_dir = Path(run_dir)

    # Fan session data (shell responsibility). Empty Optuna / missing study is OK (§11.3):
    # Design-from-scratch and Assess still work; Results just starts empty.
    study_designs = load_study_designs(run_dir, study_name)
    assess_dir = run_dir / "cockpit_assess"  # new assessments this session land here
    runs_root = run_dir.parent
    all_assess_dirs = sorted(runs_root.glob("*/cockpit_assess")) if runs_root.exists() else []
    if assess_dir not in all_assess_dirs:
        all_assess_dirs.append(assess_dir)
    from fansim.cockpit.fan_helpers import _load_assessed_designs

    user_designs = _load_assessed_designs(all_assess_dirs)
    next_id = [max([9000] + [d.trial + 1 for d in user_designs])]  # continue past reloaded ids
    # Saved cockpit Optimize runs come back after a restart (own id block per run, ≥ 20000).
    from fansim.cockpit.data import load_saved_opt_designs

    user_designs += load_saved_opt_designs(runs_root, exclude=run_dir, existing_keys=set())
    by_trial = {d.trial: d for d in study_designs}
    by_trial.update({d.trial: d for d in user_designs})

    server = get_server(client_type="vue3")
    state, ctrl = server.state, server.controller
    _quiet_connection_reset(server)
    from fansim.cockpit.ws_guard import install as _guard_websockets

    _guard_websockets()  # one frozen tab must not freeze every session (QA UI-16)
    # Serve exports/ so Export can offer a browser download, not only a server-side path (§23.19).
    from fansim.cockpit.fan_copy import _CTRL_IMG_DIR, CONTROL_IMAGES_URL_PREFIX
    from fansim.cockpit.paths import exports_dir

    _exports = exports_dir()
    _exports.mkdir(parents=True, exist_ok=True)
    _serve_dirs = {EXPORTS_URL_PREFIX: str(_exports)}
    if _CTRL_IMG_DIR.is_dir():
        _serve_dirs[CONTROL_IMAGES_URL_PREFIX] = str(_CTRL_IMG_DIR)
    server.enable_module({"serve": _serve_dirs})

    # Fan plotter only at startup; Mixed/Volute/Prop construct on first visit (§12.3).
    from fansim.cockpit.plotters import make_white_plotter

    plotter = make_white_plotter()

    # Busy helpers (shared).
    busy_expr = make_busy_expr()
    busy_bar = make_busy_bar(v3, busy_expr)
    spawn_busy_ticker = make_spawn_busy_ticker(state, asynchronous)

    ctx = CockpitCtx(
        server=server,
        state=state,
        ctrl=ctrl,
        run_dir=run_dir,
        runs_root=runs_root,
        plotter=plotter,
        prop_plotter=None,
        mf_plotter=None,
        volute_plotter=None,
        busy_bar=busy_bar,
        busy_expr=busy_expr,
        spawn_busy_ticker=spawn_busy_ticker,
        # Fan session fields
        study_name=study_name,
        study_designs=study_designs,
        user_designs=user_designs,
        by_trial=by_trial,
        next_id=next_id,
        assess_dir=assess_dir,
    )

    # Tab setup (lazy imports: keep tests/light imports happy).
    from fansim.cockpit.cror_tab import render_cror_tab, setup_cror_tab
    from fansim.cockpit.fan_core import tab_for_ui_mode
    from fansim.cockpit.fan_tab import render_fan_tab, setup_fan_tab
    from fansim.cockpit.home_tab import HOME_TAB, render_home_tab, setup_home_tab
    from fansim.cockpit.mixed_tab import render_mixed_tab, setup_mixed_tab
    from fansim.cockpit.prop_tab import render_prop_tab, setup_prop_tab
    from fansim.cockpit.volute_tab import render_volute_tab, setup_volute_tab

    state.active_tab = HOME_TAB
    setup_fan_tab(ctx)
    setup_mixed_tab(ctx)
    setup_volute_tab(ctx)
    setup_prop_tab(ctx)
    setup_cror_tab(ctx)
    setup_home_tab(ctx)

    # Defer Mixed/Volute/Prop/CROR layout (and their VTK Plotters) until first tab visit.
    # Fan stays eager so trame-vtk / trame-plotly modules and ctrl.view_update / figure_update
    # register before server.start() fires state.ready().
    _lazy_ui = {"mixed": False, "volute": False, "propeller": False, "cror": False}

    with SinglePageLayout(server) as layout:
        layout.title.set_text("Fan Simulator — printable blade designer")
        try:
            layout.footer.clear()  # drop default "Powered by trame" / Kitware footer
        except Exception:  # noqa: BLE001, S110 — older trame layouts may omit footer
            pass
        with layout.toolbar:
            from trame.widgets import client as _client

            v3.VSpacer()
            with v3.VBtnToggle(v_model=("ui_mode",), mandatory=True, density="compact",
                               variant="outlined", color="primary", classes="mr-2"):
                v3.VBtn("Simple", value="simple", size="small")
                v3.VBtn("Expert", value="expert", size="small")
            # Remember the choice per browser (localStorage key fansim.ui_mode, §24).
            _client.ClientTriggers(mounted=(
                "try { const s = window.localStorage.getItem('fansim.ui_mode');"
                " if (s === 'simple' || s === 'expert') { ui_mode = s; } } catch (e) {}"))
            _client.ClientStateChange(value="ui_mode", change=(
                "try { window.localStorage.setItem('fansim.ui_mode', ui_mode); } catch (e) {}"))
        state.trame__title = "Fan Simulator"
        with layout.content:
            with v3.VContainer(fluid=True, classes="pa-2") as _tabs_box:
                with v3.VTabs(v_model=("active_tab",), color="primary", classes="mb-3"):
                    with v3.VTooltip(
                        location="bottom",
                        open_delay=400,
                        text="Start page — pick a fan, a propeller, saved designs, or accuracy info",
                    ):
                        with v3.Template(v_slot_activator="{ props }"):
                            v3.VTab("Home", value=HOME_TAB, v_bind="props")
                    with v3.VTooltip(
                        location="bottom",  # beside the tab it covered the next tab name (§23.27)
                        open_delay=400,
                        text="Fan — CFD-checked axial PC-fan blades (printable STL)",
                    ):
                        with v3.Template(v_slot_activator="{ props }"):
                            v3.VTab("Fan · blades", value="fan", v_bind="props")
                    with v3.VTooltip(
                        location="bottom",  # beside the tab it covered the next tab name (§23.27)
                        open_delay=400,
                        text=EXPERIMENTAL_LABEL,
                    ):
                        with v3.Template(v_slot_activator="{ props }"):
                            v3.VTab(
                                "Mixed · experimental",
                                value="mixed",
                                v_bind="props",
                                v_show="ui_mode === 'expert'",
                            )
                    with v3.VTooltip(
                        location="bottom",  # beside the tab it covered the next tab name (§23.27)
                        open_delay=400,
                        text=EXPERIMENTAL_LABEL,
                    ):
                        with v3.Template(v_slot_activator="{ props }"):
                            v3.VTab(
                                "Volute · experimental",
                                value="volute",
                                v_bind="props",
                                v_show="ui_mode === 'expert'",
                            )
                    with v3.VTooltip(
                        location="bottom",  # beside the tab it covered the next tab name (§23.27)
                        open_delay=400,
                        text=f"Propeller — BEMT fast estimate (~1 s). Optional CFD check is "
                        f"{EXPERIMENTAL_LABEL[0].lower() + EXPERIMENTAL_LABEL[1:]}",
                    ):
                        with v3.Template(v_slot_activator="{ props }"):
                            v3.VTab("Prop · fast estimate", value="propeller", v_bind="props")
                    with v3.VTooltip(
                        location="bottom",  # beside the tab it covered the next tab name (§23.27)
                        open_delay=400,
                        text=EXPERIMENTAL_LABEL,
                    ):
                        with v3.Template(v_slot_activator="{ props }"):
                            v3.VTab(
                                "CROR · experimental",
                                value="cror",
                                v_bind="props",
                                v_show="ui_mode === 'expert'",
                            )

                html.Div(
                    "Fan: printable PC-fan blades (airflow check). Prop: propeller (fast estimate).",
                    classes="text-caption text-medium-emphasis mb-2",
                    v_show="ui_mode === 'simple' && active_tab !== 'home'",
                )
                html.Div(
                    "3D-printable PC-fan blade designer — CFD on Fan; other tabs are faster "
                    "estimates (see tab labels).",
                    classes="text-caption text-medium-emphasis mb-2",
                    v_show="ui_mode === 'expert' && active_tab !== 'home'",
                )
                render_home_tab(ctx)
                render_fan_tab(ctx)
                # Isolated ServerTemplate slots for lazy archetype tabs so first-visit
                # rendering never re-flushes the root layout or tears down mounted VTK views.
                for _lazy_tab in ("mixed", "volute", "propeller", "cror"):
                    _client.ServerTemplate(name=f"tab_{_lazy_tab}")
                # Switching from Home to Fan unhides the VTK canvas (display:none -> visible);
                # nudge resize so vtkRemoteView re-measures and renders the Stock impeller.
                _client.ClientStateChange(
                    value="active_tab",
                    change=(
                        "try { window.setTimeout(function() { "
                        "window.dispatchEvent(new window.Event('resize')); }, 80); } catch (e) {}"
                    ),
                )

                @state.change("ui_mode")
                def _simple_leaves_proxy(ui_mode=None, **_):
                    nxt = tab_for_ui_mode(str(ui_mode or state.ui_mode or "simple"),
                                          str(state.active_tab or "fan"))
                    if nxt != state.active_tab:
                        state.active_tab = nxt

                @state.change("active_tab")
                def _lazy_tab_ui(active_tab=None, **_):
                    tab = str(active_tab or state.active_tab or "home")
                    if tab == "fan":
                        if hasattr(ctrl, "view_update"):
                            try:
                                ctrl.view_update()
                            except Exception:  # noqa: BLE001, S110
                                pass
                        return
                    lazy = {
                        "mixed": render_mixed_tab,
                        "volute": render_volute_tab,
                        "propeller": render_prop_tab,
                        "cror": render_cror_tab,
                    }
                    render = lazy.get(tab)
                    if render is None or _lazy_ui.get(tab):
                        return
                    # Render into this tab's isolated ServerTemplate so the main layout
                    # (and any already-mounted VTK views in Fan/Prop/etc.) stays untouched.
                    with DivLayout(server, template_name=f"tab_{tab}") as tab_layout:
                        render(ctx)
                    _lazy_ui[tab] = True
                    tab_layout.flush_content()

    return server
