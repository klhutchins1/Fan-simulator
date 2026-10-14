"""Run the fast pytest suite as N fresh processes (roadmap 23.9).

One long pytest keeps OCCT/VTK RSS. Sequential chunks each start clean; glibc
arenas die with the process. Extra args after ``--`` go to pytest.

    uv run --extra dev python scripts/pytest_chunks.py --chunks 3 --all -- -m "not docker and not slow" -q
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_PYTEST = ["-m", "not docker and not slow", "-q", "--tb=line"]


def collect_test_files(root: Path) -> list[Path]:
    root = Path(root)
    return sorted(p for p in root.rglob("test_*.py") if p.name != "conftest.py")


def chunk_files(files: list[Path], n: int, i: int) -> list[Path]:
    if n < 1:
        raise ValueError("chunks must be >= 1")
    if i < 0 or i >= n:
        return []
    return list(files[i::n])


def _run_chunk(files: list[Path], pytest_args: list[str]) -> int:
    if not files:
        return 0
    cmd = [sys.executable, "-m", "pytest", *[str(p) for p in files], *pytest_args]
    return int(subprocess.run(cmd).returncode)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--chunks", type=int, default=3)
    p.add_argument("--chunk", type=int, default=None, help="0-based index; omit with --all")
    p.add_argument("--all", action="store_true", help="run every chunk in this process, sequentially")
    p.add_argument("--tests", type=Path, default=Path("tests"))
    p.add_argument("--list", action="store_true", help="print file paths and exit")
    args, rest = p.parse_known_args(argv)
    if rest[:1] == ["--"]:
        rest = rest[1:]
    pytest_args = rest or list(DEFAULT_PYTEST)

    files = collect_test_files(args.tests)
    if args.list:
        idxs = range(args.chunks) if args.all or args.chunk is None else [args.chunk]
        for i in idxs:
            for f in chunk_files(files, args.chunks, i):
                print(f)
        return 0

    if args.all:
        rc = 0
        for i in range(args.chunks):
            part = chunk_files(files, args.chunks, i)
            print(f"pytest chunk {i + 1}/{args.chunks} ({len(part)} files)", flush=True)
            rc = _run_chunk(part, pytest_args) or rc
            if rc:
                return rc
        return rc

    if args.chunk is None:
        p.error("pass --chunk K or --all")
    return _run_chunk(chunk_files(files, args.chunks, args.chunk), pytest_args)


if __name__ == "__main__":
    raise SystemExit(main())
