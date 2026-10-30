"""QA r22 Task A (PREREG_R22 715891f): UI-26 / UI-27 / UI-29 / R1.4 rendered / QA-42 rendered, headless Chrome via
Playwright against the cockpit on :8080 (pattern from r13 a_modes.py). No Assess/Sweep/CFD clicked; Preview only.
Usage: pwvenv/bin/python a_ui.py <out.json> <screens_dir>"""
import json, re, sys, time
from playwright.sync_api import sync_playwright
OUT, SH = sys.argv[1], sys.argv[2]
URL = "http://127.0.0.1:8080/"
JARGON = {"hose_line": "change under Assess & print below", "camber_triplet": re.compile(r"camber 0\.\d{3}/0\.\d{3}"),
          "difficulty": re.compile(r"Difficulty \d+/100"), "gold_stock": "Gold = parametric Stock"}
PHRASE = re.compile(r"about 5\s?\u00a0?% less airflow than the real A12x25", re.I)
R = {"t0": time.strftime("%Y-%m-%d %H:%M:%S %z")}
def st(pg, k):
    try: return pg.evaluate(f"() => window.trame.state.get('{k}')")
    except Exception as e: return f"ERR {e}"[:120]
def vis_text(pg):  # visible text of the whole page
    return pg.evaluate("() => document.body.innerText")
def jargon(txt):
    return {k: bool(p.search(txt)) if hasattr(p, "search") else (p in txt) for k, p in JARGON.items()}
def mode(pg, m):
    pg.locator(".v-btn", has_text=m.upper()).first.click(); pg.wait_for_timeout(1000)
def bbox_vis(loc):
    for i in range(loc.count()):
        if loc.nth(i).is_visible(): return loc.nth(i).bounding_box()
    return None
def viewer_box(pg):
    return pg.evaluate("""() => { let best=null, a=0; for (const c of document.querySelectorAll('canvas')) {
        const r=c.getBoundingClientRect(); if (r.width*r.height>a && r.width>100) {a=r.width*r.height; best={x:r.x,y:r.y,w:r.width,h:r.height,bottom:r.bottom}} } return best; }""")
def open_fan(pg):
    tabs = pg.locator(".v-tab")
    names = [tabs.nth(i).inner_text().strip() for i in range(tabs.count()) if tabs.nth(i).is_visible()]
    R.setdefault("tabs_seen", names)
    t = pg.locator(".v-tab", has_text=re.compile(r"^\s*fan", re.I))
    if t.count(): t.first.click(); pg.wait_for_timeout(1000)
def fresh(b, w, h, m=None):
    ctx = b.new_context(viewport={"width": w, "height": h}); pg = ctx.new_page()
    pg.goto(URL, wait_until="networkidle"); pg.wait_for_timeout(6000); open_fan(pg)
    if m and st(pg, "ui_mode") != m: mode(pg, m)
    return ctx, pg
def layout(pg, tag):
    out = {"mode": st(pg, "ui_mode"), "viewer": viewer_box(pg)}
    out["picker"] = bbox_vis(pg.locator(".v-select", has_text="Design"))
    out["preview_btn"] = bbox_vis(pg.locator(".v-btn", has_text=re.compile("Preview", re.I)))
    out["controls_col"] = pg.evaluate("""() => { for (const c of document.querySelectorAll('.v-col-5')) {
        if (c.querySelector('.v-tab') && c.innerText.includes('Library')) { const r=c.getBoundingClientRect(); return {x:r.x,w:r.width}; } } return null; }""")
    out["body_font_px"] = pg.evaluate("() => parseFloat(getComputedStyle(document.body).fontSize)")
    out["start_here"] = pg.evaluate("""() => { for (const e of document.querySelectorAll('div')) {
        if (e.childElementCount===0 && e.textContent.trim().startsWith('Start here') && e.offsetParent) { const s=getComputedStyle(e);
        return {font_px: parseFloat(s.fontSize), color: s.color, cls: e.className}; } } return null; }""")
    txt = vis_text(pg); out["jargon"] = jargon(txt); out["phrase"] = bool(PHRASE.search(txt))
    pg.screenshot(path=f"{SH}/{tag}.png")
    return out
