"""Cockpit Optimize runs on the Results plot: per-run ids, labels, reload, legend, best ring."""

from __future__ import annotations

from pathlib import Path

import optuna

from fansim.cockpit.data import load_saved_opt_designs
from fansim.cockpit.figures import design_group, pareto_front, scatter_figure
from fansim.optimize.cli_argv import (
    OPT_RUN_STRIDE,
    OPT_TRIAL_OFFSET,
    latest_opt_run,
    opt_trial_offset,
    run_label,
)
from fansim.optimize.design import Design


def _d(trial, free, load, eff, **extra):
    return Design(trial=trial, params={}, feasible=True, is_pareto=False, stl_path=None,
                  objectives={"cfm_free": free, "cfm_load": load, "efficiency": eff},
                  extra=dict(extra))


def _make_study(run: Path, values: list[tuple[float, float, float]]) -> None:
    run.mkdir(parents=True)
    study = optuna.create_study(study_name="fansim", directions=["maximize"] * 3,
                                storage=f"sqlite:///{(run / 'study.db').as_posix()}")
    for v in values:
        t = study.ask()
        t.suggest_float("chord_tip", 20.0, 40.0)
        t.set_user_attr("feasible", True)
        t.set_user_attr("cfd_version", 5)
        study.tell(t, list(v))


def test_run_label_parses_stamp():
    assert run_label("cockpit_opt_20261001-100133") == "Opt 2026-10-01 10:01"
    assert run_label("opt_run1") == "opt_run1"


def test_offsets_are_per_run_and_stable(tmp_path):
    for name in ("cockpit_opt_20261001-100133", "cockpit_opt_20261002-090000"):
        (tmp_path / name).mkdir()
    a = opt_trial_offset("cockpit_opt_20261001-100133", tmp_path)
    b = opt_trial_offset("cockpit_opt_20261002-090000", tmp_path)
    assert (a, b) == (OPT_TRIAL_OFFSET, OPT_TRIAL_OFFSET + OPT_RUN_STRIDE)
    # a run that does not exist yet (about to start) is newest, so older offsets do not move
    c = opt_trial_offset("cockpit_opt_20261003-080000", tmp_path)
    assert c == OPT_TRIAL_OFFSET + 2 * OPT_RUN_STRIDE
    assert opt_trial_offset("cockpit_opt_20261001-100133", tmp_path) == a


def test_latest_opt_run_needs_a_study(tmp_path):
    assert latest_opt_run(tmp_path) is None
    _make_study(tmp_path / "cockpit_opt_20261001-100133", [(40.0, 30.0, 10.0)])
    (tmp_path / "cockpit_opt_20261002-090000").mkdir()  # started, no study yet
    assert latest_opt_run(tmp_path).name == "cockpit_opt_20261001-100133"


def test_saved_runs_reload_without_collisions(tmp_path):
    _make_study(tmp_path / "cockpit_opt_20261001-100133", [(40.0, 30.0, 10.0), (45.0, 35.0, 15.0)])
    _make_study(tmp_path / "cockpit_opt_20261002-090000", [(41.0, 31.0, 11.0)])
    opened = tmp_path / "opt_run1"
    keys: set = set()
    ds = load_saved_opt_designs(tmp_path, exclude=opened, existing_keys=keys)
    ids = [d.trial for d in ds]
    assert len(ids) == len(set(ids)) == 3
    assert {OPT_TRIAL_OFFSET, OPT_TRIAL_OFFSET + 1, OPT_TRIAL_OFFSET + OPT_RUN_STRIDE} == set(ids)
    assert all(d.extra["source"] == "cockpit_opt" and d.extra["completed"] for d in ds)
    assert len(keys) == 3
    # already-merged keys are not re-added (live Optimize polling)
    assert load_saved_opt_designs(tmp_path, exclude=opened, existing_keys=keys) == []


def test_opened_run_is_excluded(tmp_path):
    run = tmp_path / "cockpit_opt_20261001-100133"
    _make_study(run, [(40.0, 30.0, 10.0)])
    assert load_saved_opt_designs(tmp_path, exclude=run, existing_keys=set()) == []


def test_pareto_front_all_three_objectives():
    a = _d(1, 50, 40, 20)
    b = _d(2, 45, 35, 15)   # beaten by a on everything
    c = _d(3, 40, 30, 30)   # best efficiency, so not beaten
    assert pareto_front([a, b, c]) == {id(a), id(c)}


def test_groups():
    assert design_group(_d(3, 1, 1, 1), "opt_run1")[0] == "study"
    assert design_group(_d(9003, 1, 1, 1), "opt_run1") == ("assessed", "Assessed by you")
    key, label = design_group(
        _d(20004, 1, 1, 1, source="cockpit_opt", source_run="cockpit_opt_20261001-100133"))
    assert key == "opt:cockpit_opt_20261001-100133" and label == "Opt 2026-10-01 10:01"


def test_scatter_one_legend_entry_per_run_and_best_ring():
    study = [_d(1, 40, 30, 10)]
    users = [
        _d(9001, 42, 31, 12),
        _d(20000, 48, 37, 18, source="cockpit_opt", source_run="cockpit_opt_20261001-100133",
           completed="2026-10-01 12:00"),
        _d(21000, 44, 33, 14, source="cockpit_opt", source_run="cockpit_opt_20261002-090000"),
    ]
    fig = scatter_figure(study, users, opened_run="opt_run1")
    names = [t.name for t in fig.data]
    assert fig.layout.showlegend
    assert "Assessed by you" in names
    assert "Opt 2026-10-01 10:01" in names and "Opt 2026-10-02 09:00" in names
    ring = next(t for t in fig.data if t.name.startswith("Best overall"))
    assert list(ring.customdata) == [20000]  # clicking the ring still selects the design
    symbols = {t.name: t.marker.symbol for t in fig.data if t.name.startswith("Opt ")}
    assert len({str(s) for s in symbols.values()}) == 2  # distinct shape per run
    run_trace = next(t for t in fig.data if t.name == "Opt 2026-10-01 10:01")
    assert run_trace.text[0] == "Opt 2026-10-01 10:01 · done 12:00"  # same day: time only
    # only one colorbar
    assert sum(1 for t in fig.data if getattr(t.marker, "showscale", False)) == 1


def test_provenance_keeps_date_across_days_and_names_assess_run():
    from fansim.cockpit.figures import design_provenance

    d = _d(20001, 1, 1, 1, source="cockpit_opt", source_run="cockpit_opt_20261001-100133",
           completed="2026-10-02 01:15")
    assert design_provenance(d) == "Opt 2026-10-01 10:01 · 2026-10-02 01:15"
    a = _d(9005, 1, 1, 1, source_run="opt_run1", completed="2026-09-30 20:27")
    assert design_provenance(a, "opt_run1") == "Assessed under opt_run1 · 2026-09-30 20:27"
