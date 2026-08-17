---
description: Frame a build session — one thing, contract doc, exit criterion, stop-list
argument-hint: [what this session builds]
---

Frame this session as a build session under the house standard. Work through the following before writing any code.

## 1. Name the one thing

This session builds exactly one thing. If `$ARGUMENTS` names it, restate it in one sentence and confirm scope. If `$ARGUMENTS` is empty, ask the user what the one thing is — do not guess. Everything discovered along the way that is not the one thing gets logged (step 4), not built.

## 2. Read the contract before the conversation

**Start at `docs/README.md`** — the index names every document and what it is for. Failing that, look for the canonical documents wherever they live (`docs/decisions/` in the house layout, the repo root in older ones): `DECISIONS.md`, `ASSUMPTIONS.md`, `HANDOFF.md`, plus any contract doc the user named. Read the entries that touch this session's work.

- **Check `docs/incoming/` before starting.** An untriaged document there may already decide, or contradict, what this session is about to build. Routing it is a legitimate one-thing for a session — but do it deliberately, not as a side effect.

- **A named contract doc wins over the conversation.** If the user's request contradicts a settled decision, say so and stop; do not silently follow the chat.
- If a `HANDOFF.md` exists, its "next single action" and "known traps" are the starting point.
- If none of these documents exist and the work is non-trivial, say so — the fix is `architecture-inquiry` (new work) or `project-adoption` (existing repo), not proceeding blind.

## 3. State the exit criterion

Before building, state what concretely verifiable artifact ends this session — a passing check, a command with real output, a reviewable file. "It should work now" is not an exit criterion; `verification-discipline` owns what counts as proven. A session that cannot name its exit criterion has not named its one thing.

## 4. During the build: log, don't stall — with six exceptions

When a gap in the record forces a choice, make a reasonable call and log it to `ASSUMPTIONS.md` (format: `project-artifacts`) instead of stopping to ask. **Except** when the action would:

1. Be irreversible or destructive (drop, truncate, overwrite, force-push, delete)
2. Touch production data or a production environment
3. Change security posture — auth, permissions, tenant boundary, encryption, exposure surface
4. Incur spend or move money
5. Invalidate a **settled** decision in `DECISIONS.md` — filling a genuine gap is what the assumptions log is for; overturning a settled decision is not
6. Require a credential the session does not already legitimately hold

Those six stop and ask a human. Everything else is a logged assumption.

## 5. At session end: close the loop

Before the session ends:

- **Disposition every assumption** logged this session: promoted (becomes a numbered decision), refuted (reopens the affected decision), or carried (named owner + re-check trigger). An assumption without a disposition is a bad call waiting to be forgotten.
- **Verify the exit criterion** from step 3 actually ran — never describe a check that was not run.
- **Write or refresh `HANDOFF.md`** — state, proven vs. assumed, next single action, known traps — so the next session starts where this one stopped.
- **Drain the plan** — update this session's map row to its closed status (row stays forever), then archive what is now spent to `docs/old/`: the session's verbose body, any brief whose output has returned, and any build-prompt file this closure completed (project-artifacts owns the rules). A plan file that only accumulates is a plan nobody can read.
- **Reconcile what the session made stale** — sweep `reference/`, the runbooks, and the README(s) for documents this session's changes invalidated (`doc-reconciliation` owns the pass): mechanical index and link fixes land now; substantive rewrites are proposed to the human, never silently applied.

Now begin: state the one thing, list which contract documents you found and read, and give the exit criterion. Then build.
