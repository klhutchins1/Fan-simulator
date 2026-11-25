"""#58: Expert Optimize/Assess switches get control images."""

from __future__ import annotations

from pathlib import Path

from fansim.cockpit import fan_copy


def test_opt_and_assess_switch_pngs_exist():
    root = Path("docs/control_images")
    required = [
        "opt_resume", "opt_shroud", "opt_stator", "opt_stator_stack",
        "opt_sickle", "opt_stepped", "opt_notched", "opt_bem", "opt_gp",
        "opt_gp_boost", "opt_gp_nn", "opt_search_rpm",
        "assess_refine_op", "assess_wall_ks",
    ]
    missing = [k for k in required if not (root / f"{k}.png").is_file()]
    assert not missing, f"missing control images: {missing}"


def test_loader_includes_opt_and_assess_keys():
    # Reload after PNGs exist (module may have been imported before write in other tests).
    uris = fan_copy._load_control_images()
    assert "opt_shroud" in uris and uris["opt_shroud"].startswith("data:image/png")
    assert "assess_wall_ks" in uris
