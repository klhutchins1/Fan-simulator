"""Stock preview cache fingerprint / hit tests (no CadQuery build)."""

from __future__ import annotations

import json

from fansim.cockpit.stock_cache import (
    stock_cache_hit,
    stock_cache_paths,
    stock_fingerprint,
    write_stock_cache_meta,
)


def test_fingerprint_stable_and_sensitive():
    flat = {"n_blades": 9, "chord_root": 18.0, "tip_radius": 54.5}
    a = stock_fingerprint(flat, preview=True)
    b = stock_fingerprint(dict(flat), preview=True)
    assert a == b
    assert a != stock_fingerprint({**flat, "tip_radius": 56.5}, preview=True)
    assert a != stock_fingerprint(flat, preview=False)
    # Shape knobs that previously left Stock STL stale must bust the cache.
    assert a != stock_fingerprint({**flat, "le_thick_scale": 1.5}, preview=True)
    assert a != stock_fingerprint({**flat, "te_thick_scale": 1.5}, preview=True)
    assert a != stock_fingerprint({**flat, "section_family": "plate"}, preview=True)
    assert a != stock_fingerprint({**flat, "span_interp": "pchip"}, preview=True)
    assert a != stock_fingerprint({**flat, "le_skew_mid": 0.2}, preview=True)
    assert a != stock_fingerprint({**flat, "le_skew_tip": 0.3}, preview=True)
    assert a != stock_fingerprint({**flat, "camber_root": 0.04}, preview=True)
    assert a != stock_fingerprint({**flat, "thick_mode": "uniform"}, preview=True)


def test_cache_hit_requires_matching_meta(tmp_path, monkeypatch):
    import fansim.cockpit.stock_cache as sc

    monkeypatch.setattr(sc, "STOCK_CACHE_DIR", tmp_path)
    flat = {"n_blades": 9, "tip_radius": 54.5, "hub_height": 15.0}
    stl, meta = sc.stock_cache_paths("a12x25")
    stl.write_text("solid", encoding="utf-8")
    assert stock_cache_hit("a12x25", flat, preview=True) is None
    write_stock_cache_meta("a12x25", flat, preview=True)
    assert json.loads(meta.read_text(encoding="utf-8"))["fingerprint"] == stock_fingerprint(
        flat, preview=True
    )
    assert stock_cache_hit("a12x25", flat, preview=True) == stl
    assert stock_cache_hit("a12x25", {**flat, "tip_radius": 50.0}, preview=True) is None
