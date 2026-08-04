---
name: testing-strategy
description: "Decide what to test and how: behavior over implementation, never mock the thing under test, fixtures versus factories, the boundaries worth integration-testing, and what should not be tested at all. Use this whenever writing or reviewing tests, whenever the user asks about coverage, mocks, stubs, fixtures, flaky tests, or \"should I test this,\" and whenever adding a feature where the test approach should be decided deliberately rather than defaulted into."
---

# Testing Strategy

A suite's value is the failures it catches minus the drag it adds, and most bad suites
lose on both sides at once: coupled to implementation detail (so they break on every
refactor while catching nothing) and absent from the boundaries where systems actually
fail. Neither happens by malice — it happens by *defaulting into* a test approach
instead of deciding one. This skill is the deciding.

## Test behavior, not implementation

A test asserts the contract: given this input and state, this observable outcome — a
return value, a row, a response, an emitted event. It does not assert which internal
methods were called, in what order, with what private arguments.

**The refactor test:** a pure refactor — behavior identical, internals rearranged —
should break zero tests. Every test that breaks is drag masquerading as coverage: a
change detector, not a test. It punishes exactly the maintenance the suite exists to
make safe, and it trains people to update tests reflexively instead of reading
failures. Test through the unit's public surface; if a private helper seems to need
its own tests, that's usually a unit trying to be extracted, not a reason to reach
around the interface.

## Choosing the level

Pick the *lowest* level that can actually catch the failure class you're defending
against — and be honest about what each level can see:

- **Unit** — pure logic with meaningful branching: money math, date arithmetic, state
  transitions, parsers, validation rules. Fast and precise; this is where exhaustive
  cases live (boundaries, zero, negative, huge, malformed).
- **Integration** — the boundaries: your code meeting the real database, the real
  queue, the framework's real wiring, your adapter meeting the vendor's sandbox.
  Most production failures are boundary failures — serialization, SQL semantics,
  transactions, config, auth plumbing — and unit tests with mocks are *structurally
  unable* to catch them: the mock embodies your assumption, and the assumption is
  what's wrong.
- **End-to-end** — a handful, reserved for the money paths: the flows whose breakage
  is an incident (submit invoice → it reaches review; checkout → a charge exists).
  Each E2E test is slow, flake-prone, and expensive to own; each one must earn its
  place by covering a failure whose cost justifies that overhead.

The resulting shape is usually pyramid-ish — many unit, boundary-focused integration,
few E2E — but the shape is an *output* of risk analysis, not a quota to fill.

## Doubles: the policy

Full decision table in `references/doubles.md`. The rules that carry it:

- **Never mock the thing under test.** If the code you're verifying is replaced or
  partially stubbed, the test verifies the stub. This is the cardinal error and it's
  usually well-intentioned — "just isolating" — which is why it needs a hard rule.
- **Mock only at boundaries you don't own or can't run:** the paid external API, the
  clock, randomness, the network beyond your adapter. Inject these (a clock
  parameter, an adapter interface) rather than monkey-patching internals — injection
  points are the honest seams.
- **Prefer real over fake when real is cheap.** A real database in a local container
  catches what an in-memory fake structurally cannot (SQL semantics, constraints,
  transactions). Fakes drift from reality silently; where a fake must exist, pin it
  with a contract test that runs the same assertions against the real thing.
- **Call-count assertions are implementation coupling** — except where the call *is*
  the contract: "charged exactly once under retry" is a behavior; "repository.save
  was invoked with…" is not.

## Fixtures versus factories

- **Factories by default** — builders with sensible defaults and per-test overrides,
  so each test's setup states *only the fields that matter to it*. A test that reads
  `invoice(status="approved", total_cents=0)` documents its own intent; forty lines
  of irrelevant setup bury it.
- **Static fixtures for what must not drift:** golden known-answer data (the invoice
  whose total was computed by hand), recorded cross-system payloads (the actual
  Stripe webhook JSON, captured once, replayed forever), and realistic-mess samples
  (real-world names, encodings, edge formats). These are *evidence*, and evidence is
  versioned, not generated.
- **Beware the god fixture** — the one shared setup every test imports. Every change
  to it ripples through unrelated tests, and nobody can change anything. Fixtures
  stay small, purpose-named, and owned by the tests that read them.

## What not to test

Every test costs maintenance forever; these purchases are net-negative:

- **The framework or library itself** — the ORM's save/load round-trip, React
  rendering what the JSX says. Someone else's suite already covers it.
- **Trivial pass-throughs** — getters, config wiring, one-line delegations. The test
  restates the code; both change together; nothing is caught.
- **Private helpers directly** — covered through public behavior, or extracted into
  a real unit if they deserve their own contract.
- **Vendor behavior beyond your adapter's contract** — you test that *your adapter*
  handles the vendor's documented responses (recorded), not that the vendor works.
- **Pixel/styling snapshots as a default** — they fail on every intentional change
  and get approved reflexively within a month, which is a change detector with a
  rubber stamp. Reserve visual assertions for the rare case where layout *is* the
  requirement.
- **Anything whose failure would be shrugged at.** If red wouldn't block a merge,
  the test is noise generation with CI costs.

## Flaky tests

A flake is a bug — in the test, the harness, or (the valuable case) a real race in
the code under test. `references/flake-causes.md` ranks the causes with their tells
and fixes. What a flake is never: something to retry until green, wrap in a bigger
timeout unexamined, or skip and forget. A suite whose reds get re-run until they pass
has stopped being a signal, and everyone knows it within weeks — that's how suites
die. Quarantine honestly (skipped, ticketed, owned) while the cause is found; the
finding loop itself belongs to `debugging-discipline`, where installed.

## Boundaries

- **Whether the code works right now** — running today's checks to back today's
  claim — is `verification-discipline`'s job, where installed. This skill designs the
  durable suite; that one proves the current state. (A green suite verifies a change
  only if a test actually exercises it — that rule lives there.)
- **Why this test is failing** → `debugging-discipline`, where installed; the
  flake-causes reference feeds it test-specific hypotheses.
- **The cross-tenant isolation test** — this skill can explain its shape (a negative
  probe per boundary: authenticate as B, request A's data, assert denial), but in
  the house setup its *presence* is enforced as an artifact of record by tooling
  (hooks), not by this skill's persuasion. Where that enforcement exists, don't
  weaken it; where it doesn't (browser surfaces), treat the isolation test as
  non-negotiable anyway — it's the one whose absence is a breach, not a bug.
