"""Small helpers for stamping/replaying trial parameter dicts.

Import-light: used by cockpit/test helpers without pulling in geometry/CAD dependencies.
"""

from __future__ import annotations


def with_shroud_attr(trial) -> dict:
    """``trial.params`` plus stamped attrs needed to rebuild (shroud, sickle).

    ``--shroud`` stamps ring thickness after sampling; ``--sickle`` may put ``sickle_mm``
    in params when searched, but user attrs are the durable source when replaying.
    """
    flat = dict(trial.params)
    flat.setdefault(
        "shroud_thick_mm", float(trial.user_attrs.get("shroud_thick_mm", 0.0) or 0.0)
    )
    flat.setdefault("sickle_mm", float(trial.user_attrs.get("sickle_mm", 0.0) or 0.0))
    return flat
