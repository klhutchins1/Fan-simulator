"""Sample a process tree's RSS every 2 s and tag each sample with the running pytest nodeid.
Usage: python rss_sampler.py <pid> <out.tsv> [nodeid_file]. Writes t, root_mb, tree_mb, nprocs, nodeid;
an END line with peaks at exit. Linux /proc only."""
import os, sys, time

pid, out = int(sys.argv[1]), sys.argv[2]
node_file = sys.argv[3] if len(sys.argv) > 3 else "/tmp/pytest_current_nodeid"


def rss_mb(p):
    try:
        with open(f"/proc/{p}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 0


def tree(root):
    kids = {}
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                with open(f"/proc/{d}/stat") as f:
                    ppid = int(f.read().rsplit(")", 1)[1].split()[1])
                kids.setdefault(ppid, []).append(int(d))
            except OSError:
                pass
    todo, seen = [root], []
    while todo:
        p = todo.pop(); seen.append(p); todo += kids.get(p, [])
    return seen


t0 = time.time(); peak_root = peak_tree = 0; peak_node = ""
with open(out, "a", buffering=1) as f:
    f.write("t_s\troot_mb\ttree_mb\tnprocs\tnodeid\n")
    while os.path.exists(f"/proc/{pid}"):
        procs = tree(pid)
        r = rss_mb(pid); tr = sum(rss_mb(p) for p in procs)
        try:
            node = open(node_file).read().strip()
        except OSError:
            node = ""
        if tr > peak_tree:
            peak_tree, peak_node = tr, node
        peak_root = max(peak_root, r)
        f.write(f"{time.time()-t0:.0f}\t{r}\t{tr}\t{len(procs)}\t{node}\n")
        time.sleep(2)
    f.write(f"END\tpeak_root_mb={peak_root}\tpeak_tree_mb={peak_tree}\tpeak_nodeid={peak_node}\twall_s={time.time()-t0:.0f}\n")
