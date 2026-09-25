# Submission text for the Claude Code plugin directory

Form: https://platform.claude.com/plugins/submit (filled in by hand, one submission per plugin or one for the marketplace, depending on what the form asks for).

## Marketplace

- Repository URL: https://github.com/ExasyncOU/claude-plugins
- Marketplace name: `exasync-plugins`
- Owner: Exasync OU, https://exasync.ai
- Contact: security@exasync.ai (security) and the issue tracker of the repository (everything else)
- License: MIT
- Short description (under 200 characters):
  Small, dependency-free Claude Code plugins from running an autonomous AI company: a plain-text email gate, a decision precedent memory, and a usage guard hook.

## Plugin: email-format-guard

- Source: https://github.com/ExasyncOU/claude-plugins/tree/main/plugins/email-format-guard
- Category: productivity
- One line: Deterministic pre-send gate for customer-facing email.
- Description:
  Fails an email draft before it goes out if it contains an em or en dash, formatting in the body (bold, bullets, headings, HTML tags, inline styles), an unresolved placeholder, a team salutation or a double sign-off. Scan mode walks pipeline code and reports the same violations hard-wired into string literals. Python 3.10+, no dependencies, exit code 0 or 1 with line numbers.
- Why it matters: generated email that looks generated does not get replies. The gate turns a style rule into a test.

## Plugin: decision-precedent

- Source: https://github.com/ExasyncOU/claude-plugins/tree/main/plugins/decision-precedent
- Category: productivity
- One line: Never ask the human the same question twice.
- Description:
  A local decision memory for agents. Before escalating a question, the skill searches stored decisions and applies a strong match; after a human decides, the answer is stored with rationale, domain and author; every application is logged as applied or rejected so weak precedents surface. JSON store in the repository, lexical scoring, optional external backend via one environment variable.
- Why it matters: in an agent-run company the scarce resource is human attention. This keeps decisions from being asked twice across sessions.

## Plugin: usage-guard

- Source: https://github.com/ExasyncOU/claude-plugins/tree/main/plugins/usage-guard
- Category: productivity
- One line: Show subscription usage every turn and stop expensive commands before the limit.
- Description:
  Two hooks: UserPromptSubmit prints one usage line whenever the numbers move; PreToolUse for Bash denies commands matching a configurable expensive list at 85 percent and everything but checkpoint and handover commands at 92 percent. Reads a local status file that you feed from /usage or your own script. Never blocks on its own failure.
- Why it matters: parallel sessions on one subscription drain the weekly limit without warning. The guard turns a hard stop into a clean hand-over.

## Checklist before sending

- Release v0.1.0 exists and installs with `claude plugin install <name>@exasync-plugins`.
- Demo GIFs render in the README.
- SECURITY.md and issue templates are present.
- CI is green on main.
