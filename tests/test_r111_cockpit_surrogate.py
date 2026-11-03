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


def test_cli_parser_routes_surrogate_guided_through_the_gate():
    """R1.11 CLI behaviour (grok r25 A): the real parser + guard refuse a plain --surrogate-guided."""
    from tests._cli_parsers import load_build_parser

    ap = load_build_parser("run_optimization.py")()
    plain = ap.parse_args(["--surrogate-guided"])
    assert plain.stub_labels is False and plain.verify_cfd is False
    err = surrogate_guided_cli_error(guided=plain.surrogate_guided, verify_cfd=plain.verify_cfd,
                                     stub_labels=plain.stub_labels)
    assert err and "synthetic labels, not CFD" in err
    for extra in (["--stub-labels"], ["--verify-cfd"]):
        a = ap.parse_args(["--surrogate-guided", *extra])
        assert surrogate_guided_cli_error(guided=True, verify_cfd=a.verify_cfd, stub_labels=a.stub_labels) is None


def test_cli_main_checks_the_gate_before_the_surrogate_loop():
    src = (ROOT / "scripts" / "run_optimization.py").read_text(encoding="utf-8")
    body = src[src.index("def main("):]
    assert body.index("surrogate_guided_cli_error(") < body.index("run_surrogate_guided(")


def test_run_surrogate_search_refuses_ungated_stub(tmp_path, monkeypatch, capsys):
    """QA-66: the wrapper must not silently add --stub-labels."""
    import importlib.util
    import sys

    path = ROOT / "scripts" / "run_surrogate_search.py"
    spec = importlib.util.spec_from_file_location("run_surrogate_search_qa66", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setattr(sys, "argv", ["run_surrogate_search.py", "--out", str(tmp_path / "surr")])
    spec.loader.exec_module(mod)
    rc = mod.main()
    assert rc == 2
    captured = capsys.readouterr()
    assert "synthetic labels, not CFD" in (captured.out + captured.err)

