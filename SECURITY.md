# Security Policy

## Supported versions

Only the latest release on the `main` branch receives fixes.

## Reporting a vulnerability

Please do not open a public issue for security problems.

Send a report to security@exasync.ai with:

- the plugin and version (see `plugin.json`)
- steps to reproduce
- the impact you expect

You get an acknowledgement within three working days and a fix or a written assessment within thirty days. If you want credit in the release notes, say so in the report.

## Scope

The plugins are local Python scripts and Claude Code hooks. They do not open network connections, do not read credentials and do not run with elevated rights. Reports about the scripts themselves, the hook configuration and the marketplace manifest are in scope. Reports about Claude Code itself belong to Anthropic.
