from pathlib import Path
import re
import sys

plan = Path(sys.argv[1]).read_text(encoding="utf-8")
n = int(sys.argv[2])
out = Path(sys.argv[3])
lines = plan.splitlines(True)
buf = []
infence = False
intask = False
for line in lines:
    if line.startswith("```"):
        infence = not infence
    if not infence and line.startswith("#") and "Task " in line:
        m = re.match(r"^#+[ \t]+Task[ \t]+(\d+)", line)
        intask = bool(m and int(m.group(1)) == n)
    if intask:
        buf.append(line)
if not buf:
    raise SystemExit(f"task {n} not found")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("".join(buf), encoding="utf-8")
print(f"wrote {out}: {len(buf)} lines")
