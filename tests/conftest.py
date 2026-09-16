"""Shared pytest fixtures for the Fan-Simulator suite."""

from __future__ import annotations

import pytest


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
