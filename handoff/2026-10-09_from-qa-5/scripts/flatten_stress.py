"""Flatten Task A designs.jsonl (nested checks/meas) into the flat fields direction_option_a_count.py reads.
chirality is not stored by Task A; it is derived as omega*pump (the proof's own chi cross-check identity)."""
import json, sys
for l in open(sys.argv[1]):
    r = json.loads(l); m = r.get("meas", {}) or {}; k5 = m.get("K5") or {}; k6 = m.get("K6") or {}
    mc = (m.get("inputs") or {}).get("max_camber")
    if isinstance(mc, list): mc = max(mc, key=abs)
    o = {"design_id": r["id"], "k5_check": r.get("checks", {}).get("K5"), "k6_check": r.get("checks", {}).get("K6"),
         "k5_verdict": k5.get("verdict"), "k5_omega": k5.get("omega"), "k5_pump": k5.get("pump"),
         "k5_chirality": None if k5.get("omega") is None else k5["omega"] * k5["pump"],
         "k6_verdict": k6.get("verdict"), "k6_omega": k6.get("omega"),
         "k6_chirality": None if k6.get("omega") is None else k6["omega"] * k6["pump"],
         "max_camber": mc, "n_blades": (m.get("inputs") or {}).get("n_blades"),
         "tip_lean": ((m.get("inputs") or {}).get("lean") or [None])[-1], "k5_note": k5.get("note")}
    print(json.dumps(o))
