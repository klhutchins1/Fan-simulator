"""R1.10 G2 / QA-55 / R0.4 / R1.6: noise copy is not a validated ranking."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_UI_COPY = (
    ROOT / "fansim" / "cockpit" / "fan_tab_ui.py",
    ROOT / "fansim" / "cockpit" / "fan_copy.py",
    ROOT / "fansim" / "cockpit" / "data.py",
    ROOT / "fansim" / "cockpit" / "figures.py",
    ROOT / "fansim" / "manufacturability" / "print_export.py",
)

_OK_MARKERS = ("published", "relative", "measured", "estimate", "not validated")


def test_readme_says_noise_outputs_are_not_validated():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "tone + relative ranking are usable" not in text
    assert "Noise outputs are not validated" in text
    assert "blade-pass tone" in text
    assert "estimates for exploration only" in text


def test_optimize_caption_does_not_promise_absolute_db():
    src = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    assert "absolute dB" not in src
    assert "Noise ranking is not validated" in src or "not validated" in src


def test_ui_model_outputs_have_no_bare_dba():
    """R1.6: model-output dB(A)/dBA in cockpit copy must say published, relative, measured, or estimate."""
    bad: list[str] = []
    for path in _UI_COPY:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "dB(A)" not in line and "dBA" not in line:
                continue
            low = line.lower()
            if any(m in low for m in _OK_MARKERS):
                continue
            if "label=" in low and "noise" in low:
                continue  # user-measured Noise dB(A) field
            bad.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not bad, "bare dB(A)/dBA on model output:\n" + "\n".join(bad)


def test_print_sheet_labels_noise_swl_as_estimate():
    from fansim.geometry.blade import BladeParams
    from fansim.geometry.export import WatertightReport
    from fansim.manufacturability.print_export import print_readme, recommend_print_settings

    rep = WatertightReport(
        watertight=True, n_vertices=8, n_faces=12, volume_mm3=1000.0, n_bodies=1,
        bounds_mm=((-50, -50, 0), (50, 50, 20)),
    )
    md = print_readme(
        "t", BladeParams(), "PETG", rep,
        {"balanced": True, "even_spacing": True, "normalized_unbalance": 0.0},
        recommend_print_settings("PETG"), None,
        {"cfm_free": 50.0, "noise_swl": 44.2},
    )
    assert "noise_swl 44.2" not in md
    assert "not dB(A)" in md
    assert "not validated" in md
    assert "44.2" in md
