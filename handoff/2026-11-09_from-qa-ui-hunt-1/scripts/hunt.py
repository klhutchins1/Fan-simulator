"""ui-hunt-1 (PREREG cf2c813) exploratory UI bug hunt, headless Chrome against a running cockpit on QA_PORT.
Never clicks Assess / Sweep / Optimize / Export / Randomize. Inputs are typed + blurred only (restored afterwards).
Usage: pwenv/bin/python hunt.py <out.json> <screens_dir>"""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright
OUT, SH = sys.argv[1], sys.argv[2]; os.makedirs(SH, exist_ok=True)
URL = f"http://127.0.0.1:{os.environ.get('QA_PORT', '8812')}/"
FORBID = re.compile(r"assess|sweep|optimi|export|randomi|run |cancel|record|save|delete|apply|reset|continue", re.I)
R = {"t0": time.strftime("%Y-%m-%d %H:%M:%S %z"), "console": [], "pageerrors": [], "bad_responses": [], "failed_requests": [], "img_requests": []}
def hook(pg, tag):
    pg.on("console", lambda m: R["console"].append([tag, m.type, m.text[:300]]) if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: R["pageerrors"].append([tag, str(e)[:300]]))
    pg.on("requestfailed", lambda q: R["failed_requests"].append([tag, q.url[:200], q.failure]))
    def resp(r):
        if r.status >= 400: R["bad_responses"].append([tag, r.status, r.request.method, r.url[:200]])
        if re.search(r"\.(png|jpg|svg)", r.url): R["img_requests"].append([tag, r.status, r.url[-80:]])
    pg.on("response", resp)
def st(pg, k): return pg.evaluate(f"() => window.trame.state.get({json.dumps(k)})")
def sset(pg, k, v): pg.evaluate(f"() => window.trame.state.set({json.dumps(k)}, {json.dumps(v)})")
def settle(pg, maxs=20):
    t = time.monotonic(); last = None; same = 0
    while time.monotonic() - t < maxs:
        n = pg.evaluate("() => document.body.innerText.length + document.querySelectorAll('*').length")
        same = same + 1 if n == last else 0; last = n
        if same >= 3: break
        pg.wait_for_timeout(300)
    return round(time.monotonic() - t, 2)
def mode(pg, m):
    pg.locator(".v-btn", has_text=re.compile(rf"^\s*{m}\s*$", re.I)).first.click(); pg.wait_for_timeout(800); settle(pg)
def tab(pg, name):
    t = pg.locator(".v-tab:visible", has_text=re.compile(rf"^\s*{re.escape(name)}", re.I))
    if not t.count(): return None
    t0 = time.monotonic(); t.first.click(); s = settle(pg); return round(time.monotonic() - t0, 2)
OVERFLOW_JS = """() => { const de=document.documentElement; const out={page_hscroll: de.scrollWidth > de.clientWidth+1, page_w: de.scrollWidth, vw: de.clientWidth, clipped: [], offscreen_right: []};
  for (const e of document.querySelectorAll('.v-btn, .v-tab, .v-label, .v-field-label, .v-list-item-title, .v-card-title, .v-chip, .v-select__selection-text, .text-subtitle-1, .text-subtitle-2')) {
    if (!e.offsetParent) continue; const r=e.getBoundingClientRect(); if (r.width<4) continue;
    const s=getComputedStyle(e); const c=e.querySelector('.v-btn__content')||e;
    if ((c.scrollWidth > c.clientWidth+2) && (s.overflow==='hidden'||getComputedStyle(c).overflow==='hidden'||s.textOverflow==='ellipsis'||getComputedStyle(c).textOverflow==='ellipsis'))
       out.clipped.push(e.innerText.trim().slice(0,70));
    if (r.right > de.clientWidth+2 && r.width>0) out.offscreen_right.push(e.innerText.trim().slice(0,60)); }
  out.clipped=[...new Set(out.clipped)].slice(0,40); out.offscreen_right=[...new Set(out.offscreen_right)].slice(0,20); return out; }"""
def expand_all(pg):
    for _ in range(3):
        t = pg.locator(".v-expansion-panel-title:visible")
        for i in range(t.count()):
            try:
                if t.nth(i).get_attribute("aria-expanded") == "false": t.nth(i).click(); pg.wait_for_timeout(150)
            except Exception: pass
    settle(pg)
