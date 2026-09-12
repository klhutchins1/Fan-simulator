"""Tests for shared isolated-subprocess job runner (§9.5 leftover)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fansim.isolated_job import run_worker_module


def test_run_worker_module_success(tmp_path, monkeypatch):
    marker = tmp_path / "out.txt"

    def fake_run(argv, capture_output, text, timeout):
        job = Path(argv[-1])
        data = json.loads(job.read_text(encoding="utf-8"))
        Path(data["out"]).write_text("ok", encoding="utf-8")

        class Proc:
            returncode = 0
            stderr = ""
            stdout = ""

        return Proc()

    monkeypatch.setattr("fansim.isolated_job.subprocess.run", fake_run)
    proc = run_worker_module(
        "fansim.geometry._build_worker",
        {"out": str(marker)},
        timeout=30.0,
        label="test build",
        require_paths=[marker],
    )
    assert proc.returncode == 0
    assert marker.read_text(encoding="utf-8") == "ok"


def test_run_worker_module_timeout(monkeypatch):
    import subprocess

    def boom(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="x", timeout=0.01)

    monkeypatch.setattr("fansim.isolated_job.subprocess.run", boom)
    with pytest.raises(TimeoutError, match="test build exceeded"):
        run_worker_module(
            "fansim.geometry._build_worker",
            {"out": "x"},
            timeout=0.01,
            label="test build",
        )


def test_run_worker_module_nonzero(monkeypatch, tmp_path):
    def fake_run(*_a, **_k):
        class Proc:
            returncode = 1
            stderr = "native boom"
            stdout = ""

        return Proc()

    monkeypatch.setattr("fansim.isolated_job.subprocess.run", fake_run)
    with pytest.raises(RuntimeError, match="test build failed"):
        run_worker_module(
            "fansim.geometry._build_worker",
            {"out": str(tmp_path / "missing.stl")},
            timeout=30.0,
            label="test build",
            require_paths=[tmp_path / "missing.stl"],
        )
