---
name: project-adoption
description: "Bring an existing codebase under the house standard by reconstructing the record that was never written: mine the schema, config, dependencies, git history, CI, and any surviving docs or chat exports for the decisions already made; write them up as a proper decision record with evidence attached; extract the invariants enforced in the wild with their catastrophes; keep observed, inferred, and unknown strictly separate — a rationale without evidence is recorded as unknown, never invented; and finish with the full artifact set plus a prioritized gap list. Use this whenever adopting, auditing, inheriting, or resuming an existing or legacy project that predates the standard, and whenever the user says anything resembling \"audit this project,\" \"document what we have,\" \"get this repo up to standard,\" or work resumes on a codebase with no decision record."
---

# Project Adoption

Existing projects are full of decisions nobody wrote down. The code remembers *what*
was chosen; nobody remembers *why*; and development stalls or repeats old mistakes
because every session starts from archaeology it never finishes. This skill is that
archaeology, done once, properly: it reconstructs the record an inquiry would have
produced had it happened — so development can continue on the project under the same
standard as new work. It is `architecture-inquiry` run in reverse: instead of
interrogating a human before code exists, interrogate the code that exists, then bring
the human the sharpened gaps.

## Posture

- **Three labels, never blurred.** Every reconstructed fact is exactly one of:
  - **observed** — the evidence says so; cite it (file, schema, commit).
  - **inferred** — consistent with the evidence but unconfirmed; goes to the human.
  - **unknown** — no evidence; recorded as a question, never filled with a guess.

  The whole value of the record is that it can be trusted. One plausible fiction
  presented as fact poisons every future session that reads it — worse than the blank
  it replaced, because a blank at least announces itself.
- **Never invent a rationale.** "Chose Postgres" is observable; *why* is not, unless a
  commit message, doc, or human says so. "Rationale: unknown — no evidence found; ask"
  is an honest, useful entry. A plausible-sounding invented rationale will win future
  arguments it has no right to win.
- **Record what is, not what should be.** Mid-archaeology, the urge to fix and improve
  is constant. Route it: improvements go to the gap list for the human to prioritize,
  never silently into the code, and never into the record as if they'd been decided.
  Adoption that edits the patient mid-autopsy produces neither a record nor a safe change.

## The method

### 1. Mine the evidence before interviewing anyone

Read the repo in reliability order — `references/evidence-sources.md` lists the
sources, what kind of decision hides in each, and how far to trust it. Short version:
the schema is the most honest document in the repo; the README is often the least.

Interview the human *after* the evidence pass, not before. Memory is the least reliable
source, and taken first it anchors the reading of everything else; taken last, the
evidence sharpens the questions and catches the places memory contradicts the code —
which are findings in themselves.

### 2. Reconstruct the decisions

For each load-bearing choice visible in the evidence — database and data model, tenancy,
auth, framework, hosting, queue/jobs, integration points, sync direction — write a
decision entry:

- **What** was chosen: observed, with the evidence cited.
- **When**: from git history, if it's there.
- **Why**: only if evidenced (commit message, old doc, ADR, comment). Otherwise
  `rationale: unknown`, flagged for the interview.
- **Rejected alternatives**: only if evidence shows they were actually considered
  (a reverted migration, a removed dependency, a commented-out path). Recording an
  alternative that was never weighed fabricates history.
- Mark every reconstructed entry `reconstructed` so no future reader mistakes
  archaeology for a decision that had its debate.

Status: `settled` if it still holds and the project builds on it; `open` if the
evidence contradicts current reality (a "temporary" workaround now central, a dependency
abandoned upstream) or the human disputes it on review.

### 3. Extract the invariants enforced in the wild

Unique indexes, foreign keys and their cascade rules, check constraints, auth
middleware, validation layers, idempotency keys, state-transition guards — each is an
invariant somebody once cared about. State each as a quotable rule with its named
catastrophe (the invariant classes in `architecture-inquiry`'s catalog apply here in
reverse, where that skill is installed). Just as important: note where an invariant is
enforced in *one* place but violated or unguarded in another — those go straight to the
gap list.

### 4. Interview the human

Bring the sharpened gaps as a prioritized batch, highest blast radius first, each tied
to the entry it completes: unknown rationales on load-bearing decisions, places memory
is needed to arbitrate between contradictory evidence, and inferred items awaiting
confirmation. "I don't remember" is a legitimate answer — it converts the entry's
rationale to `unknown — confirmed forgotten`, which is still better than fiction,
because it tells the next session to stop digging.

### 5. Produce the artifact set

Write the results into the standard documents — their formats belong to
`project-artifacts` (use its templates where installed; otherwise the same content
under the same headings in plain markdown):

- **DECISIONS.md** — the reconstructed entries.
- **ASSUMPTIONS.md** — every *inferred* item, one entry each, disposition pending the
  human's confirmation.
- **RUNBOOK-deploy.md** — how this project deploys *today*, observed from CI config
  and deploy scripts; unknowns marked, not smoothed over. A legacy project that can't
  be safely deployed isn't adopted yet.
- **DESIGN.md** — only if a real token system or component inventory exists to record.

### 6. Deliver the gap list

The closing deliverable: what the standard expects that this project lacks, prioritized
by risk — unguarded invariants, secrets in code or logs, unverifiable behavior (no way
to tell if it works), undocumented deploy steps, load-bearing externals with no failure
handling, dead code that looks alive. Each gap states its risk and routes somewhere:
a proposed decision for the human, a candidate fix *for the human to schedule*, or an
explicit accepted-risk entry. The gap list is where the fixing urge from Posture goes
to become useful.

## Where this skill stops

- **At the record of what is.** Designing what the system *should become* — the first
  new feature, the migration off the legacy queue — is `architecture-inquiry`'s job
  (where installed), and it starts after adoption ends. Adoption hands it a full record
  to start from.
- **It does not judge the old design.** "This was a bad choice" is not an entry;
  reconstruction stays neutral or the record inherits the reviewer's bias. Adversarial
  review of the design belongs to the `adversary` subagent, where installed.
- **It does not claim anything works.** Adoption may record "deploys green as of
  <date>" as observed, and "untested — no way to verify found" as a gap; declaring
  something *verified* is `verification-discipline`'s bar, where installed.
- **It writes no new production code.** Idiom-matching for future code in this repo is
  `codebase-conventions`' territory (Tier 3); fixes are gap-list items until the human
  schedules them.
- **Document schemas** belong to `project-artifacts`; this skill fills them.
