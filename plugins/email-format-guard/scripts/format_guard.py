#!/usr/bin/env python3
"""email-format-guard: deterministic pre-send gate for customer-facing email text.

check: verify a body or file (exit 0 clean, exit 1 findings).
scan:  walk pipeline code for violations hard-wired into email templates.

Standard library only. Python 3.10+.
"""
import argparse
import os
import re
import sys

DASHES = {"—": "em dash", "–": "en dash"}  # format-guard-ok: detection map
HTML_TAGS = re.compile(r"<\s*(b|strong|ul|ol|li|h[1-6]|table|em|i)\b|style\s*=", re.I)
MD_BOLD = re.compile(r"\*\*[^*]+\*\*")
MD_BULLET = re.compile(r"^\s*[-*•]\s+\S")
MD_HEADING = re.compile(r"^\s*#{1,6}\s+\S")
TEAM_SALUTATION = re.compile(
    r"^\s*(hi|hello|hey|dear|hallo|liebes|sehr geehrtes)\s+(team|all|everyone|alle)\b", re.I)
PLACEHOLDER = re.compile(
    r"\{\{?\s*\w+\s*\}?\}|\[(name|first_?name|last_?name|company|vorname|firma|anrede)\]"
    r"|<(name|first_?name|company|vorname|firma)>", re.I)
CLOSING = re.compile(
    r"^(best regards|kind regards|warm regards|regards|best,|cheers|sincerely|thanks,"
    r"|mit freundlichen gr|viele gr|beste gr|liebe gr)", re.I)
SIGNATURE_START = re.compile(r"^(--\s*$|" + CLOSING.pattern[2:], re.I)
MAIL_HINT = re.compile(r"subject|body|betreff|mail|greeting|salutation|anrede|dear |hallo ", re.I)
SCAN_EXT = {".py", ".ps1", ".js", ".mjs", ".ts", ".html"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".venv", "venv", "dist", "build"}
PRAGMA = "format-guard-ok"


def check_text(text: str) -> list[str]:
    """Return a list of findings for an email body. Empty list means clean."""
    findings = []
    in_signature = False
    closings = 0
    for no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        for ch, name in DASHES.items():
            if ch in line:
                findings.append(f"line {no}: {name} -> '{stripped[:60]}'")
        if not in_signature and SIGNATURE_START.match(stripped):
            in_signature = True
        if CLOSING.match(stripped):
            closings += 1
        if in_signature:
            continue
        if HTML_TAGS.search(line):
            findings.append(f"line {no}: HTML formatting in body")
        if MD_BOLD.search(line):
            findings.append(f"line {no}: Markdown bold in body")
        if MD_BULLET.match(line):
            findings.append(f"line {no}: bullet list in body")
        if MD_HEADING.match(line):
            findings.append(f"line {no}: heading in body")
        if no <= 3 and TEAM_SALUTATION.match(line):
            findings.append(f"line {no}: team salutation instead of a first name")
        if PLACEHOLDER.search(line):
            findings.append(f"line {no}: unresolved placeholder -> '{stripped[:60]}'")
    if closings >= 2:
        findings.append(f"{closings} closing formulas in one body (double sign-off)")
    return findings


def scan_dir(root: str) -> list[str]:
    """Return findings for code files under root that render email."""
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if os.path.splitext(fn)[1].lower() not in SCAN_EXT:
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().splitlines()
            except OSError:
                continue
            if not any(MAIL_HINT.search(l) for l in lines):
                continue
            for no, line in enumerate(lines, 1):
                if PRAGMA in line:
                    continue
                for ch, name in DASHES.items():
                    if ch in line and ('"' in line or "'" in line):
                        findings.append(f"{path}:{no}: {name} in string literal")
                if HTML_TAGS.search(line) and MAIL_HINT.search(line):
                    findings.append(f"{path}:{no}: HTML formatting next to email template")
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Email format gate")
    sub = parser.add_subparsers(dest="mode", required=True)
    p_check = sub.add_parser("check", help="check an email body or file")
    group = p_check.add_mutually_exclusive_group(required=True)
    group.add_argument("--file")
    group.add_argument("--text")
    p_scan = sub.add_parser("scan", help="scan pipeline code for hard-wired violations")
    p_scan.add_argument("--dir", required=True)
    args = parser.parse_args(argv)

    if args.mode == "check":
        if args.text is not None:
            text = args.text
        else:
            with open(args.file, encoding="utf-8") as fh:
                text = fh.read()
        findings = check_text(text)
    else:
        findings = scan_dir(args.dir)

    if findings:
        print(f"FORMAT GATE: {len(findings)} finding(s):")
        for f in findings:
            print(f"  - {f}")
        return 1
    print("FORMAT GATE: clean")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
