import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "format_guard", os.path.join(HERE, "..", "scripts", "format_guard.py"))
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)

CLEAN = """Hi Anna,

thanks for the call yesterday. I put the numbers we discussed into the attached sheet.
If Thursday still works for you, I will send the invite tomorrow.

Best regards
Bodo
--
Exasync OU, Tallinn
"""


def test_clean_body_passes():
    assert fg.check_text(CLEAN) == []


def test_em_dash_is_flagged_everywhere_even_in_signature():
    body = CLEAN.replace("Tallinn", "Tallinn — Estonia")
    findings = fg.check_text(body)
    assert len(findings) == 1 and "em dash" in findings[0]


def test_markdown_and_html_formatting_flagged():
    body = "Hi Anna,\n\n**Important:** see below\n- first point\n<b>bold</b>\n# Heading\n\nBest regards\nBodo\n"
    kinds = " | ".join(fg.check_text(body))
    for expected in ("Markdown bold", "bullet list", "HTML formatting", "heading"):
        assert expected in kinds, kinds


def test_formatting_inside_signature_is_allowed():
    body = "Hi Anna,\n\nshort note.\n\nBest regards\nBodo\n<b>Exasync</b>\n- Tallinn\n"
    assert fg.check_text(body) == []


def test_placeholder_and_team_salutation():
    body = "Hello team,\n\nHi {{first_name}}, your order [Company] is ready.\n\nBest regards\nBodo\n"
    findings = fg.check_text(body)
    assert any("team salutation" in f for f in findings)
    assert sum("placeholder" in f for f in findings) == 1  # one line, one finding


def test_double_signoff():
    body = "Hi Anna,\n\ntext.\n\nBest regards\nBodo\n\nKind regards\nBodo\n"
    assert any("double sign-off" in f for f in fg.check_text(body))


def test_scan_dir_finds_template_dash_and_respects_pragma(tmp_path):
    (tmp_path / "mail.py").write_text(
        'subject = "Offer — today"\nbody = "<b>hi</b> " + name  # format-guard-ok\n', encoding="utf-8")
    (tmp_path / "unrelated.py").write_text('x = "a — b"\n', encoding="utf-8")
    findings = fg.scan_dir(str(tmp_path))
    assert len(findings) == 1 and "mail.py:1" in findings[0]


def test_cli_exit_codes(capsys):
    assert fg.main(["check", "--text", "Hi Anna,\n\nok\n\nBest regards\nBodo"]) == 0
    assert fg.main(["check", "--text", "Hi Anna – quick one"]) == 1
    out = capsys.readouterr().out
    assert "clean" in out and "1 finding" in out
