"""Like-for-like Assess comparison vs scored Stock (R1.10 G1 / QA-56).

Never compare a scored CFM with a datasheet number in the same sentence.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from fansim.optimize.design import Design

# Recipe knobs that say "this is parametric Stock". Hub/tip can move under frame-fit.
_STOCK_KEYS = (
    "n_blades",
    "stagger_root", "stagger_mid", "stagger_tip",
    "chord_root", "chord_mid", "chord_tip",
    "sweep_mid", "sweep_tip",
    "lean_mid", "lean_tip",
    "max_camber",
)


def _stock_recipe(fan_model: str) -> dict | None:
    try:
        from fansim.optimize.search_space import stock_blade_flat
        return stock_blade_flat(fan_model)
    except (KeyError, FileNotFoundError):
        return None


def is_parametric_stock(params: Mapping | None, fan_model: str) -> bool:
    """True when ``params`` match the parametric Stock recipe for ``fan_model``."""
    recipe = _stock_recipe(fan_model)
    if not recipe or not params:
        return False
    for key in _STOCK_KEYS:
        if key not in recipe:
            continue
        if key not in params:
            return False
        want, got = recipe[key], params[key]
        if key == "n_blades":
            if int(round(float(got))) != int(round(float(want))):
                return False
        elif abs(float(got) - float(want)) > 1e-4:
            return False
    return True


def same_test(a: Mapping | None, b: Mapping | None) -> bool:
    """True when two scored extras used the same hose / material / roughness / refine."""
    a = a or {}
    b = b or {}
    if str(a.get("fan_model") or "a12x25") != str(b.get("fan_model") or "a12x25"):
        return False
    if str(a.get("preset") or "") != str(b.get("preset") or ""):
        return False
    try:
        if abs(float(a.get("load_pa") or 0.0) - float(b.get("load_pa") or 0.0)) > 1e-6:
            return False
    except (TypeError, ValueError):
        return False
    if bool(a.get("refine_op")) != bool(b.get("refine_op")):
        return False
    if str(a.get("material") or "") != str(b.get("material") or ""):
        return False
    a_ks = float(a.get("wall_ks_mm") or 0.0) > 0.0
    b_ks = float(b.get("wall_ks_mm") or 0.0) > 0.0
    return a_ks == b_ks


def _scored_stock(designs: Iterable[Design], extra: Mapping) -> Design | None:
    extra = extra or {}
    fan_model = str(extra.get("fan_model") or "a12x25")
    found: Design | None = None
    for d in designs:
        if d is None or not d.feasible:
            continue
        ex = d.extra or {}
        if ex.get("is_reference"):
            continue
        if ex.get("cfd_stale"):
            continue
        if not same_test(ex, extra):
            continue
        if not is_parametric_stock(d.params, fan_model):
            continue
        cfm = float((d.objectives or {}).get("cfm_free") or 0.0)
        if cfm <= 0.0:
            continue
        if found is None or int(d.trial) >= int(found.trial):
            found = d
    return found


def vs_stock_same_test_line(
    cfm_free: float,
    extra: Mapping | None,
    designs: Iterable[Design],
) -> str:
    """One line vs scored Stock at the same test settings, or '' if none.

    Format: ``vs Stock (same test): +X % free air``.
    """
    stock = _scored_stock(designs, extra or {})
    if stock is None:
        return ""
    base = float((stock.objectives or {}).get("cfm_free") or 0.0)
    if base <= 0.0:
        return ""
    pct = 100.0 * (float(cfm_free) - base) / base
    return f"vs Stock (same test): {pct:+.0f} % free air"
