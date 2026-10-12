"""Export a clean copy of the repo for a public release, leaving out what RELEASE_EXCLUDE names.

    .venv/Scripts/python.exe scripts/export_release.py --out ../fan-simulator-release

Copies the git-tracked files (no history, no runs/, no caches) minus the excluded prefixes, so the
release never carries third-party data we may not redistribute (THIRD_PARTY.md, roadmap 25.8). Start
the public repo from the exported folder. Tests that need excluded data skip when it is absent.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_FILE = ROOT / "RELEASE_EXCLUDE"


def read_excludes(path: Path = EXCLUDE_FILE) -> list[str]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if entry:
            out.append(entry)
    return out


def tracked_files(root: Path = ROOT) -> list[str]:
    res = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    return [f for f in res.stdout.decode("utf-8").split("\0") if f]


def select(files: list[str], excludes: list[str]) -> list[str]:
    return [f for f in files if not any(f.startswith(e) for e in excludes)]


def export(out: Path, *, files: list[str] | None = None, excludes: list[str] | None = None,
           root: Path = ROOT) -> list[str]:
    files = tracked_files(root) if files is None else files
    excludes = read_excludes() if excludes is None else excludes
    kept = select(files, excludes)
    out = Path(out)
    for rel in kept:
        src = root / rel
        if not src.is_file():  # deleted in the working tree but still tracked
            continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return kept


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists() and any(args.out.iterdir()):
        print(f"{args.out} is not empty; choose a new folder", file=sys.stderr)
        return 2
    files = tracked_files()
    excludes = read_excludes()
    kept = export(args.out, files=files, excludes=excludes)
    print(f"exported {len(kept)} of {len(files)} tracked files to {args.out}; "
          f"left out {len(files) - len(kept)} under {', '.join(excludes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
