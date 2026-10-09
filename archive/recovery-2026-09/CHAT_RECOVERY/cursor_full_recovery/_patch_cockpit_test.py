from pathlib import Path

p = Path(r"E:/Projects/programming_2/Fan-simulator/tests/test_cockpit_view.py")
t = p.read_text(encoding="utf-8")
marker = "def test_volute_tab_in_cockpit():"
idx = t.find(marker)
if idx < 0:
    raise SystemExit("marker not found")
new = '''def test_volute_tab_in_cockpit():
    src = _read_cockpit_app_source()
    assert 'value="volute"' in src
    assert "volute_preview" in src
    assert "volute_export" in src
    assert "volute_assess" in src
    assert "evaluate_volute_isolated" in src
    assert "build_volute_preview_isolated" in src
    assert "Volute — radial blower" in src
'''
p.write_text(t[:idx] + new, encoding="utf-8")
print("updated ok")
