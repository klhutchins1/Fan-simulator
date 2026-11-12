"""Export a clean copy of the repo for a public release, leaving out what RELEASE_EXCLUDE names.

    .venv/Scripts/python.exe scripts/export_release.py --out ../fan-simulator-release

Copies the git-tracked files (no history, no runs/, no caches) minus the excluded prefixes, so the
release never carries third-party data we may not redistribute (THIRD_PARTY.md, roadmap 25.8). Start
the public repo from the exported folder. Tests that need excluded data skip when it is absent.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_FILE = ROOT / "RELEASE_EXCLUDE"
# R3.1: a public export must not name this machine. Match a user-home prefix on any
# drive, or an E: drive prefix, with either kind of slash. A letter immediately
# before the drive letter is not a prefix (a database scheme stays). The pattern is
# built so this source file does not itself contain a literal prefix.
_SLASH = "[/\\\\]"
_NOT_WORD = "(?<![A-Za-z])"
USER_PATH_RE = re.compile(
    "(?i)" + _NOT_WORD + "(?:[A-Za-z]:" + _SLASH + "Users" + _SLASH + "|E:" + _SLASH + ")"
)


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


def leaks_user_path(text: str) -> bool:
    """True when *text* embeds a user-home prefix or an E: drive prefix (R3.1)."""
    return USER_PATH_RE.search(text or "") is not None


def _posix(rel: str) -> str:
    return rel.replace("\\", "/")


def excluded(rel: str, excludes: list[str]) -> bool:
    """True when *rel* matches a RELEASE_EXCLUDE prefix, glob, or path segment."""
    path = _posix(rel)
    name = Path(path).name
    for rule in excludes:
        rule = _posix(rule)
        if "*" in rule:
            if fnmatch.fnmatch(path, rule) or fnmatch.fnmatch(name, rule):
                return True
            continue
        if rule.endswith("/"):
            if path.startswith(rule) or f"/{rule}" in f"/{path}":
                return True
            continue
        if path.startswith(rule) or path == rule:
            return True
    return False


def select(files: list[str], excludes: list[str]) -> list[str]:
    return [f for f in files if not excluded(f, excludes) and not leaks_user_path(f)]


def export(out: Path, *, files: list[str] | None = None, excludes: list[str] | None = None,
           root: Path = ROOT) -> list[str]:
    files = tracked_files(root) if files is None else files
    excludes = read_excludes() if excludes is None else excludes
    kept = select(files, excludes)
    out = Path(out)
    shipped: list[str] = []
    for rel in kept:
        src = root / rel
        if not src.is_file():  # deleted in the working tree but still tracked
            continue
        try:
            sample = src.read_bytes()[: 1_000_000]
        except OSError:
            sample = b""
        try:
            text = sample.decode("utf-8")
        except UnicodeDecodeError:
            text = sample.decode("utf-8", errors="replace")
        if leaks_user_path(text):
            continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        shipped.append(rel)
    return shipped


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
