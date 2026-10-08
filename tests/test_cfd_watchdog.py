"""Live OpenFOAM logs, the no-progress watchdog, and free-air salvage (2026-10-07 timeouts)."""

import json
import os
import sys
import time

import pytest

from fansim.cfd import runner as runner_mod
from fansim.cfd.runner import OpenFOAMRunner, log_name
from fansim.cockpit.busy import cfd_stage_hint
from fansim.isolated_job import latest_activity, run_watched, stall_timeout, watch_process
from fansim.optimize.isolated_eval import partial_free_note
from fansim.optimize.objectives import PARTIAL_FREE_FILE


@pytest.mark.parametrize("cmd,name", [
    ("snappyHexMesh -overwrite", "snappyHexMesh"),
    ("mpirun --allow-run-as-root --oversubscribe -np 8 simpleFoam -parallel", "simpleFoam"),
    ("mpirun --allow-run-as-root --oversubscribe -np 8 potentialFoam -parallel -initialiseUBCs",
     "potentialFoam"),
    ("mpirun --bind-to none -np 4 snappyHexMesh -parallel", "snappyHexMesh"),
    ("rm -rf processor* postProcessing", "rm"),
])
def test_log_name_names_the_app_not_mpirun(cmd, name):
    assert log_name(cmd) == name


def test_runner_streams_stdout_to_log_and_appends_stderr(tmp_path, monkeypatch):
    seen = {}

    def fake_run(args, stdout, stderr, text):
        stdout.write("Time = 1\nTime = 2\n")
        stdout.flush()
        # The log is already on disk while the command is still "running".
        seen["live"] = (tmp_path / "logs" / "simpleFoam.log").read_text()
        stderr.write("warn\n")
        return type("P", (), {"returncode": 0})()

    monkeypatch.setattr(runner_mod.subprocess, "run", fake_run)
    res = OpenFOAMRunner(tmp_path).run("mpirun -np 8 simpleFoam -parallel")
    assert "Time = 2" in seen["live"]
    log = (tmp_path / "logs" / "simpleFoam.log").read_text()
    assert log == "Time = 1\nTime = 2\n\n===STDERR===\nwarn\n"
    assert res.ok and res.stdout == "Time = 1\nTime = 2\n" and res.stderr == "warn\n"
    assert not list((tmp_path / "logs").glob("*.tmp"))


def test_runner_raises_with_tail_on_failure(tmp_path, monkeypatch):
    def fake_run(args, stdout, stderr, text):
        stdout.write("FOAM FATAL ERROR\n")
        return type("P", (), {"returncode": 1})()

    monkeypatch.setattr(runner_mod.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="FOAM FATAL ERROR"):
        OpenFOAMRunner(tmp_path).run("blockMesh")
    assert not OpenFOAMRunner(tmp_path).run("blockMesh", check=False).ok


class _FakeProc:
    def __init__(self, exit_after_polls=None):
        self.polls = 0
        self.exit_after = exit_after_polls

    def poll(self):
        self.polls += 1
        return 0 if self.exit_after is not None and self.polls > self.exit_after else None


class _Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def sleep(self, dt):
        self.t += dt


def test_watch_returns_none_on_normal_exit(tmp_path):
    c = _Clock()
    why = watch_process(_FakeProc(exit_after_polls=3), watch_dir=tmp_path,
                        hard_timeout_s=60, stall_s=30, clock=c, sleep=c.sleep)
    assert why is None


def test_watch_flags_stall_when_case_goes_quiet(tmp_path):
    c = _Clock()
    why = watch_process(_FakeProc(), watch_dir=tmp_path, hard_timeout_s=10_000, stall_s=30,
                        clock=c, sleep=c.sleep)
    assert why == "stall"
    assert 1030 < c.t <= 1040


def test_watch_keeps_slow_but_progressing_run_alive_until_hard_cap(tmp_path):
    (tmp_path / "logs").mkdir()
    log = tmp_path / "logs" / "simpleFoam.log"
    c = _Clock()

    def sleep(dt):  # the solver writes a line every poll -> never stalls
        c.sleep(dt)
        log.write_text("x")
        os.utime(log, (c.t, c.t))

    why = watch_process(_FakeProc(), watch_dir=tmp_path, hard_timeout_s=600, stall_s=30,
                        clock=c, sleep=sleep)
    assert why == "timeout"
    assert c.t > 1600


def test_latest_activity_sees_postprocessing_and_logs(tmp_path):
    assert latest_activity(tmp_path / "missing") == 0.0
    dat = tmp_path / "postProcessing" / "outletFlow" / "0" / "surfaceFieldValue.dat"
    dat.parent.mkdir(parents=True)
    dat.write_text("1 2\n")
    os.utime(dat, (5000.0, 5000.0))
    assert latest_activity(tmp_path) >= 5000.0


def test_stall_timeout_env(monkeypatch):
    monkeypatch.delenv("FANSIM_CFD_STALL_TIMEOUT", raising=False)
    assert stall_timeout() == 900.0
    monkeypatch.setenv("FANSIM_CFD_STALL_TIMEOUT", "1200")
    assert stall_timeout() == 1200.0
    monkeypatch.setenv("FANSIM_CFD_STALL_TIMEOUT", "5")
    assert stall_timeout() == 60.0
    assert stall_timeout(42.0) == 42.0


