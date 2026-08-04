# multitenant

Per-project enforcement plugin for the tenant-isolation invariant (house standard, SKILLS-MANIFEST §6/§13.2). **Install only on multi-tenant projects** — on single-tenant projects it would block legitimate SQL, which is exactly why it is not part of `dev-standards`.

## What it enforces

One invariant, two surfaces:

| Surface | Mechanism |
|---|---|
| Write time | `PreToolUse` hook blocks `SET app.*` without `LOCAL` and `set_config('app.*', …, false)` in any file edit, shell command, or MCP call. Exit 2; the instruction fed back to Claude names the fix (`SET LOCAL` / `set_config(…, true)`). |
| Runtime | `templates/cross-tenant.test.ts` — the cross-tenant test, which is the **artifact of record**. Copy it into the project suite, fill the TODOs, keep the `max: 1` pool. |

**Why:** on a pooled connection, a session-level GUC survives the request that set it. The next request on that connection inherits the previous tenant and reads their data. `SET LOCAL` dies at COMMIT.

## Install (per project)

```
claude plugin install multitenant@standards --scope project
```

Then restart or `/reload-plugins` — hook edits and installs do not hot-reload.

## Testing the hook

Pipe a PreToolUse payload at the script and check the exit code:

```powershell
'{"tool_name":"Bash","tool_input":{"command":"psql -c \"SET app.tenant_id = ''x''\""}}' | node hooks/scripts/tenant-guard.js
# expect exit 2 and a BLOCKED message on stderr; SET LOCAL passes with exit 0
```
