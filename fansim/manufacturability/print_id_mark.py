"""Cut recessed Crockford glyphs into the +Z hub face (roadmap 28.3).

CadQuery lives here so ``print_id`` stays importable without OCCT. Stroke layout
and the r10 band constants come from ``print_id``.
"""
from __future__ import annotations

import math

import cadquery as cq

from fansim.manufacturability.print_id import (
    MARK_DEPTH_MM,
    MARK_STROKE_MM,
    mark_strokes_xy,
    mark_will_cut,
)


def _stroke_box(
    x0: float, y0: float, x1: float, y1: float, width: float, z0: float, height: float,
) -> cq.Solid:
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return cq.Solid.makeCylinder(width / 2.0, height, cq.Vector(x0, y0, z0), cq.Vector(0, 0, 1))
    mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    span = length + width
    box = cq.Solid.makeBox(
        span, width, height, cq.Vector(mx - span / 2.0, my - width / 2.0, z0),
    )
    angle = math.degrees(math.atan2(dy, dx))
    return box.rotate(cq.Vector(mx, my, 0), cq.Vector(mx, my, 1), angle)


def engrave_print_id(
    model: cq.Workplane,
    code: str,
    *,
    z_top: float,
    hub_radius: float,
    bore_r: float = 10.0,
) -> cq.Workplane:
    """Cut 0.5 mm stroke recesses for ``code`` into the hub top. No-op if the band will not fit."""
    if not mark_will_cut(code, hub_radius, bore_r):
        return model
    segs = mark_strokes_xy(code)
    if not segs:
        return model
    # QA-74: the floor sits exactly MARK_DEPTH_MM below the face (was 0.65 mm); the tool only overshoots upward.
    z0 = float(z_top) - MARK_DEPTH_MM
    height = MARK_DEPTH_MM + 0.20
    # QA-76: fuse the strokes into one tool and cut once; one boolean per stroke on the whole
    # impeller took ~9x the unmarked export time.
    boxes = [_stroke_box(x0, y0, x1, y1, MARK_STROKE_MM, z0, height) for x0, y0, x1, y1 in segs]
    tool = boxes[0].fuse(*boxes[1:]).clean() if len(boxes) > 1 else boxes[0]
    shape = model.val().cut(tool)
    return cq.Workplane(obj=shape)
