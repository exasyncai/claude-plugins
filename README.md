# Exasync Claude Code Plugins

Three small, dependency-free Claude Code plugins that stop an agent from sending ugly email, asking the same question twice, and burning the weekly limit. Each one exists because a real incident in an autonomous AI company made it necessary. They run on Python 3.10+ and need no cloud service, no API key and no database.

| Plugin | What it does | Born from |
|---|---|---|
| [email-format-guard](plugins/email-format-guard) | Deterministic pre-send gate for customer-facing email: blocks long dashes, body formatting, unresolved placeholders, team salutations and double sign-offs. Scans pipeline code for hard-wired violations. | Generated emails that "looked generated" and cost replies. |
| [decision-precedent](plugins/decision-precedent) | Search stored decisions before asking a human, store the answer with rationale, log whether a precedent was applied. | The same question reaching the founder twice in one week. |
| [usage-guard](plugins/usage-guard) | Hook that prints your subscription usage every turn and denies expensive commands past a threshold, so sessions hand over instead of hitting the wall. | Parallel sessions burning the weekly limit on a Tuesday. |

## Install

One command inside Claude Code adds the marketplace, one more per plugin installs it. Same on Windows, macOS and Linux:

```
/plugin marketplace add ExasyncOU/claude-plugins
/plugin install email-format-guard@exasync-plugins
/plugin install decision-precedent@exasync-plugins
/plugin install usage-guard@exasync-plugins
```

From a terminal instead:

```
claude plugin marketplace add ExasyncOU/claude-plugins
claude plugin install email-format-guard@exasync-plugins
```

Or try one locally without installing:

```
claude --plugin-dir ./plugins/email-format-guard
```

Requirements: Claude Code 2.x and Python 3.10+ on PATH. Nothing else.

## What you have after 2 minutes

- Ask Claude to draft or send an email and it runs the format gate first. A draft with an em dash, a bold line, a bullet list or a `{{placeholder}}` fails with the line number instead of going out.
- Ask Claude a question you already answered last week and it finds the stored decision, applies it and logs that it did. New decisions land in `.claude/decisions.json` in your repo, with rationale and who decided.
- Every turn starts with one line like `USAGE team: session 42%, week 61%. Stage: NORMAL.` Past 85 percent the expensive commands you configured are denied, past 92 percent only checkpoint and handover commands run.

## Demos

![email-format-guard](docs/email-format-guard.gif)

![decision-precedent](docs/decision-precedent.gif)

![usage-guard](docs/usage-guard.gif)

## Limits, stated honestly

- `email-format-guard` is a rule engine, not a style model. It catches the patterns that made our mail look generated. It will not tell you whether the text is good, and it has an English and German bias in its salutation and sign-off lists.
- `decision-precedent` scores lexically (weighted token overlap). It finds a precedent you phrase similarly, not one you phrase differently. Semantic search is your job via `DECISION_BACKEND_CMD`.
- `usage-guard` reads a local status file that you feed. It does not call any billing API, so the numbers are as fresh as your last update. It reports a stale status but cannot fix it.
- All three are single-file Python scripts with tests. They are small on purpose. Read them before you trust them.

## Develop

```
python -m pytest plugins -q          # all tests
claude plugin validate ./plugins/email-format-guard --strict
claude plugin validate ./plugins/decision-precedent --strict
claude plugin validate ./plugins/usage-guard --strict
claude plugin validate . --strict    # marketplace manifest
python tools/make_gif.py             # re-render the demo GIFs from real command output
```

Plugin names are permanent once published. Everything else is fair game: open an issue or a pull request. Security reports go to the address in [SECURITY.md](SECURITY.md).

## License

MIT, see [LICENSE](LICENSE).

Built by [Exasync](https://exasync.ai), an autonomous AI company automating office work for European logistics.
