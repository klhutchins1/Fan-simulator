# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Graded printability difficulty calculator (fast, analytic)."""

from __future__ import annotations

from fansim.geometry.blade import BladeParams, RadialStation
from fansim.geometry.features import Features
from fansim.manufacturability.printability_score import (
    CLASS_EASY,
    CLASS_RESIN,
    CLASS_SUPPORTS,
    grade_printability,
)


def _mk(stag: float, thick: float, chords=(34, 44, 38), nb: int = 7, feats=None) -> BladeParams:
    return BladeParams(n_blades=nb, features=feats or Features(), stations=[
        RadialStation(0.0, chords[0], stag, thick, 0.05, 0.4, 0.0, 0, 0.0),
        RadialStation(0.5, chords[1], stag, thick, 0.06, 0.4, 3, 0, 14.0),
        RadialStation(1.0, chords[2], max(stag - 4, 15), thick * 0.7, 0.06, 0.4, 5, 0, 26.0)])


def test_grade_in_range_and_sorted():
    g = grade_printability(_mk(30, 0.10))
    assert 0.0 <= g.difficulty <= 100.0
    sev = [f.severity for f in g.factors]
    assert sev == sorted(sev, reverse=True), "factors must be worst-first"
    assert all(0.0 <= s <= 1.0 for s in sev)


def test_easy_design_is_easy_and_low():
    g = grade_printability(_mk(45, 0.14, chords=(20, 22, 20), nb=5))
    assert g.printer_class == CLASS_EASY
    assert g.difficulty < 25


def test_thin_walls_need_resin():
    # radius-aware: the tip edge alone no longer forces resin, so make the BODY sub-wall.
    g = grade_printability(_mk(30, 0.02))  # root 0.68 mm < 0.8 mm min FDM body wall
    assert g.printer_class == CLASS_RESIN
    assert g.difficulty > 55


def test_low_stagger_needs_supports_and_overhang_dominates():
    g = grade_printability(_mk(16, 0.10))
    assert g.printer_class in (CLASS_SUPPORTS,)
    overhang = next(f for f in g.factors if f.name == "Overhang")
    assert overhang.severity > 0.5


def test_harder_than_easy_ordering():
    easy = grade_printability(_mk(45, 0.14, chords=(20, 22, 20), nb=5)).difficulty
    mod = grade_printability(_mk(30, 0.10)).difficulty
    flat = grade_printability(_mk(16, 0.10)).difficulty
    assert easy < mod < flat, "difficulty should rise from easy -> moderate -> flat/thin"


def test_fine_features_add_a_factor():
    coarse = grade_printability(_mk(30, 0.10, feats=Features(serration_amp=0.04, serration_waves=4)))
    fine = grade_printability(_mk(30, 0.10, feats=Features(serration_amp=0.04, serration_waves=60)))
    # very fine serrations (60 across the ~35 mm span ~= 0.58 mm) drop below the FDM detail limit
    assert fine.printer_class == CLASS_RESIN
    assert fine.difficulty >= coarse.difficulty
