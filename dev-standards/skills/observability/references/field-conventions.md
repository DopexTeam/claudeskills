# Field conventions — the house log schema

Stable names are the whole point: every dashboard, saved query, and alert is built on
them, and a rename breaks all three silently. Adopt these names per project, extend
them in the project's decision record, and never fork a concept's name between
services.

## Core fields — every log line

| Field | Form | Notes |
|---|---|---|
| `timestamp` | ISO 8601, UTC | The logger's job, not the caller's |
| `level` | `debug` \| `info` \| `warn` \| `error` | Levels keep their meaning (see SKILL.md) |
| `event` | `domain.action`, snake_case segments | `ingest.file_parsed`, `billing.charge_failed` — a bounded, greppable vocabulary |
| `message` | short human gloss | Never parsed, never load-bearing |
| `correlation_id` | string | Minted at the edge, carried everywhere |
| `service` | string | Which deployable emitted this |

## Context fields — when applicable

| Field | Form | Notes |
|---|---|---|
| `tenant_id` | string | On every line in tenant-scoped code paths — it's the first filter in every multi-tenant investigation |
| `actor_id` | string | Who initiated (user ID, `system`, `scheduler`) — an ID, never a name/email |
| `duration_ms` | integer | Unit lives in the name; the budget version of a span |
| `outcome` | bounded enum | `success` \| `retryable_failure` \| `permanent_failure` — enums, not free text, so they can be counted |
| `error.kind` / `error.message` / `error.stack` | nested | Only on `warn`/`error`; stack only on `error` |
| domain IDs | `invoice_id`, `file_id`, … | IDs as **strings** (int IDs overflow JS consumers), named `<entity>_id` |

## Job / worker / pipeline fields

| Field | Notes |
|---|---|
| `job_id` | This execution's own identity |
| `parent_job_id` | When spawned by another job — chains stay reconstructable |
| `job_kind` | Bounded enum: `backfill.embed_file`, `poll.clan` |
| `attempt` | Integer, 1-based — retries become visible instead of looking like duplicates |
| `batch_id` / `item_ref` | Batch identity + which item, so "which file failed" is a query |
| `queue_wait_ms` / `processing_ms` | The two halves of latency — they point at different fixes |

## Rules

- **snake_case keys, everywhere.** Mixed conventions mean every query is written
  twice.
- **Units in names:** `_ms`, `_bytes`, `_cents`. A bare `duration` is a guessing game
  at 2am.
- **Bounded enums for anything counted.** `outcome`, `job_kind`, `stage` — free text
  in a counted field splinters the count.
- **No payload dumps.** Log the ID and the *derived facts you'll query*
  (`chunk_count`, `size_bytes`), not the document. Payloads are where secrets, PII,
  and schema drift live.
- **Same concept, same name, both directions:** don't reuse a name for a different
  concept either — `duration_ms` of a job and of an HTTP call in one line need
  distinct names (`processing_ms`, `upstream_call_ms`).

## Worked example

Bad — prose, unstable, unqueryable, leaky:

```
logger.info(f"Processed file {path} for {user.email}: {len(chunks)} chunks in {t}s, payload={doc.json()}")
```

Good — one event, stable names, IDs only, units explicit:

```json
{"level": "info", "event": "backfill.file_embedded", "message": "file embedded",
 "correlation_id": "c_9f31", "batch_id": "bf_2026_08_02", "item_ref": "file_8812",
 "tenant_id": "t_204", "actor_id": "scheduler", "attempt": 1,
 "chunk_count": 141, "size_bytes": 904211, "queue_wait_ms": 3200,
 "processing_ms": 8125, "outcome": "success"}
```
