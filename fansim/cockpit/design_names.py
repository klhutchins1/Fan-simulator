"""Stable short names for fan designs in Results: ``F12 · 9 blades, tubercles · Assess Sep 30``.

Internal trial numbers (9000+ for Assess, 20000+ blocks for saved Optimize runs, raw Optuna numbers
for the opened study) and run-folder names meant nothing to a reader. Each design now gets a short
ID that is assigned once and saved in ``runs/design_names.json``, so it survives restarts and
re-keying; the trial number stays the internal value (clicks, files) and moves to hover detail.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

REGISTRY_FILE = "design_names.json"
PREFIX = "F"


def design_key(d, opened_run: str = "") -> str:
    """Identity that does not change when the cockpit re-keys trial ids."""
    extra = getattr(d, "extra", None) or {}
    trial = int(extra.get("orig_trial", d.trial))
    run = str(extra.get("source_run") or opened_run)
    if extra.get("source") == "cockpit_opt":
        return f"opt:{run}:{trial}"
    if int(d.trial) >= 9000:
        return f"assess:{run}:{trial}"
    return f"study:{opened_run}:{trial}"


def origin_word(d) -> str:
    extra = getattr(d, "extra", None) or {}
    if extra.get("is_reference"):
        return "Reference"
    if extra.get("bem_screen"):
        return "BEM screen"
    if extra.get("source") == "cockpit_opt" or int(d.trial) < 9000:
        return "Optimizer"
    return "Assess"


def short_date(completed: str) -> str:
    """``2026-09-30 14:22`` -> ``Sep 30``; '' when unknown."""
    try:
        dt = datetime.strptime(str(completed)[:10], "%Y-%m-%d")
    except ValueError:
        return ""
    return f"{dt:%b} {dt.day}"


_FEATURES = (
    ("tubercle_amp", "tubercles"),
    ("serration_amp", "serrations"),
    ("dimple_amp", "dimples"),
    ("winglet_sweep", "winglets"),
    ("spacing_spread", "uneven spacing"),
    ("tip_notch_count", "notched tips"),
    ("shroud_height_frac", "shroud"),
)


def shape_summary(params: dict | None) -> str:
    """Blade count plus the special features that are switched on."""
    p = params or {}
    bits = []
    try:
        bits.append(f"{int(round(float(p['n_blades'])))} blades")
    except (KeyError, TypeError, ValueError):
        pass
    for key, word in _FEATURES:
        try:
            if float(p.get(key) or 0.0) > 0.0:
                bits.append(word)
        except (TypeError, ValueError):
            continue
    return ", ".join(bits) or "custom"


def _load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data.get("names"), dict):
            return data
    except (OSError, ValueError, AttributeError):
        pass
    return {"next": 1, "names": {}}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def assign_display_names(designs, registry: Path, opened_run: str = "") -> None:
    """Stamp ``extra['display_name']`` on every design; new ones get the next ``F<n>``.

    New designs are numbered oldest-first (by ``completed``), so the first run over an existing
    collection gives the oldest work the lowest numbers.
    """
    data = _load(registry)
    names: dict = data["names"]
    fresh = []
    for d in designs:
        if (getattr(d, "extra", None) or {}).get("is_reference"):
            continue
        key = design_key(d, opened_run)
        if key in names:
            d.extra["display_name"] = names[key]
        else:
            fresh.append((str(d.extra.get("completed") or ""), key, d))
    if not fresh:
        return
    for _, key, d in sorted(fresh, key=lambda t: (t[0], t[1])):
        if key not in names:
            names[key] = f"{PREFIX}{int(data['next'])}"
            data["next"] = int(data["next"]) + 1
        d.extra["display_name"] = names[key]
    try:
        _save(registry, data)
    except OSError:
        pass  # names still show this session; they are re-assigned identically next time


def dropdown_title(d, *, tag: str = "") -> str:
    """``F12 ✪ · 9 blades, tubercles · Assess Sep 30 · free 50.2 · load 41.4 · η 19.7``.

    Old-solver (stale) scores do not show their numbers: they are not comparable to current ones.
    """
    extra = d.extra or {}
    name = extra.get("display_name") or f"#{d.trial}"
    where = " ".join(b for b in (origin_word(d), short_date(extra.get("completed", ""))) if b)
    head = f"{name}{tag} · {shape_summary(d.params)} · {where}"
    if extra.get("cfd_stale"):
        if extra.get("bem_screen"):  # QA-bot BEM shortlist: never had CFD (runs/bem_screen_*)
            return f"⧗ {head} · needs Assess (BEM estimate only)"
        return f"⧗ {head} · needs re-run (old solver)"
    bits = [head]
    for key, lab in (("cfm_free", "free"), ("cfm_load", "load"), ("efficiency", "η")):
        v = (d.objectives or {}).get(key)
        if isinstance(v, (int, float)) and v > -1e5:
            bits.append(f"{lab} {v:.1f}")
    return " · ".join(bits)
