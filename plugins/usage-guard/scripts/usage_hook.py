#!/usr/bin/env python3
"""usage-guard hook (UserPromptSubmit + PreToolUse for Bash).

Reads a small status file with your subscription usage and
  * prints one line of context whenever the numbers changed (UserPromptSubmit),
  * denies commands that match your "expensive" patterns once the pause threshold is
    reached, and denies everything except your "always allowed" patterns past the
    hard threshold (PreToolUse).

The hook never blocks on its own failure: any exception exits 0 without output.
It reads only local files, never the network. Update the status file with
usage_set.py (see README) from whatever source you trust.

Status file (JSON), default ~/.claude/usage-guard/status.json:
  {"session_pct": 42, "weekly_pct": 61,
   "session_reset_at": "2026-09-07T10:00:00+00:00", "weekly_reset_at": "2026-09-12T05:00:00+00:00",
   "fetched_at": "2026-09-07T06:00:00+00:00", "account": "team"}
Config file (JSON, optional), default ~/.claude/usage-guard/config.json:
  {"pause_pct": 85, "hard_pct": 92, "weekly_cap_pct": 85, "stale_minutes": 30,
   "expensive": ["regex", ...], "always_allowed": ["regex", ...]}
"""
import datetime
import json
import os
import re
import sys

HOME_DIR = os.path.join(os.path.expanduser("~"), ".claude", "usage-guard")
STATUS = os.environ.get("USAGE_GUARD_STATUS") or os.path.join(HOME_DIR, "status.json")
CONFIG = os.environ.get("USAGE_GUARD_CONFIG") or os.path.join(HOME_DIR, "config.json")
DEFAULTS = {
    "pause_pct": 85,
    "hard_pct": 92,
    "weekly_cap_pct": 85,
    "stale_minutes": 30,
    "expensive": [r"claude\s+-p", r"pytest", r"npm\s+(test|run\s+build)", r"docker\s+build", r"make\b"],
    "always_allowed": [r"^\s*git\s+(status|log|diff|rev-parse)", r"^\s*(ls|cat|type|dir|pwd|echo)\b",
                       r"checkpoint", r"handover", r"status\.json"],
}


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else default
    except (OSError, ValueError):
        return default


def local_clock(ts: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
        today = datetime.datetime.now(dt.tzinfo).date()
        return dt.strftime("%H:%M") if dt.date() == today else dt.strftime("%a %H:%M")
    except (ValueError, AttributeError):
        return "?"


def stage_for(status: dict, cfg: dict) -> str:
    s = status.get("session_pct") or 0
    w = status.get("weekly_pct") or 0
    if s >= cfg["hard_pct"]:
        return "hard"
    if s >= cfg["pause_pct"] or w >= cfg["weekly_cap_pct"]:
        return "pause"
    return "normal"


def format_line(status: dict, stage: str, stale_min: int | None) -> str:
    acct = status.get("account") or "usage"
    line = "USAGE %s: session %s%% (resets %s), week %s%% (resets %s). Stage: %s." % (
        acct, status.get("session_pct"), local_clock(status.get("session_reset_at") or ""),
        status.get("weekly_pct"), local_clock(status.get("weekly_reset_at") or ""), stage.upper())
    if stale_min is not None:
        line += " STATUS IS %d MIN OLD." % stale_min
    return line


def should_emit(last: dict | None, status: dict, stage: str) -> bool:
    if not last:
        return True
    return (last.get("stage") != stage
            or abs((last.get("session_pct") or 0) - (status.get("session_pct") or 0)) >= 5
            or abs((last.get("weekly_pct") or 0) - (status.get("weekly_pct") or 0)) >= 5)


def blocked_reason(cmd, stage: str, cfg: dict):
    if stage == "normal" or not isinstance(cmd, str):
        return None
    if any(re.search(p, cmd) for p in cfg["always_allowed"]):
        return None
    if stage == "pause" and any(re.search(p, cmd) for p in cfg["expensive"]):
        return ("PAUSE: usage threshold reached. Do not start new expensive runs. Finish what is running, "
                "write a checkpoint or handover note, then stop.")
    if stage == "hard":
        return "HARD LIMIT: only checkpoint and handover commands are allowed now. Wrap up."
    return None


def main() -> int:
    data = json.loads(sys.stdin.read() or "{}")
    event = data.get("hook_event_name", "")
    status = load_json(STATUS, {})
    if not status:
        return 0
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in load_json(CONFIG, {}).items() if k in DEFAULTS})
    stale_min = None
    try:
        fetched = datetime.datetime.fromisoformat(str(status.get("fetched_at")).replace("Z", "+00:00"))
        age = (datetime.datetime.now(datetime.timezone.utc) - fetched).total_seconds() / 60
        if age > cfg["stale_minutes"]:
            stale_min = int(age)
    except (ValueError, TypeError):
        pass
    stage = stage_for(status, cfg)
    line = format_line(status, stage, stale_min)
    memo = os.path.join(os.path.dirname(STATUS), "seen-%s.json" % (data.get("session_id") or "x"))
    last = load_json(memo, None)
    emit = should_emit(last, status, stage) or stale_min is not None
    if emit:
        try:
            os.makedirs(os.path.dirname(memo), exist_ok=True)
            with open(memo, "w", encoding="utf-8") as fh:
                json.dump({"session_pct": status.get("session_pct"), "weekly_pct": status.get("weekly_pct"),
                           "stage": stage}, fh)
        except OSError:
            pass
    if event == "UserPromptSubmit":
        if emit:
            print(line)
        return 0
    if event == "PreToolUse" and data.get("tool_name") == "Bash":
        reason = blocked_reason((data.get("tool_input") or {}).get("command"), stage, cfg)
        if reason:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                     "permissionDecisionReason": line + " " + reason}}))
        elif emit:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": line}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # a broken hook must never block the session
        sys.exit(0)
