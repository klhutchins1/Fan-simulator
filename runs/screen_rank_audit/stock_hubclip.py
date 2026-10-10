"""Stock re-Assess after the hub-face clip (measurement; compare with runs/screen_rank_audit/stock/full)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT))
import screen_rank_audit as sra
r = sra.run_full("stock_hubclip", sra.designs()["stock"])
print(json.dumps({k: r.get(k) for k in ("feasible", "cfm_free", "cfm_load", "efficiency", "free_raw_cfm", "load_raw_cfm", "wall_s")}), flush=True)
