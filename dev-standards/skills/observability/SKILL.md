---
name: observability
description: "Instrument code so production failures are diagnosable: structured logs with stable field names, correlation IDs carried across service and job boundaries, what belongs in a log versus a trace versus an alert, and never logging secrets or PII. Use this whenever adding logging or error tracking, wiring up Sentry, building a background job, worker, or integration, and whenever the user asks how they will know something broke or how to debug something that already happened in production."
---

# Observability

A production failure is diagnosed with whatever was recorded *before* anyone knew
there would be a failure. Instrumentation is writing the evidence file for a debugging
session that hasn't happened yet — which sets the bar for every line: **will this
answer a question someone asks at 2am, and can a machine group and filter it?** A log
that can't do both is cost without evidence.

## Structured logs with stable field names

- **Structured key-value events, never interpolated prose.**
  `{"event": "invoice.approved", "invoice_id": "INV-0117", "tenant_id": "t_204"}`
  beats `"Invoice INV-0117 was approved"` — because logs are *queried*, not read in
  order. Prose can't be grouped by tenant, filtered by event, or joined on an ID;
  the 2am question is always a query.
- **Field names are a contract.** The same concept carries the same name everywhere —
  `tenant_id` never `tenantId` in one service and `org` in another. Every saved
  query, dashboard, and alert is built on those names, and a rename breaks them all
  *silently* — dashboards don't error, they just go quiet. The house set lives in
  `references/field-conventions.md`.
- **`event` is a namespaced constant** (`domain.action`: `ingest.file_parsed`,
  `billing.charge_failed`); the human-readable `message` is a gloss, never the thing
  parsed.
- **Log IDs, not objects.** A serialized object dump bloats storage, drifts with the
  schema, and is where secrets and PII sneak in. The ID lets the investigator join to
  the source of truth, which is fresher than any log anyway.

## Correlation IDs across every boundary

Mint one ID at the edge — request arrives, webhook received, job enqueued, timer
fires — and carry it through everything that follows: HTTP handler → queue message
metadata → worker → downstream API calls → every log line and error report each of
them emits.

Without it, production diagnosis degenerates to joining logs on timestamps, which
fails precisely when it matters — under concurrency and retries, when five workers'
lines interleave. With it, one filter reconstructs the whole story of one request.

- Chained work carries both its own ID and its parent's (`correlation_id` from the
  edge, `job_id` of its own, `parent_job_id` when spawned).
- Batch work adds `batch_id` + a per-item reference, so "which file failed" is a
  query, not an inference.
- The error tracker gets the same IDs as context — a Sentry event that can't be
  joined to its logs is a stack trace with amnesia.

## What goes where: log, trace, metric, alert

Four different questions, four different instruments — most observability messes are
one of these doing another's job:

| Instrument | Question it answers | Shape |
|---|---|---|
| **Log** | What happened, with what context? | Discrete structured events — the evidence |
| **Trace/span** | Where did the time go? | Timed tree across boundaries. No tracing infra? `duration_ms` fields on wide log events are the budget version |
| **Metric** | How much / how many / how fast, over time? | Cheap aggregates, **low-cardinality labels only** — feeds dashboards and thresholds |
| **Alert** | Does a human need to act *now*? | A demand for attention; the scarcest resource in the system |

The two classic cross-wirings: alerting on everything that logs an error (pager
fatigue — after a week, all alerts are ignored, including the real one), and logging
what should be a metric (a log line per poll per item, at volume, answering no 2am
question). Alert design — what deserves a page versus a dashboard — lives in
`references/alert-design.md`.

## Levels that keep their meaning

`ERROR`: an invariant broke or work was lost — a human should look. `WARN`: degraded
or retried but handled — patterns matter, single events don't. `INFO`: state changes
worth an audit trail. `DEBUG`: off in production by default.

The discipline point: an ERROR that fires routinely and means nothing teaches
everyone to ignore ERROR — level inflation is how real failures hide in plain sight.
If it's expected and handled, it is not an ERROR, however alarming it felt to write.

## Cardinality and retention sanity

- **Unbounded values never become metric labels.** `user_id`, `file_path`, raw URLs
  with IDs — each unique value mints a new time series; the cost curve is the number
  of *distinct values*, not events. IDs belong in logs and traces; metrics get
  bounded enums (`outcome: success|retryable|permanent`, `stage`, `queue`).
- **Retention follows the question's lifespan.** Logs are short-lived evidence
  (weeks); metrics are long-lived trends (months+); and **audit records are not
  logs** — "who approved this invoice" is domain data with its own store and
  retention, not a log line that expires with the shipper's window.
- **Sample the noisy success path if volume demands it — never sample errors.** A
  sampled success stream still shows the shape; a sampled error stream hides the one
  event the whole apparatus exists to catch.

## Never log secrets or PII

Logs replicate to more places than the database ever will — the shipper, a
third-party SaaS, dashboards, CI output, a developer's terminal scrollback. A secret
in a log is a secret with copies, and PII in logs quietly extends every privacy
obligation to your logging vendor.

- Never: tokens, passwords, connection strings, cookies/headers wholesale, card or
  bank numbers, raw request/response bodies (they contain all of the above on their
  worst day).
- Minimize PII: IDs instead of names and emails; if a human needs the email, they
  can join the ID to the source system, which is access-controlled — the log stream
  isn't.
- **Design redaction at the logger boundary, not the call site.** A serializer-level
  allowlist of loggable fields survives the hundredth hurried log line; per-callsite
  discipline doesn't. In the house setup a hook *enforces* the no-secrets rule at
  write time (enforcement is its job, not this skill's); design so that hook never
  has anything to catch — and on surfaces with no hooks, this section is the whole
  defense.

## Error trackers (Sentry and kin)

Capture the unhandled everywhere it can happen (server, client, edge/functions — an
app instrumented only server-side is blind in one eye), tag every event with
`correlation_id`, `tenant_id`, and release, and upload source maps so stack traces
name real lines. Alert on *new issue, regression, spike* — not on every event; the
tracker is a grouping tool, not a pager. Scrub before send (PII settings off by
default, `beforeSend` as the allowlist gate) — the previous section applies doubly to
a third-party sink.

## Boundaries

- **Blocking a secret at write time** is the §6 hook's job — enforcement, not
  persuasion. This skill designs logging so the hook stays silent.
- **Temporary instrumentation while chasing a bug** — added, used, removed — belongs
  to `debugging-discipline`, where installed. This skill owns what *ships*; if a
  chase-line earns permanence, it re-enters here through the same rules as any other
  line (structured, stable names, no secrets).
- **User-facing progress reporting for long jobs** → `integration-adapters`, where
  installed. Same pipeline, different audience: this skill instruments for the
  operator; that one governs what the *user* is told.
- **Proving the instrumentation works** (the log line actually emits, the alert
  actually fires) → `verification-discipline`, where installed — an alert that has
  never fired in a test is a hope with a threshold.
