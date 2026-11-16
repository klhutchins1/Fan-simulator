"""The night queue never starts work that could reach the 4-9 PM peak window (AGENTS.md rule 2)."""
from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "night_queue", Path(__file__).resolve().parents[1] / "scripts" / "night_queue.py")
nq = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(nq)


def _t(h, m=0):
    return dt.datetime(2026, 10, 18, h, m)


def test_night_start_ok():
    assert nq.may_start(_t(0, 30), 2)
    assert nq.may_start(_t(21, 30), 8)          # ends 05:30 next day


def test_never_into_the_peak_window():
    assert not nq.may_start(_t(15, 30), 0.1)    # last start is before 15:30
    assert not nq.may_start(_t(17, 0), 0.1)     # inside 4-9 PM
    assert not nq.may_start(_t(14, 30), 2)      # would end 16:30
    assert nq.may_start(_t(13, 0), 2)           # ends 15:00
    assert not nq.may_start(_t(21, 0), 20)      # would end 17:00 next day


def test_python_means_this_venv():
    assert nq.resolve_cmd(["python", "-V"])[0] == sys.executable
    assert nq.resolve_cmd(["git", "python"]) == ["git", "python"]


def test_a_finished_job_is_not_run_again():
    job = {"id": "a", "cmd": ["python", "-V"], "status": "queued"}
    done = {}
    assert nq.should_run(job, done)
    nq.mark_ran(done, job, "exit 0", "2026-10-18")
    assert not nq.should_run(job, done)                       # same spec: skipped the next night
    assert nq.should_run({**job, "cmd": ["python", "-c", "1"]}, done)   # changed spec runs again
    assert nq.should_run({**job, "status": "rerun"}, done)    # explicit rerun
    assert not nq.should_run({**job, "status": "done"}, done)


def test_results_go_to_the_main_checkout():
    out = nq.results_root()
    assert out.name == "night" and out.parent.name == "runs"
    assert "fansim-night" not in str(out)


# --- self-update follows origin/master, so a pushed job runs even if nobody updated the local branch ---

import subprocess


def _g(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _clone(tmp_path):
    origin = tmp_path / "origin.git"
    _g(tmp_path, "init", "-q", "--bare", "-b", "master", str(origin))
    work = tmp_path / "work"
    _g(tmp_path, "clone", "-q", str(origin), str(work))
    _g(work, "config", "user.email", "t@example.com")
    _g(work, "config", "user.name", "t")
    (work / "a.txt").write_text("1")
    _g(work, "add", "-A")
    _g(work, "commit", "-q", "-m", "base")
    _g(work, "push", "-q", "origin", "HEAD:master")
    return origin, work


def test_self_update_uses_origin_master_when_it_is_ahead(tmp_path):
    origin, work = _clone(tmp_path)
    other = tmp_path / "other"
    _g(tmp_path, "clone", "-q", str(origin), str(other))
    _g(other, "config", "user.email", "t@example.com")
    _g(other, "config", "user.name", "t")
    (other / "b.txt").write_text("2")
    _g(other, "add", "-A")
    _g(other, "commit", "-q", "-m", "pushed by another agent")
    _g(other, "push", "-q", "origin", "HEAD:master")
    assert nq.update_target(work) == "origin/master"


def test_self_update_keeps_local_master_when_it_has_unpushed_commits(tmp_path):
    _, work = _clone(tmp_path)
    (work / "c.txt").write_text("3")
    _g(work, "add", "-A")
    _g(work, "commit", "-q", "-m", "local only")
    assert nq.update_target(work) == "master"


def test_self_update_falls_back_to_local_master_when_fetch_fails(tmp_path):
    _, work = _clone(tmp_path)
    _g(work, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    assert nq.update_target(work) == "master"


# --- the runner says what it did: which master it followed and why, and what the morning check printed ---

def test_choose_target_says_why_for_each_outcome(tmp_path):
    origin, work = _clone(tmp_path)
    target, why = nq.choose_update_target(work)
    assert target == "master" and "up to date" in why
    other = tmp_path / "other"
    _g(tmp_path, "clone", "-q", str(origin), str(other))
    _g(other, "config", "user.email", "t@example.com")
    _g(other, "config", "user.name", "t")
    (other / "b.txt").write_text("2")
    _g(other, "add", "-A")
    _g(other, "commit", "-q", "-m", "pushed")
    _g(other, "push", "-q", "origin", "HEAD:master")
    target, why = nq.choose_update_target(work)
    assert target == "origin/master" and "ahead" in why
    (work / "c.txt").write_text("3")
    _g(work, "add", "-A")
    _g(work, "commit", "-q", "-m", "local only")
    target, why = nq.choose_update_target(work)
    assert target == "master" and "unpushed" in why


def test_a_failed_fetch_is_named_not_silent(tmp_path):
    _, work = _clone(tmp_path)
    _g(work, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    target, why = nq.choose_update_target(work)
    assert target == "master"
    assert why.startswith("FETCH FAILED")
    assert nq.update_target(work) == "master"          # old name still works


def test_runner_log_is_written_even_when_no_job_runs(tmp_path):
    day = tmp_path / "2026-11-16"
    nq.log_runner(day, "update target master (FETCH FAILED: ssh: no key)", now=dt.datetime(2026, 11, 16, 23, 30))
    nq.log_runner(day, "0 jobs ran", now=dt.datetime(2026, 11, 16, 23, 31))
    lines = (day / "runner.log").read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("2026-11-16 23:30") and "FETCH FAILED" in lines[0]
    assert lines[1].startswith("2026-11-16 23:31") and "0 jobs ran" in lines[1]
