#!/usr/bin/env python3
"""Render the demo GIFs in docs/ from real command output.

Each demo is a list of (command, cwd, env) steps. The command is executed, its output
captured, and both are typed into a terminal-styled frame sequence. No screen
recording, no external tools: Pillow only.

  python tools/make_gif.py            # all demos
  python tools/make_gif.py usage-guard
"""
import json
import os
import subprocess
import sys
import tempfile
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
PY = sys.executable
W, H, PAD, LINE = 900, 420, 18, 20
BG, FG, DIM, PROMPT, OK, ERR = (14, 14, 15), (230, 230, 230), (150, 150, 160), (77, 74, 255), (80, 200, 120), (255, 110, 110)


def font(size=14):
    for name in ("consola.ttf", "cour.ttf", "DejaVuSansMono.ttf", "Menlo.ttc"):
        for base in ("C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/System/Library/Fonts"):
            p = os.path.join(base, name)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


FONT = font()


def frame(lines, cursor=True):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, W, 28), radius=0, fill=(30, 30, 36))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse((12 + i * 20, 8, 24 + i * 20, 20), fill=c)
    d.text((W // 2 - 40, 6), "claude code", fill=DIM, font=FONT)
    y = 36
    shown = lines[-((H - 36 - PAD) // LINE):]
    for kind, text in shown:
        color = {"prompt": FG, "out": FG, "ok": OK, "err": ERR, "dim": DIM}[kind]
        if kind == "prompt":
            d.text((PAD, y), "$ ", fill=PROMPT, font=FONT)
            d.text((PAD + 18, y), text, fill=color, font=FONT)
        else:
            d.text((PAD, y), text, fill=color, font=FONT)
        y += LINE
    if cursor:
        d.rectangle((PAD, y, PAD + 8, y + 15), fill=FG)
    return img


PRETTY = {}  # real temp paths -> what the demo shows instead


def run(cmd, cwd, env):
    proc = subprocess.run(cmd, cwd=cwd, env={**os.environ, "PYTHONIOENCODING": "utf-8", **env},
                          capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False)
    out = (proc.stdout + proc.stderr).rstrip("\n")
    for real, nice in PRETTY.items():
        for variant in (real, real.replace("\\", "\\\\"), real.replace("\\", "/")):
            out = out.replace(variant, nice)
    return out, proc.returncode


def render(name, steps):
    frames, durations, lines = [], [], []
    for cmd, shown, cwd, env in steps:
        typed = ""
        for ch in shown:
            typed += ch
            frames.append(frame(lines + [("prompt", typed)]))
            durations.append(35)
        frames.append(frame(lines + [("prompt", typed)]))
        durations.append(400)
        out, rc = run(cmd, cwd, env)
        lines.append(("prompt", shown))
        for l in out.splitlines()[:16]:
            kind = "ok" if l.startswith(("FORMAT GATE: clean", "USAGE", "=== ")) or '"ok": true' in l else \
                   "err" if l.startswith(("FORMAT GATE:", "  - ")) or "deny" in l else "out"
            for part in textwrap.wrap(l, 118, subsequent_indent="    ") or [""]:
                lines.append((kind, part))
        frames.append(frame(lines))
        durations.append(2600)
    frames.append(frame(lines, cursor=False))
    durations.append(3000)
    os.makedirs(DOCS, exist_ok=True)
    out = os.path.join(DOCS, f"{name}.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    print(f"wrote {out} ({len(frames)} frames)")


def demos():
    tmp = tempfile.mkdtemp(prefix="plugin-demo-")
    draft = os.path.join(tmp, "draft.txt")
    with open(draft, "w", encoding="utf-8") as fh:
        fh.write("Hi all,\n\n**Quick update** on the pilot \u2014 we deliver by Friday.\n- setup done\n"
                 "Your contact: {{first_name}}\n\nBest regards\nBodo\n\nKind regards\nBodo\n")
    clean = os.path.join(tmp, "clean.txt")
    with open(clean, "w", encoding="utf-8") as fh:
        fh.write("Hi Anna,\n\nquick update on the pilot: setup is done, we deliver by Friday.\n\nBest regards\nBodo\n")
    fg = os.path.join(ROOT, "plugins", "email-format-guard", "scripts", "format_guard.py")
    dp = os.path.join(ROOT, "plugins", "decision-precedent", "scripts", "decision.py")
    ug = os.path.join(ROOT, "plugins", "usage-guard", "scripts")
    store_env = {"DECISION_STORE": os.path.join(tmp, "decisions.json")}
    status_env = {"USAGE_GUARD_STATUS": os.path.join(tmp, "status.json"), "USAGE_GUARD_CONFIG": os.path.join(tmp, "none")}
    PRETTY[os.path.join(tmp, "decisions.json")] = ".claude/decisions.json"
    PRETTY[os.path.join(tmp, "status.json")] = "~/.claude/usage-guard/status.json"
    counter = [0]

    def hook(payload, shown):
        counter[0] += 1
        hook_in = os.path.join(tmp, f"hook{counter[0]}.json")
        with open(hook_in, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        return ([PY, "-c", f"import subprocess,sys;sys.exit(subprocess.run([sys.executable,r'{ug}/usage_hook.py'],"
                            f"stdin=open(r'{hook_in}')).returncode)"], shown, ROOT, status_env)

    return {
        "email-format-guard": [
            ([PY, fg, "check", "--file", draft], "python format_guard.py check --file draft.txt", ROOT, {}),
            ([PY, fg, "check", "--file", clean], "python format_guard.py check --file clean.txt", ROOT, {}),
        ],
        "decision-precedent": [
            ([PY, dp, "search", "--domain", "architecture", "own table for project threads or reuse the todo table?"],
             'python decision.py search --domain architecture "own table for project threads or reuse the todo table?"', ROOT, store_env),
            ([PY, dp, "store", "--domain", "architecture", "--slug", "threads-vs-todos",
              "--question", "Own table for project threads or reuse the todo table?",
              "--decision", "Own table. Todos stay a flat list; a thread may point to a todo.",
              "--rationale", "Done and to-do have different lifecycles.", "--by", "human"],
             'python decision.py store --domain architecture --slug threads-vs-todos --question "..." --decision "Own table..." --by human', ROOT, store_env),
            ([PY, dp, "search", "--domain", "architecture", "should project threads get their own table?"],
             'python decision.py search --domain architecture "should project threads get their own table?"', ROOT, store_env),
            ([PY, dp, "feedback", "--key", "decisions/architecture/threads-vs-todos", "--outcome", "applied"],
             "python decision.py feedback --key decisions/architecture/threads-vs-todos --outcome applied", ROOT, store_env),
        ],
        "usage-guard": [
            ([PY, os.path.join(ug, "usage_set.py"), "--session", "42", "--weekly", "61", "--account", "team",
              "--session-reset", "2026-09-07T10:00:00+00:00", "--weekly-reset", "2026-09-12T05:00:00+00:00"],
             "python usage_set.py --session 42 --weekly 61 --account team", ROOT, status_env),
            hook({"hook_event_name": "UserPromptSubmit", "session_id": "demo1"}, "# next prompt: the hook adds one line of context"),
            ([PY, os.path.join(ug, "usage_set.py"), "--session", "87"], "python usage_set.py --session 87", ROOT, status_env),
            hook({"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "demo2",
                  "tool_input": {"command": "python -m pytest tests"}}, "# Claude tries: python -m pytest tests"),
            hook({"hook_event_name": "PreToolUse", "tool_name": "Bash", "session_id": "demo2",
                  "tool_input": {"command": "python checkpoint.py"}}, "# Claude tries: python checkpoint.py"),
        ],
    }


if __name__ == "__main__":
    wanted = sys.argv[1:]
    for name, steps in demos().items():
        if not wanted or name in wanted:
            render(name, steps)
