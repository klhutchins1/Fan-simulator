"""Headless visibility check of the cockpit (Simple vs Expert). Read-only: switches mode, opens
expansion panels and hovers controls; never clicks Preview/Assess/Optimize/Export/Randomize."""
import json, sys, time
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8080/"
OUT = "/workspace/fansim/qa_tooltips/data"
res = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
    for mode in ("simple", "expert"):
        pg = b.new_page(viewport={"width": 1600, "height": 1000})
        pg.goto(URL); pg.wait_for_timeout(8000)
        pg.get_by_role("button", name=mode.capitalize(), exact=True).first.click()
        pg.wait_for_timeout(2500)
        # open every closed expansion panel on the Design sub-tab
        for _ in range(3):
            titles = pg.locator(".v-expansion-panel-title:visible")
            for i in range(titles.count()):
                t = titles.nth(i)
                try:
                    if t.get_attribute("aria-expanded") == "false":
                        t.click(); pg.wait_for_timeout(250)
                except Exception:
                    pass
        vis = pg.evaluate("""() => {
          const out = [];
          const sel = '.v-label, .v-btn, .v-tab, .v-expansion-panel-title, .v-select .v-field-label, .text-caption > span:first-child';
          document.querySelectorAll(sel).forEach(e => {
            const r = e.getBoundingClientRect();
            const st = getComputedStyle(e);
            if (r.width > 0 && r.height > 0 && st.visibility !== 'hidden') {
              const t = (e.innerText || '').trim().replace(/\\s+/g, ' ');
              if (t) out.push(t);
            }
          });
          return [...new Set(out)];
        }""")
        res[mode] = vis
        pg.screenshot(path=f"{OUT}/headless_{mode}_design.png", full_page=True)
        # hover checks
        hov = {}
        for lab in ["Blades", "Tip ring / shroud", "Hub profile", "Application (hose resistance)"]:
            loc = pg.get_by_text(lab, exact=True).first
            try:
                if not loc.is_visible():
                    hov[lab] = "not visible"; continue
                loc.scroll_into_view_if_needed(); loc.hover(); pg.wait_for_timeout(900)
                ov = pg.locator(".v-overlay--active .v-overlay__content:visible")
                n = ov.count()
                if n == 0:
                    hov[lab] = "no tooltip"
                else:
                    c = ov.last
                    hov[lab] = {"img": c.locator("img").count(), "text": c.inner_text()[:120]}
                    pg.screenshot(path=f"{OUT}/hover_{mode}_{lab.split()[0].lower()}.png")
                pg.mouse.move(5, 5); pg.wait_for_timeout(400)
            except Exception as e:
                hov[lab] = f"err {e!s:.80}"
        res[mode + "_hover"] = hov
        pg.close()
    b.close()
json.dump(res, open(f"{OUT}/headless.json", "w"), indent=1, ensure_ascii=False)
s, e = set(res["simple"]), set(res["expert"])
print("simple", len(s), "expert", len(e))
print("EXPERT-ONLY:", sorted(e - s))
print("SIMPLE-ONLY:", sorted(s - e))
print(json.dumps({k: v for k, v in res.items() if k.endswith("hover")}, indent=1, ensure_ascii=False))
