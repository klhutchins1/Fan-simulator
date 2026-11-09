"""23.9: fast-suite file list splits into disjoint chunks that cover every test file."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location(
        "pytest_chunks", ROOT / "scripts" / "pytest_chunks.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_three_chunks_are_disjoint_and_cover_the_tree():
    m = _mod()
    files = m.collect_test_files(ROOT / "tests")
    assert (ROOT / "tests" / "test_mount_gauge.py") in files
    assert (ROOT / "tests" / "conftest.py") not in files
    chunks = [m.chunk_files(files, 3, i) for i in range(3)]
    flat = [p for c in chunks for p in c]
    assert sorted(flat) == files
    assert not (set(chunks[0]) & set(chunks[1]))
    assert all(chunks)


def test_chunk_index_out_of_range_is_empty():
    m = _mod()
    files = [Path("a.py"), Path("b.py")]
    assert m.chunk_files(files, 3, 5) == []


# --- R3.5b: run every chunk, tolerate the OCCT teardown crash, refuse empty / out-of-range chunks ---

import sys
import textwrap

import pytest

FAKE_PYTEST = textwrap.dedent(
    """
    import sys
    from pathlib import Path
    files = [a for a in sys.argv[1:] if a.endswith('.py')]
    rc, summary = 0, ''
    for f in files:
        line = Path(f).read_text().splitlines()[0]   # '# FAKE: <rc> | <summary>'
        r, s = line.split(':', 1)[1].split('|', 1)
        rc, summary = max(rc, int(r)), s.strip()
    print('....')
    print(summary)
    sys.exit(rc)
    """
)


def _fake_tree(tmp_path, specs):
    """One test file per spec (rc, summary); with --chunks len(specs) each chunk gets one file."""
    tests = tmp_path / "tests"
    tests.mkdir()
    for i, (rc, summary) in enumerate(specs):
        (tests / f"test_{i}.py").write_text(f"# FAKE: {rc} | {summary}\n")
    fake = tmp_path / "fake_pytest.py"
    fake.write_text(FAKE_PYTEST)
    return tests, [sys.executable, str(fake)]


def _run(m, monkeypatch, tests, cmd, *argv):
    monkeypatch.setattr(m, "PYTEST_CMD", cmd)
    return m.main(["--tests", str(tests), *argv])


def test_all_runs_every_chunk_after_teardown_crash(tmp_path, monkeypatch, capsys):
    m = _mod()
    tests, cmd = _fake_tree(
        tmp_path,
        [(127, "658 passed, 3 deselected in 120.00s"), (0, "40 passed in 9.0s"), (0, "12 passed in 3.0s")],
    )
    rc = _run(m, monkeypatch, tests, cmd, "--chunks", "3", "--all")
    out = capsys.readouterr().out
    assert rc == 0
    assert "40 passed" in out and "12 passed" in out  # chunks 2 and 3 ran
    assert "passed (teardown exit 127)" in out


def test_all_reports_a_real_failure_but_still_runs_the_rest(tmp_path, monkeypatch, capsys):
    m = _mod()
    tests, cmd = _fake_tree(
        tmp_path,
        [(1, "1 failed, 10 passed in 2.0s"), (0, "5 passed in 1.0s"), (0, "6 passed in 1.0s")],
    )
    rc = _run(m, monkeypatch, tests, cmd, "--chunks", "3", "--all")
    out = capsys.readouterr().out
    assert rc != 0
    assert "6 passed" in out  # the last chunk still ran
    assert "FAILED" in out


def test_teardown_crash_after_failures_is_still_a_failure(tmp_path, monkeypatch):
    m = _mod()
    tests, cmd = _fake_tree(tmp_path, [(127, "2 failed, 600 passed in 100.0s")])
    assert _run(m, monkeypatch, tests, cmd, "--chunks", "1", "--chunk", "0") != 0


def test_teardown_crash_after_errors_is_still_a_failure(tmp_path, monkeypatch):
    m = _mod()
    tests, cmd = _fake_tree(tmp_path, [(127, "600 passed, 1 error in 100.0s")])
    assert _run(m, monkeypatch, tests, cmd, "--chunks", "1", "--chunk", "0") != 0


def test_single_chunk_teardown_crash_counts_as_passed(tmp_path, monkeypatch, capsys):
    m = _mod()
    tests, cmd = _fake_tree(tmp_path, [(139, "658 passed in 120.00s")])  # a crash code the fake can emit
    assert _run(m, monkeypatch, tests, cmd, "--chunks", "1", "--chunk", "0") == 0
    assert "passed (teardown exit 139)" in capsys.readouterr().out


def test_crash_without_a_summary_line_is_a_failure(tmp_path, monkeypatch):
    m = _mod()
    tests, cmd = _fake_tree(tmp_path, [(127, "")])
    assert _run(m, monkeypatch, tests, cmd, "--chunks", "1", "--chunk", "0") != 0


def test_chunk_that_runs_zero_tests_fails(tmp_path, monkeypatch, capsys):
    m = _mod()
    tests, cmd = _fake_tree(tmp_path, [(5, "no tests ran in 0.01s")])
    assert _run(m, monkeypatch, tests, cmd, "--chunks", "1", "--chunk", "0") != 0


def test_chunk_with_no_files_fails(tmp_path, monkeypatch):
    m = _mod()
    tests, cmd = _fake_tree(tmp_path, [(0, "1 passed in 0.1s")])
    # 1 file, 2 chunks: chunk 1 is empty
    assert _run(m, monkeypatch, tests, cmd, "--chunks", "2", "--chunk", "1") != 0


def test_out_of_range_chunk_is_refused(tmp_path, monkeypatch):
    m = _mod()
    tests, cmd = _fake_tree(tmp_path, [(0, "1 passed in 0.1s")] * 3)
    with pytest.raises(SystemExit) as e:
        _run(m, monkeypatch, tests, cmd, "--chunks", "3", "--chunk", "3")
    assert e.value.code == 2


def test_green_chunk_passes(tmp_path, monkeypatch):
    m = _mod()
    tests, cmd = _fake_tree(tmp_path, [(0, "40 passed, 2 skipped in 9.0s")])
    assert _run(m, monkeypatch, tests, cmd, "--chunks", "1", "--chunk", "0") == 0
