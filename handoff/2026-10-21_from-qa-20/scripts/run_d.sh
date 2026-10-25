#!/bin/bash
# QA r20 D runner: creates throwaway user fsdry (empty HOME) and a fresh mktemp dir once; resumable.
set -e
R=/workspace/fansim/qa/r20
id fsdry >/dev/null 2>&1 || sudo useradd -m -s /bin/bash fsdry
sudo mkdir -p /tmp/fsdry_src && sudo cp -n /workspace/fansim/handoff_in/r20/fansim.bundle /tmp/fsdry_src/ && sudo chmod -R a+rX /tmp/fsdry_src
[ -f $R/data/d_workdir.txt ] || sudo -u fsdry mktemp -d /tmp/fsdry_clone.XXXXXX > $R/data/d_workdir.txt
mkdir -p $R/logs/d
exec python3 -u $R/scripts/d_dryrun.py $R/data/d_workdir.txt $R/data/d_steps.jsonl $R/logs/d
