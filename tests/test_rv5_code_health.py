"""RV-5 code health & issue #89 regression tests (failing-first before implementation edits)."""

from __future__ import annotations

import inspect
import math
import warnings
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import trimesh

from fansim.acoustics.proxies import epsilon_from_komega, proudman_power_density
from fansim.cfd import flow_report, flow_verdicts, spanwise
from fansim.cfd.flow_report import FlowMetrics
from fansim.cfd.metrics import RHO_AIR, FanMetrics, parse_fan_metrics
from fansim.geometry.features import Features
from fansim.optimize import objectives as obj_mod
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat

STOCK = FlowMetrics(
    0.06, False, [2.0, 4.0, 6.0, 8.0, 6.0], 0.20, 0.05, 0.80, 60.0, 2.5, mean_dp0_pa=6.0,
)


def _m(**kw) -> FlowMetrics:
    return FlowMetrics.from_dict(STOCK.to_dict() | kw)


def _write_pp(case: Path, fo: str, filename: str, rows: str) -> None:
    d = case / "postProcessing" / fo / "0"
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text("# header\n" + rows, encoding="utf-8")


def _minimal_cfd_case(tmp_path: Path, *, rho_inf: float | None = None) -> Path:
    case = tmp_path / "case"
    _write_pp(case, "forces", "moment.dat", "600  0 0 -0.010  0 0 -0.010  0 0 0\n")
    _write_pp(case, "forces", "force.dat", "600  0 0 0.28  0 0 0.28  0 0 0\n")
    _write_pp(case, "outletFlow", "surfaceFieldValue.dat", "600  0.025\n")
    _write_pp(case, "inletP", "surfaceFieldValue.dat", "600  -5.0\n")
    _write_pp(case, "outletP", "surfaceFieldValue.dat", "600  0.0\n")
    if rho_inf is not None:
        (case / "system").mkdir(parents=True, exist_ok=True)
        (case / "system" / "controlDict").write_text(
            f"functions\n{{\n    forces\n    {{\n        rhoInf          {rho_inf};\n    }}\n}}\n",
            encoding="utf-8",
        )
    return case


# ---------------------------------------------------------------------------
# 1. flow_verdicts.py: dead constants, _dead edge cases, overall_line edge cases
# ---------------------------------------------------------------------------


def test_flow_verdicts_dead_constants_removed():
    for dead in ("BACKFLOW_MARGIN", "SWIRL_FACTOR", "DEAD_MARGIN", "TIP_FACTOR"):
        assert not hasattr(flow_verdicts, dead), f"dead constant {dead} should be removed"
    # Kept because tests/test_flow_verdicts.py & registry still pin them.
    assert flow_verdicts.BAND_TOL == 0.06
    assert flow_verdicts.HINT_MARGIN_DB == 0.5


@pytest.mark.parametrize("stock_tip", [0.0, -0.25])
def test_dead_stock_nonpositive_tip_ratio_is_unavailable_not_close(stock_tip):
    row = flow_verdicts.judge(STOCK, _m(tip_band_uz_ratio=stock_tip))[3]
    assert row.key == "dead"
    assert row.status == "na"
    assert row.better is None
    assert "Too close to call" not in row.text
    assert "tip" in row.text.lower()


def test_dead_stock_nonpositive_tip_still_flags_worse_dead_air():
    d = _m(dead_frac=STOCK.dead_frac + flow_verdicts.CLOSE_DEAD + 0.05)
    row = flow_verdicts.judge(d, _m(tip_band_uz_ratio=0.0))[3]
    assert row.status == "warn"
    assert row.better is False
    assert "tip" in row.text.lower()


def test_dead_better_tip_with_unchanged_dead_frac_mentions_tips():
    strong_tip = STOCK.tip_band_uz_ratio * (1.0 + flow_verdicts.CLOSE_TIP_REL) + 0.1
    row = flow_verdicts.judge(_m(tip_band_uz_ratio=strong_tip), STOCK)[3]
    assert row.status == "ok"
    assert row.better is True
    assert "tip" in row.text.lower()


def test_overall_line_all_missing_na_does_not_claim_about_same():
    missing = _m(
        backflow_frac=math.nan,
        mean_dp0_pa=math.nan,
        swirl_frac=math.nan,
        dead_frac=math.nan,
        tip_band_uz_ratio=math.nan,
    )
    rows = flow_verdicts.judge(missing, STOCK)
    line = flow_verdicts.overall_line(rows, compared=True)
    assert "About the same as Stock" not in line
    assert "couldn't compare" in line.lower() or "no checks" in line.lower()


