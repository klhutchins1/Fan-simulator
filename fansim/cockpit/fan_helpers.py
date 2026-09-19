"""Pure Fan cockpit helpers (no Trame/PyVista).

Extracted from `fansim.cockpit.app` as part of cockpit tab-split (Approach B).
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Iterable
from pathlib import Path

from fansim.cockpit.data import Design
from fansim.optimize.search_space import OBJECTIVE_NAMES

_log = logging.getLogger(__name__)


def append_user_designs(
    lock: threading.Lock,
    user_designs: list[Design],
    by_trial: dict[int, Design],
    designs: Design | Iterable[Design],
) -> int:
    """Append Assess/Optimize designs under lock (§9.11 poll_merge vs async UI)."""
    batch = [designs] if isinstance(designs, Design) else list(designs)
    with lock:
        for d in batch:
            user_designs.append(d)
            by_trial[int(d.trial)] = d
    return len(batch)


def upsert_by_trial(
    lock: threading.Lock,
    by_trial: dict[int, Design],
    design: Design,
) -> None:
    """Replace a by_trial entry under the same designs lock."""
    with lock:
        by_trial[int(design.trial)] = design


def _has_real_cfm(d: Design) -> bool:
    """False for infeasible Optuna sentinels (cfm_free = -1e6) that wreck plot axes."""
    try:
        return float(d.objectives.get(OBJECTIVE_NAMES[0], -1e9)) > -1e5
    except (TypeError, ValueError):
        return False


def _blade_z_extent(params) -> float:
    """Axial impeller envelope (blades + hub + nose + shroud) — FAST, no CAD solid."""
    from fansim.cockpit.placement import impeller_z_extent

    return impeller_z_extent(params)


def _blade_max_dia(params) -> float:
    """Max impeller DIAMETER (mm) from section points + optional tip ring (same as placement).

    Uses ``params.features`` so tip-fit / snap match Preview/Assess featured geometry.
    """
    from fansim.cockpit.placement import blade_max_dia

    return blade_max_dia(params)


def _depth_drivers(flat: dict, top: int = 3) -> list[tuple[str, float]]:
    """For THIS design, how much each slider would cut the blade's Z-depth -- ranked.

    Features off (they barely affect depth) so it's fast. Returns [(label, mm_saved), ...] biggest first.
    """
    from fansim.geometry.features import Features
    from fansim.optimize.search_space import blade_from_flat

    base = _blade_z_extent(blade_from_flat(flat, Features()))
    tests = [
        ("Sweep tip", "sweep_tip", -4.0),
        ("Sweep mid", "sweep_mid", -4.0),
        ("Mid stagger/pitch", "stagger_mid", -6.0),
        ("Tip stagger/pitch", "stagger_tip", -6.0),
        ("Root stagger/pitch", "stagger_root", -6.0),
        ("Mid chord", "chord_mid", -6.0),
        ("Tip chord", "chord_tip", -6.0),
        ("Root chord", "chord_root", -6.0),
        ("LE curve tip", "le_sweep_tip", 0.0),
        ("LE curve mid", "le_sweep_mid", 0.0),
        ("Wrap tip", "lean_tip", -10.0),
        ("Wrap mid", "lean_mid", -10.0),
        ("Tip radius / length", "tip_radius", -5.0),
    ]
    out: list[tuple[str, float]] = []
    for label, key, delta in tests:
        f = dict(flat)
        f[key] = 0.0 if delta == 0.0 else f.get(key, 0.0) + delta
        try:
            saved = base - _blade_z_extent(blade_from_flat(f, Features()))
        except Exception:  # noqa: BLE001
            continue
        if saved > 0.3:
            out.append((label, saved))
    f = dict(flat)
    for k in ("thickness_root", "thickness_mid", "thickness_tip"):
        f[k] = max(0.03, f.get(k, 0.08) - 0.02)
    try:
        saved = base - _blade_z_extent(blade_from_flat(f, Features()))
        if saved > 0.3:
            out.append(("Thinner blades", saved))
    except Exception:  # noqa: BLE001
        pass
    # Hub contributions to TOTAL depth (the hub, not just the blades, can be the binding element).
    nose = float(flat.get("hub_nose", 0.0))
    if nose > 0.3 and str(flat.get("hub_profile", "cylinder")).lower() != "cylinder":
        out.append(("Hub nose (set profile to cylinder / 0 nose)", nose))
    hh = float(flat.get("hub_height", 0.0))
    if hh > 0.0:  # explicit hub taller than the auto (root-covering) minimum adds depth
        try:
            from fansim.geometry.blade import _root_axial_span

            p = blade_from_flat(flat, Features())
            r_lo, r_hi = _root_axial_span(p)
            auto_h = (r_hi - r_lo) + 2.0 * p.hub_axial_margin
            if hh - auto_h > 0.3:
                out.append(("Hub height above auto (set Hub height to 0)", hh - auto_h))
        except Exception:  # noqa: BLE001
            pass
    out.sort(key=lambda t: -t[1])
    return out[:top]


def _load_assessed_designs(assess_dirs) -> list[Design]:
    """Reload designs the user assessed in earlier cockpit sessions (persisted as design.json).

    Accepts a single dir or an iterable of cockpit_assess dirs so a design assessed under ANY run
    shows up regardless of which --run is currently open (user designs are the user's own work, not
    tied to one optimizer run). Trial ids that collide across runs are re-keyed to a fresh id (the
    original is kept in extra['orig_trial']); each design records its source run in extra['source_run'].
    """
    if isinstance(assess_dirs, (str, Path)):
        assess_dirs = [Path(assess_dirs)]
    out: list[Design] = []
    used: set[int] = set()

    def _fresh() -> int:
        i = 9000
        while i in used:
            i += 1
        used.add(i)
        return i

    for assess_dir in assess_dirs:
        assess_dir = Path(assess_dir)
        if not assess_dir.exists():
            continue
        run_name = assess_dir.parent.name
        for jf in sorted(assess_dir.glob("design_*/design.json")):
            try:
                d = json.loads(jf.read_text())
                stl = jf.parent / "impeller.stl"
                orig = int(d["trial"])
                if orig in used:
                    tid = _fresh()
                else:
                    tid = orig
                    used.add(tid)
                extra = dict(d.get("extra", {}))
                extra.setdefault("source_run", run_name)
                from fansim.cockpit.data import cfd_is_stale
                extra["cfd_stale"] = cfd_is_stale(extra.get("cfd_version"))
                if tid != orig:
                    extra["orig_trial"] = orig
                out.append(
                    Design(
                        trial=tid,
                        params=d.get("params", {}),
                        objectives=d["objectives"],
                        feasible=d.get("feasible", True),
                        is_pareto=False,
                        stl_path=stl if stl.exists() else None,
                        reason=d.get("reason", ""),
                        extra=extra,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - skip a corrupt/partial assess dir
                _log.warning(
                    "skip corrupt assess design.json %s: %s: %s",
                    jf, type(exc).__name__, exc)
                continue
    return out
