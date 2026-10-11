---
name: remocon-orchestrate
description: Inspect Claude Code sessions across all registered machines (Remocon). Use when the user wants to see what's running where — list machines, list a machine's folders/sessions, or read what a specific session is doing — from one place. Read-only: it observes sessions, it does not drive them.
---

# Remocon Orchestrate

You are a **manager session** that inspects the user's Claude Code sessions across
machines via the Remocon hub. This skill is
**read-only**: it lists machines/folders/sessions and reads transcripts. To start
or continue interactive work in a session, open its `claude.ai/code` URL from the
web UI — this skill does not send prompts on your behalf.

Run the CLI with Bash:

```
python3 ~/.claude/skills/remocon-orchestrate/remocon_cli.py <command>
```

(Set `REMOCON_URL` if the hub isn't at the local default.)

## Commands

- `machines` — list registered machines (id, nickname, agentReady, host).
- `folders <machine>` — folders that have sessions on that machine (with live count).
- `sessions <machine> <cwd>` — sessions in a folder (id, live flag, title).
- `transcript <machine> <sessionId>` — **READ-ONLY**: the recent messages of a
  session. Use this to see *what a session is doing* — it never interrupts it.

## How to use

1. `machines` to see what's available (only `ready=True` machines are reachable).
2. `folders <machine>` then `sessions <machine> <cwd>` to drill down to a session.
3. **To answer "what is session X doing?"** → `transcript <machine> <sessionId>`
   (safe, read-only — it reads the session's local jsonl, never interrupts it).
4. Summarize what you find, noting which machine each session is on. To actually
   take over a session, the user opens its `claude.ai/code` URL from the web UI.

## Notes

- `transcript` is the reliable monitoring path — it reflects the live conversation
  without touching the running session.
- Report `ERROR: ...` honestly (e.g. an offline machine errors).
- Quote the `<cwd>` argument (Windows paths contain backslashes).
