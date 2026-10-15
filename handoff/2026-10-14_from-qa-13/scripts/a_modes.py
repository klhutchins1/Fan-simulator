"""QA r13 Task A (PREREG_R13 02584e6): 24.2 Simple vs Expert, headless Chrome via Playwright against the cockpit on :8080.
Usage: pwvenv/bin/python a_modes.py <out.json> <screens_dir>"""
import json, sys, time
from playwright.sync_api import sync_playwright
OUT, SH = sys.argv[1], sys.argv[2]
RES = ["Glossary — CFM", "Gold ✕ = datasheet", "Hide scatter points whose built tip", "CFM scatter — up and right"]
CTL = ["Fits this fan only", "Declutter", "Show stock"]
DES = ["Chord = LE→TE", "NACA = cambered", "Camber = the scoop", "Wall = the thin dimension", "NACA: LE/TE scales",
       "Three boxy", "0 thickness = off", "Blade on hub: + raises"]
PANELS = ["Geometry — modify design", "Planform", "Pitch / twist", "Airfoil", "3-D shape", "Tip — round", "Hub", "Spacing", "Features"]
R = {"t0": time.time()}
def vis(pg, key):
    loc = pg.get_by_text(key, exact=False)
    return any(loc.nth(i).is_visible() for i in range(loc.count()))
def keys(pg, ks): return {k: vis(pg, k) for k in ks}
def mode(pg, m):
    pg.locator(".v-btn", has_text=m.upper()).first.click(); pg.wait_for_timeout(800)
def sub(pg, name):
    pg.locator(".v-tab", has_text=name.upper()).first.click(); pg.wait_for_timeout(800)
def expand(pg):
    for t in PANELS:
        loc = pg.locator(".v-expansion-panel", has=pg.locator(".v-expansion-panel-title", has_text=t))
        for i in range(loc.count()):
            p = loc.nth(i)
            if p.is_visible() and "v-expansion-panel--active" not in (p.get_attribute("class") or ""):
                p.locator(".v-expansion-panel-title").first.click(); pg.wait_for_timeout(400)
def tooltip(pg):
    sl = [s for s in pg.locator(".v-slider").all() if s.is_visible()]
    if not sl: return {"sliders": 0, "tooltip": None}
    sl[0].scroll_into_view_if_needed(); pg.mouse.move(0, 0); pg.wait_for_timeout(300)
    sl[0].hover(); t = time.monotonic(); seen = None
    while time.monotonic() - t < 3:
        o = pg.locator(".v-overlay__content")
        txt = [o.nth(i).inner_text()[:80] for i in range(o.count()) if o.nth(i).is_visible()]
        if txt: seen = txt; break
        pg.wait_for_timeout(200)
    return {"sliders": len(sl), "tooltip": seen}
def state(pg, k):
    try: return pg.evaluate(f"() => window.trame.state.get('{k}')")
    except Exception as e: return f"ERR {e}"[:120]
def readout_visible(pg, txt):
    return bool(txt) and isinstance(txt, str) and vis(pg, txt.strip()[:40])
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True); ctx = b.new_context(viewport={"width": 1366, "height": 768}); pg = ctx.new_page()
    pg.goto("http://127.0.0.1:8080/", wait_until="networkidle"); pg.wait_for_timeout(6000)
    R["cold_mode"] = state(pg, "ui_mode"); R["cold_ls"] = pg.evaluate("() => localStorage.getItem('fansim.ui_mode')")
    sub(pg, "Results"); R["S0_res"] = keys(pg, RES); R["S0_ctl"] = keys(pg, CTL)
    R["S0_design_select"] = vis(pg, "Design")
    sc = pg.locator(".js-plotly-plot").first
    R["S4_simple_bbox"] = sc.bounding_box() if sc.count() else None
    pg.screenshot(path=f"{SH}/a_results_simple_768.png")
    mode(pg, "Expert"); R["S1_expert_res"] = keys(pg, RES)
    R["S4_expert_bbox"] = sc.bounding_box() if sc.count() else None
    pg.screenshot(path=f"{SH}/a_results_expert_768.png")
    mode(pg, "Simple"); R["S1_back_simple_res"] = keys(pg, RES)
    mode(pg, "Expert"); R["ls_before_reload"] = pg.evaluate("() => localStorage.getItem('fansim.ui_mode')")
    pg.reload(wait_until="networkidle"); pg.wait_for_timeout(6000)
    R["after_reload_mode"] = state(pg, "ui_mode"); R["after_reload_ls"] = pg.evaluate("() => localStorage.getItem('fansim.ui_mode')")
    sub(pg, "Results"); R["S1_reload_res"] = keys(pg, RES)
    # Design, Expert
    sub(pg, "Design"); expand(pg)
    R["S3_expert_design"] = keys(pg, DES); R["S3_expert_tooltip"] = tooltip(pg)
    pg.screenshot(path=f"{SH}/a_design_expert.png", full_page=True)
    mode(pg, "Simple"); expand(pg)
    R["S2_simple_design"] = keys(pg, DES); R["S2_hover_hint"] = vis(pg, "Hover any slider")
    R["S2_simple_tooltip"] = tooltip(pg)
    hub, tip, wall = state(pg, "hub_fit_info"), state(pg, "tip_fit_info"), state(pg, "thick_wall_readout")
    R["S2_readouts"] = {"hub_fit_info": [str(hub)[:100], readout_visible(pg, hub)], "tip_fit_info": [str(tip)[:100], readout_visible(pg, tip)],
                        "thick_wall_readout": [str(wall)[:100], readout_visible(pg, wall)]}
    pg.screenshot(path=f"{SH}/a_design_simple.png", full_page=True)
    b.close()
r = R
r["S0"] = r["cold_mode"] == "simple" and not any(r["S0_res"].values()) and all(r["S0_ctl"].values()) and r["S0_design_select"]
r["S1"] = all(r["S1_expert_res"].values()) and not any(r["S1_back_simple_res"].values()) and r["after_reload_mode"] == "expert" and all(r["S1_reload_res"].values()) and r["after_reload_ls"] == "expert"
r["S2"] = r["S2_hover_hint"] and r["S2_simple_tooltip"]["sliders"] >= 1 and r["S2_readouts"]["hub_fit_info"][1] and r["S2_readouts"]["tip_fit_info"][1] and not any(r["S2_simple_design"].values())
r["S3"] = all(r["S3_expert_design"].values()) and bool(r["S3_expert_tooltip"]["tooltip"]) and bool(r["S2_simple_tooltip"]["tooltip"])
json.dump(R, open(OUT, "w"), indent=1, default=str)
print({k: R[k] for k in ("S0", "S1", "S2", "S3")})
