"""Per-test-file peak RSS from rss_samples.tsv (2 s samples tagged with the running nodeid)."""
import collections, sys
src = sys.argv[1] if len(sys.argv) > 1 else "rss_samples.tsv"
peak, node_at_peak, entry = {}, {}, {}
prev = None
for line in open(src):
    p = line.rstrip("\n").split("\t")
    if len(p) < 5 or not p[0].isdigit() or not p[4] or "::" not in p[4]:
        continue
    f = p[4].split("::")[0]; mb = int(p[2])
    if f not in entry: entry[f] = prev if prev is not None else mb
    if mb > peak.get(f, -1): peak[f], node_at_peak[f] = mb, p[4]
    prev = mb
rows = sorted(peak.items(), key=lambda kv: -kv[1])
print("file\tpeak_mb\trss_before_file_mb\tdelta_mb\tnodeid_at_peak")
for f, mb in rows[: int(sys.argv[2]) if len(sys.argv) > 2 else 10]:
    print(f"{f}\t{mb}\t{entry[f]}\t{mb-entry[f]}\t{node_at_peak[f].split('::',1)[1]}")
