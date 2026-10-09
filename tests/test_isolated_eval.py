from pathlib import Path

from fansim.fan_spec import get_fan_spec
from fansim.optimize.isolated_eval import eval_job_dict
from fansim.optimize._eval_worker import eval_kwargs_from_job


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


def test_eval_worker_source_passes_load_pa():
    text = Path("fansim/optimize/_eval_worker.py").read_text(encoding="utf-8")
    assert "eval_kwargs_from_job" in text
    assert "load_pa" in text


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
