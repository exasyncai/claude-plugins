---
name: precedent
description: Decision memory with an escalation ladder (agent -> lead agent -> human). Before any real decision, search the stored precedents; a strong match is applied instead of asking again. After a human decides, store question, decision and rationale so the next session reuses it. After applying a precedent, log the outcome. Use when an architecture, strategy or customer decision comes up, when the user answers a direction question ("remember this decision"), or when checking whether something similar was decided before. Keywords - decision, precedent, already decided, remember this decision, escalation, ask the user, decision log, do not ask twice.
---

# Decision Precedent

The rule this skill enforces: a question that a human already answered is never asked again. The store is a JSON file in the project (`.claude/decisions.json` by default), so it travels with the repository and works offline.

## Before a decision: search

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/decision.py" search --domain architecture "<the decision question>"
```

The script ranks stored decisions by keyword overlap (title, question, decision, rationale, tags) and prints a verdict for the best match:

- `APPLY` (score >= 0.60): strong precedent. Read it and apply it if it fits. Do not ask the human again.
- `CONTEXT` (0.35 to 0.60): related. Decide deliberately with the precedent as context.
- `WEAK` or no match: decide yourself if the strategy is clear, otherwise ask the human.

Scores are lexical, not semantic. A paraphrased question can score lower than it deserves, so read the top hits before dismissing them.

## When to ask the human anyway

Irreversible, costs money, changes what a customer sees, or is an architecture fork (new table, new service). Everything else the agent may decide itself and store with `--by agent`.

## After a decision: store

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/decision.py" store --domain architecture --slug threads-vs-todos \
  --question "Separate table for project threads or reuse the todo table?" \
  --decision "Separate table. Todos stay a flat list; a thread may point to a todo." \
  --rationale "Done vs to-do are different lifecycles." --by human --scope "whole repo"
```

Keys follow `decisions/<domain>/<slug>`. Storing the same key again replaces the decision and keeps its outcome history.

## After applying a precedent: feedback (required)

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/decision.py" feedback --key decisions/architecture/threads-vs-todos --outcome applied --note "used in migration 0042"
```

`--outcome` is `applied` or `rejected`. Outcomes are appended, never overwritten. A precedent with many rejections is a precedent to revisit.

## Other commands

- `list [--domain d]` shows all stored decisions.
- `show --key k` prints one decision with its outcomes.

## Configuration

- `DECISION_STORE=/path/to/decisions.json` overrides the store location.
- `DECISION_BACKEND_CMD="python my_backend.py"` delegates `search`, `store` and `feedback` to your own command (a vector store, a database). It receives the subcommand and the same arguments and must print the same JSON the built-in backend prints.
