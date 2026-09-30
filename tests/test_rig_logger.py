"""Unit tests for scripts/rig_logger.py parse + CSV append (no serial hardware)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

from rig_logger import append_row, parse_line  # noqa: E402
from validation.ingest import CSV_COLUMNS, load_measurements  # noqa: E402


def test_parse_line_aliases():
    row = parse_line(
        "rpm=2000,dp=12.3,cfm=45,noise=38,restriction=plate3",
        default_source="sdp810",
    )
    assert row is not None
    assert row["rpm"] == "2000"
    assert row["dp_pa"] == "12.3"
    assert row["cfm"] == "45"
    assert row["noise_dba"] == "38"
    assert row["restriction_id"] == "plate3"
    assert row["source"] == "sdp810"


def test_parse_line_requires_rpm():
    with pytest.raises(ValueError, match="rpm"):
        parse_line("cfm=45,dp=1")


def test_append_and_reload(tmp_path):
    path = tmp_path / "rig.csv"
    row = parse_line(
        "rpm=2000,dp=12.3,cfm=45,noise=38,restriction=plate3,tach=1998,ambient=22,humidity=40",
        default_source="sdp810",
    )
    assert row is not None
    append_row(path, row)
    with path.open(newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert header == list(CSV_COLUMNS)
    pts = load_measurements(path)
    assert len(pts) == 1
    assert pts[0].dp_pa == 12.3 and pts[0].restriction_id == "plate3"
    assert pts[0].tach_rpm == 1998.0 and pts[0].source == "sdp810"
