"""Headless "we say X, we do Y" checks (adopted from QA r12 Task E, roadmap 29.1 / 29.2).

No CFD, no 3-D, no real fuse: worker boundaries are stubbed by name, as in
tests/test_fan_tab_setup_smoke.py. Seeded from r12 Task D (PLA+ picker): on 143d5a8 the two material tests FAIL
by design; that is the finding, not a test bug.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.modules.setdefault("pytest", sys.modules[__name__])
trame = pytest.importorskip("trame.app")


class _T(dict):
    def __bool__(self):
        return True


@pytest.fixture
def ui(tmp_path, monkeypatch):
    import fansim.cockpit.fan_runtime as fan_runtime
    import fansim.cockpit.fan_tab as fan_tab
    from fansim.cockpit.context import CockpitCtx

    tasks: list = []
    monkeypatch.setattr(fan_runtime, "asynchronous",
                        SimpleNamespace(create_task=lambda c: tasks.append(c) or MagicMock()), raising=False)
    sessions: list = []

    class Cap(fan_tab.FanSession):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            sessions.append(self)

    monkeypatch.setattr(fan_tab, "FanSession", Cap)
    server = trame.get_server(f"qa12e_{tmp_path.name}")
    server.controller.figure_update = lambda *a, **k: None
    server.controller.view_update = lambda *a, **k: None
    ctx = CockpitCtx(server=server, state=server.state, ctrl=server.controller, run_dir=tmp_path,
                     runs_root=tmp_path.parent, plotter=MagicMock(), busy_bar=lambda *a, **k: None,
                     busy_expr=lambda *a, **k: "", spawn_busy_ticker=lambda **_: (MagicMock(), 0.0),
                     study_name=None, study_designs=[], user_designs=[], by_trial=_T(), next_id=[9000],
                     assess_dir=tmp_path / "cockpit_assess")
    fan_tab.setup_fan_tab(ctx)
    for c in tasks:
        c.close()
    tasks.clear()
    return SimpleNamespace(ctx=ctx, st=ctx.state, s=sessions[0], tasks=tasks)


def _drive(tasks):
    loop = asyncio.new_event_loop()
    try:
        while tasks:
            loop.run_until_complete(tasks.pop(0))
    finally:
        loop.close()


def _export_payload(ui, monkeypatch, tmp_path):
    """Press Export with the isolated worker stubbed; return (payload, export_msg)."""
    import fansim.cockpit.fan_export as fe
    import fansim.isolated_job as ij
    from fansim.manufacturability import print_id as pid_mod

    monkeypatch.setattr(pid_mod, "INDEX_PATH", tmp_path / "index.jsonl")
    monkeypatch.setattr(fe, "exports_dir", lambda: tmp_path / "exports")
    got: dict = {}

    def fake(mod, payload, **kw):
        got.update(payload)
        Path(payload["result"]).write_text(json.dumps({"ok": True, "mount_fits": None, "mount_msg": "",
                                                       "mirror_note": "", "gauge": None,
                                                       "print_id": payload["print_id"]}))

    monkeypatch.setattr(ij, "run_worker_module", fake)

    ui.st.cup_build_ok = True
    ui.ctx.fan_export_stl_current()
    _drive(ui.tasks)
    return got, ui.st.export_msg or ""


def test_export_material_follows_picker(ui, monkeypatch, tmp_path):
    """Kimball 2026-10-14: PLA+ picked, Export README/temps still PETG. The worker gets the spec it prints from."""
    ui.st.assess_material = "PLA+"
    payload, _ = _export_payload(ui, monkeypatch, tmp_path)
    assert payload, "export worker was not called"
    assert payload["spec"].get("material") == "PLA+", payload["spec"].get("material")


def test_preview_fit_grams_follow_picker(ui, tmp_path, monkeypatch):
    """The Preview '✓ fits … g' line must weigh the part in the picked filament.

    Checked at the weight call, not the caption: the caption rounds to whole grams and the 2.4 % PETG/PLA+ density gap
    disappears for small parts (Stock: 11.13 vs 10.87 g, both "11 g")."""
    import trimesh
    import fansim.cockpit.fan_assess as fa

    seen = []
    real = fa.estimate_weight_g
    monkeypatch.setattr(fa, "estimate_weight_g", lambda v, m: seen.append(m) or real(v, m))
    stl = tmp_path / "c.stl"
    trimesh.creation.annulus(r_min=46, r_max=52, height=14).export(str(stl))
    ui.st.assess_material = "PLA+"
    ok, msg = ui.s.spec_status(stl, ui.s.build_edit_params())
    assert msg.startswith("✓ fits"), msg
    assert seen == ["PLA+"], seen


def test_export_caption_print_id_matches_file(ui, monkeypatch, tmp_path):
    """28.2: the code we tell the user to Sharpie is the one in the file name."""
    payload, msg = _export_payload(ui, monkeypatch, tmp_path)
    from fansim.manufacturability.print_id import verify_print_id

    pid = payload["print_id"]
    assert verify_print_id(pid)
    assert Path(payload["out"]).name.startswith(pid + "_")
    assert f"`{pid}`" in msg


def test_picker_offers_only_registered_materials(ui):
    from fansim.manufacturability.materials import MATERIALS

    items = [i if isinstance(i, str) else (i.get("value") or i.get("title")) for i in ui.st.assess_material_items]
    assert "PLA+" in items and set(items) <= set(MATERIALS), items
