from fansim.cockpit.score_caption import score_caption, stamp_score_extra


def test_score_caption_lists_hose_duct_and_print_k():
    text = score_caption({
        "preset": "case",
        "load_pa": 8.0,
        "duct": "circular",
        "print_k_cfm": 0.95,
        "print_k_eta": 0.92,
    })
    assert "hose: case 8 Pa @ 50 CFM" in text
    assert "circular duct" in text
    assert "printed ×0.95" in text
    assert "×0.92" in text


def test_score_caption_beam_regime_warn():
    text = score_caption({"beam_regime_ok": False, "beam_aspect": 0.98})
    assert "WARN beam aspect 0.98" in text
    assert "§19.18" in text


def test_score_caption_near_stall_warn():
    text = score_caption({"near_stall": True, "near_stall_reason": "incidence 12.1 deg >= stall 10.0 deg"})
    assert "near stall" in text.lower()
    assert "incidence" in text


def test_score_caption_empty_does_not_claim_circular():
    text = score_caption({})
    assert "circular" not in text.lower()
    assert text == ""


def test_score_caption_adds_screening_when_not_grid_converged():
    """#6: Assess CFM must carry screening / rank-not-absolute honesty."""
    text = score_caption({"grid_converged": False, "preset": "case", "load_pa": 8.0})
    assert "hose: case 8 Pa @ 50 CFM" in text
    low = text.lower()
    assert "screening" in low or "not absolute" in low or "compare designs" in low
    assert "gci" in low or "rank" in low


def test_score_caption_skips_screening_when_grid_converged():
    text = score_caption({"grid_converged": True, "preset": "case", "load_pa": 8.0})
    assert "screening" not in text.lower()


def test_stamp_score_extra_copies_raw_and_hose():
    extra: dict = {}
    stamp_score_extra(
        extra,
        {"duct": "circular", "print_k_cfm": 0.95, "print_k_eta": 0.92, "k": 1.2, "dp_op_pa": 6.0, "q_ref_cfm": 50.0},
        load_pa=20.0,
        preset="heatsink",
    )
    assert extra["load_pa"] == 20.0
    assert extra["preset"] == "heatsink"
    assert extra["duct"] == "circular"
    assert extra["print_k_cfm"] == 0.95
    assert extra["k"] == 1.2
    assert extra.get("op_cfd") is None
    assert extra["refine_op"] is False


def test_score_caption_lists_op_cfd_when_present():
    text = score_caption({"op_cfd": "solved"})
    assert "op CFD: solved" in text


def test_stamp_score_extra_copies_refine_op():
    extra: dict = {}
    stamp_score_extra(
        extra,
        {"op_cfd": "solved", "cfm_op_alg": 42.0},
        load_pa=8.0,
        preset="case",
        refine_op=True,
    )
    assert extra["refine_op"] is True
    assert extra["op_cfd"] == "solved"
    assert extra["cfm_op_alg"] == 42.0


def test_stamp_score_extra_off_does_not_invent_op_cfd():
    extra: dict = {}
    stamp_score_extra(
        extra, {"op_cfd": "solved"}, load_pa=1.0, preset="legacy", refine_op=False,
    )
    assert extra["refine_op"] is False
    assert "op_cfd" not in extra


def test_fresh_assess_clears_an_old_scored_case_pointer():
    """Review finding: after a re-Assess the score lives in the design's own folder again."""
    from fansim.cockpit.score_caption import stamp_score_extra
    extra = {"case_dir": "screen_rank_audit/t9005/full"}
    stamp_score_extra(extra, {}, load_pa=8.0, preset="case")
    assert "case_dir" not in extra
    stamp_score_extra(extra, {}, load_pa=8.0, preset="case", case_dir="screen_rank_audit/x/full")
    assert extra["case_dir"] == "screen_rank_audit/x/full"


def test_score_caption_flags_unconverged_loaded_point():
    """QA-65 / K1: an unconverged loaded point is shown on the scored design."""
    extra = stamp_score_extra({}, {"converged": False}, load_pa=8.0, preset="case", refine_op=False)
    assert extra["converged"] is False
    assert "did not settle" in score_caption(extra)


def test_score_caption_no_unconverged_flag_when_settled_or_unknown():
    """Only False warns: converged, None and old designs without the key stay silent."""
    for raw in ({"converged": True}, {"converged": None}, {}):
        extra = stamp_score_extra({}, raw, load_pa=8.0, preset="case", refine_op=False)
        assert "did not settle" not in score_caption(extra)
    assert "did not settle" not in score_caption({"preset": "case", "load_pa": 8.0})
