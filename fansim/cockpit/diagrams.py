"""Small self-contained inline SVG diagrams for cockpit parameter tooltips & visual guides.

Zero external dependencies: pure SVG encoded as data URIs so they work offline in any browser
and render crisply inside Vuetify tooltips and light cards alike.
"""

from __future__ import annotations

import base64

_SVG_HEADER = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 116" width="320" height="116">'
    '<rect x="1" y="1" width="318" height="114" rx="8" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5"/>'
    '<style>'
    'text{font-family:system-ui,-apple-system,sans-serif;fill:#1e293b}'
    '.t{font-size:11px;font-weight:700}'
    '.s{font-size:9.5px;fill:#475569}'
    '.b{stroke:#2563eb;stroke-width:3;stroke-linecap:round;fill:none}'
    '.a{stroke:#0284c7;stroke-width:1.6;fill:none;marker-end:url(#arr)}'
    '</style>'
    '<defs>'
    '<marker id="arr" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
    '<path d="M 0 1 L 10 5 L 0 9 z" fill="#0284c7"/>'
    '</marker>'
    '</defs>'
)

_SVGS: dict[str, str] = {
    "blade_pitch": (
        _SVG_HEADER
        + '<text x="12" y="18" class="t">Blade angle (pitch)</text>'
        + '<line x1="160" y1="24" x2="160" y2="106" stroke="#e2e8f0" stroke-width="1"/>'
        # Low angle (flatter)
        + '<text x="16" y="35" class="s">Low angle (flatter)</text>'
        + '<line x1="30" y1="68" x2="128" y2="68" stroke="#94a3b8" stroke-dasharray="3,3"/>'
        + '<path d="M 38 76 Q 80 58 122 60" class="b"/>'
        + '<path d="M 80 42 L 80 55" class="a"/>'
        + '<text x="16" y="96" class="s">More overlap · higher pressure</text>'
        # High angle (steeper)
        + '<text x="172" y="35" class="s">High angle (steeper)</text>'
        + '<line x1="186" y1="68" x2="284" y2="68" stroke="#94a3b8" stroke-dasharray="3,3"/>'
        + '<path d="M 206 86 Q 236 66 266 44" class="b"/>'
        + '<path d="M 272 46 L 272 82" class="a"/>'
        + '<text x="172" y="96" class="s">Bigger bite · more open airflow</text>'
        + '</svg>'
    ),
    "blade_sweep": (
        _SVG_HEADER
        + '<text x="12" y="18" class="t">Blade sweep &amp; wrap (3-D curve)</text>'
        + '<line x1="160" y1="24" x2="160" y2="106" stroke="#e2e8f0" stroke-width="1"/>'
        # Straight
        + '<text x="16" y="35" class="s">Zero sweep (straight)</text>'
        + '<rect x="52" y="44" width="16" height="44" rx="4" fill="#cbd5e1" stroke="#64748b"/>'
        + '<path d="M 68 54 L 130 54 L 130 78 L 68 78 Z" fill="#bfdbfe" stroke="#2563eb" stroke-width="1.8"/>'
        + '<text x="16" y="102" class="s">Radial paddle · shortest depth</text>'
        # Swept / curved
        + '<text x="172" y="35" class="s">Forward sweep / wrap</text>'
        + '<rect x="192" y="44" width="16" height="44" rx="4" fill="#cbd5e1" stroke="#64748b"/>'
        + '<path d="M 208 56 Q 248 56 286 42 L 296 64 Q 252 78 208 78 Z" fill="#93c5fd" stroke="#2563eb" stroke-width="1.8"/>'
        + '<path d="M 254 84 L 288 76" class="a"/>'
        + '<text x="172" y="102" class="s">Curved tip · smooths airflow</text>'
        + '</svg>'
    ),
    "hub_ratio": (
        _SVG_HEADER
        + '<text x="12" y="18" class="t">Hub size vs airflow ring (hub ratio)</text>'
        # Fan circle on left
        + '<circle cx="82" cy="67" r="40" fill="#dbeafe" stroke="#2563eb" stroke-width="2"/>'
        + '<circle cx="82" cy="67" r="16" fill="#94a3b8" stroke="#334155" stroke-width="1.8"/>'
        + '<line x1="82" y1="67" x2="98" y2="67" stroke="#0f172a" stroke-width="1.5"/>'
        + '<line x1="82" y1="67" x2="82" y2="27" stroke="#1d4ed8" stroke-width="1.5"/>'
        + '<text x="69" y="70" style="font-size:8.5px;fill:#fff;font-weight:700">Hub</text>'
        + '<text x="86" y="44" style="font-size:8.5px;fill:#1d4ed8;font-weight:700">Tip R</text>'
        # Explanation on right
        + '<text x="142" y="44" class="t">Blue ring = airflow area</text>'
        + '<text x="142" y="61" class="s">• Smaller hub → bigger ring → more CFM</text>'
        + '<text x="142" y="76" class="s">• Hub must still clear the motor barrel</text>'
        + '<text x="142" y="91" class="s">• Outer tip must fit inside frame bore</text>'
        + '</svg>'
    ),
    "static_pressure": (
        _SVG_HEADER
        + '<text x="12" y="18" class="t">Static pressure (airflow resistance)</text>'
        # Case
        + '<rect x="14" y="30" width="90" height="72" rx="6" fill="#ecfdf5" stroke="#10b981" stroke-width="1.4"/>'
        + '<text x="24" y="46" class="t">Case · 8 Pa</text>'
        + '<path d="M 24 62 L 90 62" class="a"/>'
        + '<path d="M 24 72 L 90 72" class="a"/>'
        + '<text x="24" y="92" class="s">Open airflow</text>'
        # Heatsink
        + '<rect x="115" y="30" width="90" height="72" rx="6" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.4"/>'
        + '<text x="123" y="46" class="t">Heatsink · 20 Pa</text>'
        + '<line x1="168" y1="53" x2="168" y2="79" stroke="#64748b" stroke-width="2" stroke-dasharray="4,3"/>'
        + '<path d="M 124 66 L 192 66" class="a"/>'
        + '<text x="123" y="92" class="s">Fin restriction</text>'
        # Radiator
        + '<rect x="216" y="30" width="90" height="72" rx="6" fill="#fef3c7" stroke="#f59e0b" stroke-width="1.4"/>'
        + '<text x="223" y="46" class="t">Radiator · 35 Pa</text>'
        + '<line x1="264" y1="53" x2="264" y2="79" stroke="#92400e" stroke-width="2.5" stroke-dasharray="2,2"/>'
        + '<line x1="272" y1="53" x2="272" y2="79" stroke="#92400e" stroke-width="2.5" stroke-dasharray="2,2"/>'
        + '<path d="M 224 66 L 292 66" class="a"/>'
        + '<text x="223" y="92" class="s">Tight fins / high Pa</text>'
        + '</svg>'
    ),
    "blade_scoop": (
        _SVG_HEADER
        + '<text x="12" y="18" class="t">Blade scoop (camber)</text>'
        + '<line x1="160" y1="24" x2="160" y2="106" stroke="#e2e8f0" stroke-width="1"/>'
        # Flat
        + '<text x="16" y="35" class="s">0.00 = flat paddle</text>'
        + '<line x1="34" y1="66" x2="128" y2="66" class="b"/>'
        + '<text x="16" y="96" class="s">Less lift · simpler cross-section</text>'
        # Scooped
        + '<text x="172" y="35" class="s">0.06–0.12 = scooped face</text>'
        + '<line x1="190" y1="74" x2="288" y2="74" stroke="#94a3b8" stroke-dasharray="3,3"/>'
        + '<path d="M 190 74 Q 238 40 288 74" class="b"/>'
        + '<path d="M 239 74 L 239 58" class="a"/>'
        + '<text x="172" y="96" class="s">Curves air · stronger push</text>'
        + '</svg>'
    ),
}

