"""QA-37: a worker must not outlive the cockpit that started it (it kept fusing ~6 GB after the cockpit died)."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from fansim.isolated_job import parent_alive


def test_parent_alive_tells_live_from_finished_processes():
    import os

    assert parent_alive(os.getpid())
    done = subprocess.run([sys.executable, "-c", "pass"])
    assert done.returncode == 0
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    assert not parent_alive(p.pid)


def test_worker_exits_soon_after_its_parent_dies(tmp_path):
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import json, sys, time\n"
        "from fansim.isolated_job import watch_parent\n"
        "job = json.loads(open(sys.argv[1]).read())\n"
        "watch_parent(job, interval_s=0.5)\n"
        "time.sleep(60)\n"
        "open(job['done'], 'w').write('finished')\n")
    parent = tmp_path / "parent.py"
    parent.write_text(
        "import json, os, subprocess, sys\n"
        f"job = {{'parent_pid': os.getpid(), 'done': {str(tmp_path / 'done.txt')!r}}}\n"
        f"jf = {str(tmp_path / 'job.json')!r}\n"
        "open(jf, 'w').write(json.dumps(job))\n"
        f"p = subprocess.Popen([sys.executable, {str(worker)!r}, jf])\n"
        "print(p.pid, flush=True)\n")
    root = Path(__file__).resolve().parents[1]
    out = subprocess.run([sys.executable, str(parent)], capture_output=True, text=True,
                         cwd=root, env={**__import__("os").environ, "PYTHONPATH": str(root)})
    child = int(out.stdout.strip())
    t0 = time.monotonic()
    while parent_alive(child) and time.monotonic() - t0 < 15:
        time.sleep(0.2)
    assert not parent_alive(child), "worker kept running after its parent exited"
    assert not (tmp_path / "done.txt").exists()


def _stub_export(monkeypatch, tmp_path, *, crash_in_readme=False):
    import dataclasses
    from types import SimpleNamespace

    import fansim.manufacturability.print_export as pe
    from fansim.fan_spec import get_fan_spec
    from fansim.manufacturability import print_id as pid_mod

    monkeypatch.setattr(pid_mod, "INDEX_PATH", tmp_path / "index.jsonl")

    def fake_export(params, out, mount=None, **_kw):
        Path(out).write_text("solid x\nendsolid x\n")
        Path(out).with_suffix(".step").write_text("step")
        return SimpleNamespace(ok=True, mount_fits=None, mount_msg="")

    def readme(*a, **k):
        if crash_in_readme:
            raise KeyboardInterrupt  # stands in for the process dying mid-export
        return "readme"

    monkeypatch.setattr(pe, "export_print_ready", fake_export)
    monkeypatch.setattr(pe, "print_readme", readme)
    return dataclasses.replace(get_fan_spec("a12x25"), motor_mount=None)


def test_export_publishes_only_when_complete(monkeypatch, tmp_path):
    """QA-37: a worker that died after the STL left `{id}_….stl` with no README and no registry row.
    The export is staged in a hidden folder and moved into exports/ only when complete."""
    import pytest

    from fansim.cockpit.fan_export import do_export, staged_export_path
    from fansim.geometry.config import load_blade_params

    params = load_blade_params("config/problems/a12x25_reference.yaml")
    final = tmp_path / "exports" / "AB12C_stock_20261015.stl"
    final.parent.mkdir()

    spec = _stub_export(monkeypatch, tmp_path, crash_in_readme=True)
    with pytest.raises(KeyboardInterrupt):
        do_export(params, staged_export_path(final), spec, print_id="AB12C", publish_dir=final.parent)
    assert [p.name for p in final.parent.iterdir() if not p.name.startswith(".")] == []
    assert not (tmp_path / "index.jsonl").exists()

    spec = _stub_export(monkeypatch, tmp_path)
    do_export(params, staged_export_path(final), spec, print_id="AB12C", publish_dir=final.parent)
    names = sorted(p.name for p in final.parent.iterdir() if not p.name.startswith("."))
    assert final.name in names and final.with_suffix(".md").name in names
    fit = json.loads(final.with_name(final.stem + "_print_fit.json").read_text())
    assert fit["stl"] == str(final)
    row = json.loads((tmp_path / "index.jsonl").read_text().splitlines()[-1])
    assert row["stl"] == str(final)


def test_watchdog_runs_the_cleanup_hook_before_exiting(tmp_path):
    """29.4: the Assess CFD worker must stop its OpenFOAM container when the cockpit dies, so the
    watchdog runs a cleanup hook (``kill_cfd_containers`` there) before exiting."""
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import json, sys, time\n"
        "from fansim.isolated_job import watch_parent\n"
        "job = json.loads(open(sys.argv[1]).read())\n"
        "watch_parent(job, interval_s=0.5,\n"
        "             on_parent_exit=lambda: open(job['cleaned'], 'w').write('yes'))\n"
        "time.sleep(60)\n")
    parent = tmp_path / "parent.py"
    parent.write_text(
        "import json, os, subprocess, sys\n"
        f"job = {{'parent_pid': os.getpid(), 'cleaned': {str(tmp_path / 'cleaned.txt')!r}}}\n"
        f"jf = {str(tmp_path / 'job.json')!r}\n"
        "open(jf, 'w').write(json.dumps(job))\n"
        f"p = subprocess.Popen([sys.executable, {str(worker)!r}, jf])\n"
        "print(p.pid, flush=True)\n")
    root = Path(__file__).resolve().parents[1]
    import os

    out = subprocess.run([sys.executable, str(parent)], capture_output=True, text=True, cwd=root,
                         env={**os.environ, "PYTHONPATH": str(root)})
    child = int(out.stdout.strip())
    t0 = time.monotonic()
    while parent_alive(child) and time.monotonic() - t0 < 15:
        time.sleep(0.2)
    assert not parent_alive(child)
    assert (tmp_path / "cleaned.txt").read_text() == "yes"


def test_assess_cfd_job_carries_the_launcher_pid(tmp_path, monkeypatch):
    """29.4: the Assess CFD worker is started by isolated_eval via run_watched, not run_worker_module,
    so it never got a parent pid and kept solving after the cockpit died."""
    import os

    import fansim.optimize.isolated_eval as ie
    from fansim.fan_spec import get_fan_spec
    from fansim.optimize.search_space import stock_blade_flat

    seen = {}

    def fake_run_watched(cmd, **kw):
        seen.update(json.loads(Path(cmd[-1]).read_text()))
        return 1, "", "stub"

    monkeypatch.setattr(ie, "run_watched", fake_run_watched)
    try:
        ie.evaluate_candidate_isolated(stock_blade_flat(), {}, tmp_path / "case",
                                       spec=get_fan_spec("a12x25"))
    except RuntimeError:
        pass
    assert seen.get("parent_pid") == os.getpid()
