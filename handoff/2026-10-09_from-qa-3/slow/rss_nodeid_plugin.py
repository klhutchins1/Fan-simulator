"""Tiny pytest plugin (load with `-p rss_nodeid_plugin`, dir on PYTHONPATH): publishes the running
test's nodeid to $RSS_NODEID_FILE so an external RSS sampler can attribute memory to it, and logs
per-test RSS after each test to $RSS_PERTEST_LOG (nodeid, outcome, rss_mb_after, hwm_mb)."""
import os

_NODE = os.environ.get("RSS_NODEID_FILE", "/tmp/pytest_current_nodeid")
_LOG = os.environ.get("RSS_PERTEST_LOG")
_fh = open(_LOG, "a", buffering=1) if _LOG else None


def _status():
    rss = hwm = 0
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                rss = int(line.split()[1]) // 1024
            elif line.startswith("VmHWM:"):
                hwm = int(line.split()[1]) // 1024
    return rss, hwm


def _publish(text):
    tmp = _NODE + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, _NODE)


def pytest_runtest_logstart(nodeid, location):
    _publish(nodeid)


def pytest_runtest_logreport(report):
    if _fh and report.when == "call" or (_fh and report.when == "setup" and report.outcome != "passed"):
        rss, hwm = _status()
        _fh.write(f"{report.nodeid}\t{report.outcome}\t{rss}\t{hwm}\t{report.duration:.2f}\n")


def pytest_sessionfinish(session, exitstatus):
    _publish("<session finished>")
