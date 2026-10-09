"""Chord realisation: disk cache + untrimmed measurement (roadmap §23.17)."""

import pytest

from fansim.geometry import chord_realisation as cr
from fansim.geometry.blade import BladeParams


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("FANSIM_CACHE_DIR", str(tmp_path))
    return tmp_path / "loft_chords"


def test_second_call_hits_the_disk_cache(cache, monkeypatch):
    bp = BladeParams()
    first = cr.loft_chords_for_measured_targets(bp)
    assert len(list(cache.glob("*.json"))) == 1

    def boom(*_a, **_k):
        raise AssertionError("re-measured despite a cache hit")

    monkeypatch.setattr(cr, "measure_station_chords", boom)
    assert cr.loft_chords_for_measured_targets(bp) == first


def test_any_param_change_misses(cache):
    a, b = BladeParams(), BladeParams()
    b.stations[1].stagger_deg += 1.0
    assert cr._cache_key(a, 2) != cr._cache_key(b, 2)
    assert cr._cache_key(a, 2) != cr._cache_key(a, 3)


def test_corrupt_or_wrong_length_entry_is_ignored(cache):
    bp = BladeParams()
    cache.mkdir(parents=True)
    key = cr._cache_key(bp, 2)
    (cache / f"{key}.json").write_text("[1.0]")          # wrong length
    assert cr._cache_get(key, len(bp.stations)) is None
    (cache / f"{key}.json").write_text("not json")
    assert cr._cache_get(key, len(bp.stations)) is None
