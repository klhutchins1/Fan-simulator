"""Execution smoke for the Fan tab (§13.9 refactor net).

Unlike test_fan_tab_parse (which only ``ast.parse``s the file), this actually runs
``setup_fan_tab`` against a headless Trame server and invokes the bound handlers, so a
broken cross-reference in a callback fails a test instead of only at cockpit runtime.

This is the safety net for splitting ``setup_fan_tab`` into FanSession binders: the bind
path plus every synchronous handler must resolve every name it calls.
"""

from __future__ import annotations

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
    """A ctx with setup_fan_tab already run; async spawns are neutralized."""
    import fansim.cockpit.fan_runtime as fan_runtime
    import fansim.cockpit.fan_tab as fan_tab

    # Run the sync prefix of async handlers but don't schedule the coroutine
    # (no running loop in the test; the coroutine bodies need one).
    monkeypatch.setattr(
        fan_runtime,
        "asynchronous",
        SimpleNamespace(create_task=lambda coro: coro.close()),
        raising=False,
    )
    ctx = _make_ctx(tmp_path)
    fan_tab.setup_fan_tab(ctx)  # binds + runs initial population (refresh_*, readouts)
    return ctx


def test_setup_fan_tab_binds_without_error(bound_ctx):
    # Every fan_* handler the UI renderer relies on must be exposed after setup.
    for name in (
        "fan_select", "fan_on_plotly_click", "fan_load_stock_reference",
        "fan_do_preview", "fan_on_assess", "fan_export_stl_current",
        "fan_on_optimize", "fan_cancel_optimize", "fan_cancel_assess",
        "fan_on_sweep", "fan_cancel_sweep", "fan_on_fit_envelope",
        "fan_on_scale_to_hub", "fan_randomize_geometry", "fan_randomize_features",
        "fan_select_library_design", "fan_on_library_scale_to_hub",
        "fan_load_model_into_form", "fan_save_model", "fan_delete_model",
        "fan_save_measurement", "fan_hub_designs", "fan_active_spec",
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
    bound_ctx.fan_select(None)
    bound_ctx.fan_on_plotly_click(None)


def test_cancel_handlers_are_safe_when_idle(bound_ctx):
    bound_ctx.fan_cancel_assess()
    bound_ctx.fan_cancel_sweep()
    bound_ctx.fan_cancel_optimize()


def test_async_handlers_run_sync_prefix(bound_ctx):
    """Async handlers must resolve their names up to the (neutralized) task spawn."""
    bound_ctx.fan_do_preview()
    bound_ctx.fan_on_assess()
    bound_ctx.fan_on_sweep()
    bound_ctx.fan_on_optimize()
    bound_ctx.fan_load_stock_reference()
