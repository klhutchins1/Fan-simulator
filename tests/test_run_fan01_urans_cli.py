"""Argument parsing for the FAN-01 URANS CLI flags (no CFD/Docker).

See ``scripts/run_fan01.py``: --urans, --revs, --max-co, --n-outer, --delta-t, --pilot-seconds.
"""

from __future__ import annotations

from scripts.run_fan01 import build_parser


def test_urans_flags_defaults():
    args = build_parser().parse_args([])
    assert args.urans is False
    assert args.revs == 4.0
    assert args.max_co == 5.0
    assert args.n_outer == 3
    assert args.delta_t == 1e-5
    assert args.pilot_seconds == 600.0


def test_urans_flag_alone():
    args = build_parser().parse_args(["--urans"])
    assert args.urans is True
    assert args.pilot is False


def test_urans_pilot_combo():
    args = build_parser().parse_args(["--urans", "--pilot", "--pilot-seconds", "120"])
    assert args.urans is True
    assert args.pilot is True
    assert args.pilot_seconds == 120.0


def test_urans_overrides():
    args = build_parser().parse_args([
        "--urans", "--revs", "6", "--max-co", "8", "--n-outer", "4", "--delta-t", "2e-5",
    ])
    assert args.revs == 6.0
    assert args.max_co == 8.0
    assert args.n_outer == 4
    assert args.delta_t == 2e-5
