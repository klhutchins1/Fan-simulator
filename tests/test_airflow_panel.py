"""Shared airflow-panel helper: field selection + fail-soft pack (no Docker)."""

from __future__ import annotations

from pathlib import Path

from fansim.cockpit.airflow_panel import (
    AIRFLOW_CAPTIONS,
    AIRFLOW_FIELDS,
    pick_airflow_uri,
    png_data_uri,
    render_airflow_pack,
)


def test_png_data_uri_missing_is_empty(tmp_path: Path):
    assert png_data_uri(None) == ""
    assert png_data_uri(tmp_path / "nope.png") == ""


def test_png_data_uri_reads_a_file(tmp_path: Path):
    p = tmp_path / "x.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"abc")
    assert png_data_uri(p).startswith("data:image/png;base64,")


def test_pick_airflow_uri_selected_field_wins():
    uris = {"U": "u", "p": "pp", "uz": "z", "stream": "s"}
    uri, cap = pick_airflow_uri(uris, "uz")
    assert uri == "z" and cap == AIRFLOW_CAPTIONS["uz"]


def test_pick_airflow_uri_falls_back_to_umag():
    uris = {"U": "u", "p": "", "uz": "", "stream": ""}
    uri, cap = pick_airflow_uri(uris, "stream")  # streamlines missing -> fall back to |U|
    assert uri == "u" and cap == AIRFLOW_CAPTIONS["U"]


def test_pick_airflow_uri_none_available():
    uri, cap = pick_airflow_uri({"U": "", "p": "", "uz": "", "stream": ""}, "U")
    assert uri == "" and cap == ""


def test_render_airflow_pack_no_case_is_failsoft(tmp_path: Path):
    pack = render_airflow_pack(tmp_path / "no_such_case", image_ok=lambda: False)
    assert pack["available"] is False
    assert set(pack["uris"]) == set(AIRFLOW_FIELDS)
    assert all(v == "" for v in pack["uris"].values())


def test_render_airflow_pack_scroll_skips_uz_and_stream(tmp_path: Path):
    pack = render_airflow_pack(tmp_path / "no_such_case", layout="scroll", image_ok=lambda: False)
    assert pack["layout"] == "scroll"
    assert pack["uris"]["uz"] == ""
    assert pack["uris"]["stream"] == ""
    assert pack["available"] is False


def test_pick_airflow_uri_scroll_captions():
    uris = {"U": "u", "p": "pp", "uz": "", "stream": ""}
    uri, cap = pick_airflow_uri(uris, "U", layout="scroll")
    assert uri == "u"
    assert "scroll" in cap.lower()
    assert "+X" in cap

