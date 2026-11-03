import re, sys
p = sys.argv[1]; s = open(p, encoding="utf-8").read()
M = "r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch)"
upd = {
 "UI-26": f" {M}; 1366 Simple miss again (render timing).",
 "UI-27": f" {M}.",
 "UI-29": f" {M}.",
 "UI-31": " r25b: **verified on master 0635a18**: 0 Surrogate-guided labels rendered, argv has no `--surrogate-guided` with state forced on, CLI guard refuses (`run_optimization.py:164-170`). R1.11 not closable (QA-66; CLI test guard-only). `docs/qa/notes/r25b-master-0635a18-recheck.md`.",
 "UI-32": f" {M}.",
 "UI-33": f" {M}.",
 "UI-34": f" {M}; Boost/NN tooltips now name only GP skip, switches still enabled with GP skip off.",
 "UI-35": f" {M} (range_check 58 rows, 20 mismatches).",
 "UI-36": f" {M} (0/8 hovers; inventory 292 rows, byte-identical to branch).",
 "UI-37": f" {M}.",
 "UI-38": f" {M}.",
 "QA-40": f" {M}.",
 "QA-42": f" {M}.",
}
n = 0
for k, add in upd.items():
    pat = re.compile(r"^(\| " + re.escape(k) + r" \|.*?)( \|)\s*$", re.M)
    s, c = pat.subn(lambda m: m.group(1) + add + m.group(2), s, count=1); n += c
    assert c == 1, k
s = s.rstrip("\n") + "\n\n" + open(sys.argv[2], encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(s); print("rows updated", n)
