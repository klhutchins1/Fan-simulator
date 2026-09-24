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
    _listen_sqlite_pragmas(storage, timeout_s=timeout_s)
    return storage


def _listen_sqlite_pragmas(storage: RDBStorage, *, timeout_s: float) -> None:
    """WAL plus synchronous=NORMAL on every Optuna connection.

    The default SQLite mode flushes the whole database on each trial commit. A fast
    BEMT study then pegs the project disk. NORMAL still checkpoints the WAL; it does
    not fsync every trial.
    """
    from sqlalchemy import event

    busy_ms = int(float(timeout_s) * 1000)

    def _on_connect(dbapi_connection, _record):
        cur = dbapi_connection.cursor()
        try:
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute(f"PRAGMA busy_timeout={busy_ms}")
        finally:
            cur.close()

    event.listen(storage.engine, "connect", _on_connect)
    storage.engine.dispose()
