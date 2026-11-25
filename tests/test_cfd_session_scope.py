"""CFD containers are killed only by their own session (2026-11-25 FAN-01 crash).

Before this, a process with no FANSIM_CFD_SESSION (every script, every test run, a cockpit started
without --reload) did an *unscoped* cleanup: ``docker kill`` on every ``fansim_cfd=1`` container
without a session label. ``tests/test_cfd_watchdog.py::test_run_watched_kills_on_hard_cap`` reaches
that cleanup for real, so a test suite run killed a FAN-01 validation run's snappyHexMesh
(exit 137) on the same machine. Every process now has a session, and cleanup is always scoped.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import fansim.cfd.runner as runner_mod


def test_the_test_suite_runs_in_its_own_session():
    assert os.environ[runner_mod.ENV_SESSION].startswith("pytest-")


def test_every_container_carries_a_session_label():
    args = runner_mod._label_args()
    assert args[:2] == ["--label", "fansim_cfd=1"]
    assert f"fansim_cfd_session={runner_mod.cfd_session()}" in args


def test_a_process_without_a_session_gets_its_own_and_children_inherit_it():
    code = textwrap.dedent("""
        import os, subprocess, sys
        os.environ.pop("FANSIM_CFD_SESSION", None)
        import fansim.cfd.runner as r
        mine = r.cfd_session()
        child = subprocess.run([sys.executable, "-c",
                                "import os; print(os.environ['FANSIM_CFD_SESSION'])"],
                               capture_output=True, text=True).stdout.strip()
        print(mine, child)
    """)
    env = {k: v for k, v in os.environ.items() if k != runner_mod.ENV_SESSION}
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=env, check=True).stdout.split()
    assert out[0].startswith("pid") and out[0] == out[1]


def test_cleanup_kills_only_its_own_sessions_containers(monkeypatch):
    calls = []
    mine = runner_mod.cfd_session()

    def fake_run(args, capture_output, text, timeout, check=False):
        calls.append(args)
        out = f"aaa {mine}\n" if args[1] == "ps" else ""
        return type("P", (), {"stdout": out, "returncode": 0})()

    monkeypatch.setattr(runner_mod.subprocess, "run", fake_run)
    assert runner_mod.kill_cfd_containers() == 1
    assert f"label=fansim_cfd_session={mine}" in calls[0]       # docker ps filter is scoped
    assert calls[-1] == ["docker", "kill", "aaa"]
    assert "label=fansim_cfd=1" not in calls[0]                  # never the unscoped filter


def test_watchdog_hard_cap_cleanup_is_scoped(monkeypatch, tmp_path):
    """The exact path that killed FAN-01: run_watched's hard-cap cleanup."""
    import pytest

    from fansim.isolated_job import run_watched

    seen = []
    real_run = subprocess.run

    def spy(args, *a, **k):
        if args and args[0] == "docker":
            seen.append(list(args))
            return type("P", (), {"stdout": "", "returncode": 0})()
        return real_run(args, *a, **k)

    monkeypatch.setattr(runner_mod.subprocess, "run", spy)
    with pytest.raises(TimeoutError, match="hard cap"):
        run_watched([sys.executable, "-c", "import time; time.sleep(60)"],
                    watch_dir=tmp_path, hard_timeout_s=0.5, stall_s=60, label="t")
    ps = [a for a in seen if a[1] == "ps"]
    assert ps and all(f"label=fansim_cfd_session={runner_mod.cfd_session()}" in a for a in ps)
