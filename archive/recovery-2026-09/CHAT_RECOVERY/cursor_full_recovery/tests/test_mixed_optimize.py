"""Mixed-flow BEM Optimize (§8.6 follow-on) — no Docker / CadQuery."""

from __future__ import annotations

from pathlib import Path

from fansim.centrifugal.geometry import MixedFlowParams
from fansim.centrifugal.optimize import evaluate_mixed_bem, run_mixed_study, suggest_mixed
from fansim.centrifugal.persist import (
    latest_mixed_opt_dir,
    load_all_mixed_designs,
    load_mixed_pareto,
    mixed_opt_out_path,
    save_mixed_design_json,
    save_mixed_pareto,
)


def test_suggest_mixed_eye_lt_back():
    class _T:
        def suggest_int(self, name, lo, hi):
            return lo

        def suggest_float(self, name, lo, hi):
            return lo

    p = suggest_mixed(_T())
    assert p.r_eye_mm < p.r_back_mm
    assert isinstance(p, MixedFlowParams)


def test_evaluate_mixed_bem_returns_positive_cfm():
    q0, q_op, eta = evaluate_mixed_bem(MixedFlowParams(), rpm=2000.0, load_pa=8.0)
    assert q0 > 0
    assert 0 < q_op <= q0
    assert 0 < eta < 80


def test_run_mixed_study_persists_and_resumes(tmp_path: Path):
    out = tmp_path / "cockpit_mf_opt_t"
    study1, pareto = run_mixed_study(
        n_trials=40, seed=0, load_pa=8.0, out_dir=out, hose="case")
    assert (out / "study.db").exists()
    assert (out / "pareto.json").exists()
    assert len(pareto) >= 1
    assert pareto[0]["extra"]["source"] == "mixed_optimize"
    assert pareto[0]["extra"]["bem_adapter"] == "axial"
    n1 = len(study1.trials)
    study2, _ = run_mixed_study(
        n_trials=15, seed=1, load_pa=8.0, out_dir=out, hose="case")
    assert len(study2.trials) == n1 + 15
    loaded = load_mixed_pareto(out)
    assert len(loaded) >= 1


def test_mixed_bem_crash_is_fail_not_zero_zero(monkeypatch):
    """§9.7 — BEM exception must FAIL the trial, not invent a (0, 0) COMPLETE point."""
    import optuna

    from fansim.centrifugal import optimize as mo

    def boom(*_a, **_k):
        raise RuntimeError("bem exploded")

    monkeypatch.setattr(mo, "evaluate_mixed_bem", boom)
    study, pareto = mo.run_mixed_study(n_trials=8, seed=0, load_pa=8.0)
    assert all(t.state == optuna.trial.TrialState.FAIL for t in study.trials)
    assert pareto == []
    assert any("bem exploded" in str(t.user_attrs.get("reason", "")) for t in study.trials)


def test_mixed_opt_out_path_and_latest(tmp_path: Path):
    last = tmp_path / "cockpit_mf_opt_old"
    last.mkdir()
    (last / "study.db").write_text("", encoding="utf-8")
    new = mixed_opt_out_path(
        resume=False, last_dir=last, stamp="20260101_120000", runs_root=tmp_path)
    assert new.name.startswith("cockpit_mf_opt_")
    assert mixed_opt_out_path(resume=True, last_dir=last, runs_root=tmp_path) == last
    assert latest_mixed_opt_dir(tmp_path) == last


def test_load_all_merges_assess_and_optimize(tmp_path: Path):
    save_mixed_design_json(
        tmp_path / "cockpit_mf_a",
        trial=9000,
        params={"n_blades": 9},
        objectives={"cfm_free": 40.0, "cfm_load": 30.0, "efficiency": 20.0},
        extra={"source": "mixed_assess"},
    )
    save_mixed_pareto(
        tmp_path / "cockpit_mf_opt_b",
        [{
            "trial": 20001,
            "params": {"n_blades": 10},
            "objectives": {"cfm_free": 55.0, "cfm_load": 40.0, "efficiency": 25.0},
            "extra": {"source": "mixed_optimize", "bem_adapter": "axial"},
        }],
    )
    rows = load_all_mixed_designs(tmp_path)
    assert len(rows) == 2
    sources = {(r.get("extra") or {}).get("source") for r in rows}
    assert "mixed_assess" in sources or any(
        (r.get("extra") or {}).get("source") != "mixed_optimize" for r in rows)
    assert any((r.get("extra") or {}).get("source") == "mixed_optimize" for r in rows)


def test_mf_scatter_separates_opt_and_assess():
    from fansim.cockpit.figures import mf_scatter_figure

    designs = [
        {
            "trial": 20001,
            "objectives": {"cfm_free": 50.0, "cfm_load": 40.0, "efficiency": 22.0},
            "extra": {"source": "mixed_optimize"},
            "params": {},
        },
        {
            "trial": 9000,
            "objectives": {"cfm_free": 45.0, "cfm_load": 38.0, "efficiency": 28.0},
            "extra": {"source": "mixed_assess"},
            "params": {},
        },
    ]
    fig = mf_scatter_figure(designs)
    assert len(fig.data) == 2


def test_refine_pareto_cfd_monkeypatched(tmp_path, monkeypatch):
    from fansim.centrifugal import optimize as mo
    from fansim.optimize.objectives import ObjectiveResult

    calls = []

    def fake_eval(params, workdir, **kw):
        calls.append({"n_blades": params.n_blades, "load_pa": kw.get("load_pa")})
        return ObjectiveResult(
            feasible=True, cfm_free=42.0, cfm_load=30.0, efficiency=18.0, reason="")

    monkeypatch.setattr("fansim.centrifugal.evaluate.evaluate_mixed_flow", fake_eval)
    pareto = [{
        "params": {
            "n_blades": 9, "r_eye_mm": 16.0, "r_back_mm": 28.0, "r_tip_mm": 54.5,
            "z_span_mm": 18.0, "chord_mm": 22.0, "stagger_deg": 35.0,
        },
        "objectives": {"cfm_free": 55.0, "cfm_load": 40.0, "efficiency": 22.0},
    }]
    rows = mo.refine_pareto_cfd(pareto, tmp_path / "ref", n_top=1, load_pa=8.0)
    assert len(rows) == 1
    assert rows[0]["cfd_cfm_free"] == 42.0
    assert calls == [{"n_blades": 9, "load_pa": 8.0}]
    assert (tmp_path / "ref" / "cfd_refine.json").exists()


def test_refine_mixed_cli_declares_flags():
    text = Path("scripts/refine_mixed_pareto.py").read_text(encoding="utf-8")
    assert "--pareto-dir" in text
    assert "--n-top" in text
    assert "refine_pareto_cfd" in text
