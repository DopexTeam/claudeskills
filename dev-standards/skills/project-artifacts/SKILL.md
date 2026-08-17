---
name: project-artifacts
description: "Write and maintain the project's canonical documents using fixed templates: numbered decision records, the ASSUMPTIONS log, operational runbooks, session handoffs, and the DESIGN ledger. Use this whenever a decision needs recording, a runbook or deployment procedure needs writing, an assumption needs logging mid-build, work needs handing off to another session or contributor, or the user asks where something should be documented — and whenever another skill produces output that needs a durable home. Owns document structure only; never makes the decisions it records."
---

# Project Artifacts

Sessions end. Decisions, assumptions, procedures, and design choices must not end with
them. Five documents are the project's durable memory — the interface between sessions,
between agents and humans, and between the person who decided and the person who
executes. This skill owns their structure and nothing else: it records decisions, it
never makes them.

## Routing — what just happened → which document

| Event | Document | Template |
|---|---|---|
| A decision was made, rejected, or deliberately deferred | `DECISIONS.md` | `assets/DECISIONS.md` |
| Work proceeded on an unverified belief | `ASSUMPTIONS.md` | `assets/ASSUMPTIONS.md` |
| A procedure will be run again — by a human, a machine, or both | `RUNBOOK-<name>.md` | `assets/RUNBOOK.md` |
| A session is ending or work is changing hands | `HANDOFF.md` | `assets/HANDOFF.md` |
| A visual or UI decision was resolved, or a direction rejected | `DESIGN.md` | `assets/DESIGN.md` |

If output from other work needs a durable home and none of the five fits, the answer is
almost always that a decision was actually made and belongs in `DECISIONS.md` — not that
a sixth document is needed. New document types dilute the guarantee that a reader knows
where to look.

## Rules that apply to all five

- **Copy the template from `assets/` on first use. Never improvise a variant.** The
  schema is a contract: any tooling that greps for a field name, and any human who has
  learned where to look, breaks silently when the structure drifts. Keep the template's
  comment block — it carries the rules to the next writer, who won't have this skill open.
- **IDs are permanent.** `D-014` stays `D-014` forever — never renumbered, never reused,
  even when superseded. Commits, handoffs, and assumption entries refer to decisions by
  ID; renumbering breaks every back-reference invisibly. Supersede with a new entry that
  links back.
- **One home per fact.** If a fact already lives in a sibling document, link it by ID
  rather than restating it. Two copies of a fact will eventually disagree, and a reader
  can't tell which one is lying.
- **Default location: `docs/`, split by how the document changes.** Not by topic — in a
  code repo nearly every document is developer-facing, so a `dev/` bucket swallows the
  tree and immediately needs subfolders. Mutability discriminates; topic doesn't:

  | Folder | Admission test |
  |---|---|
  | `decisions/` | Append-only, permanent IDs? → `DECISIONS.md`, `ASSUMPTIONS.md` |
  | `reference/` | Describes current state, overwritten in place? |
  | `sessions/` | Scoped to one build session? → build prompts, `HANDOFF.md` |
  | `ops/` | Read while something is on fire? → `RUNBOOK.md` |
  | `business/` | Reader is not an engineer? |
  | `legal/` | Legally operative, authority from outside engineering? |
  | `incoming/` | Authored outside the repo, not yet routed? |
  | `old/` | Superseded by a named successor that exists **today** — or a spent session document (see below)? |

  Ties break toward the earlier row. `docs/README.md` is the index and the **only** home
  for the map. Four files stay at the repo root because tooling pins them there —
  `CLAUDE.md`, `AGENTS.md`, `README.md`, `ONBOARDING.md` — and moving them breaks the
  thing that loads them.

  **A very small project can keep these at the root**, and a project that already does
  should not be reorganized as a drive-by. Moving an existing flat root into the tree is
  its own deliberate act, recorded as a numbered decision. When you do move: **the ID
  scheme already in use wins** over this skill's `D-001` format — back-references are
  load-bearing, and renumbering breaks every one of them silently.

