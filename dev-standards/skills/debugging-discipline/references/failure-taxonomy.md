# Failure taxonomy — recurring classes, tells, and first probes

Nine failure classes that account for a disproportionate share of real bugs. For each:
the **tell** (the symptom pattern that suggests the class), the **usual mechanism**,
and the **first probe** — the cheapest observation that confirms or kills the match.
A matched class is a hypothesis, not a verdict: it still gets a falsification condition
like any other.

## 1. Heisenbugs — it disappears when observed

**Tell:** fails normally, passes under the debugger, with logging added, or when run
step-by-step. **Mechanism:** the failure depends on timing or memory layout, and
observation changes both — a race that the debugger's slowness hides, an uninitialized
value that instrumentation happens to overwrite. **First probe:** switch to the least
invasive observation available — post-hoc log correlation, a counter written at exit,
core dump analysis — and treat "observation makes it pass" as evidence in itself: the
bug is timing-sensitive, which immediately suggests class 2.

## 2. Ordering and races

**Tell:** intermittent; worsens under load or parallelism; "works on my machine";
failure rate changes when unrelated code changes timing. **Mechanism:** two operations
whose order was assumed but never enforced — shared state, unawaited async work, test
pollution from a previous test's leftovers. **First probe:** force the suspected order
both ways (add a deliberate delay or barrier); if failure becomes deterministic in one
ordering, the race is confirmed. For test flakes: run the failing test alone — if it
passes solo and fails in the suite, it's pollution, and bisecting the *test order*
finds the polluter.

## 3. Cache and staleness

**Tell:** "the fix didn't take"; correct after a restart or hard refresh; two readers
disagree about the same value; behavior lags a deploy. **Mechanism:** a stale layer —
CDN, HTTP cache, app-level cache, ORM identity map, memoization, browser — serving a
value whose source has moved on; or a cache key missing a dimension (see class 7).
**First probe:** bypass the suspected layer explicitly (cache-buster, direct source
query) and compare answers; a mismatch convicts the layer. Then enumerate every cache
between the reader and the source — the one nobody remembers exists is the usual
culprit.

## 4. Environment drift

**Tell:** works locally, fails in CI or production (or vice versa); broke without any
code change; works for one developer only. **Mechanism:** the environments genuinely
differ — runtime version, env var, locale, installed extension, filesystem
case-sensitivity, region, clock. **First probe:** stop reasoning from memory of what
the environments *should* be and diff what they *are*: print versions, env names (not
values — secrets), locale, timezone from inside both environments and compare
mechanically. The drift is usually in the layer everyone considers too boring to check.

## 5. Timezone and DST

**Tell:** off by exactly one hour, one day, or a "date" boundary; affects only some
users or only some dates; failures cluster twice a year (DST transitions) or at
midnight/month boundaries. **Mechanism:** a timestamp interpreted in different zones by
different layers, date-only values stored as midnight timestamps, or arithmetic done in
local time. **First probe:** take one failing value and trace its exact representation
through every layer — DB storage, ORM, API JSON, client display — writing down zone and
offset at each hop; the hop where the meaning changes is the bug.

## 6. Encoding and normalization

**Tell:** works for ASCII, breaks for names with accents, emoji, or CJK text; two
strings that print identically compare unequal; data corrupts only through one
particular path. **Mechanism:** mixed encodings at a boundary, or Unicode
normalization mismatch (é as one codepoint vs. e + combining accent), case-folding
surprises, invisible characters from copy-paste. **First probe:** hex-dump the actual
bytes of one failing value at each boundary (file → DB → API → display); the boundary
where the bytes change unexpectedly is the culprit. Never trust what a terminal
*displays* — inspect bytes.

## 7. Off-by-one-tenant

**Tell:** a user sees data that isn't theirs; counts or totals include a stranger's
rows; a bug reproducible only as a specific tenant, or only after a *different* tenant
was active. **Mechanism:** an unscoped query, a cache key missing the tenant dimension,
or tenant context leaking across pooled connections (session-level state that outlives
the request). **First probe:** find one leaked record and ask "what query path could
have returned this row?" — then check that path's tenant scoping, its cache key
composition, and whether connection-level state (`SET` vs `SET LOCAL`, thread-locals)
persists across requests. Treat any confirmed case as an incident, not just a bug — a
tenant boundary failed.

## 8. Double-processing and non-idempotency

**Tell:** exactly-twice effects — duplicate emails, double charges, repeated rows with
close timestamps; intermittent; worse under load or retries; "can't reproduce locally"
(local runs have no retries or concurrency). **Mechanism:** at-least-once delivery
doing what it promises (webhook redelivery, queue retry after a slow ack, client
retry on timeout) against a handler that assumes exactly-once; or two consumers on one
subscription. **First probe:** take one duplicate pair and compare the *delivery
identifiers*, not the payload: same message ID delivered twice (redelivery — check ack
timing and retry policy) vs. different message IDs with identical content (producer
sent twice) vs. same message consumed by two workers (concurrency). The identifiers
decide which of three different bugs it is — and which idempotency key would have
absorbed it.

## 9. Aggregation and join fan-out

**Tell:** a value is exactly N× the correct answer — double, triple — and only for some
slices (some warehouses, some months, some customers); detail rows look right, the
total is wrong. **Mechanism:** a join that duplicates rows before an aggregate — a
dimension with duplicate keys, a many-to-many crossed where one-to-many was assumed, a
filter context (SQL join, BI relationship, DAX measure) multiplying rows for exactly
the slices that have multiple matches. **First probe:** pick one bad slice and count
the *rows feeding the aggregate* against the count for a good slice; if the bad slice
shows N rows per expected one, hunt the duplicating key — `GROUP BY key HAVING
COUNT(*) > 1` on the joined dimension (or the BI equivalent) names it directly. The
slices that fail are the slices with duplicates; that correlation is the confirmation.
