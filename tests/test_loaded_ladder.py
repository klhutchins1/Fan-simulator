from fansim.validation.loaded_ladder import ladder_verdict


def R(b, q, c=True):
    return {"back_pa": b, "cfm": q, "converged": c}


def test_pass_when_curve_matches():
    rows = [R(0, 58.0), R(5, 45.0), R(10, 31.0), R(15, 18.0), R(20, 6.0)]
    v = ladder_verdict(rows)
    assert v["verdict"] == "PASS", v
    assert 17.9 <= v["shutoff_pa"] <= 27.9


def test_fail_on_early_collapse():
    rows = [R(0, 58.7), R(5, 21.6, False), R(10, -6.2), R(15, -72.5)]
    assert ladder_verdict(rows)["verdict"] == "FAIL"


def test_unconverged_loaded_point_is_inconclusive_even_if_in_band():
    rows = [R(0, 58.0), R(5, 45.0, False), R(10, 31.0), R(15, 18.0), R(20, 6.0)]
    v = ladder_verdict(rows)
    assert v["verdict"] == "INCONCLUSIVE" and any("converge" in r for r in v["reasons"])


def test_free_air_out_of_tolerance_fails():
    rows = [R(0, 50.0), R(5, 40.0), R(10, 30.0), R(15, 18.0), R(20, 6.0)]
    assert ladder_verdict(rows)["verdict"] == "FAIL"
