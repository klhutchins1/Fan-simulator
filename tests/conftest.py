"""Shared pytest fixtures for the Fan-Simulator suite."""

from __future__ import annotations

import os
import uuid

import pytest

# The suite gets its own CFD session before anything imports fansim.cfd.runner, so a test that
# reaches real container cleanup can only touch the suite's own containers, never a validation
# run on the same machine (2026-11-25: a test run killed FAN-01's snappyHexMesh).
os.environ["FANSIM_CFD_SESSION"] = f"pytest-{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def _isolate_stock_cache(tmp_path_factory, monkeypatch):
    """Redirect the parametric Stock preview cache to a per-test tmp dir.

    The stock cache is a rebuildable runtime artifact; without this, a test that triggers a
    stock preview would write into the real cache location and could clobber tracked reference
    data. Pointing it at a fresh tmp dir keeps every test hermetic and read-only w.r.t. git.
    """
    try:
        import fansim.cockpit.stock_cache as sc
    except ImportError:
        return  # cockpit deps (optim extra) absent here — nothing can write the stock cache

    monkeypatch.setattr(
        sc, "STOCK_CACHE_DIR", tmp_path_factory.mktemp("stock_cache"), raising=False
    )


@pytest.fixture(autouse=True, scope="module")
def _release_memory_between_files():
    """Hand freed memory back to the OS after each test file (roadmap §23.9).

    Measured 2026-10-08 on Windows: the fast suite peaks ~2.5 GB private and drops back (no leak);
    ~1.3 GB is the one-time OCCT/VTK/SciPy import. On Linux, glibc keeps freed arenas, so one
    process grew to 4-6 GB and the suite was OOM-killed on a 16 GB box. ``malloc_trim(0)`` after a
    garbage collection returns those pages; it is a no-op where unavailable.
    """
    yield
    import gc
    import sys

    gc.collect()
    if sys.platform.startswith("linux"):
        try:
            import ctypes

            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except (OSError, AttributeError):
            pass