def pick_stock(pg):
    if st(pg, "selected_trial") == 100000:  # cold start already has the reference (Stock) selected
        return {"stock_items": ["already selected on cold start"], "selected_trial": 100000}
    sel = pg.locator(".v-select", has_text="Design"); sel = [sel.nth(i) for i in range(sel.count()) if sel.nth(i).is_visible()][0]
    sel.click(); pg.wait_for_timeout(800)
    it = pg.locator(".v-list-item", has_text=re.compile("stock", re.I))
    names = [it.nth(i).inner_text()[:60] for i in range(min(it.count(), 5))]
    if it.count(): it.first.click()
    else: pg.keyboard.press("Escape")
    pg.wait_for_timeout(3000)
    return {"stock_items": names, "selected_trial": st(pg, "selected_trial")}
def preview(pg, timeout=240):
    before = st(pg, "preview_msg"); pg.locator(".v-btn", has_text=re.compile("Preview", re.I)).first.click()
    t = time.monotonic(); pg.wait_for_timeout(2000)
    while time.monotonic() - t < timeout:
        if not st(pg, "preview_busy"): break
        pg.wait_for_timeout(1000)
    return {"secs": round(time.monotonic() - t, 1), "msg": str(st(pg, "preview_msg"))[:600]}
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    for (w, h) in ((1366, 768), (1920, 1080)):
        for m in ("simple", "expert"):
            ctx, pg = fresh(b, w, h, m); R[f"{w}x{h}_{m}"] = layout(pg, f"fan_{w}x{h}_{m}"); ctx.close()
    # R1.4 rendered: Stock selected, Expert vs Simple; then QA-42 rendered Preview with two materials (Expert view)
    ctx, pg = fresh(b, 1366, 768, "expert")
    R["stock_pick"] = pick_stock(pg); txt = vis_text(pg)
    R["stock_expert_phrase"] = bool(PHRASE.search(txt)); R["stock_expert_jargon"] = jargon(txt)
    pg.screenshot(path=f"{SH}/stock_expert_1366.png", full_page=True)
    mode(pg, "simple"); txt = vis_text(pg); R["stock_simple_phrase"] = bool(PHRASE.search(txt)); R["stock_simple_jargon"] = jargon(txt)
    mode(pg, "expert")
    R["material_items"] = st(pg, "assess_material_items"); R["preview"] = {}
    mats = [x.get("value", x.get("title")) if isinstance(x, dict) else x for x in (R["material_items"] or [])]
    for mat in [m for m in mats if m in ("PETG", "PLA+")] or mats[:2]:
        pg.evaluate(f"() => window.trame.state.set('assess_material', {json.dumps(mat)})"); pg.wait_for_timeout(800)
        R["preview"][mat] = preview(pg); R["preview"][mat]["material_state"] = st(pg, "assess_material")
        pg.screenshot(path=f"{SH}/preview_{re.sub('[^A-Za-z0-9]', '', mat)}.png")
    b.close()
def ok27(L): return bool(L["viewer"]) and L["viewer"]["bottom"] <= 768 and bool(L["picker"]) and L["picker"]["y"] + L["picker"]["height"] <= 768 and bool(L["preview_btn"]) and L["preview_btn"]["y"] + L["preview_btn"]["height"] <= 768
def ok29(L):
    sh = L["start_here"]
    return bool(L["controls_col"]) and L["controls_col"]["w"] / 1920 >= 0.25 and L["body_font_px"] >= 14 and bool(sh) and sh["font_px"] >= 14 and "text-caption" not in sh["cls"] and "medium-emphasis" not in sh["cls"]
R["UI27_simple"], R["UI27_expert"] = ok27(R["1366x768_simple"]), ok27(R["1366x768_expert"])
R["UI29_simple"] = ok29(R["1920x1080_simple"])
R["UI26_rendered_any"] = {k: any(R[k]["jargon"].values()) for k in R if k.endswith(("_simple", "_expert")) and isinstance(R[k], dict) and "jargon" in R[k]}
json.dump(R, open(OUT, "w"), indent=1, default=str)
print(json.dumps({k: R[k] for k in ("UI27_simple", "UI27_expert", "UI29_simple", "UI26_rendered_any", "stock_expert_phrase", "stock_simple_phrase")}, default=str))
