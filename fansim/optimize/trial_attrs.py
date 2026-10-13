"""Small helpers for stamping/replaying trial parameter dicts.

Import-light: used by cockpit/test helpers without pulling in geometry/CAD dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone

# Commit 37728b9 (2026-09-30 11:42:08 -0600) changed station ``chord`` from the loft chord to the
# measured cylinder-cut chord. Anything saved before it holds loft chords ("loft"); newer
# optimizer trials stamp ``chord_basis`` explicitly. Used only to classify unstamped records.
CHORD_BASIS_CUTOFF = datetime(2026, 9, 30, 17, 42, 8, tzinfo=timezone.utc)


def chord_basis_at(when: datetime | None) -> str:
    """Chord basis implied by a record's creation time (unknown time = legacy "loft")."""
    if when is None:
        return "loft"
    if when.tzinfo is None:   # optuna stores naive local times
        when = when.astimezone(timezone.utc)
    return "measured" if when >= CHORD_BASIS_CUTOFF else "loft"


def chord_basis_for_trial(trial) -> str:
    """The trial's stamped ``chord_basis`` attr, else inferred from when it started."""
    stamped = (getattr(trial, "user_attrs", None) or {}).get("chord_basis")
    if stamped:
        return str(stamped)
    return chord_basis_at(getattr(trial, "datetime_start", None))


def section_wrap_for_trial(trial) -> str:
    """The trial's stamped ``section_wrap``; unstamped trials predate wrapped sections (27.4)."""
    stamped = (getattr(trial, "user_attrs", None) or {}).get("section_wrap")
    return str(stamped) if stamped else "planar"


def trial_flat(trial) -> dict:
    """``trial.params`` plus ``chord_basis`` / ``section_wrap`` — the flat dict to rebuild it."""
    flat = dict(trial.params)
    flat.setdefault("chord_basis", chord_basis_for_trial(trial))
    flat.setdefault("section_wrap", section_wrap_for_trial(trial))
    return flat


def with_shroud_attr(trial) -> dict:
    """``trial.params`` plus stamped attrs needed to rebuild (shroud, sickle).

    ``--shroud`` stamps ring thickness after sampling; ``--sickle`` may put ``sickle_mm``
    in params when searched, but user attrs are the durable source when replaying.
    """
    flat = trial_flat(trial)
    flat.setdefault(
        "shroud_thick_mm", float(trial.user_attrs.get("shroud_thick_mm", 0.0) or 0.0)
    )
    flat.setdefault("sickle_mm", float(trial.user_attrs.get("sickle_mm", 0.0) or 0.0))
    return flat