- **Session documents drain into `old/` when they are spent.** Three cases, one rule —
  the plan stays lean, the record stays whole:
  - A **completed build-prompt file** (every session in it closed) moves to `docs/old/`
    whole, with a header naming what closed it and when.
  - A **closed session's body** inside a still-active plan file archives to `docs/old/`
    (one accumulating archive file per plan is fine) — but **its map row stays in the
    plan forever**: status, date, what it shipped as. The row is the record; the body
    is the archive.
  - A **spent brief** — a session input whose output has returned and been routed —
    moves to `docs/old/` with a pointer to the output. A brief whose deliverable exists
    is done; keeping it in `sessions/` makes the plan read longer than it is.
  On filename collisions with a live successor, suffix the version
  (`PRICING-BOOK-V0.md`), never keep two files answering to one bare name.

- **Documents authored outside the repo land in `docs/incoming/` first, never straight
  into the tree.** A browser session, another chatbot, a lawyer's draft — none of them
  had the record in view, so they may assert things about the system that aren't true or
  re-decide something already settled. Filing one directly launders an outside opinion
  into project truth. The full pass — classify, preserve the ID namespace, check claims
  against the repo, diff against the record, escalate contradictions, route with
  provenance — is in `references/incoming-triage.md`. **Read it before routing anything.**
  The one rule that cannot be deferred: an incoming document that contradicts a *settled*
  decision produces a supersession proposal and a stop, never a quiet amendment.

## DECISIONS.md — the numbered record

Template: `assets/DECISIONS.md` (includes a worked example).

- Every entry carries a **status**: `settled`, `open`, or `deferred`. The statuses are
  load-bearing: settled means the project builds on it without re-asking; open means it
  still needs the human; deferred means deliberately postponed, with the record showing
  it was postponement, not oversight.
- **Reopening a settled decision is an escalation, not an edit.** A session that
  concludes a settled decision is wrong stops and surfaces it to the human — it does not
  quietly work around the decision or log an assumption over it. Filling a gap the
  record never covered is what `ASSUMPTIONS.md` is for; contradicting the record is not.
- **Rejected alternatives are mandatory, each with the specific reason it lost.** The
  record's job is to prevent re-litigation. Six weeks later the rejected option looks
  attractive again for exactly one reason: the reason it lost has been forgotten. A
  decision recorded without its rejected alternatives is half a decision.
- **Invariants attach to decisions, and every invariant names its catastrophe.**
  "Always use `SET LOCAL` for tenant context" survives only as long as someone remembers
  why. "Always use `SET LOCAL` — a session-level `SET` leaks tenant A's data into tenant
  B's queries" defends itself. An invariant without a named catastrophe gets traded away
  in the first performance discussion.
- **Invariant wording never drifts.** Quote it exactly wherever it is repeated.
  Paraphrases accumulate loopholes one rewording at a time.

## ASSUMPTIONS.md — the log that keeps work moving

Template: `assets/ASSUMPTIONS.md` (includes a worked example).

- The purpose: when a genuine gap appears mid-build and the human isn't there to fill
  it, assume, log, and keep moving — instead of stalling or silently deciding.
- **Check the stop-list before logging.** Some things must never be assumed through.
  Stop and ask the human when the action would: be irreversible or destructive; touch
  production data or environments; change security posture (auth, permissions, tenant
  boundaries, encryption, exposure); incur spend or move money; invalidate a *settled*
  decision; or require a credential the session doesn't legitimately hold. Logging an
  assumption over any of these turns the log into the place bad calls go to be
  forgotten.
- **Blast radius is a required field** — what breaks if the assumption is wrong, how far
  it spreads, how hard it is to undo. It is the triage key: at review time,
  high-blast-radius entries get checked first, and an entry whose blast radius can't be
  stated is a sign the thing shouldn't have been assumed at all.
