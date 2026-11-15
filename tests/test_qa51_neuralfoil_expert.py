"""QA-51: NeuralFoil stays off the Simple-mode polar menu until it converges."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# prop_tab stubs VTK when pytest is already imported.
sys.modules.setdefault("pytest", sys.modules[__name__])
trame = pytest.importorskip("trame.app")


def _items_for_mode(tmp_path, mode: str):
    from fansim.cockpit.context import CockpitCtx
    from fansim.cockpit.prop_tab import setup_prop_tab

    server = trame.get_server(f"qa51_polar_{mode}_{tmp_path.name}")
    server.state.ready()
    server.state.ui_mode = "simple"
    server.state.flush()
    ctx = CockpitCtx(
        server=server,
        state=server.state,
        ctrl=server.controller,
        run_dir=tmp_path,
        runs_root=tmp_path,
        plotter=MagicMock(),
        busy_bar=lambda *a, **k: None,
        busy_expr=lambda *a, **k: "",
        spawn_busy_ticker=lambda **_: (MagicMock(), 0.0),
    )
    setup_prop_tab(ctx)
    server.state.flush()
    if mode != "simple":
        server.state.ui_mode = mode
        server.state.flush()
    return list(server.state.prop_polar_backend_items)


def test_simple_mode_does_not_offer_neuralfoil(tmp_path):
    simple = _items_for_mode(tmp_path, "simple")
    assert all(item.get("value") != "neuralfoil" for item in simple)


def test_expert_neuralfoil_title_contains_experimental(tmp_path):
    expert = _items_for_mode(tmp_path, "expert")
    neuralfoil = [item for item in expert if item.get("value") == "neuralfoil"]
    assert len(neuralfoil) == 1
    assert "experimental" in neuralfoil[0]["title"]
