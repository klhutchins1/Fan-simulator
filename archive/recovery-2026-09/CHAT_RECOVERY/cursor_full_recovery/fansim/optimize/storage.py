"""Optuna SQLite storage helpers — avoid ``database is locked`` under cockpit + Optimize."""

from __future__ import annotations

from pathlib import Path

import optuna
from optuna.storages import RDBStorage


def study_db_path(out_dir: str | Path) -> Path:
    return Path(out_dir) / "study.db"


def make_sqlite_storage(out_dir: str | Path, *, timeout_s: float = 120.0) -> RDBStorage:
    """SQLite-backed Optuna storage with a busy timeout and WAL when possible.

    Cockpit polls ``study.db`` every ~5 s while Optimize writes the same file. Without a
    timeout, readers raise ``sqlite3.OperationalError: database is locked``.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    db = study_db_path(out_dir)
    url = f"sqlite:///{db.resolve().as_posix()}"
    storage = RDBStorage(
        url=url,
        engine_kwargs={"connect_args": {"timeout": float(timeout_s), "check_same_thread": False}},
    )
    # Best-effort WAL: concurrent reader (cockpit) + writer (Optimize) on Windows.
    try:
        import sqlite3

        con = sqlite3.connect(str(db), timeout=float(timeout_s))
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA busy_timeout=%d" % int(float(timeout_s) * 1000))
            con.commit()
        finally:
            con.close()
    except Exception:  # noqa: BLE001 — storage still usable without WAL
        pass
    return storage
