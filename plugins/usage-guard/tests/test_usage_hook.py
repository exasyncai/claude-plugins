import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "..", "scripts", "usage_hook.py")
SETTER = os.path.join(HERE, "..", "scripts", "usage_set.py")


def load_hook():
    spec = importlib.util.spec_from_file_location("usage_hook", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_hook(env, payload):
    proc = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True,
                          text=True, env={**os.environ, **env})
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def write_status(tmp_path, session, weekly, fetched="2999-01-01T00:00:00+00:00"):
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"session_pct": session, "weekly_pct": weekly, "fetched_at": fetched,
                                "session_reset_at": "2026-09-07T10:00:00+00:00",
                                "weekly_reset_at": "2026-09-12T05:00:00+00:00", "account": "team"}))
    return {"USAGE_GUARD_STATUS": str(path), "USAGE_GUARD_CONFIG": str(tmp_path / "missing.json")}


def test_stage_logic():
    hook = load_hook()
    cfg = hook.DEFAULTS
    assert hook.stage_for({"session_pct": 10, "weekly_pct": 10}, cfg) == "normal"
    assert hook.stage_for({"session_pct": 85, "weekly_pct": 10}, cfg) == "pause"
    assert hook.stage_for({"session_pct": 10, "weekly_pct": 85}, cfg) == "pause"
    assert hook.stage_for({"session_pct": 92, "weekly_pct": 10}, cfg) == "hard"


def test_prompt_line_emitted_once_then_silent(tmp_path):
    env = write_status(tmp_path, 40, 55)
    payload = {"hook_event_name": "UserPromptSubmit", "session_id": "s1"}
    first = run_hook(env, payload)
    assert first.startswith("USAGE team: session 40% ") and "Stage: NORMAL" in first
    assert run_hook(env, payload) == ""  # unchanged numbers: no repeat


def test_pause_denies_expensive_but_allows_checkpoint(tmp_path):
    env = write_status(tmp_path, 86, 20)
    deny = json.loads(run_hook(env, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "s2",
                                     "tool_input": {"command": "python -m pytest tests"}}))
    assert deny["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "PAUSE" in deny["hookSpecificOutput"]["permissionDecisionReason"]
    ok = run_hook(env, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "s2",
                        "tool_input": {"command": "git status"}})
    assert "deny" not in ok


def test_hard_denies_everything_but_allowed(tmp_path):
    env = write_status(tmp_path, 95, 20)
    deny = json.loads(run_hook(env, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "s3",
                                     "tool_input": {"command": "python build.py"}}))
    assert deny["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "HARD LIMIT" in deny["hookSpecificOutput"]["permissionDecisionReason"]
    assert "deny" not in run_hook(env, {"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "s3",
                                        "tool_input": {"command": "python checkpoint.py --by me"}})


def test_stale_status_is_flagged(tmp_path):
    env = write_status(tmp_path, 10, 10, fetched="2020-01-01T00:00:00+00:00")
    out = run_hook(env, {"hook_event_name": "UserPromptSubmit", "session_id": "s4"})
    assert "MIN OLD" in out


def test_missing_status_is_silent_and_never_blocks(tmp_path):
    env = {"USAGE_GUARD_STATUS": str(tmp_path / "nope.json")}
    assert run_hook(env, {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                          "tool_input": {"command": "pytest"}}) == ""


def test_usage_set_writes_status(tmp_path):
    env = {**os.environ, "USAGE_GUARD_STATUS": str(tmp_path / "status.json")}
    proc = subprocess.run([sys.executable, SETTER, "--session", "42", "--weekly", "61", "--account", "team"],
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    data = json.loads((tmp_path / "status.json").read_text())
    assert data["session_pct"] == 42 and data["weekly_pct"] == 61 and data["fetched_at"]
