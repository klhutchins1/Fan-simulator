"""Regression tests for HIGH cockpit bugs (sweep camber, sweep features, wall_ks_mm, prop_model clobber)."""

from __future__ import annotations

import asyncio
import json
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from trame.app import get_server

from fansim.cfd.wall_roughness import FDM_WALL_KS_MM
from fansim.cockpit import fan_assess, run_settings
from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.data import load_designs
from fansim.cockpit.score_caption import stamp_score_extra
from fansim.cockpit.vs_stock import same_test
from fansim.fan_spec import get_fan_spec
from fansim.geometry.blade import Features
from fansim.optimize.search_space import (
    FLAT_STATION_SLOT_R,
    FLAT_STATION_SLOTS,
    FLAT_STATIONS,
    blade_from_flat,
    stock_blade_flat,
)
from fansim.prop_spec import get_prop_spec, prop_spec_names


class _SyncState:
    """Minimal state stub supporting attribute assignment, flush(), and @state.change."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self._callbacks: list[tuple[tuple[str, ...], object]] = []

    def change(self, *keys):
        def _dec(fn):
            self._callbacks.append((keys, fn))
            return fn

        return _dec

    def flush(self):
        return None


def _run_sweep_sync(tmp_path, monkeypatch, sweep_param: str, steps: int = 3):
    """Run fan_assess.on_sweep() with mocked isolated CFD and return captured (params, flats, designs)."""
    from fansim.cockpit import fan_runtime

    base_flat = stock_blade_flat("a12x25")
    base_feat = {
        "tubercle_amp": 0.0,
        "tubercle_waves": 0,
        "serration_amp": 0.0,
        "serration_waves": 0,
        "dimple_amp": 0.0,
        "dimple_rows": 0,
        "dimple_cols": 0,
    }
    state = _SyncState(
        assess_busy=False,
        assess_cancel=False,
        sweep_active=False,
        sweep_cancel=False,
        sweep_progress=0,
        sweep_param=sweep_param,
        sweep_steps=steps,
        sweep_items=[],
        assess_msg="",
        assess_preset="case",
        assess_wall_ks=False,
        assess_refine_op=False,
        assess_material="PETG",
        fan_model="a12x25",
        library_parent_id="",
        library_place_op="",
        selected_trial=None,
        opt_running=False,
    )
    user_designs: list = []
    by_trial: dict = {}
    captured: list[tuple[dict, Features]] = []

    class _FakeEvalResult:
        feasible = True
        cfm_free = 60.0
        cfm_load = 45.0
        efficiency = 0.35
        reason = ""
        over_spec: tuple[str, ...] = ()
        actual_rpm = 2000.0

        def __init__(self) -> None:
            self.raw = {"duct": "circular", "converged": True}

    def _fake_eval(flat, features, workdir, **_kw):
        captured.append((dict(flat), features))
        workdir.mkdir(parents=True, exist_ok=True)
        return _FakeEvalResult()

    monkeypatch.setattr(fan_assess, "evaluate_candidate_isolated", _fake_eval)
    monkeypatch.setattr(
        fan_assess,
        "check_printability",
        lambda _p: SimpleNamespace(printable=True, reason=""),
    )

    scheduled: list = []
    monkeypatch.setattr(
        fan_runtime,
        "asynchronous",
        SimpleNamespace(create_task=lambda coro: scheduled.append(coro)),
    )

    session = SimpleNamespace(
        state=state,
        run_dir=tmp_path,
        assess_dir=tmp_path / "cockpit_assess",
        user_designs=user_designs,
        by_trial=by_trial,
        next_id=[9000],
        designs_lock=threading.Lock(),
        assess_proc=[None],
        sel_sig=[None],
        active_spec=lambda: get_fan_spec("a12x25"),
        edit_flat=lambda: dict(base_flat),
        _feat_dict=lambda: dict(base_feat),
        _depth_driver_msg=lambda _f: "",
        refresh_items=lambda: None,
        refresh_figure=lambda: None,
    )
    fan_assess.bind(session)
    session.on_sweep()
    assert len(scheduled) == 1
    asyncio.run(scheduled[0])
    return captured, user_designs


def test_fan_sweep_camber_actually_varies_station_cambers(tmp_path, monkeypatch):
    """HIGH #1: sweeping 'camber' must vary camber_root/mid/tip, not only ignored max_camber."""
    captured, designs = _run_sweep_sync(tmp_path, monkeypatch, "camber", steps=3)
    assert len(captured) == 3
    assert len(designs) == 3

    for expected, (flat, feat) in zip((0.0, 0.03, 0.06), captured):
        assert flat["max_camber"] == pytest.approx(expected)
        assert flat["camber_root"] == pytest.approx(expected)
        assert flat["camber_mid"] == pytest.approx(expected)
        assert flat["camber_tip"] == pytest.approx(expected)
        # Verify on 3-station flat (no recipe station payload) every station takes the exact value.
        flat_3 = {
            k: v
            for k, v in flat.items()
            if k not in (FLAT_STATIONS, FLAT_STATION_SLOTS, FLAT_STATION_SLOT_R)
        }
        st3 = [s.max_camber for s in blade_from_flat(flat_3, feat).stations]
        assert st3 == pytest.approx([expected, expected, expected])

    # On 7-station Stock payload, swept station cambers must strictly increase across steps.
    mean_cambers = [
        sum(s.max_camber for s in blade_from_flat(flat, feat).stations)
        / len(blade_from_flat(flat, feat).stations)
        for flat, feat in captured
    ]
    assert mean_cambers[0] < mean_cambers[1] < mean_cambers[2]
    assert mean_cambers[2] - mean_cambers[0] == pytest.approx(0.06, abs=1e-4)


