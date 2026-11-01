"""Drive the repo's own tooltip generator (scripts/generate_control_images.py) WITHOUT editing it.

Imports the module, swaps its CONTROLS list and OUT dir, then calls its main(). Rendering, camera,
size (460x250), colours and 'min = / max =' captions are all the generator's own code.

Usage (from anywhere; repo venv):
  REPO=/workspace/fansim/repo-tt
  $REPO/.venv/bin/python run_repo_generator.py missing   # new rows -> qa_tooltips/img/
  $REPO/.venv/bin/python run_repo_generator.py ranges    # stale-range re-renders -> img/range_fix/
"""
import importlib.util, os, sys
from pathlib import Path

REPO = Path(os.environ.get("REPO", "/workspace/fansim/repo-tt"))
IMG = Path("/workspace/fansim/qa_tooltips/img")
os.chdir(REPO)  # generator imports fansim from the venv; keep relative paths sane
spec = importlib.util.spec_from_file_location("gci", REPO / "scripts/generate_control_images.py")
gci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gci)

MISSING = [
    # Design control with no image and no text (plain VSelect, fan_tab_ui.py:856)
    ("e_hub_profile", "Hub profile (cylinder vs cone)", "hub_profile", "cylinder", "cone", "fan",
     {"hub_nose": 12.0, "hub_height": 18.0}),
    ("e_hub_profile_dome", "Hub profile (cylinder vs dome)", "hub_profile", "cylinder", "dome", "fan",
     {"hub_nose": 12.0, "hub_height": 18.0}),
    # Optimize 'Geometry stamps' that act on the rotor (same recipes the optimizer stamps)
    ("opt_shroud", "Shroud ring stamp (SHROUD_DEFAULT_MM=1.6)", "shroud_thick_mm", 0.0, 1.6, "fan",
     {"shroud_height_frac": 0.65}),
    ("opt_sickle", "Sickle LE stamp (sickle_mm, searched 4-12)", "sickle_mm", 0.0, 12.0, "fan",
     {"lean_tip": 10.0, "cylindrical_tip": False}),
    ("opt_notched", "Notched tips stamp (3 x 1.5 mm)", "notched_tips", 0, 1, "fan",
     {"lean_tip": 20.0, "chord_tip": 40.0, "cylindrical_tip": True}),
]

# Existing images whose min/max differ from the cockpit slider (range_check.json) -> re-render at UI range
RANGES = [
    ("e_camber_root", "Camber / scoop — root", "camber_root", 0.0, 0.15, "blade"),
    ("e_camber_mid", "Camber / scoop — mid", "camber_mid", 0.0, 0.15, "blade"),
    ("e_camber_tip", "Camber / scoop — tip", "camber_tip", 0.0, 0.15, "blade"),
    ("e_hub_radius", "Hub radius", "hub_radius", 15, 35, "fan"),
    ("e_skew_mid", "Skew mid", "skew_mid", -20, 20, "fan"),
    ("e_skew_tip", "Skew tip", "skew_tip", -25, 25, "fan"),
    ("e_winglet_sweep", "Winglet sweep", "winglet_sweep", 0, 15, "fan"),
    ("e_winglet_lean", "Winglet lean", "winglet_lean", 0, 30, "fan"),
    ("e_tip_notch_depth", "Tip notch depth", "tip_notch_depth_mm", 0.5, 3.0, "fan",
     {"notched_tips": True, "lean_tip": 20.0, "chord_tip": 40.0}),
    ("e_thick_mm", "Wall thickness", "thick_mm", 0.8, 4.0, "blade", {"section_family": "plate"}),
    ("e_le_thick", "LE thick scale", "le_thick_scale", 0.0, 2.0, "blade",
     {"section_family": "naca", "thickness_mid": 0.08}),
    ("e_te_thick", "TE thick / roundness", "te_thick_scale", 0.0, 2.0, "blade",
     {"section_family": "plate", "thickness_mid": 0.10, "max_camber": 0.0,
      "camber_root": 0.0, "camber_mid": 0.0, "camber_tip": 0.0}),
    ("e_shroud_height", "Shroud height", "shroud_height_frac", 0.0, 1.0, "fan",
     {"shroud_thick_mm": 1.6}),
]

which = sys.argv[1] if len(sys.argv) > 1 else "missing"
if which == "missing":
    gci.CONTROLS, gci.OUT = MISSING, IMG
else:
    gci.CONTROLS, gci.OUT = RANGES, IMG / "range_fix"
gci.main(sys.argv[2:] or None)
