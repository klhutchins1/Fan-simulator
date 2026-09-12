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


def test_score_caption_empty_does_not_claim_circular():
    text = score_caption({})
    assert "circular" not in text.lower()
    assert text == ""


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
