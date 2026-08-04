# How runbooks fail

Nine recurring failure modes. Consult this while writing or reviewing a runbook; the
template in `assets/RUNBOOK.md` builds several of the preventions in structurally, but
the structure only helps if the author knows what it's defending against.

## 1. The placeholder command

"Configure the environment variables." "Point the app at the new database." These are
goals, not steps — the reader at 2am doesn't know which variables, which file, which
connection string format. **Prevention:** every command is exact and copy-pasteable.
Genuine placeholders are declared visibly (`<TENANT_ID>`) with a note on where the
value comes from.

## 2. The warning after the step

The irreversible note lives in the paragraph *below* the destructive command. Runbooks
are executed line by line under stress; anything after the command is read after the
damage. **Prevention:** the warning is its own numbered step *before* the one it
protects, and it names a verification that must pass before proceeding.

## 3. The unmarked audience

A step written as if automated that a human was supposed to do (so it's silently
skipped), or a step written as an instruction that automation already handles (so a
human waits forever, or does it twice). **Prevention:** every step carries `[YOU]` or
`[RUN]`. No untagged steps.

## 4. Half-success unhandled

The step processed 3 of 5 migrations, or succeeded in one region and timed out in the
other. The runbook describes only success and total failure, so the operator improvises
in the worst possible moment. **Prevention:** every `[RUN]` step names its expected
output *and* what a partial result looks like, with the action to take.

## 5. Implicit ordering

Steps that look independent get reordered or run in parallel by an operator trying to
save time — and step 6 silently depended on step 4's side effect. **Prevention:** state
order sensitivity once at the top; mark the exceptions ("safe to run while step 3
completes") explicitly.

## 6. Stale commands

The runbook was written once; the infrastructure moved on. The first command that fails
destroys the reader's trust in every step after it, which is worse than having no
runbook — improvisation with false confidence. **Prevention:** a "Last verified
end-to-end" date at the top. A runbook whose date predates the last infra change is
due for a verification run, not a production run.

## 7. No rollback story

Not even "there is none." The operator discovers mid-incident that nobody thought about
undoing, and starts improvising a rollback against an irreversible step. **Prevention:**
the Rollback section is mandatory. "No rollback exists past step 4 — that is why step 3
is a verification gate" is a complete and honest answer.

## 8. Unstated environment assumptions

Works from the author's machine: VPN connected, cloud CLI authenticated as the right
account, correct tool versions. The reader has none of that and the failure messages
won't say so. **Prevention:** the Prerequisites section carries access, credentials,
versions, and required starting state — everything the author's environment provided
for free.

## 9. Success undefined

The last command runs and the procedure just... ends. Did it work? The operator pokes
around the UI and decides by vibes. **Prevention:** the final step is always a
verification: the named check whose output defines "done." (What makes a check count as
verification is the `verification-discipline` skill's territory, where installed — the
runbook's job is to make sure a check is *present*.)
