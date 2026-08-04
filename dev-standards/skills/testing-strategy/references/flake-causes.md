# Flake causes — ranked, with tells and fixes

A flake is a bug with a probability attached. The causes below are ranked roughly by
how often they're the culprit; each carries its tell, the first probe, and the real
fix. The diagnosis *loop* (hypothesis, falsification, bisection) belongs to
`debugging-discipline` — this file supplies the test-specific hypotheses to feed it.
The one response that is never on the list: re-run until green and move on. Retries
convert a signal into a lie.

## 1. Test pollution — shared state between tests

**Tell:** passes alone, fails in the full suite (or vice versa); failure depends on
which tests ran before; "fails about a third of the time" tracks parallel-worker
scheduling. **Probe:** run the failing test in isolation, then run the suite in a
fixed seeded order that reproduces the failure — bisect the *test order* to find the
polluter. **Fix:** isolate — per-test transactions rolled back, per-test data with
unique keys, reset globals/caches in teardown. Then keep randomized order on locally,
so new pollution surfaces immediately instead of in CI.

## 2. Time-based waits in async tests

**Tell:** `sleep(2)` (or a fixed timeout) before asserting something async happened;
fails on slow CI, passes on a fast laptop; failure rate tracks machine load.
**Probe:** does doubling the sleep drop the failure rate? Then it's this. **Fix:**
wait on the *condition*, not the clock — poll for the row/message/state with a
generous ceiling. A condition-wait passes in 50ms locally and 4s on CI; a fixed sleep
is always both too long and too short. (Blindly raising the timeout is the same bug
with worse latency.)

## 3. Shared resources on the CI runner

**Tell:** local is fine; CI fails when the suite runs parallel workers — port
collisions, same temp path, two workers on one database/schema, Docker port already
allocated. **Probe:** run CI with one worker; if the flake vanishes, it's contention.
**Fix:** per-worker everything — ephemeral ports (bind port 0), per-worker
schemas/databases, `mktemp` dirs, container names salted with the worker ID.

## 4. Unpinned nondeterminism

**Tell:** failures mention ordering (lists compared where the query has no
`ORDER BY`, set/dict iteration), or IDs/randoms that occasionally collide, or
snapshot diffs on timestamps. **Fix:** pin the nondeterminism — explicit `ORDER BY`
before comparing sequences, seeded randomness, injected clock/ID generator — or relax
the assertion to what's actually promised (set equality, not sequence equality).

## 5. The environment boundary inside the test

**Tell:** the test reaches something real — the vendor sandbox, DNS, the network —
and fails with timeouts or 429s at busy hours. **Fix:** that dependency belongs
behind the adapter's few contract tests (see `doubles.md`); everything else runs
against the recorded/faked boundary. A consumer test that can be failed by someone
else's rate limiter is testing their weather, not your code.

## 6. Readiness races in test infrastructure

**Tell:** first test after container/app startup fails; "connection refused" then
green on retry. **Fix:** health-check readiness (poll the port/endpoint until it
answers correctly), never a startup sleep — same principle as cause 2, applied to
infra.

## 7. Time itself — clocks, zones, boundaries

**Tell:** fails only around midnight, month-end, DST transitions, or on the CI
runner's timezone; date assertions off by one. **Fix:** injected clock, UTC
normalization in test data, and — where date math is the subject — explicit boundary
cases as *deterministic* unit tests (Dec 31, DST day, leap day) instead of hoping the
calendar never lands there.

## 8. A real race in the code under test

The valuable flake. **Tell:** none of the above fits; the failure reproduces (rarely)
even in isolation with pinned time and data; stack traces differ run to run;
production shows matching intermittent weirdness. **Response:** do not kill the
messenger — don't serialize the test or widen a lock in the *test* to make it green.
This is a bug report from your own suite: hand it to the debugging loop
(`debugging-discipline`, failure class "ordering and races") and treat the test as
the reproduction it just handed you.
