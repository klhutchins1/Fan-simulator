"""--mountable optimizer constraint: search only hubs that can house the motor + gate the rest."""

from __future__ import annotations

import optuna

from fansim.fan_spec import get_fan_spec, mount_min_hub_radius
from fansim.geometry.blade import BladeParams
from fansim.optimize.objectives import evaluate_candidate
from fansim.optimize.search_space import suggest_params

optuna.logging.set_verbosity(optuna.logging.WARNING)

A12_MIN_HUB = 37.25 / 2.0 + 1.2  # 19.825 mm — measured cup 2026-08-31


def test_mount_min_hub_radius():
    assert mount_min_hub_radius(get_fan_spec("a12x25")) == A12_MIN_HUB
    from fansim.fan_spec import FanSpec
    bare = FanSpec(name="x", tip_dia_mm=(1, 2), hub_dia_mm=(1, 2), depth_mm=(1, 2),
                   rpm=1, voltage_v=1, max_current_a=1)
    assert mount_min_hub_radius(bare) is None


def test_mountable_range_forces_big_hub():
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    lo, hi = A12_MIN_HUB, 24.0
    for _ in range(15):
        t = study.ask()
        bp = suggest_params(t, hub_radius_range=(lo, hi))
        assert lo <= bp.hub_radius <= hi, f"hub {bp.hub_radius} outside mountable range"
        study.tell(t, (0.0, 0.0, 0.0))


def test_extended_without_mountable_can_go_small():
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    small = False
    for _ in range(20):
        t = study.ask()
        bp = suggest_params(t, with_extended=True)   # EXTENDED hub is (17, 28)
        small = small or bp.hub_radius < A12_MIN_HUB
        study.tell(t, (0.0, 0.0, 0.0))
    assert small, "extended search (no --mountable) should sample hubs below the mount minimum"


def test_gate_rejects_unmountable_hub(tmp_path):
    # 16.5 mm is below the measured 19.825 mm cup + wall
    res = evaluate_candidate(BladeParams(hub_radius=16.5), tmp_path / "d", require_mountable=True)
    assert not res.feasible
    assert "not mountable" in res.reason


def test_gate_accepts_measured_min_hub(tmp_path):
    res = evaluate_candidate(BladeParams(hub_radius=21.5), tmp_path / "d", require_mountable=True)
    # 21.5 >= 19.825 — must NOT be rejected on mount (may still fail later gates / CFD)
    assert "not mountable" not in (res.reason or "")
