# Exasync Claude Code Plugins

Three small, dependency-free plugins extracted from the toolchain of an autonomous AI company. Each one exists because a real incident made it necessary. They run on Python 3.10+ and need no cloud service, no API key and no database.

| Plugin | What it does | Born from |
|---|---|---|
| [email-format-guard](plugins/email-format-guard) | Deterministic pre-send gate for customer-facing email: blocks long dashes, body formatting, unresolved placeholders, team salutations and double sign-offs. Scans pipeline code for hard-wired violations. | Generated emails that "looked generated" and cost replies. |
| [decision-precedent](plugins/decision-precedent) | Search stored decisions before asking a human, store the answer with rationale, log whether a precedent was applied. | The same question reaching the founder twice in one week. |
| [usage-guard](plugins/usage-guard) | Hook that prints your subscription usage every turn and denies expensive commands past a threshold, so sessions hand over instead of hitting the wall. | Parallel sessions burning the weekly limit on a Tuesday. |

## Install

```
/plugin marketplace add exasync/claude-plugins
/plugin install email-format-guard@exasync-plugins
/plugin install decision-precedent@exasync-plugins
/plugin install usage-guard@exasync-plugins
```

Or try one locally without installing:

```
claude --plugin-dir ./plugins/email-format-guard
```

## Demos

![email-format-guard](docs/email-format-guard.gif)

![decision-precedent](docs/decision-precedent.gif)

![usage-guard](docs/usage-guard.gif)

## Develop

```
python -m pytest plugins -q          # all tests
claude plugin validate ./plugins/email-format-guard --strict
claude plugin validate ./plugins/decision-precedent --strict
claude plugin validate ./plugins/usage-guard --strict
claude plugin validate . --strict    # marketplace manifest
python tools/make_gif.py             # re-render the demo GIFs from real command output
```

Plugin names are permanent once published. Everything else is fair game: open an issue or a pull request.

## License

MIT, see [LICENSE](LICENSE).
