"""The public-release export leaves out everything RELEASE_EXCLUDE names (roadmap 25.8)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("export_release", ROOT / "scripts" / "export_release.py")
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)


def test_reads_prefixes_and_ignores_comments(tmp_path):
    f = tmp_path / "RELEASE_EXCLUDE"
    f.write_text("# header\na/b/   # why\n\nc/\n", encoding="utf-8")
    assert er.read_excludes(f) == ["a/b/", "c/"]


def test_selects_tracked_files_minus_excluded():
    files = ["fansim/x.py", "validation/reference/drone_radial/obj_1.stl",
             "docs/qa/benchmarks/nv150/curve.csv", "docs/qa/benchmarks/lt120/curve.csv", "handoff/a.md"]
    kept = er.select(files, ["validation/reference/drone_radial/", "docs/qa/benchmarks/nv150/", "handoff/"])
    assert kept == ["fansim/x.py", "docs/qa/benchmarks/lt120/curve.csv"]


def test_repo_exclude_list_covers_the_known_problem_data():
    ex = er.read_excludes(ROOT / "RELEASE_EXCLUDE")
    for must in ("validation/reference/drone_radial/", "docs/qa/benchmarks/nv150/", "handoff/"):
        assert must in ex


def test_export_writes_only_kept_files(tmp_path):
    out = tmp_path / "rel"
    er.export(out, files=["README.md", "handoff/x.md"], excludes=["handoff/"], root=ROOT)
    assert (out / "README.md").is_file() and not (out / "handoff").exists()