def snap_state(pg):
    return pg.evaluate("() => { const s=window.trame.state.state, o={}; for (const k in s) { const v=s[k]; if (v===null||['number','boolean','string'].includes(typeof v)) o[k]=(typeof v==='string'? v.slice(0,160): v); } return o; }")
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
    # ---------- 1. cold first view + UI-26 timing ----------
    ctx = b.new_context(viewport={"width": 1366, "height": 768}); pg = ctx.new_page(); hook(pg, "cold")
    t0 = time.monotonic(); pg.goto(URL, wait_until="networkidle"); R["first_paint_s"] = round(time.monotonic() - t0, 2)
    gold_t = None
    for _ in range(120):
        msg = st(pg, "preview_msg") or ""
        if "Gold = parametric Stock" in msg: gold_t = round(time.monotonic() - t0, 1); break
        pg.wait_for_timeout(1000)
    R["UI26"] = {"secs_until_gold_msg": gold_t, "visible_in_text": "Gold = parametric Stock" in pg.evaluate("() => document.body.innerText"), "mode": st(pg, "ui_mode")}
    pg.screenshot(path=f"{SH}/01_cold_1366_simple.png")
    # ---------- 2. every tab, sub-tab, both modes, overflow ----------
    R["tabs"] = {}
    tops = [x.strip() for x in pg.locator(".v-tab").all_inner_texts()]
    R["top_tabs"] = tops
    for m in ("simple", "expert"):
        mode(pg, m)
        for name in ["FAN · CFD", "Mixed · estimate", "Volute · estimate", "PROP · FAST ESTIMATE", "CROR · estimate"]:
            secs = tab(pg, name.split(" ")[0])
            subs = {}
            for sub in ("DESIGN", "RESULTS", "LIBRARY"):
                sl = pg.locator(".v-tab:visible", has_text=re.compile(rf"^\s*{sub}\s*$", re.I))
                if sl.count():
                    t1 = time.monotonic(); sl.first.click(); settle(pg); subs[sub] = {"secs": round(time.monotonic() - t1, 2), **pg.evaluate(OVERFLOW_JS)}
                    pg.screenshot(path=f"{SH}/02_{m}_{name.split(' ')[0].lower()}_{sub.lower()}_1366.png", full_page=True)
            if not subs:
                subs["main"] = pg.evaluate(OVERFLOW_JS); pg.screenshot(path=f"{SH}/02_{m}_{name.split(' ')[0].lower()}_1366.png", full_page=True)
            R["tabs"][f"{m}:{name}"] = {"click_secs": secs, "subs": subs}
        tab(pg, "FAN")
        pg.locator(".v-tab:visible", has_text=re.compile(r"^\s*DESIGN\s*$", re.I)).first.click(); settle(pg)
    # ---------- 3. Fan Expert: expand everything, count controls, overflow, links ----------
    mode(pg, "expert"); tab(pg, "FAN"); expand_all(pg)
    R["fan_expert_expanded"] = pg.evaluate(OVERFLOW_JS)
    pg.screenshot(path=f"{SH}/03_fan_expert_expanded_1366.png", full_page=True)
    hrefs = pg.evaluate("() => [...document.querySelectorAll('a[href]')].map(a => ({t:a.innerText.trim().slice(0,50), h:a.getAttribute('href'), vis: !!a.offsetParent}))")
    R["links"] = []
    for h in hrefs:
        u = h["h"] or ""; rec = dict(h)
        if u.startswith("http") and "127.0.0.1" not in u: rec["status"] = "external (not fetched)"
        elif u.startswith("data:") or u == "": rec["status"] = "data/empty"
        else:
            try: rec["status"] = pg.request.get(URL.rstrip("/") + "/" + u.lstrip("/") if not u.startswith("http") else u).status
            except Exception as e: rec["status"] = f"ERR {e}"[:80]
        R["links"].append(rec)
    # tooltip images: hover every Design slider label that has an image tooltip
    imgs = []
    labels = pg.locator(".v-slider .v-label:visible, .v-input .v-label:visible")
    n = min(labels.count(), 80)
    for i in range(n):
        try:
            l = labels.nth(i); txt = l.inner_text().strip()[:40]; l.scroll_into_view_if_needed(); l.hover(); pg.wait_for_timeout(450)
            ov = pg.locator(".v-overlay--active .v-overlay__content:visible")
            if ov.count():
                im = ov.last.locator("img")
                info = {"label": txt, "imgs": im.count()}
                if im.count():
                    info["natural_w"] = im.first.evaluate("e => e.naturalWidth"); info["src_head"] = (im.first.get_attribute("src") or "")[:40]
                    box = ov.last.bounding_box(); info["box"] = box and [round(box["x"]), round(box["y"]), round(box["width"]), round(box["height"])]
                imgs.append(info)
            pg.mouse.move(2, 2); pg.wait_for_timeout(150)
        except Exception as e: imgs.append({"i": i, "err": str(e)[:100]})
    R["tooltip_hover"] = {"labels_hovered": n, "with_tooltip": len([x for x in imgs if "imgs" in x]), "with_img": len([x for x in imgs if x.get("imgs")]),
                          "img_broken": [x for x in imgs if x.get("imgs") and not x.get("natural_w")],
                          "img_tooltip_offscreen": [x["label"] for x in imgs if x.get("box") and (x["box"][1] < 0 or x["box"][1] + x["box"][3] > 768 or x["box"][0] + x["box"][2] > 1366)],
                          "sample": imgs[:12]}
    # ---------- 4. input validation on every visible text field (Fan Expert, expanded) ----------
    base = snap_state(pg); R["inputs"] = []
    fields = pg.locator(".v-text-field:visible")
    for i in range(fields.count()):
        f = fields.nth(i)
        try:
            lab = (f.locator(".v-label").first.inner_text().strip() if f.locator(".v-label").count() else "")[:60]
            inp = f.locator("input").first
            if not inp.count() or inp.get_attribute("readonly") is not None or inp.is_disabled(): continue
            if f.locator("xpath=ancestor::*[contains(@class,'v-select') or contains(@class,'v-slider')]").count() or "v-select" in (f.get_attribute("class") or ""): continue
            orig = inp.input_value(); typ = inp.get_attribute("type"); rec = {"label": lab, "type": typ, "orig": orig, "res": {}}
            for v in ("", "-5", "1e9", "abc"):
                s0 = snap_state(pg)
                inp.fill(v) if typ != "number" or v != "abc" else inp.press_sequentially("abc")
                inp.press("Tab"); pg.wait_for_timeout(500)
                s1 = snap_state(pg); ch = {k: [s0.get(k), s1.get(k)] for k in s1 if s1.get(k) != s0.get(k) and not k.startswith("trame__")}
                err = f.locator(".v-messages__message").all_inner_texts()
                rec["res"][v or "<empty>"] = {"shown": inp.input_value(), "state_changes": dict(list(ch.items())[:4]), "msg": [e[:80] for e in err],
                                              "error_cls": "v-input--error" in (f.get_attribute("class") or "")}
            inp.fill(orig); inp.press("Tab"); pg.wait_for_timeout(400)
            R["inputs"].append(rec)
        except Exception as e: R["inputs"].append({"i": i, "err": str(e)[:120]})
    after = snap_state(pg); R["inputs_state_not_restored"] = {k: [base.get(k), after.get(k)] for k in after if after.get(k) != base.get(k) and not k.startswith("trame__") and "msg" not in k and "info" not in k}
    # ---------- 5. G2 visual: injected flow rows ----------
    rows = [{"key": "direction", "title": "Air direction", "icon": "✓", "status": "ok", "text": "QA-direction-row", "expert_only": False, "img": "", "stock_img": ""},
            {"key": "noise", "title": "Noise", "icon": "·", "status": "na", "text": "QA-noise-row Hint 76.4 (Stock 75.4). Scales with tip speed and airflow only; this is not a comparison of how quiet the design is.", "expert_only": True, "img": "", "stock_img": ""}]
    orig_items = st(pg, "trial_items")
    sset(pg, "trial_items", (orig_items or []) + [{"title": "QA fake", "value": -999}]); sset(pg, "fan_subtab", "results")
    sset(pg, "flow_rows", rows); sset(pg, "flow_overall", "QA overall"); pg.wait_for_timeout(1200)
    g2 = {}
    for m in ("expert", "simple"):
        sset(pg, "ui_mode", m); pg.wait_for_timeout(1000)
        txt = pg.evaluate("() => document.body.innerText")
        el = pg.get_by_text("QA-noise-row").first
        g2[m] = {"card_visible": "How the air moves" in txt, "direction_row_visible": "QA-direction-row" in txt, "noise_row_visible": "QA-noise-row" in txt}
        if "QA-noise-row" in txt or m == "simple":
            try: pg.get_by_text("How the air moves").first.scroll_into_view_if_needed(); pg.screenshot(path=f"{SH}/05_g2_noise_row_{m}.png")
            except Exception: pass
    R["G2_visual_injected"] = g2
    sset(pg, "flow_rows", []); sset(pg, "trial_items", orig_items); sset(pg, "fan_subtab", "design"); sset(pg, "ui_mode", "expert"); pg.wait_for_timeout(800)
    # ---------- 6. state across tab switch + reload ----------
    sl = pg.locator(".v-slider:visible input[type=range], .v-slider:visible .v-slider-thumb").first
    before = st(pg, "e_stagger_mid")
    try:
        th = pg.locator(".v-slider-thumb:visible").first; th.focus(); th.press("ArrowRight"); th.press("ArrowRight"); pg.wait_for_timeout(800)
    except Exception as e: R["slider_err"] = str(e)[:100]
    changed = snap_state(pg); diffs = {k: [after.get(k), changed.get(k)] for k in changed if k.startswith("e_") and changed.get(k) != after.get(k)}
    sset(pg, "fan_subtab", "library"); pg.wait_for_timeout(500)
    tab(pg, "PROP"); tab(pg, "FAN")
    s_tab = {"ui_mode": st(pg, "ui_mode"), "fan_subtab": st(pg, "fan_subtab"), "slider_diffs_still": {k: st(pg, k) for k in diffs}}
    pg.reload(wait_until="networkidle"); pg.wait_for_timeout(5000)
    s_rel = {"ui_mode": st(pg, "ui_mode"), "fan_subtab": st(pg, "fan_subtab"), "active_tab": st(pg, "active_tab"), "slider_values": {k: st(pg, k) for k in diffs},
             "edited_stale": st(pg, "edited_stale"), "design_label": pg.locator(".v-select", has_text="Design").first.inner_text()[:90] if pg.locator(".v-select", has_text="Design").count() else None}
    pg.screenshot(path=f"{SH}/06_after_reload_1366.png")
    R["state_persistence"] = {"slider_changes": diffs, "after_tab_switch": s_tab, "after_reload": s_rel}
    # ---------- 7. rapid Simple/Expert toggling ----------
    e0 = len(R["pageerrors"]) + len([c for c in R["console"] if c[1] == "error"])
    counts = {}
    for k in range(6):
        m = "expert" if k % 2 == 0 else "simple"; mode(pg, m)
        counts.setdefault(m, []).append(pg.locator(".v-input:visible").count())
    R["mode_toggle"] = {"visible_inputs": counts, "new_errors": len(R["pageerrors"]) + len([c for c in R["console"] if c[1] == "error"]) - e0}
    ctx.close()
    # ---------- 8. 1920 Expert per top tab (layout only) ----------
    ctx = b.new_context(viewport={"width": 1920, "height": 1080}); pg = ctx.new_page(); hook(pg, "1920")
    pg.goto(URL, wait_until="networkidle"); pg.wait_for_timeout(5000); mode(pg, "expert")
    R["tabs_1920"] = {}
    for name in ["FAN", "Mixed", "Volute", "PROP", "CROR"]:
        tab(pg, name); R["tabs_1920"][name] = pg.evaluate(OVERFLOW_JS); pg.screenshot(path=f"{SH}/08_expert_{name.lower()}_1920.png")
    ctx.close(); b.close()
json.dump(R, open(OUT, "w"), indent=1, ensure_ascii=False, default=str)
print("done", len(R["console"]), len(R["pageerrors"]), len(R["bad_responses"]))
