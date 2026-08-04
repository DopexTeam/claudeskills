# Progress honesty — reporting long-running work truthfully

The contract: **everything the user sees about a running job derives from real,
durable state.** A progress bar is a claim; a fake one is an unearned claim rendered
as UI, and it gets discovered the way all unearned claims do — at the worst moment,
by the person whose trust mattered most.

## The patterns

- **Checkpointed fraction** — determinate progress (`412 of 1,206 files`) is
  legitimate only when both numbers are real: the denominator known, the numerator
  read from durable checkpoints (rows, not memory). Chunk the work; checkpoint each
  chunk; the bar reads the checkpoints.
- **Honest indeterminate** — when the denominator isn't known yet (still
  enumerating), do not invent a percentage. Show phase plus a live counter:
  *"Scanning files… 2,341 found."* A counter that visibly climbs is more reassuring
  than a fake bar, because users can tell the difference.
- **Phase progress** — multi-stage jobs report the stage by name: *"Step 2 of 4 —
  embedding documents."* Phases are real state; name them.
- **Heartbeat + last-progress timestamp** — long jobs display when progress last
  advanced (*"last update 14:02:33"*). This is what makes a stall *visible* instead
  of ambiguous; a bar frozen at 61% with a fresh heartbeat is slow, without one it's
  stuck, and the user can tell which.
- **ETA only from measured rate** — computed from actual throughput so far, shown
  with its uncertainty (*"~40 min at current rate"*), never from hope. If the rate
  is wildly variable, show the rate, not an ETA.

## Reveal discipline

- **"Done" follows the check.** The success state renders after verification
  confirms the outcome (counts reconciled, artifact exists) — not when the loop
  ends. Optimistic UI is fine for instant, reversible, local actions; a
  multi-hour backfill is none of those.
- **Partial success is shown as partial.** "1,180 of 1,206 imported — 26 failed
  (view list)" is a true statement the user can act on. Rounding it to "Done ✓"
  is a lie with a delay; rounding it to "Failed" discards 1,180 truths.

## Stall handoff

When the heartbeat stops past a threshold, the job is presumed stalled, and the
user gets an accurate account, not a spinner:

1. **Where it stopped** — the last durable checkpoint (*"stopped during embedding,
   after file 412 of 1,206, 14:07"*).
2. **The confirmed/unknown split** — what is checkpoint-verified done, what was in
   flight and is now unknown. Never round "unknown" up to "done."
3. **What happens next** — resume from checkpoint (the whole point of durable
   checkpoints: restart costs one chunk, not four hours), retry, or escalate to a
   human with this same account.

The operator-facing view of the same events — structured logs, the dead-man alert
that notices the stall without a user watching — is `observability`'s territory;
the two views share checkpoints, so they never disagree.

## Anti-patterns, named

- **The timer bar** — progress as `elapsed / guessed_total`. It's a clock in a
  costume.
- **The 90%-and-hold** — an easing curve that sprints to 90 and waits for reality
  to catch up. Users have learned exactly what it means; it buys nothing and spends
  credibility.
- **The immortal spinner** — no heartbeat, no timeout, no stall state. Ambiguity as
  UI.
- **Success-then-verify** — showing ✓ and checking afterward. When the check fails,
  the UI has already lied.
- **Failure-erases-progress** — reporting a stalled job as simply "failed," hiding
  that 95% completed and is durably checkpointed. The user re-runs four hours for
  one bad chunk.
