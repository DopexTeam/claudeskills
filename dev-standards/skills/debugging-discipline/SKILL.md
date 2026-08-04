---
name: debugging-discipline
description: "Diagnose a failure methodically instead of guess-patching: reproduce it first, form a falsifiable hypothesis before touching any code, instrument before guessing, bisect to isolate, and revert failed shotgun changes rather than layering fixes. Use this whenever something is broken, failing, erroring, flaky, hanging, or \"not working,\" whenever the user pastes a stack trace or error message, whenever a test starts failing, and whenever behavior is unexpected. Use it especially after two attempted fixes have not worked — that is the strongest signal the current hypothesis is wrong."
---

# Debugging Discipline

The default failure mode under pressure is guess-patching: change something plausible,
run it, change something else, run it again. Each guess that doesn't work contaminates
the crime scene — the code drifts from the state where the evidence made sense, and by
the fifth change nobody can say which behavior belongs to the bug and which to the
attempted fixes. This skill is the loop that replaces guessing. Its center of gravity
is not the fixing; it's knowing when to stop, abandon, revert, or escalate.

`references/failure-taxonomy.md` catalogs recurring failure classes — their tells and
the first probe for each. Check it once symptoms are in hand; matching a known class
can save the whole search.

## The loop

### 1. Reproduce it first

Get the failure happening on demand, in the smallest form that still fails. A bug you
can't reproduce is a bug you can't prove fixed — any "fix" for it is a hope with a
commit message.

When it genuinely can't be reproduced (production-only, intermittent, load-dependent),
say so and change the goal: the job is now *capturing evidence* — instrumentation,
correlation of existing logs, narrowing the conditions — not fixing. The honest claim
after an unreproduced fix is "made the suspected cause impossible; watching for
recurrence," never "fixed."

### 2. Form a falsifiable hypothesis before touching any code

State it in one sentence with three parts: *I believe X, because of evidence Y; if I'm
right, Z will be observable — and if Z is absent, the hypothesis is dead.* A hypothesis
that can't be stated this way is a guess wearing a lab coat.

The falsification condition is the load-bearing part. Deciding *in advance* what result
kills the theory is what makes abandoning it cheap — the result arrives, the theory
dies, no negotiation with sunk cost. Without it, every result gets reinterpreted to
keep the favorite theory alive.

### 3. Instrument before editing

Observe the failing state before changing behavior: add the log line, inspect the
variable, capture the payload, run the query. An edit made while blind changes the
system being studied and destroys the baseline — instrumentation converts belief into
evidence while leaving the crime scene intact.

This instrumentation is scaffolding: remove it once the bug is understood. What should
*stay* — structured logging, correlation IDs, error tracking — is `observability`'s
territory, designed deliberately rather than left over from a debugging session.

### 4. Bisect to isolate

Halve the search space, repeatedly, along whichever axis the evidence offers:

- **History:** `git bisect` between last-known-good and first-known-bad.
- **Data:** which warehouse, which tenant, which record class fails? Diff a failing
  case against its nearest passing neighbor — the difference between them is usually
  the mechanism.
- **Path:** disable half the pipeline, stub half the calls, shrink the input until the
  failure just barely still occurs.

Elimination is logarithmic; reading code hoping to spot the bug is linear in the size
of the codebase. Bisect even when an inspection target seems obvious — especially then,
because "obvious" is how the wrong file absorbs an afternoon.

### 5. One change at a time — and revert what didn't work

Test one hypothesis per change, and when a fix attempt fails, revert it *before* the
next attempt. Layered failed fixes create a compound state nobody understands: attempt
one can mask or mutate the symptom attempt two is judged against, and the "bug" being
chased by attempt three may be an artifact of the first two. Clean state is what makes
the next piece of evidence trustworthy. Reverting is not losing progress — the dead
hypothesis is the progress; keep the knowledge, discard the diff.

## Stop conditions

The most valuable moves in debugging are the stopping moves. Each of these is a
tripwire — when it fires, the response is immediate, not negotiable with momentum:

- **The falsification condition fired → the hypothesis is dead.** Log it in one line —
  *ruled out: X, because Z was absent* — and return to the evidence. A killed theory
  narrows the space; only clinging to it wastes the work. Recording it also stops the
  next session (or the next hour) from re-walking the same dead end.
- **Two fix attempts have failed → the hypothesis is wrong, not the execution.** Do not
  write the third variation. Revert everything, go back to the evidence, and form a
  *different* hypothesis — the failure is upstream of where the edits are happening.
  This is the strongest signal in debugging, and the moment guess-patching usually
  takes over instead.
- **The working tree contains changes that can't each be explained → revert to clean.**
  That's shotgun state; no observation made from it can be trusted.
- **The next diagnostic step would touch production data, destroy or overwrite
  anything, change auth or tenant boundaries, incur spend, contradict a settled
  decision, or need credentials the session doesn't hold → stop and ask the human.**
  Diagnosis does not earn exemptions from the escalation stop-list; "I was debugging"
  is how test data ends up deleted from production.
- **The failure stops reproducing and it's unclear why → treat that as a finding, not
  a fix.** Something changed; find what, or the bug is merely dormant and now
  unmonitored.

## Exit: what "diagnosed" means

The loop ends when the root cause can be stated as a mechanism, not a proximity:
*"the cache key omits the tenant ID, so the second tenant reads the first tenant's
entry"* — never *"restarting seems to fix it."* If the explanation can't say **why the
fix works**, the bug isn't understood; it's dormant.

Then hand off, by name:

- Proving the fix actually works — including that the reproduction from step 1 now
  passes — belongs to `verification-discipline`, where installed. Diagnosis earns no
  verification claims by itself.
- Keeping the fix diff minimal — no drive-by cleanups collected along the way —
  belongs to `change-scoping`.
- Whether this bug deserves a permanent regression test belongs to `testing-strategy`.
- Any instrumentation worth keeping belongs to `observability`; everything else added
  during the chase comes out before the fix ships.
