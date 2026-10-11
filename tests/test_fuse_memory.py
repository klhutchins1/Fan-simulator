"""Predict the fuse's peak RAM from the face count and refuse plainly when it won't fit (roadmap 25.5)."""

from __future__ import annotations

import pytest

from fansim import resources


def test_estimate_matches_measured_builds():
    # Windows, 2026-10-11: plain 9-blade design 18 k faces -> 2.0 GB; featured S5_0011 71 k -> 6.5 GB.
    assert resources.fuse_peak_estimate_gb(18_084) == pytest.approx(2.0, abs=0.2)
    assert resources.fuse_peak_estimate_gb(71_229) == pytest.approx(6.5, abs=0.3)


def test_refuses_with_plain_message_when_ram_too_small(monkeypatch):
    monkeypatch.setattr(resources, "free_ram_bytes", lambda: int(3.0 * resources.GB))
    monkeypatch.delenv(resources.ENV_TIER, raising=False)
    monkeypatch.setenv(resources.ENV_FUSE_GUARD, "1")  # the cockpit turns the guard on
    with pytest.raises(MemoryError, match="GB of free memory"):
        resources.check_fuse_memory(71_229)


def test_batch_builds_are_never_refused(monkeypatch):
    """Optimizer / Assess / scripts: a refusal would be scored as an infeasible design, so the guard
    only acts where a person reads the message (the cockpit sets FANSIM_FUSE_GUARD)."""
    monkeypatch.setattr(resources, "free_ram_bytes", lambda: int(1.0 * resources.GB))
    monkeypatch.delenv(resources.ENV_TIER, raising=False)
    monkeypatch.delenv(resources.ENV_FUSE_GUARD, raising=False)
    resources.check_fuse_memory(71_229)


def test_allows_when_ram_is_enough_or_unknown(monkeypatch):
    monkeypatch.setenv(resources.ENV_FUSE_GUARD, "1")
    monkeypatch.setattr(resources, "free_ram_bytes", lambda: int(12.0 * resources.GB))
    resources.check_fuse_memory(71_229)
    monkeypatch.setattr(resources, "free_ram_bytes", lambda: None)  # can't read: don't block
    resources.check_fuse_memory(71_229)


def test_fuse_impeller_checks_before_the_boolean(monkeypatch):
    from fansim.geometry import blade

    seen = []
    monkeypatch.setattr(resources, "check_fuse_memory", lambda n: seen.append(n))
    monkeypatch.setattr(blade, "fuse_many", lambda base, tools, tier=None: base)

    class _S:
        def __init__(self, n):
            self.n = n

        def Faces(self):
            return [0] * self.n

    blade.fuse_impeller(_S(10), [_S(100), _S(100)], _S(5))
    assert seen == [215]


def test_cockpit_build_job_carries_the_guard_flag(monkeypatch, tmp_path):
    """Preview/Export ask for the guard; plain build_stl_isolated callers (batch) do not."""
    from fansim.geometry import isolated

    jobs = []
    monkeypatch.setattr(isolated, "run_worker_module", lambda module, job, **k: jobs.append(job))
    isolated.build_stl_isolated({}, {}, tmp_path / "a.stl", fuse_guard=True)
    isolated.build_stl_isolated({}, {}, tmp_path / "b.stl")
    assert jobs[0].get("fuse_guard") is True and "fuse_guard" not in jobs[1]
