"""R1.11 / UI-31: cockpit Optimize must not rank designs with synthetic_label."""
from pathlib import Path
from types import SimpleNamespace

from fansim.cockpit.fan_optimize import cockpit_optimization_argv
from fansim.optimize.cli_argv import surrogate_guided_cli_error

ROOT = Path(__file__).resolve().parents[1]


def test_cockpit_optimize_does_not_wire_surrogate_guided_state():
    src = (ROOT / "fansim" / "cockpit" / "fan_optimize.py").read_text(encoding="utf-8")
    assert "surrogate_guided=bool(state.opt_surrogate_guided)" not in src
    assert "surrogate_guided=False" in src


def test_surrogate_guided_switch_is_hidden_from_the_cockpit():
    ui = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    assert "opt_surrogate_guided" not in ui
    assert "Surrogate-guided" not in ui


def test_cockpit_argv_omits_surrogate_guided_even_if_state_on():
    state = SimpleNamespace(
        fan_model="a12x25",
        assess_preset="case",
        assess_refine_op=False,
        opt_shroud=False,
        opt_bem=False,
        opt_gp=False,
        opt_gp_boost=False,
        opt_gp_nn=False,
        opt_surrogate_guided=True,
        opt_stator=False,
        opt_stator_stack=False,
        opt_sickle=False,
        opt_stepped=False,
        opt_notched=False,
        assess_wall_ks=False,
        assess_material="PETG",
    )
    argv = cockpit_optimization_argv(
        state,
        trials=8,
        out="runs/x",
        resume_study=None,
        search_rpm=False,
        rpm_min=None,
        rpm_max=None,
    )
    assert "--surrogate-guided" not in argv
    assert "--verify-cfd" not in argv


def test_cli_refuses_surrogate_guided_stub_without_a_gate():
    assert surrogate_guided_cli_error(guided=True, verify_cfd=False, stub_labels=False)
    err = surrogate_guided_cli_error(guided=True, verify_cfd=False, stub_labels=False)
    assert "synthetic labels, not CFD" in err
    assert surrogate_guided_cli_error(guided=True, verify_cfd=True, stub_labels=False) is None
    assert surrogate_guided_cli_error(guided=True, verify_cfd=False, stub_labels=True) is None
    assert surrogate_guided_cli_error(guided=False, verify_cfd=False, stub_labels=False) is None


def test_dead_surrogate_guided_tooltip_is_gone():
    copy = (ROOT / "fansim" / "cockpit" / "fan_copy.py").read_text(encoding="utf-8")
    assert "opt_surrogate_guided" not in copy
    assert "Surrogate-guided" not in copy

