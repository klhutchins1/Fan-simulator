"""The public-release export leaves out everything RELEASE_EXCLUDE names (roadmap 25.8)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("export_release", ROOT / "scripts" / "export_release.py")
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)


def _machine(letter: str, slash: str, tail: str = "") -> str:
    """Build a drive prefix at runtime so this file does not contain one literally."""
    return letter + ":" + slash + tail


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
    assert er.leaks_user_path("root = r'" + _machine("C", "\\", "Users\\Kimball\\proj") + "'")
    assert er.leaks_user_path("see " + _machine("E", "\\", "scratch\\fan"))
    assert not er.leaks_user_path("the Users folder in the docs")


def test_export_skips_files_that_embed_user_paths(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.py").write_text("print('hi')\n", encoding="utf-8")
    leak = "root = r'" + _machine("C", "\\", "Users\\Kimball\\proj") + "'\n"
    (src / "leak.py").write_text(leak, encoding="utf-8")
    out = tmp_path / "out"
    kept = er.export(out, files=["ok.py", "leak.py"], excludes=[], root=src)
    assert kept == ["ok.py"]
    tree = "\n".join(p.read_text(encoding="utf-8") for p in out.rglob("*") if p.is_file())
    assert _machine("C", "\\", "Users") not in tree


def test_tracked_selection_has_no_hygiene_leaks():
    kept = er.select(er.tracked_files(ROOT), er.read_excludes(ROOT / "RELEASE_EXCLUDE"))
    assert not any(f.startswith("archive/") for f in kept)
    assert not any(f.startswith("memory/") for f in kept)
    assert not any(f.startswith("handoff/") for f in kept)
    assert not any(f.startswith("docs/qa/screenshots/") for f in kept)
    assert not any(f.endswith(".bak") for f in kept)
    assert not any("CHAT_RECOVERY" in f.replace("\\", "/") for f in kept)


def test_leaks_user_path_detects_forward_slashes():
    assert er.leaks_user_path("root = '" + _machine("C", "/", "Users/Kimball/proj") + "'")
    assert er.leaks_user_path("see " + _machine("E", "/", "scratch/fan"))
    assert not er.leaks_user_path("the Users folder in the docs")


def test_select_drops_tracked_paths_with_a_user_machine_prefix():
    files = [
        "ok.py",
        "notes/" + _machine("C", "/", "Users/Kimball/a.txt"),
        "notes/" + _machine("E", "/", "scratch/b.txt"),
        "notes\\" + _machine("C", "\\", "Users\\Kimball\\c.txt"),
        "notes\\" + _machine("E", "\\", "scratch\\d.txt"),
    ]
    assert er.select(files, []) == ["ok.py"]


def test_export_grep_is_empty_for_forward_slash_user_paths(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.py").write_text("print('hi')\n", encoding="utf-8")
    (src / "home.py").write_text(
        "root = '" + _machine("C", "/", "Users/Kimball/proj") + "'\n", encoding="utf-8"
    )
    (src / "drive.py").write_text(
        "see " + _machine("E", "/", "scratch/fan") + "\n", encoding="utf-8"
    )
    out = tmp_path / "out"
    kept = er.export(out, files=["ok.py", "home.py", "drive.py"], excludes=[], root=src)
    assert kept == ["ok.py"]
    blob = "\n".join(p.read_text(encoding="utf-8") for p in out.rglob("*") if p.is_file())
    assert _machine("C", "/", "Users") not in blob
    assert _machine("C", "\\", "Users") not in blob
    assert _machine("E", "/") not in blob
    assert _machine("E", "\\") not in blob


# R3.9 ruling: these stay tracked in git and are left out of the public export.
NAMED_LARGE = (
    "validation/reference/fan01/fan01_rotor.stl",
    "validation/reference/fan01/cad_model.zip",
    "validation/reference/a12x25_impeller.stl",
)


def test_export_omits_named_large_files_and_keeps_them_in_git(tmp_path):
    tracked = er.tracked_files(ROOT)
    fan01_stl = [
        f for f in tracked
        if f.startswith("validation/reference/fan01/") and f.lower().endswith(".stl")
    ]
    assert fan01_stl == ["validation/reference/fan01/fan01_rotor.stl"]
    stay = [
        "validation/reference/fan01/characteristic.csv",
        "validation/reference/fan01/characteristic.zip",
        "validation/reference/fan01/README.md",
    ]
    for path in (*NAMED_LARGE, *stay):
        assert path in tracked
    out = tmp_path / "rel"
    kept = er.export(
        out,
        files=[*NAMED_LARGE, *stay, "README.md"],
        excludes=er.read_excludes(ROOT / "RELEASE_EXCLUDE"),
        root=ROOT,
    )
    for path in NAMED_LARGE:
        assert path not in kept
        assert not (out / path).exists()
    for path in (*stay, "README.md"):
        assert path in kept
        assert (out / path).is_file()


def test_export_ships_the_exporter_and_exclude_list(tmp_path):
    out = tmp_path / "rel"
    kept = er.export(
        out,
        files=["scripts/export_release.py", "RELEASE_EXCLUDE"],
        excludes=[],
        root=ROOT,
    )
    assert kept == ["scripts/export_release.py", "RELEASE_EXCLUDE"]
    blob = "\n".join((out / rel).read_text(encoding="utf-8") for rel in kept)
    assert not er.leaks_user_path(blob)


def test_sqlite_url_is_not_a_user_machine_path():
    assert not er.leaks_user_path('storage = f"sqlite:///{db.as_posix()}"')
    assert not er.leaks_user_path("scheme sqlite:///study.db")


def test_msys_default_is_not_a_user_machine_prefix():
    text = (ROOT / "fansim" / "external_tools.py").read_text(encoding="utf-8")
    assert not er.leaks_user_path(text)


def test_export_test_module_does_not_embed_a_user_machine_path():
    text = (ROOT / "tests" / "test_export_release.py").read_text(encoding="utf-8")
    assert not er.leaks_user_path(text)


# These product docs must ship. Machine paths in them are redacted, not a reason to drop the file.
MUST_SHIP_DOCS = (
    "docs/QA_REVIEW.md",
    "docs/roadmap.md",
    "docs/fluidx3d-setup.md",
    "docs/release/RELEASE_PLAN.md",
)


def test_export_ships_product_docs_without_machine_prefixes(tmp_path):
    out = tmp_path / "rel"
    kept = er.export(
        out,
        files=list(MUST_SHIP_DOCS),
        excludes=er.read_excludes(ROOT / "RELEASE_EXCLUDE"),
        root=ROOT,
    )
    assert kept == list(MUST_SHIP_DOCS)
    for rel in MUST_SHIP_DOCS:
        text = (out / rel).read_text(encoding="utf-8")
        assert not er.leaks_user_path(text), rel
