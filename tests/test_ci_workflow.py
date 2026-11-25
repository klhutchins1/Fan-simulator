"""R3.5: the GitHub workflow has a short Windows geometry/export job and changed-files ruff."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

GEOMETRY_EXPORT = (
    "tests/test_export_release.py",
    "tests/test_geometry.py",
    "tests/test_stl_sanitize.py",
    "tests/test_span_interp.py",
)


def _doc() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _runs(job: dict) -> str:
    return "\n".join(str(step.get("run", "")) for step in job.get("steps", []))


def test_windows_job_is_the_fast_geometry_and_export_subset():
    jobs = _doc()["jobs"]
    assert set(jobs) == {"fast", "windows-geometry"}
    job = jobs["windows-geometry"]
    assert job["runs-on"] == "windows-latest"
    script = _runs(job)
    assert "--all" not in script
    assert "--chunks" not in script
    assert "not docker and not slow" in script
    assert "judge(" in script
    for path in GEOMETRY_EXPORT:
        assert path in script
    names = [step.get("name") for step in job["steps"]]
    assert "Fast geometry and export" in names


def test_default_ruff_runs_on_changed_files_only():
    jobs = _doc()["jobs"]
    checkout = jobs["fast"]["steps"][0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"]["fetch-depth"] == 0
    runs = "\n".join(_runs(job) for job in jobs.values())
    assert "ruff check fansim tests scripts --select F811,F821" in runs
    assert "github.event.pull_request.base.sha" in runs
    assert "github.event.before" in runs
    assert "git diff" in runs
    changed = [
        str(step.get("run", ""))
        for job in jobs.values()
        for step in job.get("steps", [])
        if "ruff check" in str(step.get("run", "")) and "--select" not in str(step.get("run", ""))
    ]
    assert len(changed) == 1
    assert "ruff check fansim" not in changed[0]
    assert "ruff check ." not in changed[0]
    names = [step.get("name") for job in jobs.values() for step in job["steps"]]
    assert "Ruff changed files" in names
    assert "pytest_chunks.py --chunks 3 --all" in _runs(jobs["fast"])


def test_ci_fails_on_physics_audit_drift_before_pytest():
    """RV-0: the ledger drifted for five weeks because nothing failed on it."""
    steps = _doc()["jobs"]["fast"]["steps"]
    runs = [str(step.get("run", "")) for step in steps]
    audit = [i for i, r in enumerate(runs) if "scripts/audit_status.py --strict" in r]
    pytest_step = [i for i, r in enumerate(runs) if "pytest_chunks.py" in r]
    assert len(audit) == 1 and pytest_step
    assert audit[0] < pytest_step[0]
