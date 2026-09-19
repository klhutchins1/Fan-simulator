"""Stale-CFD detection: unstamped / old-version scores are flagged (roadmap §18.1)."""

from __future__ import annotations

from fansim.cfd.metrics import CFD_VERSION
from fansim.cockpit.data import cfd_is_stale


def test_current_version_is_not_stale():
    assert not cfd_is_stale(CFD_VERSION)
    assert not cfd_is_stale(CFD_VERSION + 1)  # a newer score is also acceptable


def test_missing_or_old_version_is_stale():
    assert cfd_is_stale(None)          # pre-stamp trials (no cfd_version user_attr)
    assert cfd_is_stale(0)
    assert cfd_is_stale(CFD_VERSION - 1)


def test_garbage_version_is_stale():
    assert cfd_is_stale("nan")
    assert cfd_is_stale([])
