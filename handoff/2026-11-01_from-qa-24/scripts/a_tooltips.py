"""QA r24 A (PREREG_R24 88c4e79): UI-32/33/34/36/38 rendered checks, Expert mode, headless Chrome on :8080.
No Assess/Sweep/Optimize/CFD clicked. Usage: pwenv/bin/python a_tooltips.py <out.json>"""
import json, re, sys
from playwright.sync_api import sync_playwright
out = {}
def hover(pg, loc):
    loc.scroll_into_view_if_needed(); loc.hover(); pg.wait_for_timeout(1000)
    ov = pg.locator(".v-overlay--active .v-overlay__content:visible")
    r = "no tooltip" if ov.count() == 0 else {"img": ov.last.locator("img").count(), "text": ov.last.inner_text()[:100]}
    pg.mouse.move(5, 5); pg.wait_for_timeout(500)
    return r
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.goto("http://127.0.0.1:8080/"); pg.wait_for_timeout(8000)
    pg.get_by_role("button", name="Expert", exact=True).first.click(); pg.wait_for_timeout(2000)
    for _ in range(3):
        t = pg.locator(".v-expansion-panel-title:visible")
        for i in range(t.count()):
            if t.nth(i).get_attribute("aria-expanded") == "false":
                t.nth(i).click(); pg.wait_for_timeout(250)
    ui36 = {}
    for lab in ["Fan model (hub)", "Hub profile", "Application (hose resistance)", "Print material",
                "Sweep", "Allow intake overbuild (+Z)", "Fit hub to the motor"]:
        try:
            loc = pg.locator(f".v-input:has(label:text-is('{lab}'))").first
            if loc.count() == 0:
                loc = pg.locator(f".v-input:has(label:has-text('{lab}'))").first
            ui36[lab] = hover(pg, loc)
        except Exception as e:
            ui36[lab] = f"err {e!s:.80}"
    try:
        ui36["Preview (action row)"] = hover(pg, pg.locator(".v-btn", has_text=re.compile(r"^\s*Preview", re.I)).first)
    except Exception as e:
        ui36["Preview (action row)"] = f"err {e!s:.80}"
    out["UI36"] = ui36
    out["UI36_n_with_tooltip"] = sum(isinstance(v, dict) for v in ui36.values())
    opt = {}
    for lab in ["Boost + GP mean", "NN + GP mean", "Surrogate-guided", "Catalog GP skip"]:
        try:
            loc = pg.locator(f".v-input:has(label:has-text('{lab}'))").first
            dis = loc.evaluate("e => e.classList.contains('v-input--disabled') || !!e.querySelector('input:disabled')")
            opt[lab] = {"disabled": dis, "hover": hover(pg, loc)}
        except Exception as e:
            opt[lab] = f"err {e!s:.80}"
    out["optimize_switches"] = opt
    st = lambda k: pg.evaluate(f"() => window.trame.state.get('{k}')")
    out["state"] = {k: st(k) for k in ["opt_gp_floor", "opt_surrogate_guided", "opt_gp_boost", "opt_gp_nn"]}
    panel = pg.locator(".v-expansion-panel", has_text="Optimize (hours").first
    txt = panel.inner_text()
    out["optimize_panel_text_head"] = txt[:600]
    out["UI33_hits"] = [w for w in ["slider", "Design slider", "not used", "ignore", "from scratch", "new shapes", "doesn't start"] if w.lower() in txt.lower()]
    body = pg.evaluate("() => document.body.innerText")
    out["UI38_material_caption"] = "Used by Assess and Optimize" in body
    out["UI38_honesty_caption"] = "Also applied when you press Optimize" in body
    b.close()
json.dump(out, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if k != "optimize_panel_text_head"}, indent=1, ensure_ascii=False))
