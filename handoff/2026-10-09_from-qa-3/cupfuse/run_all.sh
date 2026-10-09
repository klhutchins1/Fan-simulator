#!/bin/bash
# Run strategies one at a time; wait for >= 9 GB MemAvailable before each (box: 16 GB, no swap).
root=${1:-/workspace/fansim/qa/r4_cupfuse}; shift
here=$(dirname "$0")
for s in "$@"; do
  for i in $(seq 1 60); do
    av=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo); [ "$av" -ge 9000 ] && break; sleep 5
  done
  echo "$(date +%T) $s start avail=${av}MB"
  .venv/bin/python "$here/cupfuse_driver.py" "$s" "$root" 1800
done
