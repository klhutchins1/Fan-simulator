"""Polar-family BEM cache: family name is the cache key (no cross-family leak)."""

from __future__ import annotations

from fansim.propeller import polars


def test_polar_family_cache_keyed_by_name():
    polars.clear_polar_cache()
    a = polars.family_for_camber(0.0, 0.12)
    b = polars.family_for_camber(0.04, 0.12)
    assert a != b
    # Distinct families must resolve to distinct load_polar_family cache entries.
    fa = polars.load_polar_family(a)
    fb = polars.load_polar_family(b)
    assert fa is not fb
    assert set(fa.keys())  # non-empty Re tables
    assert set(fb.keys())
    # Same-name lookup returns the identical cached object.
    assert polars.load_polar_family(a) is fa
