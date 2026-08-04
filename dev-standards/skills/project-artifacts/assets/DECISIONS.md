# DECISIONS

<!--
Copy this file to the project's document location on first use. Keep this comment block.
- IDs are permanent. Never renumber, never reuse — commits, handoffs, and assumptions
  refer to entries by ID. Supersede with a new entry that links back; never rewrite history.
- Status moves: open → settled, open → deferred, deferred → open.
  settled → open is a REOPENING: it requires the human's sign-off, never a session's
  own judgment. A session that believes a settled decision is wrong stops and asks.
- Invariants are quoted exactly wherever they are repeated. Paraphrases drift, and a
  drifted invariant is a loophole.
-->

## D-001 — <short title>

- **Status:** settled | open | deferred
- **Date:** YYYY-MM-DD
- **Decision:** <what was decided, concretely — one or two sentences>
- **Rationale:** <why this option won>
- **Rejected alternatives:**
  - <alternative> — <the specific reason it lost>
- **Invariants:** <rules this decision creates; omit the section if none>
  - "<exact, quotable wording of the rule>" — **catastrophe if violated:** <the named, concrete bad outcome>
- **Supersedes / superseded by:** <D-### links, or omit>

---

### Worked example (delete once real entries exist)

## D-001 — Job queue: managed queue service over a Postgres-backed queue

- **Status:** settled
- **Date:** 2026-08-02
- **Decision:** Background work runs through the platform's managed queue service, not a jobs table in Postgres.
- **Rationale:** Retry semantics, dead-lettering, and visibility timeouts come built; a hand-rolled jobs table re-implements all three badly and couples job throughput to the primary database.
- **Rejected alternatives:**
  - Postgres `jobs` table with `SELECT ... FOR UPDATE SKIP LOCKED` — workable at low volume, but backfill bursts would contend with tenant queries on the same instance.
  - Redis-backed queue — one more stateful service to operate; nothing in the workload needs its latency.
- **Invariants:**
  - "A job must be idempotent: processing the same message twice produces the same end state." — **catastrophe if violated:** duplicate delivery (which the queue explicitly permits) double-bills a customer or double-writes a record.
