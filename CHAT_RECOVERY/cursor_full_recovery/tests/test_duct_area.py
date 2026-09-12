"""Circular duct inlet-area honesty (§10.10)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from fansim.cfd.duct_area import (
    circular_inlet_area_error,
    circular_inlet_area_ok,
    expected_circular_area_m2,
    inlet_patch_area_m2,
    require_circular_inlet_area,
)


def test_expected_area_is_pi_r2():
    r = 0.055
    assert expected_circular_area_m2(r) == math.pi * r * r


def test_ok_within_tol():
    r = 0.055
    a = expected_circular_area_m2(r)
    assert circular_inlet_area_ok(a, r)
    assert circular_inlet_area_ok(a * 1.10, r)
    assert not circular_inlet_area_ok(a * 1.30, r)
    assert not circular_inlet_area_ok(a * 0.70, r)


def test_error_message_mentions_ratio():
    msg = circular_inlet_area_error(0.02, 0.055)
    assert "πR²" in msg or "pi" in msg.lower() or "ratio" in msg


def _write_tiny_circular_mesh(case: Path, *, r: float = 0.055, box_scale: float = 1.0) -> None:
    """ASCII polyMesh with a single square inlet of side ``2*r*box_scale``."""
    mesh = case / "constant" / "polyMesh"
    mesh.mkdir(parents=True)
    h = r * box_scale
    points = [
        (-h, -h, 0.0),
        (h, -h, 0.0),
        (h, h, 0.0),
        (-h, h, 0.0),
        (-h, -h, 0.1),
        (h, -h, 0.1),
        (h, h, 0.1),
        (-h, h, 0.1),
    ]
    (mesh / "points").write_text(
        "FoamFile { version 2.0; format ascii; class vectorField; object points; }\n"
        f"{len(points)}\n(\n"
        + "\n".join(f"({x} {y} {z})" for x, y, z in points)
        + "\n)\n",
        encoding="utf-8",
    )
    # face 0 = inlet (z=0), face 1 = outlet
    (mesh / "faces").write_text(
        "FoamFile { version 2.0; format ascii; class faceList; object faces; }\n"
        "2\n(\n"
        "4(0 1 2 3)\n"
        "4(4 5 6 7)\n"
        ")\n",
        encoding="utf-8",
    )
    (mesh / "boundary").write_text(
        "FoamFile { version 2.0; format ascii; class polyBoundaryMesh; object boundary; }\n"
        "2\n(\n"
        "    inlet { type patch; nFaces 1; startFace 0; }\n"
        "    outlet { type patch; nFaces 1; startFace 1; }\n"
        ")\n",
        encoding="utf-8",
    )


def test_inlet_patch_area_from_polyMesh(tmp_path):
    _write_tiny_circular_mesh(tmp_path, r=0.055, box_scale=1.0)
    area = inlet_patch_area_m2(tmp_path)
    assert area == pytest.approx((2 * 0.055) ** 2, rel=1e-9)


def test_require_ok_near_pi_r2(tmp_path):
    # Square of area πR² → side = R√π; box_scale = √π / 2 so side = 2 R (√π/2) = R√π
    r = 0.055
    scale = math.sqrt(math.pi) / 2.0
    _write_tiny_circular_mesh(tmp_path, r=r, box_scale=scale)
    assert require_circular_inlet_area(tmp_path, r) == pytest.approx(math.pi * r * r, rel=1e-9)


def test_require_rejects_oversized_hex_inlet(tmp_path):
    # BOX_SCALE=1.12 hex half-side → area (2.24 R)² ≈ 5.02 R² ≫ πR²
    r = 0.055
    _write_tiny_circular_mesh(tmp_path, r=r, box_scale=1.12)
    with pytest.raises(RuntimeError, match="snappy bypass"):
        require_circular_inlet_area(tmp_path, r)