def test_overall_line_uncompared_reversed_direction_reflects_failure():
    rows = flow_verdicts.judge(_m(net_reversed=True), None)
    assert rows[0].status == "bad"
    line = flow_verdicts.overall_line(rows, compared=False)
    assert line.startswith("No Stock comparison")
    assert "only the air direction is checked" not in line
    assert "wrong way" in line.lower() or "failed" in line.lower()


# ---------------------------------------------------------------------------
# 2. spanwise.py: single-sourced slab constants from flow_report.py
# ---------------------------------------------------------------------------


def test_spanwise_uses_flow_report_slab_helpers(monkeypatch):
    assert not hasattr(spanwise, "_PLANE_Z_FRAC")
    seen: list[float] = []
    orig = flow_report.slab_half_width

    def spy(tip_r: float) -> float:
        seen.append(tip_r)
        return orig(tip_r)

    monkeypatch.setattr(flow_report, "slab_half_width", spy)
    pts = np.array([[0.03, 0.0, 0.01], [0.04, 0.0, -0.01]], dtype=float)
    u = np.array([[0.0, 0.0, 2.0], [0.0, 0.0, 2.0]], dtype=float)
    p = np.zeros(2, dtype=float)
    spanwise.compute_spanwise_profile(pts, u, p, hub_r=0.02, tip_r=0.055, omega=200.0)
    assert seen == [0.055]


# ---------------------------------------------------------------------------
# 3. metrics.py: custom rho vs rhoInf consistency warning & CROR precondition doc
# ---------------------------------------------------------------------------


def test_parse_fan_metrics_default_rho_no_warning(tmp_path):
    case = _minimal_cfd_case(tmp_path, rho_inf=RHO_AIR)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        m = parse_fan_metrics(case, omega_rad_s=200.0, rho=RHO_AIR)
    assert not caught
    assert m.static_pressure_rise_pa == pytest.approx(5.0 * RHO_AIR)


def test_parse_fan_metrics_custom_rho_mismatch_warns(tmp_path):
    case = _minimal_cfd_case(tmp_path, rho_inf=1.2)
    with pytest.warns(UserWarning, match="rhoInf"):
        m = parse_fan_metrics(case, omega_rad_s=200.0, rho=1.225)
    # Preserves existing numeric contract while alerting caller to mismatch.
    assert m.static_pressure_rise_pa == pytest.approx(5.0 * 1.225)


def test_parse_fan_metrics_custom_rho_matching_control_dict_no_warning(tmp_path):
    case = _minimal_cfd_case(tmp_path, rho_inf=1.225)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        m = parse_fan_metrics(case, omega_rad_s=200.0, rho=1.225)
    assert not caught
    assert m.static_pressure_rise_pa == pytest.approx(5.0 * 1.225)


def test_parse_fan_metrics_custom_rho_without_control_dict_warns(tmp_path):
    case = _minimal_cfd_case(tmp_path, rho_inf=None)
    with pytest.warns(UserWarning, match="rhoInf"):
        parse_fan_metrics(case, omega_rad_s=200.0, rho=1.225)


def test_parse_fan_metrics_documents_cror_equal_omega_precondition():
    doc = parse_fan_metrics.__doc__ or ""
    assert "CROR" in doc and "omega" in doc.lower()


# ---------------------------------------------------------------------------
# 4. acoustics/proxies.py: epsilon_from_komega clamps negative undershoot
# ---------------------------------------------------------------------------


def test_epsilon_from_komega_clamps_negative_omega_and_k():
    assert float(epsilon_from_komega(2.0, -10.0)) == 0.0
    assert float(epsilon_from_komega(-2.0, 10.0)) == 0.0
    arr = epsilon_from_komega(np.array([1.0, 2.0, -1.0]), np.array([-5.0, 10.0, 10.0]))
    np.testing.assert_allclose(arr, [0.0, 0.09 * 2.0 * 10.0, 0.0])
    pd = proudman_power_density(np.array([1.0, 2.0]), epsilon_from_komega([1.0, 2.0], [-5.0, 10.0]))
    assert np.all(pd >= 0.0)


# ---------------------------------------------------------------------------
# 5. objectives.py: stage helpers extracted from evaluate_candidate
# ---------------------------------------------------------------------------


def _printable_params():
    return replace(blade_from_flat(stock_blade_flat("a12x25"), Features()), tip_radius=50.0)


def test_evaluate_candidate_has_stage_helpers_and_is_concise():
    stage_names = (
        "_run_cheap_gates",
        "_run_prescreens",
        "_build_and_gate_geometry",
        "_run_cfd_solves",
        "_score_operating_result",
        "evaluate_candidate",
    )
    for name in stage_names:
        fn = getattr(obj_mod, name, None)
        assert callable(fn), f"missing stage helper {name}"
        src_lines = inspect.getsourcelines(fn)[0]
        assert len(src_lines) <= 150, f"{name} is {len(src_lines)} lines (> 150)"


