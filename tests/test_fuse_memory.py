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
    with pytest.raises(MemoryError, match="GB of free memory"):
        resources.check_fuse_memory(71_229)


def test_allows_when_ram_is_enough_or_unknown(monkeypatch):
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