DIAGRAM_KEYS: tuple[str, ...] = tuple(_SVGS.keys())

_URI_CACHE: dict[str, str] = {
    k: "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
    for k, svg in _SVGS.items()
}

# Controls that benefit from an explanatory SVG diagram when no rendered PNG exists.
CONTROL_DIAGRAM: dict[str, str] = {
    "assess_preset": "static_pressure",
    "volute_load_pa": "static_pressure",
    "p_pitch": "blade_pitch",
    "mf_stagger": "blade_pitch",
    "mf_stagger_root": "blade_pitch",
    "mf_stagger_tip": "blade_pitch",
    "cror_f_stagger": "blade_pitch",
    "cror_r_stagger": "blade_pitch",
    "p_sweep_mid": "blade_sweep",
    "p_sweep_tip": "blade_sweep",
    "p_lean_mid": "blade_sweep",
    "p_lean_tip": "blade_sweep",
    "cror_f_sweep_mid": "blade_sweep",
    "cror_f_sweep_tip": "blade_sweep",
    "cror_r_sweep_mid": "blade_sweep",
    "cror_r_sweep_tip": "blade_sweep",
    "p_camber_root": "blade_scoop",
    "p_camber_mid": "blade_scoop",
    "p_camber_tip": "blade_scoop",
    "mf_camber": "blade_scoop",
    "cror_f_camber_mid": "blade_scoop",
    "cror_r_camber_mid": "blade_scoop",
    "mf_r_eye": "hub_ratio",
    "mf_r_back": "hub_ratio",
    "mf_r_tip": "hub_ratio",
    "volute_r_hub": "hub_ratio",
    "volute_r_tip": "hub_ratio",
    "cror_hub_r": "hub_ratio",
    "cror_tip_r": "hub_ratio",
}


def diagram_svg(name: str) -> str:
    """Raw SVG markup for ``name``, or '' if unknown."""
    return _SVGS.get(name, "")


def diagram_data_uri(name: str) -> str:
    """Base64 SVG data URI for ``name``, or '' if unknown."""
    return _URI_CACHE.get(name, "")


def diagram_for_control(model: str) -> str:
    """Return an explanatory SVG data URI for ``model``, or '' if none mapped."""
    key = CONTROL_DIAGRAM.get(model)
    return _URI_CACHE.get(key, "") if key else ""


def visual_guide_cards() -> list[dict[str, str]]:
    """Four key visual-guide cards for the Home accuracy/guide panel & Fan Geometry help."""
    return [
        {
            "key": "blade_pitch",
            "title": "Blade angle (pitch)",
            "caption": "Flatter angles overlap for pressure; steeper angles move more open air.",
            "src": diagram_data_uri("blade_pitch"),
        },
        {
            "key": "blade_sweep",
            "title": "Sweep & wrap",
            "caption": "Curving the blade tip smooths flow and changes total fan depth.",
            "src": diagram_data_uri("blade_sweep"),
        },
        {
            "key": "hub_ratio",
            "title": "Hub size vs airflow ring",
            "caption": "Smaller hub opens more airflow area, while still clearing the motor.",
            "src": diagram_data_uri("hub_ratio"),
        },
        {
            "key": "static_pressure",
            "title": "Static pressure (resistance)",
            "caption": "Case (8 Pa) is open; heatsink (20 Pa) and radiator (35 Pa) push back harder.",
            "src": diagram_data_uri("static_pressure"),
        },
    ]
