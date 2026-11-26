"""Fan-tab library binder: load catalog/library recipes into the editor (§13.9).

Loads a catalog design or a parametric library recipe (fit-to-envelope or scale-to-hub) into
the editor and previews it. Cross-domain: seeds the editor (``session._init_editor`` /
``_set_baseline``), previews (``session.do_preview``), and exposes ``_depth_driver_msg`` used
by the assess spec-status caption.
"""

from __future__ import annotations

import logging

from fansim.catalog import get_entry
from fansim.cockpit.errors import log_caught
from fansim.cockpit.fan_helpers import _depth_drivers
from fansim.cockpit.library_view import apply_library_recipe
from fansim.fan_spec import mount_min_hub_radius
from fansim.optimize.search_space import blade_from_flat

_log = logging.getLogger(__name__)


def bind(session) -> None:
    state = session.state

    def load_catalog_design(design_id=None, **_):
        if not design_id:
            return
        e = get_entry(design_id)
        if e is None:
            msg = f"'{design_id}' was not found in the saved designs list — restart the cockpit after adding a new run."
            state.catalog_info = msg
            state.library_msg = msg
            state.flush()
            return
        state.library_parent_id = ""
        state.library_place_op = ""
        state.library_leftover = ""
        session._init_editor(e.params)
        session._set_baseline()
        parts = [f"Loaded {e.design_id}", f"{e.source}"]
        if isinstance(e.cfm_free, (int, float)):
            parts.append(
                f"sim {e.cfm_free:.0f}/{e.cfm_load or 0:.0f} CFM  eff {e.efficiency or 0:.0f}%"
            )
        if e.dp_op_pa is not None:
            parts.append(f"op {e.dp_op_pa:.1f} Pa @ {e.q_ref_cfm or 50:.0f} CFM")
        try:
            from fansim.manufacturability.printability_score import grade_printability

            lp = blade_from_flat(e.params)
            need = mount_min_hub_radius(session.active_spec())
            parts.append("mountable" if (need is None or lp.hub_radius >= need) else "NOT mountable")
            parts.append(f"print {grade_printability(lp).difficulty:.0f}/100")
        except Exception as exc:  # noqa: BLE001 - catalog caption is best-effort
            log_caught(_log, "catalog printability caption", exc, level=logging.DEBUG)
        if e.has_measurement and e.measured_cfm is not None:
            parts.append(
                f"MEASURED {e.measured_cfm:.0f} CFM (sim {e.cfm_error_pct:+.0f}%)"
                if e.cfm_error_pct is not None
                else f"MEASURED {e.measured_cfm:.0f} CFM"
            )
        state.catalog_info = "  ·  ".join(parts)
        state.library_msg = f"Loaded {e.design_id} into Design. Press Preview to see it."
        state.preview_msg = (
            f"Loaded {e.design_id} from the catalog. Press Preview to see it."
        )
        state.flush()

    def _apply_library_to_editor(design_id: str, op: str):
        if not state.fan_model:
            state.library_msg = "Select a fan model first."
            state.preview_msg = state.library_msg
            state.flush()
            return
        if not design_id:
            state.library_msg = "Click a saved design row below first."
            state.preview_msg = state.library_msg
            state.flush()
            return
        e = get_entry(design_id)
        if e is None:
            msg = f"'{design_id}' was not found in the saved designs list — restart the cockpit after adding a new run."
            state.library_msg = msg
            state.preview_msg = msg
            state.flush()
            return
        rec = apply_library_recipe(e.params or {}, session.active_spec(), op=op, parent_id=design_id)
        state.library_sel = design_id
        state.library_parent_id = rec.parent_id
        state.library_place_op = rec.place_op
        state.library_leftover = rec.leftover or rec.message
        if not rec.ok or rec.flat is None:
            state.library_msg = rec.message or rec.leftover
            state.preview_msg = state.library_msg
            state.flush()
            return
        state.library_msg = f"Loaded {design_id} into Design ({op.replace('_', ' ')})."
        session._init_editor(rec.flat)
        session._set_baseline()
        session.do_preview()
        state.flush()

    def select_library_design(design_id=None, **_):
        if not design_id:
            return
        _apply_library_to_editor(design_id, "fit_envelope")

    def on_library_scale_to_hub():
        if getattr(state, "preview_busy", False) or getattr(state, "assess_busy", False):
            return
        _apply_library_to_editor(state.library_sel, "scale_to_hub")

    def _depth_driver_msg(flat):
        try:
            drivers = _depth_drivers(flat)
        except Exception:  # noqa: BLE001
            return ""
        if not drivers:
            return ""
        return "  Top depth drivers here: " + ", ".join(
            f"{lab} (~{mm:.0f} mm)" for lab, mm in drivers
        )

    session.load_catalog_design = load_catalog_design
    session.select_library_design = select_library_design
    session.on_library_scale_to_hub = on_library_scale_to_hub
    session._depth_driver_msg = _depth_driver_msg