def test_run_watched_real_subprocess_exit_and_output(tmp_path):
    holder: list = []
    code, out, err = run_watched(
        [sys.executable, "-c", "import sys; print('hi'); sys.stderr.write('oops')"],
        watch_dir=tmp_path, hard_timeout_s=60, stall_s=60, label="t", proc_holder=holder)
    assert (code, out.strip(), err) == (0, "hi", "oops")
    assert holder == [None]


def test_run_watched_kills_on_hard_cap(tmp_path):
    t0 = time.time()
    with pytest.raises(TimeoutError, match="hard cap"):
        run_watched([sys.executable, "-c", "import time; time.sleep(60)"],
                    watch_dir=tmp_path, hard_timeout_s=0.5, stall_s=60, label="t")
    assert time.time() - t0 < 30


def test_partial_free_note(tmp_path):
    assert partial_free_note(tmp_path) == ""
    (tmp_path / PARTIAL_FREE_FILE).write_text(json.dumps({"cfm": 55.04, "converged": True}))
    note = partial_free_note(tmp_path)
    assert "55.0 CFM raw CFD" in note and "converged" in note


def test_stage_hint_reads_live_iteration_and_phase(tmp_path):
    (tmp_path / "impeller.stl").write_text("")
    assert cfd_stage_hint(tmp_path) == "meshing…"
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "checkMesh.log").write_text("cells: 10\n")
    assert cfd_stage_hint(tmp_path) == "meshing done — starting solve…"
    (logs / "decomposePar.log").write_text("")
    assert cfd_stage_hint(tmp_path) == "solve: starting…"
    (logs / "simpleFoam.log").write_text(
        "Time = 311\nExecutionTime = 3 s\n\nTime = 312\nsmoothSolver: ...\n")
    assert cfd_stage_hint(tmp_path) == "solve: iteration 312"
    (tmp_path / PARTIAL_FREE_FILE).write_text("{}")
    assert cfd_stage_hint(tmp_path) == "load solve (free-air done): iteration 312"


def test_mesh_pipeline_serial_unchanged_and_parallel_reconstructs():
    from fansim.cfd.openfoam_case import MESH_PIPELINE, mesh_pipeline

    assert mesh_pipeline(1) == MESH_PIPELINE
    par = mesh_pipeline(8)
    snap = next(c for c in par if "snappyHexMesh" in c)
    assert "-np 8" in snap and "-parallel" in snap
    # the parallel mesh is reconstructed and the processor dirs removed before the serial tail,
    # so topoSet/renumber/checkMesh and the solves see the same single-region case as serial
    i = par.index(snap)
    assert par[i + 1] == "reconstructParMesh -constant" and par[i + 2] == "rm -rf processor*"
    assert par[-3:] == MESH_PIPELINE[-3:]


def test_reconstructed_fields_older_than_mesh_are_ignored(tmp_path):
    from fansim.cfd.midplane import has_reconstructed_fields

    (tmp_path / "500").mkdir()
    u = tmp_path / "500" / "U"
    u.write_text("old field")
    owner = tmp_path / "constant" / "polyMesh" / "owner"
    owner.parent.mkdir(parents=True)
    owner.write_text("mesh")
    os.utime(u, (1000.0, 1000.0))       # field from an earlier solve...
    os.utime(owner, (2000.0, 2000.0))   # ...on an earlier mesh than the current one
    assert has_reconstructed_fields(tmp_path) is False
    os.utime(u, (3000.0, 3000.0))       # reconstructed after the current mesh
    assert has_reconstructed_fields(tmp_path) is True


@pytest.mark.skipif(
    sys.platform == "win32" or not __import__("shutil").which("bash"),
    reason="runs in the Linux OpenFOAM container; Git Bash launched from a non-MSYS parent "
           "rewrites argv (verified in opencfd/openfoam-default:2406 on 2026-10-07)")
def test_clean_before_solve_keeps_zero_and_non_time_dirs(tmp_path):
    import subprocess

    from fansim.cfd.openfoam_case import CLEAN_BEFORE_SOLVE

    for d in ("0", "250", "500", "1e-05", "constant", "system", "processor0", "postProcessing",
              "0.orig"):
        (tmp_path / d).mkdir()
    (tmp_path / "2").write_text("a file, not a time dir")
    subprocess.run(["bash", "-c", CLEAN_BEFORE_SOLVE], cwd=tmp_path, check=True)
    left = sorted(p.name for p in tmp_path.iterdir())
    assert left == ["0", "0.orig", "2", "constant", "system"]


def test_unscoped_container_kill_spares_other_sessions(monkeypatch):
    calls = []

    def fake_run(args, capture_output, text, timeout):
        calls.append(args)
        out = "aaa \nbbb overnight-audit\nccc \n" if args[1] == "ps" else ""
        return type("P", (), {"stdout": out, "returncode": 0})()

    monkeypatch.setattr(runner_mod.subprocess, "run", fake_run)
    monkeypatch.delenv("FANSIM_CFD_SESSION", raising=False)
    assert runner_mod.kill_cfd_containers() == 2
    assert calls[-1] == ["docker", "kill", "aaa", "ccc"]
    # a scoped kill takes every container of its own session
    calls.clear()
    monkeypatch.setattr(runner_mod.subprocess, "run", lambda args, **k: (
        calls.append(args), type("P", (), {"stdout": "bbb overnight-audit\n" if args[1] == "ps"
                                            else "", "returncode": 0})())[1])
    assert runner_mod.kill_cfd_containers(session="overnight-audit") == 1
    assert "label=fansim_cfd_session=overnight-audit" in calls[0]
