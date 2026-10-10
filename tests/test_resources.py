"""Memory tiers pick the fuse strategy from free RAM; every strategy builds the same solid."""

from __future__ import annotations

import pytest

from fansim import resources as R


@pytest.mark.parametrize("free_gb, name", [
    (40.0, "32gb"), (24.0, "32gb"), (12.0, "16gb"), (8.7, "8gb"), (6.5, "8gb"),
    (5.5, "6gb"), (3.5, "4gb"), (1.0, "2gb"), (0.0, "2gb"),
])
def test_tier_for_free_ram(free_gb, name):
    assert R.tier_for_free_gb(free_gb).name == name


def test_tiers_get_leaner_as_ram_shrinks():
    names = [t.name for t in R.TIERS]
    assert names == ["32gb", "16gb", "8gb", "6gb", "4gb", "2gb"]
    mins = [t.min_free_gb for t in R.TIERS]
    assert mins == sorted(mins, reverse=True)
    for t in R.TIERS:
        assert not (t.fuse_parallel and t.fuse_one_blade_at_a_time)
    assert [t.cup_build_ok for t in R.TIERS] == [True, True, True, True, False, False]


def test_env_override_and_bad_value(monkeypatch):
    monkeypatch.setenv(R.ENV_TIER, "6gb")
    assert R.current_tier().name == "6gb"
    monkeypatch.setenv(R.ENV_TIER, "64gb")
    with pytest.raises(ValueError, match="FANSIM_MEMORY_TIER"):
        R.current_tier()


def test_unreadable_ram_falls_back_to_the_safe_serial_tier(monkeypatch):
    monkeypatch.delenv(R.ENV_TIER, raising=False)
    monkeypatch.setattr(R, "free_ram_bytes", lambda: None)
    assert R.current_tier().name == "8gb"


def test_free_ram_is_readable_here():
    free = R.free_ram_bytes()
    assert free is not None and free > 64 * 1024 * 1024


@pytest.mark.parametrize("tier", ["32gb", "8gb", "6gb"])
def test_every_fuse_strategy_gives_the_same_solid(tier, monkeypatch):
    import cadquery as cq

    from fansim.geometry.blade import fuse_many

    hub = cq.Solid.makeCylinder(10, 5)
    blades = [cq.Solid.makeBox(20, 2, 4, cq.Vector(5, -1, 0.5)).rotate(
        cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), k * 60.0) for k in range(6)]
    out = fuse_many(hub, blades, tier=dict((t.name, t) for t in R.TIERS)[tier])
    assert len(out.Solids()) == 1 and out.isValid()
    ref = hub.fuse(*blades).clean()
    assert out.Volume() == pytest.approx(ref.Volume(), rel=1e-9)
