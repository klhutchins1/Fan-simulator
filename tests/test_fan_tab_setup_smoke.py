"""Execution smoke for the Fan tab (§13.9 refactor net).

Unlike test_fan_tab_parse (which only ``ast.parse``s the file), this actually runs
``setup_fan_tab`` against a headless Trame server and invokes the bound handlers, so a
broken reference in a callback fails a test instead of only at cockpit runtime.

Two levels:
- sync handlers are called directly;
- async handlers (Preview/Assess/Sweep/Optimize/Export/Stock) have their ``async def task()``
  body actually driven, with the heavy I/O boundaries (``run_in_executor`` targets and
  ``subprocess.Popen``) stubbed by name. That catches name/attribute typos *inside* the
  coroutine bodies, which a plain ``coro.close()`` would skip.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# fan_tab consults this at import to stub pyvista/asynchronous; keep it truthy.
sys.modules.setdefault("pytest", sys.modules[__name__])

trame = pytest.importorskip("trame.app")


def _make_ctx(tmp_path):
    from fansim.cockpit.context import CockpitCtx

    server = trame.get_server(f"fan_tab_smoke_{tmp_path.name}")
    state, ctrl = server.state, server.controller
    # render_fan_tab registers these in the real app; handlers (refresh_figure/view_update)
    # call them after the UI exists. Register no-ops so driving handlers headless doesn't
    # raise FunctionNotImplementedError.
    ctrl.figure_update = lambda *a, **k: None
    ctrl.view_update = lambda *a, **k: None

    def _ticker(**_):
        return MagicMock(), 0.0

    return CockpitCtx(
        server=server,
        state=state,
        ctrl=ctrl,
        run_dir=tmp_path,
        runs_root=tmp_path.parent,
        plotter=MagicMock(),
        busy_bar=lambda *a, **k: None,
        busy_expr=lambda *a, **k: "",
        spawn_busy_ticker=_ticker,
        study_name=None,
        study_designs=[],
        user_designs=[],
        by_trial={},
        next_id=[9000],
        assess_dir=tmp_path / "cockpit_assess",
    )


@pytest.fixture
def bound_ctx(tmp_path, monkeypatch):
    """A ctx with setup_fan_tab run; scheduled coroutines are collected on ``ctx._tasks``."""
    import fansim.cockpit.fan_runtime as fan_runtime
    import fansim.cockpit.fan_tab as fan_tab

    tasks: list = []

    def _create_task(coro):
        tasks.append(coro)
        return MagicMock()  # code calls .cancel() on the returned handle

    monkeypatch.setattr(
        fan_runtime, "asynchronous", SimpleNamespace(create_task=_create_task), raising=False
    )
    ctx = _make_ctx(tmp_path)
    fan_tab.setup_fan_tab(ctx)  # binds + runs initial population (refresh_*, readouts)
    ctx._tasks = tasks  # type: ignore[attr-defined]
    return ctx


def test_setup_fan_tab_binds_without_error(bound_ctx):
    # Every fan_* handler the UI renderer relies on must be exposed after setup.
    for name in (
        "fan_select", "fan_on_plotly_click", "fan_load_stock_reference",
        "fan_do_preview", "fan_on_assess", "fan_export_stl_current",
        "fan_on_optimize", "fan_cancel_optimize", "fan_cancel_assess",
        "fan_on_sweep", "fan_cancel_sweep", "fan_on_fit_envelope",
        "fan_on_scale_to_hub", "fan_seed_from_duty", "fan_randomize_geometry", "fan_randomize_features",
        "fan_select_library_design", "fan_on_library_scale_to_hub",
        "fan_load_model_into_form", "fan_save_model", "fan_delete_model",
        "fan_save_measurement", "fan_show_store_calibration",
        "fan_hub_designs", "fan_active_spec",
        "fan_score_multi_point_bem",
    ):
        assert callable(getattr(bound_ctx, name, None)), name


def test_readonly_handlers_run(bound_ctx):
    """Handlers that only read/compute must resolve every name they call."""
    assert bound_ctx.fan_active_spec() is not None
    assert isinstance(bound_ctx.fan_hub_designs(), list)
    bound_ctx.fan_load_model_into_form()
    bound_ctx.fan_randomize_geometry()
    bound_ctx.fan_randomize_features()
    bound_ctx.fan_on_fit_envelope()
    bound_ctx.fan_on_scale_to_hub()
    bound_ctx.fan_seed_from_duty()
    bound_ctx.fan_select(None)
    bound_ctx.fan_on_plotly_click(None)


def test_randomize_geometry_touches_every_intended_dof(bound_ctx):
    """randomize_geometry must actually vary every editable blade DOF, not just a subset.

    Regression for the bug where section family, LE/TE thickness, span smoothing, cylindrical
    tip, tip notches, the shroud ring, hub placement and uneven spacing were never randomized.
    We drive the randomizer under a fixed seed and require each field to take >= 2 distinct
    values across the runs (continuous fields vary trivially; on/off DOFs must show both states).
    """
    import random

    state = bound_ctx.state
    # Fields that MUST vary — the core geometry knobs plus every one previously omitted.
    fields = (
        "e_n_blades", "e_stagger_mid", "e_chord_tip", "e_camber_mid", "e_lean_tip",
        "e_hub_radius", "e_tip_radius", "e_hub_profile", "e_thick_mm",
        # Previously omitted DOFs:
        "e_section_family", "e_le_thick", "e_te_thick", "e_smooth_span",
        "e_cylindrical_tip", "e_tip_notched", "e_tip_notch_depth",
        "e_shroud_thick", "e_shroud_height", "e_hub_height", "e_blade_hub_z", "e_spacing",
    )
    seen: dict[str, set] = {k: set() for k in fields}
    random.seed(20260918)
    for _ in range(60):
        bound_ctx.fan_randomize_geometry()
        for k in fields:
            seen[k].add(getattr(state, k))

    stuck = sorted(k for k, vals in seen.items() if len(vals) < 2)
    assert not stuck, f"randomize_geometry left these DOFs unchanged: {stuck}"


def test_cancel_handlers_are_safe_when_idle(bound_ctx):
    bound_ctx.fan_cancel_assess()
    bound_ctx.fan_cancel_sweep()
    bound_ctx.fan_cancel_optimize()


class _LoopProxy:
    """Wraps the real loop but returns canned results for run_in_executor (no real I/O)."""

    def __init__(self, real, canned):
        object.__setattr__(self, "_real", real)
        object.__setattr__(self, "_canned", canned)

    def __getattr__(self, k):
        return getattr(self._real, k)

    def run_in_executor(self, executor, fn, *args):
        fut = self._real.create_future()
        try:
            fut.set_result(self._canned(fn, *args))
        except Exception as exc:  # surface stub bugs as a test failure
            fut.set_exception(exc)
        return fut


def _drive(coro, canned):
    """Run one coroutine to completion with run_in_executor stubbed by fn name."""
    async def runner():
        proxy = _LoopProxy(asyncio.get_running_loop(), canned)
        saved = asyncio.get_running_loop
        asyncio.get_running_loop = lambda: proxy  # cockpit code awaits proxy.run_in_executor
        try:
            await coro
        finally:
            asyncio.get_running_loop = saved

    asyncio.run(runner())


def test_async_handler_bodies_execute(bound_ctx, monkeypatch, tmp_path):
    """Drive each async handler's task() body; catches typos inside the coroutine."""
    tasks = bound_ctx._tasks

    result = SimpleNamespace(
        feasible=True, reason="", over_spec=[],
        cfm_free=10.0, cfm_load=8.0, efficiency=40.0, actual_rpm=2000.0, raw={},
    )
    rep = SimpleNamespace(ok=True, mount_fits=None, mount_msg="")

    def canned(fn, *args):
        name = getattr(fn, "__name__", "")
        return {
            "_blocking_eval": result,
            "_do_export": (rep, None),
            "_ensure_stock_preview": tmp_path / "stock.stl",
            "poll_merge": 0,
            "get_item": None,  # ends the optimize log loop immediately
        }.get(name)  # default None (e.g. _build_preview_stl)

    class _FakeProc:
        def __init__(self, *a, **k):
            self.stdout = iter(["trial 0 ok\n", "done\n"])
            self.pid = 4321

        def poll(self):
            return 0

        def wait(self):
            return 0

        def terminate(self):
            pass

    monkeypatch.setattr(subprocess, "Popen", _FakeProc)

    for handler in (
        "fan_do_preview", "fan_on_assess", "fan_on_sweep",
        "fan_on_optimize", "fan_load_stock_reference", "fan_export_stl_current",
    ):
        getattr(bound_ctx, handler)()
        # Drain the queue: driving a body (all named ``task``) can enqueue more (the assess
        # progress ticker); pop until empty, driving task bodies and closing the rest.
        while tasks:
            coro = tasks.pop(0)
            if coro.cr_code.co_name == "task":
                _drive(coro, canned)
            else:
                coro.close()
