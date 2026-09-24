"""Prop persist / reload helpers (§8.5) — no CadQuery / Docker."""

from __future__ import annotations

import logging
from pathlib import Path

from fansim.prop_spec import get_prop_spec
from fansim.propeller.optimize import run_prop_study
from fansim.propeller.persist import (
    load_all_prop_results,
    load_prop_analyze_points,
    load_prop_pareto,
    merge_prop_rows,
    prop_row_from_bemt,
    save_prop_analyze_point,
    save_prop_pareto,
)


def test_save_load_prop_pareto_roundtrip(tmp_path: Path):
    pareto = [
        {
            "thrust_g": 1200.0,
            "eff_g_per_w": 4.5,
            "power_w": 260.0,
            "fm": 0.7,
            "n_blades": 3,
            "rel_dba": 55.0,
            "tip_mach": 0.6,
            "params": {
                "n_blades": 3, "pitch_in": 4.5,
                "chord_root": 0.2, "chord_mid": 0.25, "chord_tip": 0.1, "camber": 0.04,
            },
        }
    ]
    out = tmp_path / "cockpit_prop_test"
    path = save_prop_pareto(out, pareto, prop_model="fpv_5inch")
    assert path.exists()
    loaded = load_prop_pareto(out)
    assert len(loaded) == 1
    assert loaded[0]["thrust_g"] == 1200.0
    assert loaded[0]["params"]["pitch_in"] == 4.5
    assert loaded[0]["source"] == "optimize"
    assert loaded[0]["prop_model"] == "fpv_5inch"


def test_analyze_point_save_load_and_merge(tmp_path: Path):
    assess = tmp_path / "cockpit_prop_assess"
    row = prop_row_from_bemt(
        params_flat={
            "n_blades": 2, "pitch_in": 5.0,
            "chord_root": 0.18, "chord_mid": 0.22, "chord_tip": 0.09, "camber": 0.03,
        },
        thrust_g=900.0,
        eff_g_per_w=5.1,
        power_w=176.0,
        fm=0.72,
        rel_dba=48.0,
        tip_mach=0.55,
        prop_model="fpv_5inch",
    )
    save_prop_analyze_point(assess, row, trial=9000)
    pts = load_prop_analyze_points(assess)
    assert len(pts) == 1
    assert pts[0]["source"] == "analyze"
    assert pts[0]["thrust_g"] == 900.0

    opt = [{
        "thrust_g": 1100.0, "eff_g_per_w": 4.0, "power_w": 275.0, "fm": 0.65,
        "n_blades": 3, "rel_dba": 60.0, "tip_mach": 0.6,
        "params": {"n_blades": 3, "pitch_in": 4.0},
        "source": "optimize",
    }]
    merged = merge_prop_rows(opt + pts + pts)  # duplicate analyze should collapse
    assert len(merged) == 2
    assert merged[0]["thrust_g"] >= merged[1]["thrust_g"]


def test_run_prop_study_persists_study_db_and_pareto(tmp_path: Path):
    spec = get_prop_spec("fpv_5inch")
    out = tmp_path / "cockpit_prop_opt"
    study, pareto = run_prop_study(
        spec, n_trials=40, seed=0, out_dir=out, prop_model="fpv_5inch")
    assert (out / "study.db").exists()
    assert (out / "pareto.json").exists()
    assert len(pareto) >= 1
    reloaded = load_prop_pareto(out)
    assert len(reloaded) == len(pareto)
    assert study.best_trials


def test_load_all_prop_results_scans_runs_root(tmp_path: Path):
    opt_dir = tmp_path / "cockpit_prop_aaa"
    save_prop_pareto(opt_dir, [{
        "thrust_g": 1000.0, "eff_g_per_w": 4.0, "power_w": 250.0, "fm": 0.7,
        "n_blades": 3, "rel_dba": 50.0, "params": {"n_blades": 3, "pitch_in": 4.2},
    }], prop_model="fpv_5inch")
    assess = tmp_path / "cockpit_prop_assess"
    save_prop_analyze_point(assess, prop_row_from_bemt(
        params_flat={"n_blades": 2, "pitch_in": 5.0},
        thrust_g=800.0, eff_g_per_w=5.0, power_w=160.0, fm=0.7, rel_dba=45.0,
    ), trial=9001)
    all_rows = load_all_prop_results(tmp_path)
    assert len(all_rows) == 2
    sources = {r["source"] for r in all_rows}
    assert sources == {"optimize", "analyze"}


def test_prop_scatter_figure_accepts_user_points():
    from fansim.cockpit.figures import prop_scatter_figure

    study = [{
        "thrust_g": 1000.0, "eff_g_per_w": 4.0, "rel_dba": 50.0,
        "params": {}, "source": "optimize",
    }]
    user = [{
        "thrust_g": 900.0, "eff_g_per_w": 5.0, "rel_dba": 45.0,
        "params": {}, "source": "analyze",
    }]
    fig = prop_scatter_figure(study, user)
    assert len(fig.data) == 2


def test_load_prop_pareto_logs_corrupt(tmp_path, caplog):
    """§9.9 — corrupt prop pareto.json is skipped with a warning."""
    out = tmp_path / "cockpit_prop_bad"
    out.mkdir()
    (out / "pareto.json").write_text("{not-json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="fansim.propeller.persist"):
        assert load_prop_pareto(out) == []
    assert "skip corrupt prop pareto.json" in caplog.text


def test_pareto_rows_prefer_user_attrs_over_values():
    import optuna
    from fansim.propeller.persist import pareto_rows_from_study

    study = optuna.create_study(directions=["maximize", "minimize"])

    def objective(trial):
        trial.set_user_attr("thrust_g", 900.0)
        trial.set_user_attr("eff", 3.5)
        trial.set_user_attr("power_w", 200.0)
        trial.set_user_attr("fm", 0.6)
        trial.set_user_attr("n_blades", 3)
        trial.set_user_attr("rel_dba", 70.0)
        trial.set_user_attr("tip_mach", 0.5)
        trial.set_user_attr("hover_minutes", None)
        trial.set_user_attr("range_km", None)
        trial.set_user_attr("mission", "quiet_thrust")
        trial.set_user_attr("feasible", True)
        return 900.0, 70.0

    study.optimize(objective, n_trials=1)
    rows = pareto_rows_from_study(study)
    assert rows[0]["thrust_g"] == 900.0
    assert rows[0]["eff_g_per_w"] == 3.5
    assert rows[0]["rel_dba"] == 70.0
    assert rows[0]["mission"] == "quiet_thrust"
    assert rows[0]["hover_minutes"] is None
    assert rows[0]["range_km"] is None


def test_pareto_rows_drop_infeasible_and_fall_back_when_thrust_missing():
    import optuna
    from fansim.propeller.persist import pareto_rows_from_study

    study = optuna.create_study(directions=["maximize", "maximize"])

    def objective(trial):
        if trial.number == 0:
            trial.set_user_attr("feasible", False)
            trial.set_user_attr("thrust_g", 1.0)
            trial.set_user_attr("eff", 1.0)
            return 0.0, 0.0
        return 400.0, 5.0

    study.optimize(objective, n_trials=2)
    rows = pareto_rows_from_study(study)
    assert len(rows) == 1
    assert rows[0]["thrust_g"] == 400.0
    assert rows[0]["eff_g_per_w"] == 5.0
