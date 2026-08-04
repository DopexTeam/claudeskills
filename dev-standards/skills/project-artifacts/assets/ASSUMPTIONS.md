# ASSUMPTIONS

<!--
Copy this file to the project's document location on first use. Keep this comment block.
- Log an assumption instead of stalling — but check the stop-list first. If the action
  would be irreversible or destructive, touch production, change security posture, incur
  spend, invalidate a SETTLED decision, or need a credential the session doesn't hold:
  STOP AND ASK. Those are escalations, not assumptions.
- IDs are permanent; same rules as DECISIONS.md.
- Every entry gets a disposition by session end. Nothing crosses a handoff as "pending".
  promoted → write the D-### entry it became. refuted → the affected decision moves
  back to open. carried → it keeps a named owner and a concrete re-check trigger.
-->

## A-001 — <the assumption, stated as a claim that could be wrong>

- **Date:** YYYY-MM-DD
- **Why needed:** <the gap that forced it — what couldn't proceed without assuming>
- **Blast radius if wrong:** <what breaks, how far it spreads, how hard it is to undo>
- **Disposition:** pending | promoted → D-### | refuted → reopens D-### | carried (owner: <name>, re-check: <trigger>)

---

### Worked example (delete once real entries exist)

## A-001 — Procore invoice webhooks arrive at most once per invoice per hour

- **Date:** 2026-08-02
- **Why needed:** Rate limiting on the ingest endpoint had to be set before the client could confirm actual webhook volume; work would have stalled a day waiting.
- **Blast radius if wrong:** Bursts above the limit get 429s and Procore retries with backoff — invoices delayed, none lost. Annoying, recoverable, invisible to tenants.
- **Disposition:** carried (owner: Jason, re-check: first week of production traffic — compare ingest logs against the limit)
