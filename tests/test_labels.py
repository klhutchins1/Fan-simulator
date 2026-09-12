from fansim.cockpit.labels import run_label


def test_known_run_uses_english_name():
    assert run_label("opt_realframe") == "Tip constrained to 110 mm A12x25 frame"


def test_unknown_run_echoes_folder_name():
    assert run_label("opt_brand_new") == "opt_brand_new"


def test_empty_run_is_empty():
    assert run_label("") == ""
