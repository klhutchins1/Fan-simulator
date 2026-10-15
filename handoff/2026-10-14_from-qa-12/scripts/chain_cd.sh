#!/bin/bash
# QA r12 C then D (each skipped if its output exists). setsid nohup bash chain_cd.sh
cd /tmp; export PYTHONPATH=/workspace/fansim/qa/run_r12 PYTHONDONTWRITEBYTECODE=1
PY=/workspace/fansim/repo-r9/.venv/bin/python; S=/workspace/fansim/repo-r13/handoff/2026-10-14_from-qa-12/scripts; D=$S/../data
[ -f $D/c_cockpit.json ] || $PY $S/cd_cockpit.py C $D/c_cockpit.json
[ -f $D/d_cockpit.json ] || $PY $S/cd_cockpit.py D $D/d_cockpit.json
echo CHAIN_DONE
