"""QA r13 Task C RSS sampler (PREREG_R13 02584e6). Every 2 s (monotonic): RSS of every descendant of <root_pid>;
writes one JSON line per sample: mono, chunk label (last 'pytest chunk i/3' in <suite_log>), tree_kb, max_kb, max_pid.
Usage: python c_sampler.py <root_pid> <suite_log> <out.jsonl>"""
import json, os, re, sys, time
root, log, out = int(sys.argv[1]), sys.argv[2], sys.argv[3]
def kids():
    ch = {}
    for p in os.listdir("/proc"):
        if p.isdigit():
            try:
                f = open(f"/proc/{p}/stat").read(); pp = int(f.rsplit(")", 1)[1].split()[1]); ch.setdefault(pp, []).append(int(p))
            except Exception: pass
    s, todo = [], [root]
    while todo:
        x = todo.pop(); s.append(x); todo += ch.get(x, [])
    return s
def rss(p):
    try:
        for l in open(f"/proc/{p}/status"):
            if l.startswith("VmRSS:"): return int(l.split()[1])
    except Exception: pass
    return 0
with open(out, "a") as fo:
    while os.path.exists(f"/proc/{root}"):
        lab = None
        try:
            m = re.findall(r"pytest chunk (\d+/\d+)", open(log, errors="replace").read()); lab = m[-1] if m else None
        except OSError: pass
        r = {p: rss(p) for p in kids()}; mp = max(r, key=r.get)
        fo.write(json.dumps({"mono": round(time.monotonic(), 1), "chunk": lab, "tree_kb": sum(r.values()), "max_kb": r[mp], "max_pid": mp}) + "\n"); fo.flush()
        time.sleep(2)
