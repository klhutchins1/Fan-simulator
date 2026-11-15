"""Run the fast pytest suite as N fresh processes (roadmap 23.9).

One long pytest keeps OCCT/VTK RSS. Sequential chunks each start clean; glibc
arenas die with the process. Extra args after ``--`` go to pytest.

    uv run --extra dev python scripts/pytest_chunks.py --chunks 3 --all -- -m "not docker and not slow" -q
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_PYTEST = ["-m", "not docker and not slow", "-q", "--tb=line"]
PYTEST_CMD = [sys.executable, "-m", "pytest"]


def collect_test_files(root: Path) -> list[Path]:
    root = Path(root)
    return sorted(p for p in root.rglob("test_*.py") if p.name != "conftest.py")


def chunk_files(files: list[Path], n: int, i: int) -> list[Path]:
    if n < 1:
        raise ValueError("chunks must be >= 1")
    if i < 0 or i >= n:
        return []
    return list(files[i::n])


_SUMMARY = re.compile(r"\b(?:\d+ \w+(?:, )?)+.* in [\d.]+s\b|\bno tests ran\b")
_COUNT = re.compile(r"(\d+) (passed|failed|errors?|xpassed)\b")


def _parse_summary(line: str) -> dict[str, int] | None:
    """Counts from pytest's final summary line, or None if the line is not one."""
    if not _SUMMARY.search(line):
        return None
    counts = {"passed": 0, "failed": 0, "error": 0}
    for n, word in _COUNT.findall(line):
        key = "error" if word.startswith("error") else ("passed" if word == "xpassed" else word)
        counts[key] += int(n)
    return counts


def judge(rc: int, summary: str | None) -> tuple[bool, str]:
    """(ok, verdict) for one chunk.

    A chunk passes only if pytest's summary shows >= 1 passed and no failures or errors.
    A non-zero exit after such a summary is the known OCCT/VTK teardown crash
    (docs/validation/suite_baseline_2026-09-14.md): reported, not counted as a failure.
    """
    counts = _parse_summary(summary) if summary else None
    if counts is None:
        return False, f"FAILED (no pytest summary line, exit {rc})"
    if counts["failed"] or counts["error"]:
        return False, f"FAILED ({summary.strip()})"
    if counts["passed"] == 0:
        return False, f"FAILED (0 tests ran: {summary.strip()})"
    if rc != 0:
        return True, f"passed (teardown exit {rc}): {summary.strip()}"
    return True, f"passed: {summary.strip()}"


def _run_chunk(files: list[Path], pytest_args: list[str]) -> tuple[bool, str]:
    if not files:
        return False, "FAILED (chunk has no test files)"
    cmd = [*PYTEST_CMD, *[str(p) for p in files], *pytest_args]
    summary = None
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", bufsize=1)
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        if _parse_summary(line) is not None:
            summary = line.strip().strip("=").strip()
    sys.stdout.flush()
    return judge(int(proc.wait()), summary)


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
    if args.chunks < 1:
        p.error("--chunks must be >= 1")
    if args.chunk is not None and not 0 <= args.chunk < args.chunks:
        p.error(f"--chunk {args.chunk} is out of range: indexes are 0..{args.chunks - 1} (0-based)")

    files = collect_test_files(args.tests)
    if args.list:
        idxs = range(args.chunks) if args.all or args.chunk is None else [args.chunk]
        for i in idxs:
            for f in chunk_files(files, args.chunks, i):
                print(f)
        return 0

    if args.all:
        idxs = list(range(args.chunks))
    elif args.chunk is None:
        p.error("pass --chunk K or --all")
    else:
        idxs = [args.chunk]

    results = []
    for i in idxs:
        part = chunk_files(files, args.chunks, i)
        print(f"pytest chunk {i}/{args.chunks} (0-based; {len(part)} files)", flush=True)
        results.append((i, *_run_chunk(part, pytest_args)))
    print(flush=True)
    for i, ok, verdict in results:
        print(f"chunk {i}: {verdict}")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
