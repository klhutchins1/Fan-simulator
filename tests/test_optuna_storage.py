"""Optuna SQLite storage concurrency helpers."""

from __future__ import annotations

from pathlib import Path

from fansim.optimize.storage import make_sqlite_storage, study_db_path


def test_make_sqlite_storage_creates_db(tmp_path: Path):
    storage = make_sqlite_storage(tmp_path, timeout_s=5.0)
    assert study_db_path(tmp_path).is_file()
    import optuna

    study = optuna.create_study(study_name="t", storage=storage, load_if_exists=True)
    study.optimize(lambda t: 1.0, n_trials=1)
    names = optuna.get_all_study_names(storage=storage)
    assert "t" in names
    with storage.engine.connect() as conn:
        journal = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
        sync = conn.exec_driver_sql("PRAGMA synchronous").scalar()
    assert str(journal).lower() == "wal"
    assert int(sync) == 1  # NORMAL
