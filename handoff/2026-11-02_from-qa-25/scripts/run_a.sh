#!/bin/bash
# QA r25 A runner (PREREG_R25 b7e7574). Usage: run_a.sh <name> <repo> <port>. Cockpit headless; Preview-only clicks.
set -u; N=$1; R=$2; P=$3; Q=/workspace/fansim/qa_r25; PW=/workspace/fansim/qa_tooltips/pwenv/bin/python
D=$Q/data/$N; S=$Q/screens/$N; RUN=$Q/cockpit_run/$N; mkdir -p $D $S; rm -rf $RUN; mkdir -p $RUN
cd $R && nohup .venv/bin/python scripts/cockpit.py --run $RUN --port $P > $D/cockpit.log 2>&1 &
for i in $(seq 1 90); do curl -s -o /dev/null http://127.0.0.1:$P/ && break; sleep 2; done
export QA_PORT=$P
$PW $Q/scripts/a_ui.py $D/a_ui.json $S > $D/a_ui.log 2>&1; echo "a_ui $?"
$PW $Q/scripts/a_probe.py $D/a_probe.json > $D/a_probe.log 2>&1; echo "a_probe $?"
$PW $Q/scripts/a_tooltips.py $D/a_tooltips.json > $D/a_tooltips.log 2>&1; echo "a_tooltips $?"
pkill -f "scripts/cockpit.py --run $RUN"
cd $R; export QA_REPO=$R QA_DATA=$D
.venv/bin/python $Q/scripts/a_flowcard.py $D/a_flowcard.json > $D/a_flowcard.log 2>&1; echo "flowcard $?"
.venv/bin/python $Q/scripts/scan_controls.py $R $D/scan.json > $D/scan.log 2>&1; echo "scan $?"
.venv/bin/python $Q/scripts/build_inventory.py > $D/inventory.log 2>&1; echo "inventory $?"
QA_RANGE_OUT=$D/range_check.json .venv/bin/python $Q/scripts/range_check.py $R > $D/range.log 2>&1; echo "range $?"
grep -rn "15–30\|30–40" README.md fansim/cockpit/*.py > $D/qa61_grep.txt
T="tests/test_axial_scripts_oriented.py tests/test_fuse_memory.py tests/test_optimization_argv.py"; [ -f tests/test_r111_cockpit_surrogate.py ] && T="$T tests/test_r111_cockpit_surrogate.py"
.venv/bin/python -m pytest -q -p no:cacheprovider --no-header -rf $T > $D/targeted_tests.txt 2>&1; echo "targeted $?"
grep -n "validate_lt120" tests/test_axial_scripts_oriented.py > $D/qa62_list.txt
