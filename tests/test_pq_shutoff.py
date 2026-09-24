"""Shut-off report helper for multi-back P–Q validation rows."""

from __future__ import annotations

from fansim.validation.pq_shutoff import shutoff_report_from_pq_rows


def test_uses_honest_shut_off_when_near_zero():
    rows = [
        {"back_pa": 10.0, "cfm": 8.0, "converged": True},
        {"back_pa": 20.0, "cfm": 2.0, "converged": True},
        {"back_pa": 22.0, "cfm": 0.5, "converged": False},
    ]
    r = shutoff_report_from_pq_rows(rows, published_pa=22.9)
    assert r["n_converged"] == 2
    assert r["lowest_converged_cfm"] == 2.0
    assert r["method"].startswith("shut_off_pa")
    assert r["shutoff_pa"] is not None
    assert r["interim_pass"] in (True, False)


def test_falls_back_to_last_two_proxy_when_far_from_zero():
    rows = [
        {"back_pa": 14.0, "cfm": 11.4, "converged": True},
        {"back_pa": 16.0, "cfm": 9.1, "converged": True},
        {"back_pa": 18.0, "cfm": 6.7, "converged": False},
    ]
    r = shutoff_report_from_pq_rows(rows, published_pa=22.9, q_near_zero=5.0)
    assert r["method"].startswith("last_two_converged")
    assert abs(r["shutoff_pa"] - 23.97) < 0.2
    assert "proxy" in r["note"].lower()


def test_ignores_unconverged_only():
    assert shutoff_report_from_pq_rows(
        [{"back_pa": 18.0, "cfm": 1.0, "converged": False}],
    )["shutoff_pa"] is None


def test_near_shutoff_preset_backs():
    from scripts.run_a12x25_validation import apply_near_shutoff_defaults, build_parser

    ns = build_parser().parse_args(["--near-shutoff"])
    apply_near_shutoff_defaults(ns)
    assert ns.backs.startswith("0,5,10,12")
    assert "26" in ns.backs
    assert ns.iters == 1200
