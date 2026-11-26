"""Library list copy. Keep Trame/app.py free of recipe-title formatting."""

from __future__ import annotations

from dataclasses import dataclass

from fansim.catalog import CatalogEntry
from fansim.cockpit.labels import run_label
from fansim.cockpit.placement import fit_envelope, measure_flat, nominal_fits_spec, scale_to_hub
from fansim.fan_spec import FanSpec

HINT_FITS = "fits this hub"
HINT_BIG = "too big — use Scale to this hub"
HINT_NONE = "no geometry yet"
NO_PARAMS_MSG = "This recipe has no blade numbers to Fit."


def empty_library_info(n: int) -> str:
    """Library header copy. ``n`` is the number of clickable recipe rows."""
    if n <= 0:
        return (
            "No saved designs yet — Assess a blade or run Optimize; scored runs show up here."
        )
    return (
        f"{n} saved design(s) — click a row to load it. "
        "Scale to this hub shrinks a design that is too big."
    )


@dataclass(frozen=True)
class LibraryApply:
    ok: bool
    message: str
    flat: dict | None
    parent_id: str
    place_op: str
    fit_status: str
    leftover: str


def apply_library_recipe(flat: dict, spec: FanSpec, op: str, parent_id: str) -> LibraryApply:
    p = flat or {}
    if "hub_radius" not in p or "tip_radius" not in p:
        return LibraryApply(False, NO_PARAMS_MSG, None, parent_id, op, "unplaced", "")
    if op == "scale_to_hub":
        result = scale_to_hub(p, spec)
    elif op == "fit_envelope":
        result = fit_envelope(p, spec)
    else:
        raise ValueError(f"unknown place op {op!r}")
    if result.fit_status == "unplaced":
        return LibraryApply(False, result.leftover, None, parent_id, op, result.fit_status, result.leftover)
    return LibraryApply(
        ok=True,
        message=result.leftover or "",
        flat=result.flat,
        parent_id=parent_id,
        place_op=op,
        fit_status=result.fit_status,
        leftover=result.leftover,
    )


def fit_hint(entry: CatalogEntry, spec: FanSpec) -> str:
    p = entry.params or {}
    if "hub_radius" not in p or "tip_radius" not in p:
        return HINT_NONE
    measured = measure_flat(p)
    if measured is None:
        return HINT_NONE
    try:
        if nominal_fits_spec(p, spec, measured):
            return HINT_FITS
    except Exception:  # noqa: BLE001
        return HINT_NONE
    return HINT_BIG


def library_list_items(entries: list, spec: FanSpec) -> list[dict]:
    items: list[dict] = []
    last_run = object()
    for e in entries or []:
        run = e.run or ""
        if run != last_run:
            title_grp = run_label(run) or run or "Ungrouped"
            # Issue #99: do not repeat the raw folder slug when no friendly label exists.
            caption = "" if title_grp == run else run
            items.append({"role": "group", "title": title_grp, "caption": caption, "run": run})
            last_run = run
        p = e.params or {}
        try:
            n = int(p.get("n_blades") or e.n_blades or 0)
        except (TypeError, ValueError):
            n = 0
        try:
            hub_d = round(2.0 * float(p["hub_radius"])) if "hub_radius" in p else None
            tip_d = round(2.0 * float(p["tip_radius"])) if "tip_radius" in p else None
        except (TypeError, ValueError):
            hub_d = tip_d = None
        if n and hub_d is not None and tip_d is not None:
            title = f"{n} blades · hub {hub_d} mm · tip {tip_d} mm"
        elif n:
            title = f"{n} blades"
        else:
            title = e.design_id
        hint = fit_hint(e, spec)
        free = f"{e.cfm_free:.0f}" if isinstance(e.cfm_free, (int, float)) else "?"
        subtitle = f"{free} CFM at original size · {hint}"
        items.append({
            "role": "row",
            "value": e.design_id,
            "title": title,
            "subtitle": subtitle,
            "clickable": hint != HINT_NONE,
            "fits": hint == HINT_FITS,
        })
    return items


def filter_library_items(
    items: list[dict],
    query: str = "",
    fits_only: bool = False,
) -> list[dict]:
    """Filter grouped library items by search text and optional 'fits this hub' toggle (#99)."""
    q = (query or "").strip().lower()
    out: list[dict] = []
    pending_group: dict | None = None
    group_haystack = ""
    for it in items or []:
        role = it.get("role")
        if role == "group":
            pending_group = it
            group_haystack = (
                f"{it.get('title', '')} {it.get('caption', '')} {it.get('run', '')}"
            ).lower()
            continue
        if role != "row":
            continue
        if fits_only and not it.get("fits"):
            continue
        if q:
            row_haystack = (
                f"{it.get('title', '')} {it.get('subtitle', '')} {it.get('value', '')} "
                f"{group_haystack}"
            ).lower()
            if q not in row_haystack:
                continue
        if pending_group is not None:
            out.append(pending_group)
            pending_group = None
        out.append(it)
    return out
