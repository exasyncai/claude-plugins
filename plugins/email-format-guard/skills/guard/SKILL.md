---
name: guard
description: Deterministic pre-send gate for customer-facing email text. Checks a draft, a file or a whole pipeline directory for long dashes (em/en dash), formatting inside the body (bold, bullets, headings, tables, inline HTML styling), unresolved placeholders, team salutations and double sign-offs. Use before sending or saving any customer email, before generating an outreach batch, and before deploying code that renders email templates. Keywords - email check, format check, long dash, em dash, plain text mail, draft check, pre-send gate, outreach batch, mail template scan.
---

# Email Format Guard

Plain-text email reads as written by a person. Formatted email reads as generated. This skill is the deterministic gate that enforces that rule before anything leaves the house.

## Mode 1: check a draft (before sending or saving)

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/format_guard.py" check --file draft.txt
python "${CLAUDE_PLUGIN_ROOT}/scripts/format_guard.py" check --text "<email body>"
```

Exit 0 means clean. Exit 1 lists every finding with line number and rule:

- Long dashes: em dash (U+2014) and en dash (U+2013). Replace with a comma, a period, a colon or a plain hyphen.
- Formatting in the body: HTML tags (`<b>`, `<strong>`, `<ul>`, `<ol>`, `<h1>` to `<h6>`, `<table>`, inline `style=`) and Markdown (`**bold**`, bullet lines, `#` headings).
- Salutation: team salutations ("Hi all", "Hello team", "Dear team") and unresolved placeholders (`{name}`, `{{first_name}}`, `[Name]`, `<Company>`).
- Double sign-off: two closing formulas in one body.

The signature block is exempt from the formatting checks: everything after a line containing only `--` or after the first closing formula ("Best regards", "Kind regards", "Mit freundlichen Gruessen" and friends). The dash check applies everywhere.

## Mode 2: scan pipeline code (before deploying)

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/format_guard.py" scan --dir ./pipeline
```

Walks `.py`, `.ps1`, `.js`, `.mjs`, `.ts` and `.html` files that contain email context (subject, body, greeting, mail) and reports long dashes and formatting tags inside string literals. A violation in a template repeats on every pipeline run, so a draft check alone is not enough.

Pragma: a code line containing the comment `format-guard-ok` is skipped in scan mode. Use it for deliberate exceptions such as the guard's own detection maps, and justify every exception.

## Rules for the agent

1. Customer-facing text leaves only after exit 0. If the gate fails, fix the text and run it again. Do not argue with the gate.
2. For batch generation, check the template plus one or two rendered examples before the batch runs.
3. Add the scan mode to the deploy checklist of every pipeline that renders email.
4. The gate checks form, not content. Tone, facts and consent are still your job.
