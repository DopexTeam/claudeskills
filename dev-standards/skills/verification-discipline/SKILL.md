---
name: verification-discipline
description: "Prove work actually functions using semantic checks rather than status codes or exit codes: every phase ends in something concretely verifiable, and never describe a check that was not actually run. Use this whenever finishing a task, phase, or pull request, whenever about to report something as done, working, complete, or fixed, whenever the user asks whether something works, and whenever a claim about behavior is about to be made without a command backing it."
---

# Verification Discipline

"It ran" and "it works" are different claims, and almost everything that goes wrong in
reporting work comes from blurring them. Exit code 0, HTTP 200, a green suite, and
"migration completed successfully" all say the same thing: *the operation finished.*
None of them says the world is now in the state the work promised. This skill owns the
gap between those two claims.

## The definition of verified

A claim is **verified** when all three hold:

1. **A check was actually run** — in this session, against the current state of the
   code and data. Not remembered, not implied by an earlier run before the last edit.
2. **The check is semantic** — it tests the *meaning* of the claim, not the plumbing
   around it (see below).
3. **The result was observed to match** — and the claim carries its evidence:
   *"verified: ran `<check>`, saw `<result>`."*

Anything less is a belief. Beliefs are fine — most work proceeds on them — but they
report as *expected*, never as *verified*, and the two never share a sentence without
being labeled. One inflated claim, discovered, poisons every honest report that came
before it.

## Semantic over syntactic

The syntactic signal says the machinery completed; the semantic check asks whether the
promise was kept:

| The claim | Syntactic (not enough) | Semantic (the actual check) |
|---|---|---|
| "Migration is done" | exit 0, "success" | new column exists AND is backfilled (zero unexpected NULLs) AND the constraint rejects a bad insert |
| "The endpoint works" | HTTP 200 | response body carries the right values for a known fixture case |
| "Tests pass, feature works" | suite green | a test in that suite actually exercises the changed behavior — a green suite that never touches the change verifies nothing |
| "The job processed the backlog" | job status `completed` | the downstream artifact exists and a sampled record is correct |
| "Tenant isolation works" | tenant A sees tenant A's data | **tenant B provably cannot see it** — isolation claims are only verified by the forbidden thing failing |

Two rules generalize the table:

- **Check at the boundary the claim lives at.** A database claim needs a database
  check; a UI claim needs the rendered screen. A screenshot does not verify a schema,
  and a row count does not verify a page.
- **Positive claims about restrictions need negative checks.** "Access control works,"
  "tenants are isolated," "the input is validated" — each is a claim that something
  *fails*. Run the forbidden operation and observe the failure; observing the allowed
  path proves nothing about the forbidden one.

## Never describe a check that was not run

The hard rule, and it has no exceptions for confidence:

- Never report "tests pass" without having run them, now, on this code.
- Never let "this should work" wear the clothes of "this works." The tell is a
  behavior claim with no command behind it.
- When a check *cannot* be run from here — no access, no environment, no data — say
  exactly that, and name the check that *would* settle it, so the human can run it or
  grant access. "I cannot verify this from here; the check is X" is a complete,
  honest, useful answer. A confident guess in its place is a defect with a delay on it.
- Every report separates **proven** (each item with its named check) from **expected**
  (reasoning only). If a report can't fill the proven column, that *is* the report.

## Phase exit criteria

Every phase of work ends in something concretely verifiable — defined *when the phase
is planned*, not improvised after the code is written. The exit criterion is a command
(or observable) plus the output that counts as a pass. "Code written" is not a phase
exit; "the reproduction from the bug report now passes: `<command>`" is.

Deciding the exit check up front costs one sentence and buys two things: drift gets
caught at the phase boundary where it's cheap, and "done" stops being negotiable after
the fact — the finish line doesn't move just because the work stopped short of it.

## Choosing the check

`references/check-patterns.md` has per-layer patterns — database, API, UI, background
jobs, data pipelines, and performance/3D (including the throttled-profile pattern that
performance claims require: real numbers from a constrained run, never "it feels
smooth" on a dev machine).

Prefer one known case with a known-correct answer over ten smoke checks: "invoice
`INV-0117` totals $4,517.50 and it renders $4,517.50" verifies more than ten pages
loading without error. Smoke checks prove the machinery turns over; known-answer
checks prove the work is right.

## When the check fails — or flakes

An honest failure is this skill succeeding, not failing: the check did its job.
Diagnosing *why* belongs to `debugging-discipline`, where installed — verification's
job ends at the honest result.

Do not re-run a failing check until it passes and report the pass. A check that fails
sometimes is not "passing now"; it's a finding — either the check is unreliable or the
system is, and both are worth knowing. Selection-biased retries convert real signal
into false confidence, which is worse than no check at all.

## Boundaries

- **What tests should exist** — suite design, coverage strategy, what to mock — is
  `testing-strategy`'s territory, where installed. This skill *runs* whatever proves
  today's claim; it doesn't design the permanent suite.
- **Diagnosing a failed check** → `debugging-discipline`, where installed.
- **Hunting the claims nobody thought to make** — the whole-build adversarial pass —
  belongs to the `adversary` subagent, where installed. This skill proves the claims
  that were made; the adversary asks what claims are missing.
- **Honesty in client-facing output** is the always-on policy (`CLAUDE.md`, where
  present) — this skill is its verification arm, not its restatement. On surfaces with
  no such policy file, this section carries the rule on its own: no unearned claims.
