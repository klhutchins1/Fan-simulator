"""Recessed Crockford glyphs on the +Z hub (roadmap 28.3). Layout tests are CAD-free."""
from __future__ import annotations

import math
from pathlib import Path

from fansim.manufacturability.print_id import (
    CHECK_ALPHABET,
    CROCKFORD,
    GLYPH_ADVANCE_MM,
    MARK_DEPTH_MM,
    MARK_R_INNER,
    MARK_R_OUTER,
    MARK_STROKE_MM,
    glyph_strokes,
    hub_can_take_mark,
    mark_strokes_xy,
)


def test_every_crockford_and_check_char_has_strokes_in_the_cell():
    for ch in CHECK_ALPHABET:
        segs = glyph_strokes(ch)
        assert segs, f"{ch!r} has no strokes"
        for x0, y0, x1, y1 in segs:
            for v in (x0, y0, x1, y1):
                assert 0.0 <= v <= 1.0, f"{ch!r} stroke coord {v} outside unit cell"
            assert math.hypot(x1 - x0, y1 - y0) > 0.05, f"{ch!r} has a degenerate stroke"


def test_unknown_char_has_no_strokes():
    assert glyph_strokes("I") == ()
    assert glyph_strokes("") == ()


def test_mark_band_matches_r10_spec():
    assert MARK_R_INNER == 11.5
    assert MARK_R_OUTER == 14.7
    assert MARK_DEPTH_MM == 0.5
    assert MARK_STROKE_MM >= 0.5
    assert GLYPH_ADVANCE_MM == 2.4
    assert hub_can_take_mark(21.5)
    assert not hub_can_take_mark(14.0)


def test_five_glyph_layout_stays_in_the_preferred_band():
    segs = mark_strokes_xy("A1B2C")
    assert segs
    rs = []
    for x0, y0, x1, y1 in segs:
        rs.append(math.hypot(x0, y0))
        rs.append(math.hypot(x1, y1))
    assert min(rs) >= MARK_R_INNER - 1e-6
    assert max(rs) <= MARK_R_OUTER + 1e-6
    # ≥ 1 mm from the 20 mm bore and from a 21.5 mm Stock hub rim (M3).
    assert min(rs) >= 10.0 + 1.0
    assert max(rs) <= 21.5 - 1.0


def test_export_print_ready_wires_print_id_into_the_engrave():
    src = Path("fansim/manufacturability/print_export.py").read_text(encoding="utf-8")
    assert "def export_print_ready" in src
    body = src.split("def export_print_ready", 1)[1]
    assert "print_id" in body.split("def ", 1)[0]
    assert "engrave_print_id" in body.split("def ", 1)[0]
    do = Path("fansim/cockpit/fan_export.py").read_text(encoding="utf-8")
    chunk = do.split("rep = export_print_ready", 1)[1][:200]
    assert "print_id" in chunk


def test_engrave_on_a_stock_size_disk_stays_one_solid_and_removes_a_shallow_volume():
    import cadquery as cq

    from fansim.manufacturability.print_id_mark import engrave_print_id

    z_top = 16.0
    hub = cq.Workplane("XY").circle(21.5).extrude(z_top)
    v0 = float(hub.val().Volume())
    out = engrave_print_id(hub, "A1B2C", z_top=z_top, hub_radius=21.5)
    solid = out.val()
    assert len(solid.Solids()) == 1
    dv = v0 - float(solid.Volume())
    # Dummy box pocket was 12.8 mm³; stroke-only should be the same order, not a through-cut.
    assert 4.0 < dv < 80.0
    # Floor of the recess is still material (depth 0.5 mm into a 16 mm disk).
    probe = cq.Vector(0.0, MARK_R_INNER + 1.6, z_top - MARK_DEPTH_MM - 1.0)
    assert solid.isInside(probe)


def test_engrave_skips_a_hub_too_small_for_the_band():
    import cadquery as cq

    from fansim.manufacturability.print_id_mark import engrave_print_id

    hub = cq.Workplane("XY").circle(12.0).extrude(10.0)
    v0 = float(hub.val().Volume())
    out = engrave_print_id(hub, "A1B2C", z_top=10.0, hub_radius=12.0)
    assert abs(float(out.val().Volume()) - v0) < 1e-6
