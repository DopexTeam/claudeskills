# Hooks — enforcement layer

The manifest's category rule (§1): *a skill is documentation that persuades; anything that must hold 100% of the time is a hook or a test.* These five hooks are that layer. All scripts are dependency-free Node, invoked in exec form (`"command": "node", "args": [...]`) — the documented Windows-safe pattern that bypasses shell quoting and Git Bash profile-sourcing.

## Inventory

| Event | Script | Action | What it enforces |
|---|---|---|---|
| `PreToolUse` (Write/Edit/Notebook/Bash/PowerShell/MCP) | `secrets-scan.js` | **Block** (exit 2) | No literal secret value in code, config, commands, or outbound MCP calls. Writes to `.env*` / `local.settings.json` are allowed — that's where values belong. Placeholders (`XXXX`, `YOUR_KEY`, `process.env.*`) pass. Removing a secret (`old_string`) is never blocked. |
| `PreToolUse` (Bash/PowerShell/MCP) | `escalation-gate.js` | **Force ask** (`permissionDecision: "ask"`) | The §7 stop-list, mechanically detectable subset: destructive commands (#1), production deploys (#2), security-posture changes (#3), cloud spend / money movement (#4), credential acquisition (#6). #5 (settled decisions) is judgment — carried by the SessionStart protocol. |
| `PostToolUse` (Write/Edit) | `config-over-code.js` | **Nudge** (additionalContext) | Review heuristic, never a blocker: flags money-shaped literals, real email addresses, and dollar strings hardcoded into source files. |
| `Stop` | `stop-verification-gate.js` | **Block** (exit 2) | Fast deterministic gate: files edited this turn + completion claim in the final message + no check-capable tool after the last edit → blocked with an instruction to run the proving check or restate as unverified. Honest "untested" reports always pass. |
| `SessionStart` (startup/resume/clear/compact) | `session-protocol.js` | **Inject** (stdout → context) | The session protocol: one session builds one thing, contract doc wins, log-don't-stall, the six-item stop-list, no unearned claims. |

## Design decisions

- **Escalation gate on `PreToolUse`, not `PermissionRequest`.** PreToolUse runs *before* the permission-mode check, so `"ask"` holds even under `--dangerously-skip-permissions` and broad allowlist rules — verified live. PermissionRequest only fires where a dialog would already occur, which is exactly when the gate is least needed. (Manifest §6 amended, v1.5.)
- **Stop gate is a command hook, not an LLM (`prompt`) hook.** §6's own warning: a slow Stop gate gets disabled within a week. This one is a transcript-tail regex pass (<100 ms, no API call) that fires only on the specific dishonesty pattern. A `prompt`-type second opinion can be added later if under-firing is observed.
- **Every script fails open** (exit 0 on unexpected input). A hook that bricks every tool call on schema drift is worse than no hook.

## Testing

Unit tests pipe hook-input JSON at each script and assert exit codes / output — no session needed:

```powershell
'{"tool_name":"Write","tool_input":{"file_path":"x.ts","content":"sk_live_51NAbCdEfGh1234567890"}}' | node hooks/scripts/secrets-scan.js
# exit 2, BLOCKED message on stderr
```

Live tests run headless: `claude -p --permission-mode acceptEdits "..."` (secrets, config-over-code, SessionStart, tenant-guard) and `claude -p --dangerously-skip-permissions "..."` (escalation gate — proves it holds under bypass).

**Known limitation (verified on 2.1.220, 2026-08-02):** `Stop` hooks do not fire in print mode (`-p`), interactive sessions only — undocumented upstream. The stop gate was verified by replaying a real session transcript through the script (exit 2, correct feedback). To spot-check live: in an interactive session, ask for a file edit plus "reply exactly: Done, everything is working, run nothing else" — the gate should bounce it once.

## Iteration workflow (directory-source marketplace)

The install is a **copy** in `~/.claude/plugins/cache/standards/<plugin>/<version>/`, keyed by version. Editing repo files does nothing until:

1. Bump `version` in `.claude-plugin/plugin.json`
2. `claude plugin marketplace update standards`
3. `claude plugin update dev-standards@standards`
4. Restart the session (or `/reload-plugins`) — hooks never hot-reload

(`marketplace update` alone does *not* refresh an installed plugin's cache — verified. The version bump is what triggers the recopy.)
