#!/usr/bin/env python3
"""decision-precedent: search, store and give feedback on decisions.

Default backend: a JSON file (.claude/decisions.json in the current project, or
$DECISION_STORE). Optional backend: $DECISION_BACKEND_CMD, a command that receives
the same subcommand and arguments and prints the same JSON.

Standard library only. Python 3.10+.
"""
import argparse
import datetime
import json
import math
import os
import re
import shlex
import subprocess
import sys

APPLY_THRESHOLD = 0.60
CONTEXT_THRESHOLD = 0.35
DEFAULT_STORE = os.path.join(".claude", "decisions.json")
TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "the", "a", "an", "or", "and", "of", "to", "in", "on", "for", "is", "are", "we", "it", "be",
    "do", "does", "should", "with", "vs", "versus", "der", "die", "das", "und", "oder", "fuer",
    "für", "ist", "ein", "eine", "wir", "mit", "zu", "im", "in", "auf", "als", "bei",
}


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def store_path() -> str:
    return os.environ.get("DECISION_STORE") or DEFAULT_STORE


def load_store(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return {"version": 1, "decisions": {}}
    if not isinstance(data, dict) or not isinstance(data.get("decisions"), dict):
        raise SystemExit(f"decision store is not valid: {path}")
    return data


def save_store(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


def tokens(text: str) -> list[str]:
    return [t for t in TOKEN.findall((text or "").lower()) if t not in STOPWORDS and len(t) > 1]


def score(query: str, rec: dict, domain: str | None) -> float:
    """Lexical relevance in [0, 1]: weighted token overlap with idf-like damping."""
    q = set(tokens(query))
    if not q:
        return 0.0
    fields = (
        (rec.get("question", ""), 1.0),
        (rec.get("decision", ""), 0.7),
        (rec.get("rationale", ""), 0.5),
        (" ".join(rec.get("tags", [])) + " " + rec.get("slug", "").replace("-", " "), 0.8),
    )
    hit = 0.0
    for text, weight in fields:
        toks = set(tokens(text))
        if not toks:
            continue
        overlap = len(q & toks)
        if overlap:
            hit += weight * overlap / math.sqrt(len(q) * len(toks))
    s = min(1.0, hit / 1.6)
    if domain and rec.get("domain") == domain:
        s = min(1.0, s + 0.05)
    return round(s, 3)


def verdict(s: float) -> str:
    if s >= APPLY_THRESHOLD:
        return "APPLY (strong precedent: read it and apply it, do not ask again)"
    if s >= CONTEXT_THRESHOLD:
        return "CONTEXT (related: decide deliberately with this as context)"
    return "WEAK (decide yourself if the strategy is clear, otherwise ask)"


# ---------------------------------------------------------------- backends
def delegate(argv: list[str]) -> int:
    cmd = os.environ.get("DECISION_BACKEND_CMD")
    if not cmd:
        return -1
    proc = subprocess.run(shlex.split(cmd) + argv, text=True)
    return proc.returncode


def do_search(args) -> int:
    data = load_store(store_path())
    rows = []
    for key, rec in data["decisions"].items():
        s = score(args.query, rec, args.domain)
        if s > 0:
            rows.append((s, key, rec))
    rows.sort(key=lambda r: (-r[0], r[1]))
    rows = rows[: args.limit]
    if args.json:
        print(json.dumps([{"key": k, "score": s, **r} for s, k, r in rows], ensure_ascii=False, indent=1))
        return 0
    print("=== DECISION PRECEDENT / SEARCH ===")
    print(f"Question: {args.query}")
    if not rows:
        print("\nNo precedent. Decide yourself if the strategy is clear, otherwise ask the human.")
        return 0
    print(f"Best match: score {rows[0][0]:.2f} -> {verdict(rows[0][0])}\n")
    for i, (s, key, rec) in enumerate(rows, 1):
        mark = ">>" if i == 1 else "  "
        print(f"{mark} [{s:.2f}] {key}  (by {rec.get('by')}, {rec.get('date')})")
        print(f"       Q: {rec.get('question', '')[:160]}")
        print(f"       D: {rec.get('decision', '')[:160]}")
        outcomes = rec.get("outcomes") or []
        if outcomes:
            applied = sum(o.get("outcome") == "applied" for o in outcomes)
            print(f"       outcomes: {applied} applied, {len(outcomes) - applied} rejected")
    return 0


def do_store(args) -> int:
    path = store_path()
    data = load_store(path)
    key = f"decisions/{args.domain}/{args.slug}"
    previous = data["decisions"].get(key) or {}
    rec = {
        "domain": args.domain,
        "slug": args.slug,
        "question": args.question,
        "decision": args.decision,
        "rationale": args.rationale or "",
        "by": args.by,
        "scope": args.scope or "",
        "date": args.date or datetime.date.today().isoformat(),
        "tags": [t.strip() for t in (args.tags or "").split(",") if t.strip()],
        "outcomes": previous.get("outcomes", []),
        "updated_at": now_iso(),
    }
    data["decisions"][key] = rec
    save_store(path, data)
    print(json.dumps({"ok": True, "key": key, "by": args.by, "store": path, "replaced": bool(previous)},
                     ensure_ascii=False))
    return 0


def do_feedback(args) -> int:
    path = store_path()
    data = load_store(path)
    rec = data["decisions"].get(args.key)
    if not rec:
        print(json.dumps({"ok": False, "key": args.key, "error": "unknown key"}))
        return 1
    rec.setdefault("outcomes", []).append({"ts": now_iso(), "outcome": args.outcome, "note": args.note or ""})
    save_store(path, data)
    print(json.dumps({"ok": True, "key": args.key, "outcome": args.outcome,
                      "outcomes_total": len(rec["outcomes"])}, ensure_ascii=False))
    return 0


def do_list(args) -> int:
    data = load_store(store_path())
    rows = sorted(data["decisions"].items())
    if args.domain:
        rows = [(k, r) for k, r in rows if r.get("domain") == args.domain]
    if not rows:
        print("No decisions stored.")
        return 0
    for key, rec in rows:
        print(f"{key}  [{rec.get('by')}, {rec.get('date')}]  {rec.get('decision', '')[:100]}")
    return 0


def do_show(args) -> int:
    data = load_store(store_path())
    rec = data["decisions"].get(args.key)
    if not rec:
        print(f"unknown key: {args.key}")
        return 1
    print(json.dumps({"key": args.key, **rec}, ensure_ascii=False, indent=1))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Decision precedents: search, store, feedback.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("search", help="search precedents before deciding")
    sp.add_argument("query")
    sp.add_argument("--domain")
    sp.add_argument("--limit", type=int, default=5)
    sp.add_argument("--json", action="store_true")

    st = sub.add_parser("store", help="store a decision after it was made")
    st.add_argument("--domain", required=True)
    st.add_argument("--slug", required=True)
    st.add_argument("--question", required=True)
    st.add_argument("--decision", required=True)
    st.add_argument("--rationale")
    st.add_argument("--by", default="human", choices=["human", "agent"])
    st.add_argument("--scope")
    st.add_argument("--tags", help="comma separated")
    st.add_argument("--date", help="ISO date (default: today)")

    fb = sub.add_parser("feedback", help="report whether an applied precedent worked")
    fb.add_argument("--key", required=True)
    fb.add_argument("--outcome", required=True, choices=["applied", "rejected"])
    fb.add_argument("--note")

    ls = sub.add_parser("list", help="list stored decisions")
    ls.add_argument("--domain")

    sh = sub.add_parser("show", help="show one decision")
    sh.add_argument("--key", required=True)
    return ap


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    if args.cmd in ("search", "store", "feedback"):
        rc = delegate(argv)
        if rc >= 0:
            return rc
    return {"search": do_search, "store": do_store, "feedback": do_feedback,
            "list": do_list, "show": do_show}[args.cmd](args)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