def test_fan_sweep_bio_features_persists_swept_features_in_design_json(tmp_path, monkeypatch):
    """HIGH #2: bio-feature sweep must save swept feature amps & defaulted waves into Design.params."""
    captured, designs = _run_sweep_sync(tmp_path, monkeypatch, "tubercle amp", steps=3)
    assert len(captured) == 3
    assert len(designs) == 3

    saved_amps = [d.params.get("tubercle_amp") for d in designs]
    assert saved_amps == pytest.approx([0.0, 0.05, 0.10])
    assert all(d.params.get("tubercle_waves") == 6 for d in designs)

    # Verify disk design.json matches too.
    disk = json.loads((tmp_path / "cockpit_assess" / "design_9002" / "design.json").read_text())
    assert disk["params"]["tubercle_amp"] == pytest.approx(0.10)
    assert disk["params"]["tubercle_waves"] == 6


def test_wall_ks_mm_stamped_cleared_and_respected_by_same_test():
    """HIGH #3a: stamp_score_extra / run_settings.stamp persist wall_ks_mm and clear it when off."""
    extra: dict = {}
    stamp_score_extra(extra, {"wall_ks_mm": FDM_WALL_KS_MM}, load_pa=8.0, preset="case")
    assert extra.get("wall_ks_mm") == pytest.approx(FDM_WALL_KS_MM)

    smooth_extra: dict = {}
    stamp_score_extra(smooth_extra, {}, load_pa=8.0, preset="case")
    assert "wall_ks_mm" not in smooth_extra
    assert same_test(extra, smooth_extra) is False

    # Re-assessing the same design with wall-ks turned OFF must clear stale wall_ks_mm.
    stamp_score_extra(extra, {}, load_pa=8.0, preset="case")
    assert "wall_ks_mm" not in extra
    assert same_test(extra, smooth_extra) is True

    # run_settings.stamp also preserves wall_ks even if raw omits it, and clears when False.
    rs_on = run_settings.RunSettings(
        preset="case", wall_ks=True, refine_op=False, material="PETG",
        fan_model="a12x25", spec=get_fan_spec("a12x25"),
        parent_id="", place_op="", selected_trial=None,
    )
    rs_off = run_settings.RunSettings(
        preset="case", wall_ks=False, refine_op=False, material="PETG",
        fan_model="a12x25", spec=get_fan_spec("a12x25"),
        parent_id="", place_op="", selected_trial=None,
    )
    ex2: dict = {}
    run_settings.stamp(ex2, {}, rs_on)
    assert float(ex2.get("wall_ks_mm") or 0.0) == pytest.approx(FDM_WALL_KS_MM)
    run_settings.stamp(ex2, {}, rs_off)
    assert float(ex2.get("wall_ks_mm") or 0.0) == 0.0


