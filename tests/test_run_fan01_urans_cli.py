"""Argument parsing for the FAN-01 URANS CLI flags (no CFD/Docker).

See ``scripts/run_fan01.py``: --urans, --revs, --max-co, --n-outer, --delta-t, --pilot-seconds.
"""

from __future__ import annotations

from pathlib import Path

from scripts.run_fan01 import OUT_JSON, URANS_OUT_JSON, build_parser, resolve_out_json


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


def test_align_tip_flag_default_off():
    args = build_parser().parse_args([])
    assert args.align_tip is False
    assert build_parser().parse_args(["--align-tip"]).align_tip is True


def test_out_json_defaults_match_prereg_and_protect_2026_09_28_file():
    """Steady default writes fan01_cfd_rv2.json (prereg) so the 2026-09-28 file is never overwritten."""
    assert OUT_JSON == Path("docs/validation/fan01/fan01_cfd_rv2.json")
    steady = build_parser().parse_args([
        "--points", "7,64,126,135,205,253", "--iters", "1000", "--base-cell", "0.02", "--out", "runs/fan01-rv2",
    ])
    assert steady.out == "runs/fan01-rv2"
    assert steady.out_json is None
    assert resolve_out_json(steady) == Path("docs/validation/fan01/fan01_cfd_rv2.json")

    urans = build_parser().parse_args(["--urans"])
    assert resolve_out_json(urans) == URANS_OUT_JSON


def test_out_json_override():
    steady = build_parser().parse_args(["--out-json", "runs/tmp/custom.json"])
    assert resolve_out_json(steady) == Path("runs/tmp/custom.json")

    urans = build_parser().parse_args(["--urans", "--out-json", "runs/tmp/custom_urans.json"])
    assert resolve_out_json(urans) == Path("runs/tmp/custom_urans.json")
