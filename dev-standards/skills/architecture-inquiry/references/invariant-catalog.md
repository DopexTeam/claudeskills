# Invariant catalog — recurring classes, with catastrophes

Recurring invariant classes. Each entry: when the class applies, example invariants in
quotable form, and the shape of the catastrophe. This is a prompt, not a checklist —
an invariant enters a project's record only when a domain answer justifies it, and its
catastrophe must be named concretely for *that* system ("tenant A's invoices appear in
tenant B's portal"), never generically ("data integrity issues"). An invariant without
its catastrophe gets traded away in the first performance conversation.

## Tenancy & isolation

*Applies when:* more than one tenant, client, or organization shares the system.

- "No query path returns data across a tenant boundary without an explicit,
  server-derived tenant context." — **catastrophe:** one tenant's commercial data
  (pricing, invoices, disputes) rendered in a competitor's account; contract breach,
  client loss, possible legal exposure.
- "Tenant context is derived from the authenticated session, never from a
  client-supplied identifier." — **catastrophe:** a forged ID in a request body walks
  straight through the boundary that every other control assumed was closed.
- "Tenant context set per-transaction (`SET LOCAL`), never per-session." —
  **catastrophe:** a pooled connection carries tenant A's context into tenant B's
  query; leakage that is intermittent, load-dependent, and nearly impossible to
  reproduce in dev.

## Money

*Applies when:* anything is billed, paid, refunded, or reconciled.

- "Every money-moving operation is idempotent under an idempotency key." —
  **catastrophe:** a webhook retry or double-click charges a customer twice; trust is
  spent on the apology, hours on the manual refund.
- "Money amounts are integers in minor units; floating point never touches a monetary
  value." — **catastrophe:** cent-level drift across thousands of transactions that
  reconciliation surfaces months later, with no way to say which records are right.
- "A payment event is never dropped: processed, or persisted as failed and retried —
  no third state." — **catastrophe:** a customer paid, the system has no record; the
  dispute arrives with a bank statement attached.
- "Recorded money is append-only: corrections are new entries, never edits." —
  **catastrophe:** an audit or dispute finds mutated history, and every other number
  loses credibility with it.

## Identity & authorization

*Applies when:* more than one role or actor exists.

- "Authorization derives server-side from the session; client-supplied role, ID, or
  scope is never trusted." — **catastrophe:** a modified request elevates a
  subcontractor to admin; the breach is silent because the UI never offered the button.
- "Privilege changes and sensitive reads are audit-logged with actor and timestamp." —
  **catastrophe:** an incident happens and the honest answer to "who could see this?"
  is a shrug — which is itself reportable in regulated contexts.

## Data lifecycle & audit

*Applies when:* records are edited, deleted, retained, or reviewed.

- "Records referenced by money, audit, or law are soft-deleted or archived, never
  hard-deleted." — **catastrophe:** an invoice named in a dispute no longer exists;
  its foreign keys now point at nothing, so adjacent records are corrupt too.
- "Audit trails are append-only and record actor, action, timestamp, and prior value."
  — **catastrophe:** the trail can be edited by the person it implicates, so it proves
  nothing exactly when it's needed.
- "Retention and destruction follow a stated schedule." — **catastrophe:** data held
  past its legal retention becomes liability; data destroyed early becomes spoliation.

## Concurrency & idempotency

*Applies when:* retries, queues, webhooks, background jobs, or multiple writers exist.

- "Every job and webhook handler is safe to run twice." — **catastrophe:** at-least-once
  delivery does what it promises, and the double-run double-writes, double-emails, or
  double-bills — intermittently, under load, unreproducibly in dev.
- "Concurrent edits to the same record are detected (versioning/locking), never
  last-write-wins by accident." — **catastrophe:** two people edit; one person's work
  silently vanishes; they find out when the client does.
- "Order-dependent effects declare their ordering key; nothing assumes queue order
  otherwise." — **catastrophe:** an update arrives before its create under burst load;
  the handler crashes or, worse, resurrects a deleted record.

## Time

*Applies when:* anything is scheduled, dated, deadlined, or timezone-spread.

- "Timestamps are stored in UTC; timezone conversion happens at display, using the
  *relevant party's* zone." — **catastrophe:** an invoice due date lands a day off for
  half the tenants; late fees get charged on time that never elapsed.
- "Date-only values (due dates, service dates) are stored as dates, not midnight
  timestamps." — **catastrophe:** the same DST or timezone shift moves a legal deadline
  across a day boundary.
- "Nothing assumes clocks agree across machines." — **catastrophe:** ordering built on
  wall-clock time inverts under skew; 'latest' isn't.

## External dependencies

*Applies when:* a third-party API, webhook source, or vendor system is integrated.
The umbrella rule is owned by `integration-adapters` (where installed): **externals are
never load-bearing** — restated here because it generates invariants, not to redefine it.

- "The system remains available — degraded, honest, but available — when the external
  is down." — **catastrophe:** the vendor's outage becomes your outage, and the client
  learns your product is a thin wrapper at the worst possible moment.
- "External data is validated at the boundary; nothing downstream trusts a payload
  shape." — **catastrophe:** a vendor's unannounced field change corrupts records
  quietly for weeks before anyone notices.
- "Half-configured credentials fail loudly at startup, never silently at first use." —
  **catastrophe:** the demo works, production is missing one env var, and the failure
  surfaces as a confusing runtime error three layers away from its cause.

## State machines

*Applies when:* records have a lifecycle (draft → submitted → approved → paid…).

- "State transitions go through one guarded path; no code writes a status field
  directly." — **catastrophe:** an invoice reaches `paid` without passing `approved`;
  the money moved on a record that skipped its own controls.
- "Every state is reachable and leavable; terminal states are explicit." —
  **catastrophe:** records wedge in a state no code handles, accumulating silently
  until someone asks why 400 invoices are 'processing' from last quarter.