def test_load_designs_carries_wall_ks_mm_from_optuna_user_attrs(tmp_path):
    """HIGH #3b: Optuna trial user_attr wall_ks_mm must survive load_designs into Design.extra."""
    import optuna

    db = tmp_path / "study.db"
    study = optuna.create_study(
        study_name="ks_test",
        storage=f"sqlite:///{db.as_posix()}",
        directions=["maximize", "maximize", "maximize"],
    )
    t = study.ask()
    for k, v in stock_blade_flat("a12x25").items():
        if isinstance(v, bool):
            continue
        if isinstance(v, int):
            t.suggest_int(k, v, v)
        elif isinstance(v, float):
            t.suggest_float(k, v, v)
    t.set_user_attr("feasible", True)
    t.set_user_attr("n_blades", 9)
    t.set_user_attr("wall_ks_mm", FDM_WALL_KS_MM)
    study.tell(t, [60.0, 45.0, 0.35])

    designs = load_designs(tmp_path, "ks_test")
    assert len(designs) == 1
    assert designs[0].extra.get("wall_ks_mm") == pytest.approx(FDM_WALL_KS_MM)


def test_load_prop_row_from_other_model_preserves_saved_blade_params(tmp_path, monkeypatch):
    """HIGH #4: switching prop_model in load_prop_row must not clobber loaded blade params."""
    from fansim.cockpit import prop_tab

    models = list(prop_spec_names())
    assert len(models) >= 2
    other_model = next(m for m in models if m != "fpv_5inch")
    other_spec = get_prop_spec(other_model)

    server = get_server(f"prop_load_clobber_{tmp_path.name}")
    server.controller.prop_fig_update = lambda *a, **k: None
    server.controller.prop_view_update = lambda *a, **k: None
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
        study_name=None,
        study_designs=[],
        user_designs=[],
        by_trial={},
        next_id=[9000],
        assess_dir=tmp_path / "cockpit_assess",
    )

    monkeypatch.setattr(
        prop_tab,
        "asynchronous",
        SimpleNamespace(create_task=lambda coro: coro.close() or MagicMock()),
    )
    prop_tab.setup_prop_tab(ctx)
    ctx.state.ready()
    ctx.state.prop_model = "fpv_5inch"
    ctx.state.flush()

    custom_blades = 5 if other_spec.n_blades != 5 else 4
    custom_pitch = round(float(other_spec.pitch_in) + 1.3, 2)
    custom_chord_mid = 31.5
    ctx.prop_user_store.append(
        {
            "prop_model": other_model,
            "thrust_g": 800.0,
            "eff_g_per_w": 5.0,
            "power_w": 160.0,
            "fm": 0.65,
            "n_blades": custom_blades,
            "params": {
                "n_blades": custom_blades,
                "pitch_in": custom_pitch,
                "chord_root": 22.0,
                "chord_mid": custom_chord_mid,
                "chord_tip": 14.0,
            },
        }
    )

    ctx.load_prop_row(0)
    # Trigger a second flush to emulate reactive client sync after load.
    ctx.state.flush()

    assert ctx.state.prop_model == other_model
    assert int(ctx.state.p_n_blades) == custom_blades
    assert float(ctx.state.p_pitch) == pytest.approx(custom_pitch)
    assert float(ctx.state.p_chord_mid) == pytest.approx(custom_chord_mid)

    # Subsequent manual model switch must still reset sliders to the newly chosen model defaults.
    ctx.state.prop_model = "fpv_5inch"
    ctx.state.flush()
    fpv_spec = get_prop_spec("fpv_5inch")
    assert int(ctx.state.p_n_blades) == int(fpv_spec.n_blades)
    assert float(ctx.state.p_pitch) == pytest.approx(float(fpv_spec.pitch_in))
