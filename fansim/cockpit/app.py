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

_RUNNING_TESTS = "pytest" in sys.modules

if _RUNNING_TESTS:
    asynchronous = None  # type: ignore[assignment]
    get_server = None  # type: ignore[assignment]
    SinglePageLayout = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
    pv = None  # type: ignore[assignment]
else:
    import pyvista as pv
    from trame.app import asynchronous, get_server
    from trame.ui.vuetify3 import SinglePageLayout
    from trame.widgets import vuetify3 as v3

    pv.OFF_SCREEN = True


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
        except Exception:
            pass

    server.controller.on_server_ready.add(_ready)


def load_study_designs(run_dir: str | Path, study_name: str | None = None) -> list[Design]:
    """Load feasible Optuna designs for a run, or [] if missing/empty/corrupt (§11.3)."""
    try:
        return feasible_designs(load_designs(run_dir, study_name))
    except Exception:  # noqa: BLE001
        return []


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
    by_trial = {d.trial: d for d in study_designs}
    by_trial.update({d.trial: d for d in user_designs})
    next_id = [max([9000] + [d.trial + 1 for d in user_designs])]  # continue past reloaded ids

    server = get_server(client_type="vue3")
    state, ctrl = server.state, server.controller
    _quiet_connection_reset(server)

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
    from fansim.cockpit.fan_tab import render_fan_tab, setup_fan_tab
    from fansim.cockpit.mixed_tab import render_mixed_tab, setup_mixed_tab
    from fansim.cockpit.volute_tab import render_volute_tab, setup_volute_tab
    from fansim.cockpit.prop_tab import render_prop_tab, setup_prop_tab
    from fansim.cockpit.cror_tab import render_cror_tab, setup_cror_tab

    state.active_tab = "fan"
    setup_fan_tab(ctx)
    setup_mixed_tab(ctx)
    setup_volute_tab(ctx)
    setup_prop_tab(ctx)
    setup_cror_tab(ctx)

    # Defer Mixed/Volute/Prop layout (and their VTK Plotters) until first tab visit.
    _lazy_ui = {"mixed": False, "volute": False, "propeller": False}

    with SinglePageLayout(server) as layout:
        layout.title.set_text("Fan-simulator Cockpit")
        state.trame__title = "Fan-simulator Cockpit"
        with layout.content:
            with v3.VContainer(fluid=True, classes="pa-2"):
                with v3.VTabs(v_model=("active_tab",), color="primary", classes="mb-3"):
                    with v3.VTooltip(text="Fan — CFD design"):
                        with v3.Template(v_slot_activator="{ props }"):
                            v3.VTab("Fan", value="fan", v_bind="props")
                    with v3.VTooltip(text="Mixed-flow — drop-in impeller"):
                        with v3.Template(v_slot_activator="{ props }"):
                            v3.VTab("Mixed", value="mixed", v_bind="props")
                    with v3.VTooltip(text="Volute — radial blower"):
                        with v3.Template(v_slot_activator="{ props }"):
                            v3.VTab("Volute", value="volute", v_bind="props")
                    with v3.VTooltip(text="Propeller — instant BEMT design"):
                        with v3.Template(v_slot_activator="{ props }"):
                            v3.VTab("Prop", value="propeller", v_bind="props")
                    with v3.VTooltip(text="CROR — stacked rotors (BEMT proxy)"):
                        with v3.Template(v_slot_activator="{ props }"):
                            v3.VTab("CROR", value="cror", v_bind="props")

                render_fan_tab(ctx)
                render_cror_tab(ctx)  # scatter-only; no Plotter

                @state.change("active_tab")
                def _lazy_tab_ui(active_tab=None, **_):
                    tab = str(active_tab or state.active_tab or "fan")
                    if tab == "mixed" and not _lazy_ui["mixed"]:
                        render_mixed_tab(ctx)
                        _lazy_ui["mixed"] = True
                    elif tab == "volute" and not _lazy_ui["volute"]:
                        render_volute_tab(ctx)
                        _lazy_ui["volute"] = True
                    elif tab == "propeller" and not _lazy_ui["propeller"]:
                        render_prop_tab(ctx)
                        _lazy_ui["propeller"] = True

    return server