- **Every entry gets a disposition by session end** — this is what makes the decision
  record living rather than aspirational:
  - **promoted** — it held; write it up as a numbered decision in `DECISIONS.md`.
  - **refuted** — it was wrong; the affected decision reopens (status back to `open`)
    and the entry links to what the build revealed.
  - **carried** — still unresolved; it keeps a named owner and a concrete re-check
    trigger ("first week of production traffic"), because a carried assumption with
    neither is just pending with better branding.
  - Nothing crosses a handoff as `pending`. A write-only assumptions log is where bad
    calls go to be forgotten; the disposition pass is the read that makes writing worth it.

## RUNBOOK — procedures that survive their author

Template: `assets/RUNBOOK.md`. One file per procedure (`RUNBOOK-deploy.md`,
`RUNBOOK-restore.md`). **Read `references/runbook-failure-modes.md` before writing one**
— the template's structure exists to defend against those nine failures, and it only
works if the author knows what each part is for.

The non-negotiables, each defending against a specific failure:

- **Every step is tagged `[YOU]` or `[RUN]`.** Untagged steps get skipped by humans who
  assume automation has them, or waited on by humans who don't realize they're the
  automation.
- **Irreversible warnings come *before* the step they protect**, as their own step, with
  a verification gate. Runbooks are read line by line under stress; a warning below the
  command is read after the damage.
- **Every `[RUN]` step names its expected output and its half-success mode.** Total
  failure is obvious; "3 of 5 migrations applied" is where operators start improvising.
- **Commands are exact.** Placeholders are declared (`<TENANT_ID>`) with where the value
  comes from. "Configure the environment" is a goal, not a step.
- **Rollback section always exists**, even when it says "no rollback past step 4 — that
  is why step 3 is a gate."
- **The final step is a verification** — the named check whose output defines "done."
  Executing `[YOU]` steps is the human's job, always; a session's job ends at writing
  them honestly.

## HANDOFF.md — ending a session without losing it

Template: `assets/HANDOFF.md`.

- **The proven/assumed split is the whole point.** Proven means a check actually ran —
  name the check and what it showed. Everything else is assumed, however confident the
  session feels. Never promote a claim to proven without the check that ran; a handoff
  that inflates certainty poisons the next session's starting assumptions. (Whether a
  given check actually proves the claim is `verification-discipline`'s territory, where
  installed — this document just refuses to blur the two columns.)
- **Next single action, singular.** A list of five next steps forces the next session to
  re-decide priorities with less context than the author had; one concrete action means
  it starts working immediately. Trajectory context can follow, marked as context.
- **Known traps** carry the things that cost this session time and will cost the next
  one too: what looks broken but isn't, what looks fine but isn't, which command is slow
  rather than hung.

## DESIGN.md — the design ledger

Template: `assets/DESIGN.md`.

- **Tokens are resolved values, not intentions.** "Warm neutral" is a direction;
  `#F5F1EB` is a token. The ledger exists so the next session doesn't re-derive — or
  worse, re-invent — what was already settled.
- **Rejected directions are never deleted.** They are the record of why the project
  doesn't go that way; deleting one invites re-litigating the same look next month.
  Same logic as rejected alternatives in `DECISIONS.md`.
- This skill owns the ledger's *schema* only. When to read and append it during UI work
  belongs to the design workflow, and the aesthetic choices themselves belong to the
  design skills (`design-workflow`, `frontend-design`, where installed). The ledger
  records; it does not choose.

## Boundaries

This skill formats records. It does not:

- **Make architectural decisions** — that's the architecture inquiry
  (`architecture-inquiry`, where installed). This skill writes down what that process
  concluded.
- **Make design decisions** — the design skills own those; `DESIGN.md` just holds them.
- **Execute runbook procedures** — `[YOU]` steps belong to the human, unconditionally.
- **Judge whether something is verified** — that's `verification-discipline`'s question.
  This skill only enforces that proven and assumed never share a column.

When a request mixes deciding with recording ("figure out X and write it up"), do the
deciding under whatever skill or judgment owns it, then return here for the write-up.
The templates assume the decision already exists; they have no field for "TBD".
