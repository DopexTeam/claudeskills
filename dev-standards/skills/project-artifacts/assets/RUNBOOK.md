# RUNBOOK — <procedure name>

<!--
Copy per procedure (RUNBOOK-deploy.md, RUNBOOK-restore.md, ...). Keep this comment block.
- Every step is tagged: [YOU] a human performs it · [RUN] a machine or agent executes it.
- Irreversible warnings go BEFORE the step they protect, never after — runbooks are read
  line by line under stress, and a warning below the command is read after the damage.
- Every [RUN] step states its expected output AND its half-success mode. Partial states
  are where procedures actually go wrong; success/failure alone doesn't cover them.
- Commands are exact. Placeholders are declared like <TENANT_ID>, with where to get the value.
- The Rollback section is mandatory, even when its content is "there is no rollback."
-->

**Purpose:** <what this procedure accomplishes, and the situation that calls for it>
**Prerequisites:** <access, credentials, VPN, tool versions, state that must already be true>
**Last verified end-to-end:** YYYY-MM-DD

## Steps

Order matters. Do not reorder or parallelize unless a step says it is safe to.

1. `[YOU]` <exact human action — what to open, approve, or confirm; never "prepare the environment">

2. `[RUN]` `<exact command — real values, or declared placeholders>`
   - **Expect:** <what success output looks like, concretely>
   - **Half-success:** <what a partial result looks like — e.g. 3 of 5 items processed — and what to do about it>

3. ⚠️ **IRREVERSIBLE PAST THIS POINT** — <what cannot be undone, and why>.
   Before proceeding, verify: <the specific check that must pass first>.

4. `[RUN]` `<the irreversible command>`
   - **Expect:** ...
   - **Half-success:** ...

5. `[RUN]` `<final verification command — the check that defines "done">`
   - **Expect:** <the output that means the procedure succeeded>

## Rollback

<Exact steps to undo, and the step number past which they stop working.
If there is no rollback, say so explicitly and point at the warning above.>
