"""Engine-agnostic airflow-viz helper shared by the archetype tabs (roadmap §17.3 / §17.4).

The Fan tab's Results panel renders four off-screen views of a solved OpenFOAM case — |U| and
pressure midplane slices, the axial-Uz cut-plane, and magnitude streamlines. Any archetype whose
Assess leaves a reconstructable case (Mixed/centrifugal, Volute, CROR-refine) can reuse the same
renderers; this module holds the pure, UI-free pieces so each tab wires identical behavior instead
of copy-pasting fan_viz. The renderers themselves live in ``fansim.cfd.midplane``.
"""

from __future__ import annotations

import base64
from pathlib import Path

from fansim.cfd.midplane import (
    ensure_axial_uz_artifact,
    ensure_midplane_artifacts,
    ensure_streamlines_artifact,
)

# Field key -> caption shown under the image. Keys match the VBtnToggle values.
AIRFLOW_CAPTIONS = {
    "U": "Umag midplane — FRONT LEFT -> OUTLET RIGHT",
    "p": "pressure midplane — FRONT LEFT -> OUTLET RIGHT",
    "uz": "axial Uz cut-plane — blue = delivery (+Z), red = reverse (−Z)",
    "stream": "streamlines colored by |U| — inlet (−Z) → wake (+Z)",
}
AIRFLOW_FIELDS = ("U", "p", "uz", "stream")


def png_data_uri(path) -> str:
    """Base64 ``data:`` URI for a PNG path, or ``""`` if missing/unreadable."""
    if path is None or not Path(path).is_file():
        return ""
    try:
        return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()
    except Exception:  # noqa: BLE001
        return ""


def render_airflow_pack(case_dir, *, runner_factory=None, image_ok=None) -> dict:
    """Render all four airflow views for a solved case dir. Returns per-field data URIs.

    Fail-soft: a missing case / no fields / Docker down / render error yields empty URIs and
    ``available=False`` (never raises). The midplane reconstruct is shared, so the Uz and
    streamline passes only add a slice + a trace.
    """
    case_dir = Path(case_dir) if case_dir is not None else None
    mid = ensure_midplane_artifacts(case_dir, runner_factory=runner_factory, image_ok=image_ok)
    uz = ensure_axial_uz_artifact(case_dir, runner_factory=runner_factory, image_ok=image_ok)
    stream = ensure_streamlines_artifact(case_dir, runner_factory=runner_factory, image_ok=image_ok)
    uris = {
        "U": png_data_uri(mid.u_png) if mid.available else "",
        "p": png_data_uri(mid.p_png) if mid.available else "",
        "uz": png_data_uri(uz.png) if uz is not None and uz.available else "",
        "stream": png_data_uri(stream.png) if stream is not None and stream.available else "",
    }
    return {"uris": uris, "available": any(uris.values())}


def pick_airflow_uri(uris: dict, field: str) -> tuple[str, str]:
    """(uri, caption) for the chosen field; fall back to |U| then pressure if it is unavailable."""
    uri = uris.get(field, "") if uris else ""
    shown = field
    if not uri and uris:
        if uris.get("U"):
            uri, shown = uris["U"], "U"
        elif uris.get("p"):
            uri, shown = uris["p"], "p"
    return uri, (AIRFLOW_CAPTIONS.get(shown, "") if uri else "")
