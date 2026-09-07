import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "decision", os.path.join(HERE, "..", "scripts", "decision.py"))
dec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dec)


def run(monkeypatch, tmp_path, argv):
    monkeypatch.setenv("DECISION_STORE", str(tmp_path / "decisions.json"))
    monkeypatch.delenv("DECISION_BACKEND_CMD", raising=False)
    return dec.main(argv)


def test_store_search_feedback_roundtrip(monkeypatch, tmp_path, capsys):
    assert run(monkeypatch, tmp_path, [
        "store", "--domain", "architecture", "--slug", "threads-vs-todos",
        "--question", "Separate table for project threads or reuse the todo table?",
        "--decision", "Separate table. Todos stay a flat list.",
        "--rationale", "Done and to-do have different lifecycles.", "--by", "human"]) == 0
    stored = json.loads(capsys.readouterr().out)
    assert stored["ok"] and stored["key"] == "decisions/architecture/threads-vs-todos"

    assert run(monkeypatch, tmp_path, [
        "search", "--domain", "architecture", "--json",
        "should project threads get their own table or reuse todos"]) == 0
    hits = json.loads(capsys.readouterr().out)
    assert hits and hits[0]["key"] == "decisions/architecture/threads-vs-todos"
    assert hits[0]["score"] >= dec.APPLY_THRESHOLD

    assert run(monkeypatch, tmp_path, [
        "feedback", "--key", "decisions/architecture/threads-vs-todos",
        "--outcome", "applied", "--note", "migration 0042"]) == 0
    assert json.loads(capsys.readouterr().out)["outcomes_total"] == 1

    # storing again keeps the outcome history
    assert run(monkeypatch, tmp_path, [
        "store", "--domain", "architecture", "--slug", "threads-vs-todos",
        "--question", "same", "--decision", "updated", "--by", "agent"]) == 0
    capsys.readouterr()
    assert run(monkeypatch, tmp_path, ["show", "--key", "decisions/architecture/threads-vs-todos"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["decision"] == "updated" and len(shown["outcomes"]) == 1


def test_unrelated_question_is_weak(monkeypatch, tmp_path, capsys):
    run(monkeypatch, tmp_path, [
        "store", "--domain", "ops", "--slug", "backup-hour",
        "--question", "When should the nightly backup run?",
        "--decision", "02:30 local time.", "--by", "human"])
    capsys.readouterr()
    run(monkeypatch, tmp_path, ["search", "--json", "which colour should the login button have"])
    hits = json.loads(capsys.readouterr().out)
    assert not hits or hits[0]["score"] < dec.CONTEXT_THRESHOLD


def test_feedback_unknown_key_fails(monkeypatch, tmp_path, capsys):
    assert run(monkeypatch, tmp_path, ["feedback", "--key", "decisions/x/y", "--outcome", "rejected"]) == 1


def test_verdict_thresholds():
    assert dec.verdict(0.60).startswith("APPLY")
    assert dec.verdict(0.59).startswith("CONTEXT")
    assert dec.verdict(0.35).startswith("CONTEXT")
    assert dec.verdict(0.34).startswith("WEAK")


def test_custom_backend_is_delegated(monkeypatch, tmp_path):
    marker = tmp_path / "called.txt"
    script = tmp_path / "backend.py"
    script.write_text("import sys, pathlib\npathlib.Path(sys.argv[1]).write_text(' '.join(sys.argv[2:]))\n",
                      encoding="utf-8")
    monkeypatch.setenv("DECISION_BACKEND_CMD", f'"{os.sys.executable}" "{script}" "{marker}"')
    monkeypatch.setenv("DECISION_STORE", str(tmp_path / "unused.json"))
    assert dec.main(["search", "anything"]) == 0
    assert marker.read_text(encoding="utf-8") == "search anything"
