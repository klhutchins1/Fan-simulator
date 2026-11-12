"""Short hub ring for a motor-fit check. No blades."""

from __future__ import annotations

import numpy as np
import pytest
import trimesh

from fansim.fan_spec import get_fan_spec


def test_hub_fit_coupon_is_a_short_pad_ring(tmp_path):
    """Pad tips on the 37.25 mm circle, a few millimetres tall, no blades."""
    from fansim.manufacturability.print_export import export_hub_fit_coupon

    stl = tmp_path / "hub_fit.stl"
    mount = get_fan_spec("a12x25").motor_mount
    rep = export_hub_fit_coupon(stl, mount, hub_radius=21.5, height_mm=6.0)
    assert stl.is_file()
    assert rep.ok
    assert rep.n_bodies == 1
    lo, hi = rep.bounds_mm
    assert abs((hi[2] - lo[2]) - 6.0) < 0.2
    rmax = max(abs(lo[0]), abs(hi[0]), abs(lo[1]), abs(hi[1]))
    assert 21.0 < rmax < 22.0
    # A ring, not a full impeller. Wall + pads at 6 mm is about 2 cm³.
    assert 800.0 < rep.volume_mm3 < 5000.0

    mesh = trimesh.load(stl, force="mesh")
    v = np.asarray(mesh.vertices, float)
    r = np.hypot(v[:, 0], v[:, 1])
    inner = r[(r > 15.0) & (r < 22.0)]
    tip_dia = 2.0 * float(inner.min())
    assert tip_dia == pytest.approx(mount.cavity_dia_mm, abs=0.2)
