"""CROR thin envelope + NSGA proxy."""

from __future__ import annotations

from fansim.cror.geometry import CrorParams
from fansim.cror.optimize import cror_stack_depth_mm, run_cror_study, thin_cror_for_frame


def test_default_cror_deeper_than_25mm():
    assert cror_stack_depth_mm(CrorParams()) > 25.0


def test_thin_cror_fits_25mm():
    thin = thin_cror_for_frame(CrorParams(), max_depth_mm=25.0)
    assert cror_stack_depth_mm(thin) <= 25.0 + 1e-6


def test_cror_nsga_smoke():
    study, pareto = run_cror_study(12, rpm=2000.0, max_depth_mm=25.0, seed=1)
    assert len(study.trials) == 12
    assert isinstance(pareto, list)


def test_cror_depth_overflow_is_pruned_not_origin(monkeypatch):
    """§11.5 — depth gate must not invent a (0, 0) NSGA point."""
    import optuna

    from fansim.cror import optimize as opt

    monkeypatch.setattr(opt, "thin_cror_for_frame", lambda p, **k: p)
    monkeypatch.setattr(
        opt,
        "_proxy_perf",
        lambda params, rpm: {
            "thrust_g": 50.0,
            "power_w": 5.0,
            "eff_g_per_w": 10.0,
            "depth_mm": 99.0,
            "rel_dba": 40.0,
        },
    )
    study, pareto = run_cror_study(6, rpm=2000.0, max_depth_mm=25.0, seed=0)
    assert pareto == []
    assert all(t.state == optuna.trial.TrialState.PRUNED for t in study.trials)
    assert all(t.user_attrs.get("feasible") is False for t in study.trials)
