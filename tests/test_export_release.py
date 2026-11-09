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


def test_r31_exclude_list_covers_hygiene_rules():
    ex = er.read_excludes(ROOT / "RELEASE_EXCLUDE")
    for must in ("archive/", "memory/", "handoff/", "docs/qa/screenshots/", "*.bak"):
        assert must in ex


def test_select_drops_archive_memory_bak_screenshots_and_chat_recovery():
    files = [
        "fansim/x.py",
        "archive/recovery-2026-09/CHAT_RECOVERY/00_README.md",
        "memory/fan-sim-status.md",
        "docs/qa/screenshots/ui.png",
        "notes.bak",
        "fansim/old.bak",
        "docs/CHAT_RECOVERY/dump.md",
    ]
    kept = er.select(files, er.read_excludes(ROOT / "RELEASE_EXCLUDE"))
    assert kept == ["fansim/x.py"]


def test_leaks_user_path_detects_windows_home_and_e_drive():
    assert er.leaks_user_path(r"root = r'C:\Users\Kimball\proj'")
    assert er.leaks_user_path("see E:\\scratch\\fan")
    assert not er.leaks_user_path("the Users folder in the docs")


def test_export_skips_files_that_embed_user_paths(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.py").write_text("print('hi')\n", encoding="utf-8")
    (src / "leak.py").write_text("root = r'C:\\Users\\Kimball\\proj'\n", encoding="utf-8")
    out = tmp_path / "out"
    kept = er.export(out, files=["ok.py", "leak.py"], excludes=[], root=src)
    assert kept == ["ok.py"]
    tree = "\n".join(p.read_text(encoding="utf-8") for p in out.rglob("*") if p.is_file())
    assert "C:\\Users" not in tree


def test_tracked_selection_has_no_hygiene_leaks():
    kept = er.select(er.tracked_files(ROOT), er.read_excludes(ROOT / "RELEASE_EXCLUDE"))
    assert not any(f.startswith("archive/") for f in kept)
    assert not any(f.startswith("memory/") for f in kept)
    assert not any(f.startswith("handoff/") for f in kept)
    assert not any(f.startswith("docs/qa/screenshots/") for f in kept)
    assert not any(f.endswith(".bak") for f in kept)
    assert not any("CHAT_RECOVERY" in f.replace("\\", "/") for f in kept)
