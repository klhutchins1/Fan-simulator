from pathlib import Path
import re

lines = Path(r"E:\Projects\programming_2\Fan-simulator\fansim\cockpit\fan_tab.py").read_text(
    encoding="utf-8"
).splitlines()
print("total", len(lines))

# module-level markers
print("\n=== MODULE STRUCTURE (1-332) ===")
for i, l in enumerate(lines[:332], 1):
    if re.match(r"^(def |class |# |[A-Z_][A-Z0-9_]* =|_IMG|_CTRL|_RUNNING)", l):
        print(f"{i:4d}: {l[:100]}")

print("\n=== SETUP COMMENT / PHASE MARKERS ===")
for i, l in enumerate(lines[332:2628], 333):
    s = l.strip()
    if s.startswith("# ---") or s.startswith("# ----") or s.startswith("# Expose") or s.startswith(
        "# Fan session"
    ):
        print(f"{i:4d}: {s[:110]}")
    if re.match(r"^    def ", l) and i in (
        351,
        438,
        546,
        657,
        670,
        763,
        794,
        969,
        1063,
        1177,
        1333,
        1415,
        1448,
        1566,
        1693,
        1871,
        1949,
        2084,
        2275,
        2386,
        2455,
        2528,
    ):
        print(f"{i:4d}: {s[:80]}")

print("\n=== RENDER MARKERS ===")
for i, l in enumerate(lines[2629:], 2630):
    s = l.strip()
    if (
        s.startswith("#")
        or "fan_subtab ===" in l
        or "VTab(" in l
        or "fig_widget" in l
        or "plotter_ui" in l
        or "Bind Fan" in l
        or "Actions" in l
        and "html.Div" in l
    ):
        print(f"{i:4d}: {l.rstrip()[:110]}")

# Accurate spans: handle multi-line signatures
print("\n=== FUNCTION SPANS ===")


def spans():
    i = 0
    out = []
    while i < len(lines):
        m = re.match(r"^(\s*)(async )?def (\w+)", lines[i])
        if not m:
            i += 1
            continue
        indent = len(m.group(1))
        name = m.group(3)
        start = i
        # skip signature until line ending with ):
        j = i
        while j < len(lines) and not re.search(r"\)\s*(->[^:]*)?:\s*$", lines[j]):
            j += 1
        if j >= len(lines):
            break
        end = j
        for k in range(j + 1, len(lines)):
            l = lines[k]
            if not l.strip():
                continue
            cur = len(l) - len(l.lstrip(" "))
            if cur <= indent:
                break
            end = k
        out.append((end - start + 1, start + 1, end + 1, indent, name))
        i = j + 1
    return out


all_spans = spans()
print("TOP-LEVEL:")
for sp in sorted([s for s in all_spans if s[3] == 0], reverse=True):
    print(f"  {sp[4]:30s} {sp[0]:4d} lines  ({sp[1]}-{sp[2]})")
print("LARGEST nested indent=4:")
for sp in sorted([s for s in all_spans if s[3] == 4], reverse=True)[:18]:
    print(f"  {sp[4]:30s} {sp[0]:4d} lines  ({sp[1]}-{sp[2]})")
print("LARGEST deeper:")
for sp in sorted([s for s in all_spans if s[3] > 4], reverse=True)[:10]:
    print(f"  indent={sp[3]} {sp[4]:30s} {sp[0]:4d} lines  ({sp[1]}-{sp[2]})")
