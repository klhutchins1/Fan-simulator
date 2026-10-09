"""Volute export list (roadmap §23.2: every Export after the first reported a TypeError)."""

import os

from fansim.cockpit.volute_tab import volute_export_rows


def test_lists_volute_stls_newest_first_with_folder_titles(tmp_path):
    a = tmp_path / "volute_20261001" / "impeller.stl"
    b = tmp_path / "volute_preview.stl"
    other = tmp_path / "design_100000.stl"
    for f in (a, b, other):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("solid x")
    os.utime(a, (1000, 1000))
    os.utime(b, (2000, 2000))
    rows = volute_export_rows(tmp_path)
    assert [r["title"] for r in rows] == ["volute_preview.stl", "volute_20261001/impeller.stl"]
    assert rows[1]["value"] == str(a.resolve())


def test_missing_dir_is_empty(tmp_path):
    assert volute_export_rows(tmp_path / "nope") == []
