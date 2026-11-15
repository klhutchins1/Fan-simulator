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
    """P6 / QA-80: T3 FAIL on H7MQ8 — 3.2 mm / 0.6 mm stroke was unreadable. Larger cell."""
    assert MARK_R_INNER == 11.5
    assert MARK_R_OUTER == 16.5
    assert MARK_R_OUTER - MARK_R_INNER == 5.0
    assert MARK_DEPTH_MM == 0.5
    assert MARK_STROKE_MM == 0.9
    assert GLYPH_ADVANCE_MM == 3.6
    assert hub_can_take_mark(21.5)
    assert not hub_can_take_mark(14.0)
    # Still ≥1 mm from Stock bore r=10 and rim r=21.5.
    assert MARK_R_INNER - 1.0 >= 10.0
    assert MARK_R_OUTER + 1.0 <= 21.5


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


def test_export_print_ready_engraves_the_hub_face_not_the_bbox_top():
    """t9002 blades sit ~4 mm above the hub. Cutting at BoundingBox.zmax misses the face."""
    src = Path("fansim/manufacturability/print_export.py").read_text(encoding="utf-8")
    chunk = src.split("if print_id:", 1)[1].split("export_stl", 1)[0]
    assert "_hub_axial_range" in chunk
    assert "z_top=float(bb.zmax)" not in chunk
    assert "z_top=z_top" in chunk


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


def test_engrave_still_cuts_the_hub_when_a_fin_sticks_above_it():
    import cadquery as cq

    from fansim.manufacturability.print_id_mark import engrave_print_id

    hub = cq.Workplane("XY").circle(21.5).extrude(10.0)
    fin = cq.Workplane("XY").center(40, 0).box(8, 4, 15, centered=(True, True, False))
    model = hub.union(fin)
    assert model.val().BoundingBox().zmax > 14.0
    out = engrave_print_id(model, "E0MWW", z_top=10.0, hub_radius=21.5)
    dv = float(model.val().Volume()) - float(out.val().Volume())
    assert 4.0 < dv < 80.0
    probe = cq.Vector(0.0, MARK_R_INNER + 1.6, 10.0 - MARK_DEPTH_MM - 1.0)
    assert out.val().isInside(probe)


def test_engrave_skips_a_hub_too_small_for_the_band():
    import cadquery as cq

    from fansim.manufacturability.print_id_mark import engrave_print_id

    hub = cq.Workplane("XY").circle(12.0).extrude(10.0)
    v0 = float(hub.val().Volume())
    out = engrave_print_id(hub, "A1B2C", z_top=10.0, hub_radius=12.0)
    assert abs(float(out.val().Volume()) - v0) < 1e-6


def _view_xy(code):
    """Strokes seen from outside the +Z face (looking -Z): x right, y up; theta0 = 90 deg puts the mark at +Y."""
    return [((x0, y0), (x1, y1)) for x0, y0, x1, y1 in mark_strokes_xy(code)]


def test_mark_reads_left_to_right_from_plus_z():
    from fansim.manufacturability.print_id import check_digit

    code = "K7WB" + check_digit("K7WB")
    per = len(glyph_strokes("K")), len(glyph_strokes("7")), len(glyph_strokes("W")), len(glyph_strokes("B"))
    segs = _view_xy(code)
    xs, i = [], 0
    for n in per:
        chunk = segs[i:i + n]; i += n
        xs.append(sum(a[0] + b[0] for a, b in chunk) / (2 * n))
    assert xs == sorted(xs), f"glyph centres not left-to-right seen from +Z: {xs}"


def test_seven_is_not_mirrored_from_plus_z():
    # "7": top bar plus the right-hand vertical. Seen from +Z the vertical must be on the right of the bar centre.
    segs = _view_xy("77777")[:3]  # A, B, C of the first glyph
    (a0, a1), (b0, b1) = segs[0], segs[1]
    bar_cx = (a0[0] + a1[0]) / 2
    assert (b0[0] + b1[0]) / 2 > bar_cx


def test_no_two_glyphs_cut_identically_at_stroke_width():
    import itertools

    pts = {}
    w, h, s = GLYPH_ADVANCE_MM * 0.75, MARK_R_OUTER - MARK_R_INNER, MARK_STROKE_MM
    n = 60
    for ch in CHECK_ALPHABET:
        cells = set()
        for x0, y0, x1, y1 in glyph_strokes(ch):
            ax, ay, bx, by = x0 * w, y0 * h, x1 * w, y1 * h
            L = math.hypot(bx - ax, by - ay) or 1e-9
            ux, uy = (bx - ax) / L, (by - ay) / L
            for gx in range(n):
                for gy in range(n):
                    px, py = (gx + 0.5) * w / n, (gy + 0.5) * h / n
                    t = (px - ax) * ux + (py - ay) * uy
                    d = abs(-(px - ax) * uy + (py - ay) * ux)
                    if -s / 2 <= t <= L + s / 2 and d <= s / 2:
                        cells.add((gx, gy))
        pts[ch] = frozenset(cells)
    same = [a + b for a, b in itertools.combinations(CHECK_ALPHABET, 2)
            if len(pts[a] & pts[b]) / len(pts[a] | pts[b]) >= 0.98]
    assert not same, f"glyphs that cut identically: {same}"


def test_recess_depth_is_mark_depth_on_a_plain_hub_disk():
    """QA-74: the recess floor is MARK_DEPTH_MM below the face (cheap CAD: a 21.5 mm disk, not an impeller)."""
    import cadquery as cq

    from fansim.manufacturability.print_id import check_digit
    from fansim.manufacturability.print_id_mark import engrave_print_id

    disk = cq.Workplane("XY").circle(21.5).circle(10.0).extrude(5.0)
    code = "K7WB" + check_digit("K7WB")
    cut = engrave_print_id(disk, code, z_top=5.0, hub_radius=21.5, bore_r=10.0)
    removed = disk.val().cut(cut.val())
    bb = removed.BoundingBox()
    assert len(cut.val().Solids()) == 1
    assert abs(bb.zmax - 5.0) < 1e-6
    assert abs(bb.zmin - (5.0 - MARK_DEPTH_MM)) < 1e-3, f"recess floor at {bb.zmin}"


def test_id_coupon_is_a_short_disk_with_the_mark(tmp_path):
    """P6: T3-fail path is a hub washer, not another full fan."""
    from fansim.manufacturability.print_export import export_id_coupon
    from fansim.manufacturability.print_id import check_digit

    stl = tmp_path / "coupon.stl"
    code = "H7MQ" + check_digit("H7MQ")
    rep = export_id_coupon(stl, code, hub_radius=21.5, bore_r=10.0, height_mm=8.0)
    assert stl.is_file()
    assert rep.ok
    assert rep.n_bodies == 1
    lo, hi = rep.bounds_mm
    assert hi[2] - lo[2] == 8.0 or abs((hi[2] - lo[2]) - 8.0) < 0.2
    rmax = max(abs(lo[0]), abs(hi[0]), abs(lo[1]), abs(hi[1]))
    assert 21.0 < rmax < 22.0
    # Recess is on +Z, not a through-cut.
    assert 4.0 < (math.pi * (21.5**2 - 10.0**2) * 8.0 - rep.volume_mm3) < 80.0
