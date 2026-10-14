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
