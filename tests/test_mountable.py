# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""--mountable optimizer constraint: search only hubs that can house the motor + gate the rest."""

from __future__ import annotations

import optuna

from fansim.fan_spec import get_fan_spec, mount_min_hub_radius
from fansim.geometry.blade import BladeParams
from fansim.optimize.objectives import evaluate_candidate
from fansim.optimize.search_space import suggest_params

optuna.logging.set_verbosity(optuna.logging.WARNING)


def test_mount_min_hub_radius():
    assert mount_min_hub_radius(get_fan_spec("a12x25")) == 52.0 / 2 + 1.2  # 27.2 mm
    # a model without a motor_mount returns None
    from fansim.fan_spec import FanSpec
    bare = FanSpec(name="x", tip_dia_mm=(1, 2), hub_dia_mm=(1, 2), depth_mm=(1, 2),
                   rpm=1, voltage_v=1, max_current_a=1)
    assert mount_min_hub_radius(bare) is None


def test_mountable_range_forces_big_hub():
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    lo, hi = 27.2, 30.0
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
        small = small or bp.hub_radius < 27.2
        study.tell(t, (0.0, 0.0, 0.0))
    assert small, "extended search (no --mountable) should sample hubs below the mount minimum"


def test_gate_rejects_unmountable_hub(tmp_path):
    # default hub 21.5 < 27.2 needed -> gated PRE-CFD (fast, no Docker)
    res = evaluate_candidate(BladeParams(hub_radius=21.5), tmp_path / "d", require_mountable=True)
    assert not res.feasible
    assert "not mountable" in res.reason
