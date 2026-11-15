"""R3.6: CONTRIBUTING, CHANGELOG, and issue templates exist and point at the rules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(rel: str) -> str:
    path = ROOT / rel
    assert path.is_file(), rel
    return path.read_text(encoding="utf-8")


def test_contributing_points_at_agents_and_states_the_rules():
    text = _text("CONTRIBUTING.md")
    lower = text.lower()
    assert "AGENTS.md" in text
    assert "pre-register" in lower
    assert "tests first" in lower
    assert "4 pm" in lower and "9 pm" in lower
    assert "one branch" in lower
    assert "force-push" in lower
    assert "master" in lower


def test_changelog_is_unreleased_only_and_records_the_print_id_code_change():
    text = _text("CHANGELOG.md")
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    assert headings == ["## Unreleased"]
    lower = text.lower()
    assert "qa-73" in lower
    assert "un-mirror" in lower
    assert "coupon" in lower
    assert "has not passed" in lower
    assert "v0.1.0" not in text


def test_issue_templates_ask_for_print_id_expected_and_what_happened():
    bug = _text(".github/ISSUE_TEMPLATE/bug_report.md").lower()
    measure = _text(".github/ISSUE_TEMPLATE/measurement_validation.md").lower()
    for text in (bug, measure):
        assert "print-id" in text
        assert "what you expected" in text
        assert "what happened" in text
