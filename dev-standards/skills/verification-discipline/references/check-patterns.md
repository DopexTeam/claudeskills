# Check patterns — per layer

Semantic checks by layer: for each, the claim being made and the check that actually
proves it. These are patterns, not scripts — bind them to the project's real tables,
routes, and fixtures. Every pattern assumes the hard rule: the check is *run*, and the
claim carries what was seen.

## Database

- **"The data is correct"** → query one known case with a known-correct answer and
  compare values, not row presence: `SELECT total FROM invoices WHERE id='INV-0117'`
  must equal the hand-computed figure.
- **"The constraint holds"** → attempt the forbidden write and observe the rejection.
  A unique index is verified by a duplicate insert failing; a check constraint by an
  out-of-range value bouncing. (Run in a transaction and roll back, or against a
  disposable copy — never dirty real data to prove a point.)
- **"The migration is done"** → three checks, not one: the schema object exists
  (`information_schema` / `OBJECT_ID`), the data moved (count NULLs in the new column;
  compare old-source vs. new-destination counts; sample one migrated record and diff
  its values), and the constraint/default actually enforces (probe as above). If a
  rollback was claimed to exist, it has been *run* against a copy — an untested
  rollback is a hope, not a plan.
- **"Tenants are isolated"** → the negative probe, always: authenticate (or set
  context) as tenant B and run the exact query paths that serve tenant A's data —
  expect zero rows or a hard error, and check the *pooled-connection* case
  specifically: run a request as A, then B on the same connection/session, and prove
  B doesn't inherit A's context. Seeing A's data as A verifies nothing.

## API

- **"The endpoint works"** → fixture-based positive check: known request, assert the
  *body values* (the fields, the numbers), not the status code. Capture the response
  as the evidence.
- **"Auth is enforced"** → three negatives: no credential → expect 401; valid
  credential, wrong role → expect 403; valid credential, another tenant's resource ID
  → expect 404/403 (and note which one, deliberately — it's an information-disclosure
  decision). Auth checks that only test the happy path test nothing.
- **"Errors are handled"** → send the malformed request and assert the error *shape*
  (envelope, code, message field) matches what's documented — clients integrate
  against error bodies too.
- **"It's idempotent"** → send the same request twice (same idempotency key where
  applicable); assert one effect: one row, one charge, one email.

## UI

- **"The page works"** → render against known data and assert the known value appears
  in the DOM (or visibly in a screenshot actually taken and actually looked at —
  "looked at it" is a real check only if the looking happened). A page that loads
  without errors but shows the wrong number passes smoke and fails semantics.
- **"The flow works"** → walk the interaction end to end once: fill, submit, and
  assert the *confirmation state* (the success message, the new row in the list) —
  not just the absence of an error.
- **"No console errors"** → count them; zero is a checkable number. One "harmless"
  red line in the console is a claim someone should have to make explicitly.
- **"It handles empty/error states"** → force each state (no data, failed fetch) and
  observe the designed fallback, not a blank div.

## Background jobs / workers

- **"The job works"** → enqueue one known unit of work; observe the *downstream
  artifact* (the row written, the file produced, the email in the test outbox) and
  verify its content, not the job's status field.
- **"Failures are handled"** → feed it one poison message; verify it lands where the
  design says (dead-letter, error table, alert) and the worker keeps processing the
  next message.
- **"It's safe under retry"** → deliver the same message twice; assert one effect.
  At-least-once delivery *will* exercise this in production; verify it before
  production does.
- **"Progress reporting is honest"** → compare the reported progress against the
  actual state mid-run (rows written vs. percent shown). A progress bar wired to a
  timer instead of work is an unearned claim rendered as UI.

## Data pipelines

- **"The pipeline works"** → run one known fixture through end to end; at the far
  end, check count, a checksum or aggregate, and one spot record's values against
  hand-computed truth.
- **"The backfill is complete"** → reconcile against the source: counts by partition
  (per day/tenant/type — totals hide offsetting errors), plus a sampled record
  diffed field-by-field.
- **"Replays are safe"** → re-run yesterday's batch; assert no duplicates and no
  drift (same counts, same aggregates).
- **"It's fresh"** → check the actual lag now (max timestamp at destination vs.
  source), and compare against the promise. "Real-time" is a number; measure it.

## Performance / 3D

The pattern every performance claim requires — `webgl-budget` and any "it's fast"
claim bind to this section rather than restating it:

- **Throttled-profile run with real numbers.** A dev machine at full power proves
  nothing. Constrain to the audience's hardware reality: CPU throttling (4–6× in
  DevTools, or a real mid-tier phone), throttled network for load claims, then record
  **numbers**: frame-time percentiles (p95, not average — jank lives in the tail),
  time-to-interactive, memory, bundle/texture weight. The claim is verified against a
  *stated budget* ("p95 frame time ≤ 20ms on 6× throttle"), not against a feeling.
  "It feels smooth" is not a check; it's a dev machine describing itself.
- **Sustained, not first-frame.** Run 30+ seconds (for 3D: with the scene actually
  animating/interacting). Thermal throttling and memory growth arrive late; a
  ten-second check verifies the demo, not the experience.
- **The fallback path counts.** If a no-WebGL / reduced-motion / low-end fallback is
  claimed, load with WebGL disabled and `prefers-reduced-motion: reduce` and observe
  the fallback actually render — a fallback nobody has ever seen is a 404 with good
  intentions.
- **Before/after or it isn't an improvement.** "Optimized X" is verified by the same
  measurement run on both sides of the change, same throttle, same scene. One-sided
  numbers are anecdotes.