def test_stage_helper_cheap_gates_and_prescreens(tmp_path, monkeypatch):
    params = _printable_params()
    gate_ctx, reject = obj_mod._run_cheap_gates(
        params,
        spec=obj_mod.A12X25,
        material="PETG",
        load_pa=5.0,
        require_mountable=False,
        tip_gap_mm=None,
        t0=0.0,
    )
    assert reject is None and gate_ctx is not None
    assert gate_ctx.remaining > 0.0

    # Impossible tip gap rejects inside cheap gates.
    gate_ctx2, reject2 = obj_mod._run_cheap_gates(
        params,
        spec=obj_mod.A12X25,
        material="PETG",
        load_pa=5.0,
        require_mountable=False,
        tip_gap_mm=1000.0,
        t0=0.0,
    )
    assert gate_ctx2 is None and reject2 is not None and not reject2.feasible
    assert "tip gap" in reject2.reason

    # Pre-screen stamps BEM error without rejecting when bem_screen_cfm crashes.
    monkeypatch.setattr(
        obj_mod,
        "bem_screen_cfm",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    pre_reject = obj_mod._run_prescreens(
        params,
        target_rpm=params.rpm,
        load_pa=5.0,
        remaining=gate_ctx.remaining,
        gap_raw=gate_ctx.gap_raw,
        exploit_guard=False,
        bem_prescreen_cfm=20.0,
        stator=False,
        surrogate_prescreen_cfm=0.0,
        surrogate=None,
        surrogate_load=None,
        t0=0.0,
    )
    assert pre_reject is None
    assert gate_ctx.gap_raw["bem_prescreen_error"] == "RuntimeError: boom"


def test_stage_helper_geometry_and_scoring(tmp_path, monkeypatch):
    params = _printable_params()
    gate_ctx, reject = obj_mod._run_cheap_gates(
        params,
        spec=obj_mod.A12X25,
        material="PETG",
        load_pa=5.0,
        require_mountable=False,
        tip_gap_mm=None,
        t0=0.0,
    )
    assert reject is None and gate_ctx is not None

    def fake_export(_shape, path):
        box = trimesh.creation.box(extents=(100.0, 100.0, 25.0))
        box.apply_translation((0.0, 0.0, 7.5))
        box.export(str(path))
        return path

    monkeypatch.setattr(obj_mod, "build_impeller", lambda _p: object())
    monkeypatch.setattr(obj_mod, "export_stl", fake_export)
    monkeypatch.setattr(
        obj_mod,
        "watertight_report",
        lambda _stl: SimpleNamespace(
            ok=True, n_bodies=1, bounds_mm=((-50.0, -50.0, -5.0), (50.0, 50.0, 20.0)),
        ),
    )

    geom_ctx, geom_reject = obj_mod._build_and_gate_geometry(
        params,
        workdir=tmp_path,
        spec=obj_mod.A12X25,
        material="PETG",
        min_sol_mid=None,
        min_sol_tip=None,
        gap_raw=gate_ctx.gap_raw,
        t0=0.0,
    )
    assert geom_reject is None and geom_ctx is not None
    assert geom_ctx.stl.is_file()

    def _fm(cfm: float, dp_pa: float) -> FanMetrics:
        return FanMetrics(
            flow_m3s=cfm / 2118.882,
            cfm=cfm,
            static_pressure_rise_pa=dp_pa,
            thrust_n=1.0,
            torque_nm=0.02,
            shaft_power_w=0.5,
            air_power_w=1.0,
            efficiency=0.25,
            p_inlet_kin=0.0,
            p_outlet_kin=dp_pa,
            converged=True,
            flow_drift_pct=0.5,
        )

    cfd_ctx = obj_mod._CfdContext(
        m_free=_fm(80.0, 2.0),
        m_load=_fm(55.0, 8.0),
        noise_swl=obj_mod.INFEASIBLE_NOISE,
        sanity_note="",
        solve_at=lambda _bp, _lbl=None: _fm(55.0, 8.0),
    )
    res = obj_mod._score_operating_result(
        params,
        spec=obj_mod.A12X25,
        target_rpm=params.rpm,
        load_pa=5.0,
        with_noise=False,
        noise_model="loading",
        refine_op=False,
        print_penalty=False,
        gate_ctx=gate_ctx,
        geom_ctx=geom_ctx,
        cfd_ctx=cfd_ctx,
        t0=0.0,
    )
    assert res.feasible is True
    assert res.cfm_free == pytest.approx(80.0)
    assert 0.0 < res.cfm_load < res.cfm_free
