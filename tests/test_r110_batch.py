"""R1.10 batch: G5 honesty labels, R1.2 P–Q display, R1.5 flutter, R1.9 QA-39–42/45, QA-57."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

FLUTTER = "estimate, not validated (resonance check, not flutter)"
PROP_CFD = (
    "not a performance predictor: thrust reads 40–60 % low in validation; "
    "use it for direction and flow pictures only"
)
PROP_BEMT = (
    "±15 % on thrust at static; worse toward zero-thrust J; "
    "validated on a known-section prop (TU Delft) within 7 %"
)
PRINT_LOSS = "an assumed 5 % print loss, not yet measured"
SCREEN_MESH = "screening mesh: compare designs, not absolute airflow; Stock reads about 5 % low"
VOLUTE_RANK = "ranking only, unvalidated (CFD not yet converged)"
HUB_TOO_SMALL = "hub radius too small"


def test_g5_stock_gap_is_on_stock_info_lines():
    src = (ROOT / "fansim" / "cockpit" / "fan_trials.py").read_text(encoding="utf-8")
    block = src.split("Stock reference —", 1)[1].split("state.preview_msg", 1)[0]
    assert "STOCK_RECIPE_GAP" in block


def test_g5_and_r15_flutter_copy():
    figures = (ROOT / "fansim" / "cockpit" / "figures.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    ui = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    assert "cheap safety gate" not in figures
    assert FLUTTER in figures
    assert FLUTTER in readme
    assert FLUTTER in ui
    assert "Blade vibration (flutter) is a **warning**" not in readme


def test_g5_prop_honesty():
    from fansim.propeller.honesty import PROP_BEMT_HONESTY, PROP_CFD_HONESTY

    assert PROP_CFD in PROP_CFD_HONESTY
    assert "35-45" not in PROP_CFD_HONESTY
    assert PROP_BEMT in PROP_BEMT_HONESTY
    src = (ROOT / "fansim" / "cockpit" / "prop_tab.py").read_text(encoding="utf-8")
    assert "PROP_CFD_HONESTY" in src or PROP_CFD in src
    assert "PROP_BEMT_HONESTY" in src or PROP_BEMT in src
    assert "~35-45 % low" not in src


def test_g5_print_knockdown_and_export_sheet():
    copy = (ROOT / "fansim" / "cockpit" / "fan_copy.py").read_text(encoding="utf-8")
    assert "printed-part honesty" not in copy
    assert PRINT_LOSS in copy
    from fansim.cockpit.score_caption import score_caption

    text = score_caption({"print_k_cfm": 0.95, "print_k_eta": 0.92})
    assert PRINT_LOSS in text
    from fansim.geometry.blade import BladeParams
    from fansim.geometry.export import WatertightReport
    from fansim.manufacturability.print_export import print_readme, recommend_print_settings

    md = print_readme(
        "t", BladeParams(), "PETG",
        WatertightReport(
            watertight=True, n_vertices=8, n_faces=12, volume_mm3=1000.0, n_bodies=1,
            bounds_mm=((-50, -50, 0), (50, 50, 20)),
        ),
        {"balanced": True, "even_spacing": True, "normalized_unbalance": 0.0},
        recommend_print_settings("PETG"), None, {"cfm_free": 50.0},
    )
    assert SCREEN_MESH in md


def test_g5_historical_banners():
    adv = (ROOT / "docs" / "adversarial-review.md").read_text(encoding="utf-8")
    assert "historical, 2026-09; see docs/VALIDATION.md" in adv
    pq = (ROOT / "docs" / "validation" / "a12x25_pq_report.md").read_text(encoding="utf-8")
    assert "+22–29%" in pq or "+22-29%" in pq
    line = next(ln for ln in pq.splitlines() if "22–29" in ln or "22-29" in ln)
    assert "superseded" in line.lower()


def test_r12_pq_display_stops_at_last_converged():
    from fansim.validation.pq_shutoff import pq_rows_for_display

    rows = [
        {"back_pa": 0.0, "cfm": 59.8, "converged": True},
        {"back_pa": 5.0, "cfm": 52.5, "converged": True},
        {"back_pa": 10.0, "cfm": 41.0, "converged": True},
        {"back_pa": 15.0, "cfm": 26.8, "converged": False},
        {"back_pa": 20.0, "cfm": 2.2, "converged": False},
    ]
    shown = pq_rows_for_display(rows)
    assert [r["back_pa"] for r in shown] == [0.0, 5.0, 10.0]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "20–21 Pa" not in readme and "20-21 Pa" not in readme
    plot = (ROOT / "scripts" / "run_a12x25_validation.py").read_text(encoding="utf-8")
    assert "pq_rows_for_display" in plot


def test_qa39_pp_file_sorts_time_dirs_numerically(tmp_path):
    from fansim.cfd.metrics import _pp_file
    from fansim.cfd.timing import read_fo_time_column

    fo = tmp_path / "postProcessing" / "outletFlow"
    for name, body in (("999", "0  old\n"), ("1000", "0  new\n")):
        d = fo / name
        d.mkdir(parents=True)
        (d / "surfaceFieldValue.dat").write_text("#\n" + body, encoding="utf-8")
    path = _pp_file(tmp_path, "outletFlow", "surfaceFieldValue.dat")
    assert path.parent.name == "1000"
    times = read_fo_time_column(tmp_path)
    assert times == pytest.approx([0.0])
    assert path.read_text(encoding="utf-8").endswith("new\n")
    obj = (ROOT / "fansim" / "optimize" / "objectives.py").read_text(encoding="utf-8")
    assert "latest_pp_file" in obj or "_pp_file" in obj.split("FREE_HISTORY_DIR", 1)[1]


def test_qa40_noise_without_stock_is_expert_only():
    from fansim.cfd.flow_report import FlowMetrics
    from fansim.cfd.flow_verdicts import judge

    stock = FlowMetrics(0.06, False, [2.0, 4.0, 6.0, 8.0, 6.0], 0.20, 0.05, 0.80, 60.0, 2.5,
                        mean_dp0_pa=6.0)
    rows = judge(stock, None)
    noise = next(r for r in rows if r.key == "noise")
    assert noise.expert_only
    assert "No Stock comparison for noise" in noise.text


def test_qa41_zombie_proc_state_is_gone():
    from fansim.isolated_job import proc_state_is_zombie

    assert proc_state_is_zombie("1234 (python 3) Z 1 1 1")
    assert not proc_state_is_zombie("1234 (python 3) R 1 1 1")
    src = (ROOT / "fansim" / "isolated_job.py").read_text(encoding="utf-8")
    assert "proc_state_is_zombie" in src
    assert "os.kill" in src


def test_qa42_preview_weight_names_material_and_infill():
    src = (ROOT / "fansim" / "cockpit" / "fan_assess.py").read_text(encoding="utf-8")
    assert "infill" in src.split("def spec_status", 1)[1].split("def _blocking_eval", 1)[0]
    assert "{spec.material}" in src or "spec.material" in src.split("✓ fits", 1)[1][:200]


def test_qa45_undersized_hub_says_hub_radius_too_small():
    src = (ROOT / "fansim" / "manufacturability" / "print_export.py").read_text(encoding="utf-8")
    assert HUB_TOO_SMALL in src
    carve = src.split("def _carve_with_mount", 1)[1]
    carve = carve.split("\ndef ", 1)[0]
    assert "if params.hub_radius < need" in carve
    assert HUB_TOO_SMALL in carve
    assert 'return cq.Workplane(obj=hub), False, "hub radius too small"' in carve


def test_qa57_volute_assess_is_labelled_unvalidated():
    src = (ROOT / "fansim" / "cockpit" / "volute_tab.py").read_text(encoding="utf-8")
    assess_lines = [
        ln for ln in src.splitlines()
        if "Assess runs radial MRF" in ln or "Assess: free+load CFD" in ln
    ]
    assert assess_lines
    assert "Volute CFD: ranking only, unvalidated (CFD not yet converged)." in src
    i = src.index("Assess runs radial MRF")
    assert VOLUTE_RANK in src[i:i + 220]
