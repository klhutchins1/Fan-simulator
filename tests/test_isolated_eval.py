import pytest

from fansim.fan_spec import get_fan_spec
from fansim.optimize._eval_worker import eval_kwargs_from_job
from fansim.optimize.isolated_eval import eval_job_dict


def test_eval_job_dict_stamps_load_pa():
    spec = get_fan_spec("a12x25")
    job = eval_job_dict(
        {}, {}, ".", spec, procs=2, base_cell=0.006, iters=10, out="x.json", load_pa=20.0,
    )
    assert job["load_pa"] == 20.0
    assert job["procs"] == 2


def test_eval_job_dict_defaults_load_pa_to_one():
    spec = get_fan_spec("a12x25")
    job = eval_job_dict({}, {}, ".", spec, procs=1, base_cell=0.006, iters=10, out="x.json")
    assert job["load_pa"] == 1.0


def test_eval_kwargs_from_job_pass_load_pa():
    kw = eval_kwargs_from_job({"procs": 4, "base_cell": 0.01, "iters": 50, "load_pa": 35.0})
    assert kw["load_pa"] == 35.0
    assert kw["procs"] == 4


def test_eval_kwargs_from_job_default_load_pa():
    kw = eval_kwargs_from_job({})
    assert kw["load_pa"] == 1.0


def test_eval_job_dict_stamps_refine_op():
    spec = get_fan_spec("a12x25")
    on = eval_job_dict(
        {}, {}, ".", spec, procs=1, base_cell=0.006, iters=10, out="x.json", refine_op=True,
    )
    off = eval_job_dict({}, {}, ".", spec, procs=1, base_cell=0.006, iters=10, out="x.json")
    assert on["refine_op"] is True
    assert off["refine_op"] is False


def test_eval_kwargs_from_job_pass_refine_op():
    kw = eval_kwargs_from_job({"refine_op": True})
    assert kw["refine_op"] is True
    assert eval_kwargs_from_job({})["refine_op"] is False


def test_eval_worker_forwards_load_pa_and_job_kwargs(tmp_path, monkeypatch):
    """_eval_worker.main must forward load_pa and job kwargs via eval_kwargs_from_job."""
    import json
    import sys

    from fansim.optimize import _eval_worker
    from fansim.optimize.objectives import ObjectiveResult
    from fansim.optimize.search_space import stock_blade_flat

    spec = get_fan_spec("a12x25")
    out_json = tmp_path / "res.json"
    job = eval_job_dict(
        stock_blade_flat("a12x25"), {}, tmp_path / "work", spec,
        procs=4, base_cell=0.008, iters=50, out=out_json,
        load_pa=18.5, refine_op=True, parallel_mesh=True,
    )
    job_path = tmp_path / "job.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")

    seen: dict = {}

    def fake_eval(params, workdir, *, spec, **kw):
        seen["params"] = params
        seen["workdir"] = workdir
        seen["spec"] = spec
        seen["kw"] = kw
        return ObjectiveResult(feasible=True, cfm_free=55.0, cfm_load=40.0, efficiency=30.0)

    monkeypatch.setattr(sys, "argv", ["_eval_worker", str(job_path)])
    monkeypatch.setattr("fansim.isolated_job.watch_parent", lambda *_a, **_kw: None)
    monkeypatch.setattr("fansim.optimize.objectives.evaluate_candidate", fake_eval)
    exited: list[int] = []
    monkeypatch.setattr("os._exit", lambda code: exited.append(code))

    _eval_worker.main()
    assert exited == [0]
    assert seen["kw"]["load_pa"] == pytest.approx(18.5)
    assert seen["kw"]["refine_op"] is True
    assert seen["kw"]["parallel_mesh"] is True
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["feasible"] is True
    assert payload["cfm_free"] == pytest.approx(55.0)


def test_parallel_mesh_flag_round_trips_and_defaults_off():
    spec = get_fan_spec("a12x25")
    on = eval_job_dict({}, {}, ".", spec, procs=8, base_cell=0.006, iters=10, out="x.json",
                       parallel_mesh=True)
    assert eval_kwargs_from_job(on)["parallel_mesh"] is True
    assert eval_kwargs_from_job({})["parallel_mesh"] is False


def test_surf_max_floor_round_trips_only_when_set():
    spec = get_fan_spec("a12x25")
    on = eval_job_dict({}, {}, ".", spec, procs=8, base_cell=0.006, iters=10, out="x.json",
                       surf_max_floor=4)
    assert eval_kwargs_from_job(on)["surf_max_floor"] == 4
    off = eval_job_dict({}, {}, ".", spec, procs=8, base_cell=0.006, iters=10, out="x.json")
    assert "surf_max_floor" not in eval_kwargs_from_job(off)
