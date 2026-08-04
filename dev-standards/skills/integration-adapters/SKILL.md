---
name: integration-adapters
description: "Wrap every external system behind a typed adapter with a demo implementation, make the demo the loud and obvious failure mode, throw immediately on half-configured credentials, never let an external be load-bearing, and report long-running work honestly — progress reflects real state rather than a timer, results reveal only after verified success, and stalls hand off with an accurate account of where they stopped. Use this whenever integrating a third-party API, webhook, payment provider, or vendor SDK, whenever building a background job, worker, queue, or progress indicator, and whenever an external service could be slow, down, or partially configured."
---

# Integration Adapters

Every external system is a dependency you don't control that will, on some real day,
be slow, down, changed without notice, or half-configured — usually during a demo.
This skill owns the boundary that makes that survivable: the adapter shape, the demo
implementation and its loudness, startup credential validation, the never-load-bearing
rule, and honest reporting of long-running work.

## One typed adapter per external system

- **The interface speaks your domain, not the vendor's.** `getOpenInvoices(projectId)`,
  not `listCommitmentChangeOrders(company_id, ...)`. Translation happens once, at the
  boundary — otherwise vendor vocabulary, pagination quirks, and version churn
  metastasize through the codebase, and the vendor's API shape becomes your
  architecture by accident.
- **Everything vendor-specific lives behind it:** auth and token refresh, retries,
  rate limits, timeouts, pagination, payload validation, and error translation.
- **Validate at the boundary; nothing downstream trusts a payload.** A vendor's
  unannounced field change should die at the adapter with a clear error, not corrupt
  records quietly for weeks.
- **Errors translate into your typed taxonomy** — `retryable`, `permanent`,
  `auth_expired`, `rate_limited` — so callers make policy decisions ("retry later,"
  "tell the user," "page someone") without knowing the vendor exists.

The full shape, with code, is `references/adapter-template.md`.

## The demo implementation — loud on purpose

Every adapter ships with a demo implementation: deterministic, realistic data, works
offline, needs no credentials. That's what makes development, tests, and sales demos
independent of the vendor's uptime and of credential provisioning (which is always
slower than the sprint).

Two rules keep the demo honest, and they are the heart of this skill:

- **The demo announces itself, loudly, at the surface.** A visible banner or
  watermark in any UI it feeds, and an unmistakable log line at startup. Demo data
  that looks live *will* eventually be shown to a client as live — a silently
  plausible demo is an unearned-claim generator, and one client who discovers the
  numbers were fake stops believing every number after that.
- **Mode selection is explicit config, never fallback-on-error.**
  `PROCORE_ADAPTER=live|demo`, chosen on purpose. If the live adapter fails, it
  fails loudly — it never silently downgrades to demo, because fallback-to-demo
  converts an outage into a fabrication.

## Half-configured credentials: throw at startup

Adapter configuration validates **all-or-nothing at construction**: a client ID
without its secret, a token without its base URL, three of four OAuth values —
throw immediately, naming exactly which keys are missing (names, never values).

The reason: half-configured doesn't fail at startup on its own — it fails at first
use, three layers from the cause, in a stack trace about JSON parsing, typically on
the day someone is watching. A startup failure names itself and costs one minute.
(Where credentials *live* — vault, env, never code — is the always-on policy, and in
the house setup a hook enforces it; this skill's job is refusing to hobble along on
half of them.)

## Never load-bearing — the umbrella rule

The system stays available — degraded, honest, but available — when the external is
down. This is the umbrella other surfaces inherit (3D inherits it via `webgl-budget`:
the GPU is an external too). In practice:

- **Timeouts on every call, no exceptions** — an integration without a timeout makes
  the vendor's hang your hang.
- **Retries with backoff and jitter for `retryable` errors only**; retrying a
  `permanent` error is a slow way to fail, and retrying without idempotency is how
  duplicates are minted.
- **Idempotency keys on anything that mutates** — retries and webhook redeliveries
  are normal operation, not edge cases.
- **Features that need the external degrade visibly:** the Procore-sync panel says
  "Procore unavailable — showing data as of 14:02" and the rest of the app works.
  Blank screens and infinite spinners are the load-bearing tell.

## Progress honesty — long-running work reports real state

The full patterns are in `references/progress-honesty.md`; the contract:

- **Progress is a function of real state** — work completed over work known, read
  from durable checkpoints — never a timer, an easing curve, or a bar that glides to
  90% and waits. A fake progress bar is an unearned claim rendered as UI.
- **Results reveal only after verified success.** "Done ✓" follows the check, not
  the optimistic assumption. (What counts as verified is `verification-discipline`'s
  bar, where installed.)
- **Stalls hand off honestly.** When a job stalls or dies, the user sees where it
  actually stopped — last durable checkpoint, what's confirmed done, what's unknown
  — and what happens next (resume, retry, escalate). Never a spinner forever; never
  a "failed" that discards the partial truth.
- Long jobs are **chunked with durable checkpoints** so that progress is real,
  stalls are visible, and resume starts where the work stopped instead of at zero.

## Boundaries

- **Where credentials live** → the always-on secrets policy, enforced by the §6 hook
  in the house setup. This skill detects incompleteness; it doesn't own placement.
- **Instrumenting the integration** — correlation IDs, structured events, the
  dead-man alert on a stopped poller — → `observability`, where installed. Same
  pipeline, operator-facing; this skill owns what the *user* is told.
- **Proving the integration works** → `verification-discipline`, where installed.
- **Testing the adapter** — contract tests against the sandbox, the fake pinned by
  the same contract suite — is `testing-strategy`'s doubles policy, where installed;
  the demo implementation here doubles as that fake, and the pinning rule lives
  there, not here.
