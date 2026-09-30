"""Engine-agnostic airflow-viz helper shared by the archetype tabs (roadmap §17.3 / §17.4).

The Fan tab's Results panel renders off-screen views of a solved OpenFOAM case — |U| and
pressure midplane slices, the axial-Uz cut-plane, magnitude streamlines, plus spanwise
averages and blade-to-blade Cp (§20.3). Any archetype whose Assess leaves a reconstructable
case (Mixed/centrifugal, Volute, CROR-refine) can reuse the midplane renderers; this module
holds the pure, UI-free pieces so each tab wires identical behavior instead of copy-pasting
fan_viz. Midplane / streamlines live in ``fansim.cfd.midplane``; spanwise in
``fansim.cfd.spanwise``.
"""

from __future__ import annotations

import base64
from pathlib import Path

from fansim.cfd.midplane import (
    ensure_axial_uz_artifact,
    ensure_midplane_artifacts,
    ensure_streamlines_artifact,
)
from fansim.cfd.spanwise import ensure_spanwise_artifacts

# Field key -> caption shown under the image. Keys match the VBtnToggle values.
AIRFLOW_CAPTIONS = {
    "U": "Umag midplane — FRONT LEFT -> OUTLET RIGHT",
    "p": "pressure midplane — FRONT LEFT -> OUTLET RIGHT",
    "uz": "axial Uz cut-plane — blue = delivery (+Z), red = reverse (−Z)",
    "stream": "streamlines colored by |U| — inlet (−Z) → wake (+Z)",
    "span": "spanwise averages — p0 / Uz / swirl / incidence vs radius",
    "b2b": "blade-to-blade Cp — 3–5 span stations",
}
AIRFLOW_CAPTIONS_SCROLL = {
    "U": "Umag scroll section — OUTLET RIGHT (+X), INLET UP (+Z)",
    "p": "pressure scroll section — OUTLET RIGHT (+X), INLET UP (+Z)",
}
AIRFLOW_FIELDS = ("U", "p", "uz", "stream", "span", "b2b")
AIRFLOW_FIELDS_SCROLL = ("U", "p")


def png_data_uri(path) -> str:
    """Base64 ``data:`` URI for a PNG path, or ``""`` if missing/unreadable."""
    if path is None or not Path(path).is_file():
        return ""
    try:
        return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()
    except Exception:  # noqa: BLE001
        return ""


def render_airflow_pack(case_dir, *, runner_factory=None, image_ok=None, layout: str = "axial") -> dict:
    """Render airflow views for a solved case dir. Returns per-field data URIs.

    ``layout="axial"`` (default): |U|/p midplane + axial Uz + streamlines.
    ``layout="scroll"``: |U|/p scroll section only (volute 90° machine — no axial-Uz).

    Fail-soft: a missing case / no fields / Docker down / render error yields empty URIs and
    ``available=False`` (never raises).
    """
    case_dir = Path(case_dir) if case_dir is not None else None
    mid = ensure_midplane_artifacts(
        case_dir, runner_factory=runner_factory, image_ok=image_ok, layout=layout,
    )
    if layout == "scroll":
        uris = {
            "U": png_data_uri(mid.u_png) if mid.available else "",
            "p": png_data_uri(mid.p_png) if mid.available else "",
            "uz": "",
            "stream": "",
            "span": "",
            "b2b": "",
        }
        return {"uris": uris, "available": any(uris.values()), "layout": "scroll"}

    uz = ensure_axial_uz_artifact(case_dir, runner_factory=runner_factory, image_ok=image_ok)
    stream = ensure_streamlines_artifact(case_dir, runner_factory=runner_factory, image_ok=image_ok)
    span = ensure_spanwise_artifacts(case_dir, runner_factory=runner_factory, image_ok=image_ok)
    uris = {
        "U": png_data_uri(mid.u_png) if mid.available else "",
        "p": png_data_uri(mid.p_png) if mid.available else "",
        "uz": png_data_uri(uz.png) if uz is not None and uz.available else "",
        "stream": png_data_uri(stream.png) if stream is not None and stream.available else "",
        "span": png_data_uri(span.spanwise_png) if span is not None and span.available else "",
        "b2b": png_data_uri(span.b2b_png) if span is not None and span.available else "",
    }
    return {"uris": uris, "available": any(uris.values()), "layout": "axial"}


def pick_airflow_uri(uris: dict, field: str, *, layout: str = "axial") -> tuple[str, str]:
    """(uri, caption) for the chosen field; fall back to |U| then pressure if it is unavailable."""
    captions = AIRFLOW_CAPTIONS_SCROLL if layout == "scroll" else AIRFLOW_CAPTIONS
    uri = uris.get(field, "") if uris else ""
    shown = field
    if not uri and uris:
        if uris.get("U"):
            uri, shown = uris["U"], "U"
        elif uris.get("p"):
            uri, shown = uris["p"], "p"
    return uri, (captions.get(shown, "") if uri else "")
