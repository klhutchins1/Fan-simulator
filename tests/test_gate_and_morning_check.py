"""Same-day merge gate (scripts/gate.py) and the morning check (scripts/morning_check.py)."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gate = _load("gate")
mc = _load("morning_check")


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


FAKE_CHUNKS = """import sys
print("chunk 0: {verdict}")
sys.exit({rc})
"""


@pytest.fixture
def repo(tmp_path):
    """A bare origin and a clone with master + a feature branch `feat`, both pushed."""
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "master", str(origin))
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    (work / "scripts").mkdir()
    (work / "night").mkdir()
    (work / "scripts" / "pytest_chunks.py").write_text(
        FAKE_CHUNKS.format(verdict="passed: 3 passed in 0.1s", rc=0))
    (work / "night" / "queue.json").write_text(json.dumps({"jobs": [
        {"id": "suite-feat", "branch": "feat", "cmd": ["python", "x"], "status": "queued", "merge_on_green": True},
    ]}, indent=1))
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "base")
    _git(work, "push", "-q", "origin", "HEAD:master")
    _git(work, "checkout", "-q", "-b", "feat")
    (work / "feature.py").write_text("x = 1\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "feat")
    _git(work, "push", "-q", "origin", "feat")
    _git(work, "checkout", "-q", "master")
    return work


# ---------------------------------------------------------------- gate.py

def test_gate_refuses_when_it_could_reach_the_peak_window(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("nothing may run when the gate is refused")

    monkeypatch.setattr(gate.subprocess, "run", boom)
    assert gate.main(["feat"], now_fn=lambda: dt.datetime(2026, 11, 9, 15, 0)) == 3   # 15:00 + 1.5 h > 16:00
    assert gate.main(["feat"], now_fn=lambda: dt.datetime(2026, 11, 9, 17, 0)) == 3   # inside 4-9 PM


def test_gate_green_writes_a_result_and_exits_0(repo, monkeypatch, capsys):
    monkeypatch.setattr(gate, "ROOT", repo)
    monkeypatch.setattr(gate, "OUT", repo / "runs" / "gate")
    rc = gate.main(["feat"], now_fn=lambda: dt.datetime(2026, 11, 9, 9, 0))
    assert rc == 0
    res = json.loads((repo / "runs" / "gate" / "feat.json").read_text())
    assert res["ok"] is True
    assert res["sha"] == _git(repo, "rev-parse", "feat")
    assert res["verdicts"] == ["chunk 0: passed: 3 passed in 0.1s"]
    assert "gate green" in capsys.readouterr().out
    assert not (repo / "runs" / "gate" / "wt-feat").exists()          # worktree cleaned up


def test_gate_red_exits_1(repo, monkeypatch):
    _git(repo, "checkout", "-q", "feat")
    (repo / "scripts" / "pytest_chunks.py").write_text(
        FAKE_CHUNKS.format(verdict="FAILED (1 failed, 2 passed in 0.1s)", rc=1))
    _git(repo, "commit", "-qam", "break")
    _git(repo, "checkout", "-q", "master")
    monkeypatch.setattr(gate, "ROOT", repo)
    monkeypatch.setattr(gate, "OUT", repo / "runs" / "gate")
    assert gate.main(["feat"], now_fn=lambda: dt.datetime(2026, 11, 9, 9, 0)) == 1
    assert json.loads((repo / "runs" / "gate" / "feat.json").read_text())["ok"] is False


# ---------------------------------------------------------------- morning_check.py: verdicts

def test_exit_0_is_green():
    assert mc.verdict({"result": "exit 0"}, "chunk 0: passed: 5 passed in 1s\n")[0] is True


def test_old_single_chunk_job_with_teardown_crash_is_green():
    log = "....\n717 passed, 7 skipped, 14 deselected in 1422.72s (0:23:42)\n"
    ok, text = mc.verdict({"result": "exit 4294967295"}, log)
    assert ok is True and "teardown" in text


def test_real_failure_is_red():
    log = "FAILED tests/x.py::t\n1 failed, 691 passed in 10.0s\n"
    assert mc.verdict({"result": "exit 1"}, log)[0] is False


def test_all_run_with_one_failed_chunk_is_red_even_if_the_last_chunk_passed():
    log = ("1 failed, 691 passed in 10.0s\n702 passed in 9.0s\n\n"
           "chunk 0: FAILED (1 failed, 691 passed in 10.0s)\n"
           "chunk 1: passed: 702 passed in 9.0s\n")
    assert mc.verdict({"result": "exit 1"}, log)[0] is False


def test_non_pytest_failure_and_timeout_are_red():
    assert mc.verdict({"result": "exit 2"}, "Traceback ...\n")[0] is False
    assert mc.verdict({"result": "timeout"}, "")[0] is False


def test_not_started_is_neither_green_nor_red():
    assert mc.verdict({"result": "not started: inside or would reach the 4-9 PM peak window"}, "")[0] is None


def test_doc_only_paths():
    assert mc.doc_only(["docs/release/RELEASE_PLAN.md", "night/queue.json", "README.md", "handoff/x/a.bundle"])
    assert not mc.doc_only(["docs/a.md", "fansim/cfd/x.py"])
    assert not mc.doc_only(["scripts/gate.py"])


# ---------------------------------------------------------------- morning_check.py: which branches merge

def _jobs(**over):
    jobs = [{"id": f"s-c{i}", "branch": "feat", "status": "queued", "merge_on_green": True} for i in range(3)]
    for j in jobs:
        j.update(over)
    return jobs


def test_branch_merges_only_when_every_job_for_it_is_green():
    jobs = _jobs()
    green = {"s-c0": True, "s-c1": True, "s-c2": True}
    assert mc.branches_to_merge(jobs, green) == ["feat"]
    assert mc.branches_to_merge(jobs, {**green, "s-c1": False}) == []
    assert mc.branches_to_merge(jobs, {"s-c0": True, "s-c1": True}) == []      # c2 has not run yet


def test_branch_without_merge_on_green_is_left_for_an_agent():
    assert mc.branches_to_merge(_jobs(merge_on_green=False), {"s-c0": True, "s-c1": True, "s-c2": True}) == []


def test_jobs_already_done_count_as_green():
    jobs = _jobs()
    jobs[0]["status"] = "done"
    assert mc.branches_to_merge(jobs, {"s-c1": True, "s-c2": True}) == ["feat"]


# ---------------------------------------------------------------- morning_check.py: apply (real git)

def _night(repo, result="exit 0", sha=None, log="chunk 0: passed: 3 passed in 0.1s\n"):
    day = repo / "runs" / "night" / "2026-11-09"
    day.mkdir(parents=True)
    (day / "suite-feat.log").write_text(log)
    rec = {"id": "suite-feat", "result": result, "log": str(day / "suite-feat.log"),
           "sha": sha or _git(repo, "rev-parse", "origin/feat")}
    (day / "results.json").write_text(json.dumps([rec]))
    return day


def _origin_queue(repo):
    _git(repo, "fetch", "-q", "origin")
    return {j["id"]: j for j in json.loads(_git(repo, "show", "origin/master:night/queue.json"))["jobs"]}


def test_apply_merges_a_green_branch_marks_the_job_done_and_pushes(repo):
    day = _night(repo)
    assert mc.main(["--apply", "--day", str(day)], root=repo) == 0
    job = _origin_queue(repo)["suite-feat"]
    assert job["status"] == "done"
    assert _git(repo, "show", "origin/master:feature.py") == "x = 1"
    assert "Merge branch 'feat'" in _git(repo, "log", "-3", "--format=%s", "origin/master")
    status = (repo / "runs" / "night" / "STATUS.md").read_text()
    assert "feat" in status and "merged" in status


def test_apply_marks_a_red_job_failed_and_does_not_merge(repo):
    day = _night(repo, result="exit 1", log="chunk 0: FAILED (1 failed, 2 passed in 0.1s)\n")
    mc.main(["--apply", "--day", str(day)], root=repo)
    assert _origin_queue(repo)["suite-feat"]["status"] == "failed"
    with pytest.raises(subprocess.CalledProcessError):
        _git(repo, "show", "origin/master:feature.py")


def test_apply_does_not_merge_a_branch_that_moved_after_the_gate(repo):
    day = _night(repo)
    _git(repo, "checkout", "-q", "feat")
    (repo / "feature.py").write_text("x = 2\n")
    _git(repo, "commit", "-qam", "later")
    _git(repo, "push", "-q", "origin", "feat")
    _git(repo, "checkout", "-q", "master")
    mc.main(["--apply", "--day", str(day)], root=repo)
    with pytest.raises(subprocess.CalledProcessError):
        _git(repo, "show", "origin/master:feature.py")
    assert "moved" in (repo / "runs" / "night" / "STATUS.md").read_text()


def test_apply_does_not_merge_when_master_changed_code_since_the_branch_forked(repo):
    day = _night(repo)
    (repo / "other.py").write_text("y = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "code on master")
    _git(repo, "push", "-q", "origin", "HEAD:master")
    mc.main(["--apply", "--day", str(day)], root=repo)
    with pytest.raises(subprocess.CalledProcessError):
        _git(repo, "show", "origin/master:feature.py")
    assert "gate again" in (repo / "runs" / "night" / "STATUS.md").read_text()
    assert _origin_queue(repo)["suite-feat"]["status"] == "done"       # the job itself was green


def test_without_apply_nothing_is_pushed(repo):
    day = _night(repo)
    before = _git(repo, "rev-parse", "origin/master")
    mc.main(["--day", str(day)], root=repo)
    _git(repo, "fetch", "-q", "origin")
    assert _git(repo, "rev-parse", "origin/master") == before
    assert (repo / "runs" / "night" / "STATUS.md").exists()


# ---------------------------------------------------------------- morning_check.py: it must say when it could not apply

def test_apply_that_cannot_read_the_queue_says_so_in_status(repo):
    day = _night(repo)
    _git(repo, "remote", "set-url", "origin", str(repo.parent / "gone.git"))
    _git(repo, "update-ref", "-d", "refs/remotes/origin/master")
    mc.main(["--apply", "--day", str(day)], root=repo)
    text = (repo / "runs" / "night" / "STATUS.md").read_text()
    assert "APPLY SKIPPED" in text and "origin/master" in text


def test_apply_that_crashes_still_writes_status_and_names_the_error(repo):
    day = _night(repo)
    blocker = repo / "runs" / "night" / "wt-morning"
    blocker.mkdir(parents=True)
    (blocker / "x.txt").write_text("in the way")
    mc.main(["--apply", "--day", str(day)], root=repo)
    text = (repo / "runs" / "night" / "STATUS.md").read_text()
    assert "APPLY FAILED" in text
    assert "suite-feat" in text                      # the verdict table is still there
