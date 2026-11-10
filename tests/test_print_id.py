"""Print-part ID registry (roadmap 28.2). No CAD, no hub cut."""
from __future__ import annotations

from pathlib import Path

from fansim.geometry.blade import BladeParams
from fansim.manufacturability.print_id import (
    CROCKFORD,
    check_digit,
    export_stem,
    git_head,
    issue_print_id,
    list_ids,
    normalize_read,
    record_export,
    recipe_hash,
    verify_print_id,
)
from fansim.manufacturability.print_export import print_readme, recommend_print_settings
from fansim.geometry.export import WatertightReport


def test_check_digit_is_in_crockford_plus_symbols():
    body = "A1B2"
    c = check_digit(body)
    assert c in (CROCKFORD + "*~$=U")
    assert verify_print_id(body + c)
    assert not verify_print_id(body + ("0" if c != "0" else "1"))


def test_normalize_read_maps_ilo():
    assert normalize_read("ilo") == "110"


def test_issue_is_unique_and_recorded_length(tmp_path):
    index = tmp_path / "index.jsonl"
    seen = set()
    for _ in range(20):
        pid = issue_print_id(index)
        assert len(pid) == 5
        assert pid[:4].isupper() or pid[:4].isalnum()
        assert all(ch in CROCKFORD for ch in pid[:4])
        assert verify_print_id(pid)
        assert pid not in seen
        seen.add(pid)
        record_export(index, print_id=pid, stl="x.stl")
    assert list_ids(index) == seen


def test_issue_skips_ids_already_in_the_index(tmp_path, monkeypatch):
    from fansim.manufacturability import print_id as m

    index = tmp_path / "index.jsonl"
    queue = ["TTTT", "TTTT", "YYYY"]
    monkeypatch.setattr(m, "_random_body", lambda n=4, rng=None: queue.pop(0))
    first = issue_print_id(index)
    record_export(index, print_id=first, stl="a.stl")
    second = issue_print_id(index)
    assert first.startswith("TTTT") and second.startswith("YYYY")
    assert first != second


def test_export_stem_leads_with_the_code():
    assert export_stem("A1B2C", "F12", "20261014-091500") == "A1B2C_F12_20261014-091500"


def test_recipe_hash_changes_when_camber_changes():
    a = BladeParams()
    b = BladeParams()
    assert recipe_hash(a) == recipe_hash(b)
    b.stations[0].max_camber = 0.04
    assert recipe_hash(a) != recipe_hash(b)


def test_git_head_looks_like_a_sha():
    h = git_head(Path(__file__).resolve().parents[1])
    assert len(h) >= 7 and all(c in "0123456789abcdef" for c in h.lower()[:7])


def test_readme_puts_the_code_first():
    rep = WatertightReport(
        watertight=True, n_vertices=8, n_faces=12, volume_mm3=1000.0, n_bodies=1,
        bounds_mm=((-50, -50, 0), (50, 50, 20)),
    )
    md = print_readme(
        "x", BladeParams(), "PETG", rep, {"balanced": True, "even_spacing": True,
                                          "normalized_unbalance": 0.0},
        recommend_print_settings("PETG"), None, print_id="A1B2C",
    )
    assert md.splitlines()[0].startswith("# Print sheet")
    assert "A1B2C" in md.splitlines()[0] or "A1B2C" in md.splitlines()[1] or "A1B2C" in "\n".join(md.splitlines()[:6])
    assert "Sharpie" in md
    assert "No glyphs on the part yet" not in md
    assert "recess" in md.lower()
