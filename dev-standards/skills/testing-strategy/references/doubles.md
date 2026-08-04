# Test doubles — decision table and rules

Vocabulary first, because arguments about mocking are usually two people using one
word for five things:

| Double | What it does | Legitimate use |
|---|---|---|
| **Dummy** | Fills a parameter list, never used | Satisfying a signature |
| **Stub** | Returns canned answers | Forcing a specific input condition |
| **Spy** | Records calls for later inspection | The rare case where the call is the contract |
| **Mock** | Pre-programmed expectations that fail the test if unmet | Same rare case, stricter; overused everywhere else |
| **Fake** | Working lightweight implementation (in-memory repo) | Fast consumer tests — *if* contract-pinned (below) |

## The decision table

| Boundary | Use | Why |
|---|---|---|
| **The code under test** | Nothing. Never doubled. | A doubled subject means the test verifies the double. Cardinal error. |
| **Your own database** | Real, in a local container | SQL semantics, constraints, transactions, and migrations are exactly what in-memory fakes get wrong — and exactly what fails in production. |
| **Your own queue/bus** | Real local instance, or a contract-pinned fake | Delivery semantics (at-least-once, visibility timeout) are the thing worth testing. |
| **External paid/slow API (Stripe, Procore)** | Your adapter: integration-test against the vendor **sandbox** plus **recorded real payloads**. Adapter consumers: the adapter's **fake**. | You own the adapter contract, not the vendor. Consumers testing through a fake adapter stay fast; the adapter's own tests keep the fake honest. |
| **The clock** | Injected clock/time source | Time is an input. Tests that read the real clock are flakes on a delay (DST, midnight, month-end). |
| **Randomness / ID generation** | Seeded or injected | Same: nondeterminism is an input, control it at the seam. |
| **The network itself** | Doubled at your HTTP boundary (recorded responses), never deeper | Recording keeps the double tethered to reality; hand-written response JSON drifts immediately. |
| **Filesystem** | Real temp dirs (cheap and honest) | Fake filesystems buy little and hide path/encoding bugs. |

## Rules with their reasons

- **Inject at seams; don't monkey-patch internals.** A clock parameter or adapter
  interface is a designed, visible seam. Patching a module's private import rewires
  the implementation — the test now depends on internals it was supposed to ignore,
  and breaks on refactor like any other implementation-coupled test.
- **Pin every fake with a contract test.** The fake's promises ("save then get
  returns the saved object", "duplicate key raises") are written once as a shared
  test suite and run against **both** the fake and the real implementation. When the
  real thing changes, the contract fails on the real side and the fake gets updated —
  without this, fakes drift silently and consumer tests pass against a fiction.
- **Record, don't transcribe, vendor payloads.** A webhook fixture captured from the
  sandbox (scrubbed) is evidence; one typed from the docs is a guess wearing
  evidence's clothes. Re-record when the vendor versions their API.
- **Assert call-counts only where the call is the promise.** "Exactly one charge per
  idempotency key under double-delivery" — yes, that's the behavior itself. "The
  repository's save method was called once with these arguments" — no; assert the
  row exists instead.
- **If mocking feels hard, the seam is wrong.** Needing to patch five internals to
  isolate one function is design feedback: the boundary wants extracting. Fix the
  seam rather than deepening the mocks.

## Anti-patterns, named

- **Mockery all the way down:** every dependency mocked, including the ORM the query
  under test runs through — the suite passes while no SQL has ever executed.
- **The prophetic mock:** a mock programmed with the exact call sequence the
  implementation makes, then asserted. The test is a mirror; any refactor "fails" it.
- **The drifted fake:** in-memory repo that allows what the real DB forbids (missing
  unique constraint) — consumers green, production violated. Contract-pin it.
- **Sandbox in every test:** hitting the vendor sandbox from hundreds of consumer
  tests — slow, rate-limited, flaky. The sandbox belongs to the adapter's few
  contract tests; everyone else gets the fake.
